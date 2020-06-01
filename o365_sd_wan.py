import meraki
import requests
import socket
import argparse
import uuid


# URL to Microsoft Office 365 documentation:
ms_url = 'https://endpoints.office.com/endpoints/worldwide?clientrequestid=' + str(uuid.uuid4())

# Create flags in order to pass mandatory arguments to the script
parser = argparse.ArgumentParser(description='The following input is required: 1. API key, 2. Network ID, 3. Default '
                                             'gateway.')

flags = parser.add_argument_group('Mandatory arguments')
flags.add_argument('-api', '-a', required=True, help='API key')
flags.add_argument('-net', '-n', required=True, help='Network ID')
flags.add_argument('-gw', '-g', required=True, help='Default gateway for the MS Office 365 networks on the VPN Hub')
args = parser.parse_args()

apikey = args.api
network_id = args.net
default_gateway = args.gw

# Create DashboardAPI object
dashboard = meraki.DashboardAPI(api_key=apikey)

def get_static_routes(network_id):
    """
    This function takes in NetworkID, fetches all static routes via API and returns a list of MS Office 365 routes only
    (the routes with a description "O365 - X.X.X.X").
    """
    static_routes = dashboard.mx_static_routes.getNetworkStaticRoutes(network_id)
    existing_o365_subnets = [r['subnet'] for r in static_routes if 'O365' in r['name']]
    print(f"Existing MS Office 365 routes on this VPN Hub (total: {len(existing_o365_subnets)} routes)")
    return existing_o365_subnets


def get_routes_from_microsoft(url):
    """
    This function extracts JSON file from Microsoft website, filters out IP addresses,
    returns the list of unique IP addresses.
    """
    data = requests.get(url).json()
    new_routes = [ip for entry in data for ip in entry.get('ips', [])]
    new_routes_unique = list(set(new_routes))
    return new_routes_unique


def filter_ipv4(input_list):
    """
    This function takes in a list with IPv4 and IPv6, and returns a list with IPv4 only.
    """
    filtered = []
    for e in input_list:
        if is_valid_ipv4_address(e.split('/')[0]):
            filtered.append(e)
    print(f'IPv4 routes from Microsoft website (total: {len(filtered)} routes)')
    return filtered


def is_valid_ipv4_address(address):
    """
    This function verifies IPv4 format.
    """
    try:
        socket.inet_pton(socket.AF_INET, address)
    except AttributeError:  # no inet_pton here, sorry
        try:
            socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3
    except socket.error:  # not a valid address
        return False

    return True


def compare_subnets(li1, li2):
    """
    This function compares two lists and returns the difference.
    """
    return (list(set(li1) - set(li2)))


def route_injector(routes_to_inject):
    """
    This function injects static routes to MX.
    """
    for subnet in routes_to_inject:
        create_static_route = dashboard.mx_static_routes.createNetworkStaticRoute(networkId=network_id,
                                                                                          name=('O365 - ' + subnet.split('/')[0]),
                                                                                          subnet=subnet, gatewayIp=default_gateway)
        create_static_route_subnet = create_static_route['subnet']
        print(f'Successfully added: {create_static_route_subnet}')
    return True


def get_id_to_remove(network_id):
    """
    This function returns a list of StaticRouteIDs to remove
    """
    static_routes = dashboard.mx_static_routes.getNetworkStaticRoutes(networkId=network_id)
    id_to_remove = []
    for i in static_routes:
        if i['subnet'] in subnets_to_remove:
            id_to_remove.append(i['id'])
    return id_to_remove


def route_delete(id_list):
    """
    This function removes outdated static routes.
    """
    for sr in id_list:
        dashboard.mx_static_routes.deleteNetworkStaticRoute(networkId=network_id,
                                                            staticRouteId=sr)
    return print(f'{len(id_list)} outdated routes have been removed!')


def to_advertise_subnets_over_vpn(network_id, o365_routes_existing):
    """
    This function adds O365 routes to VPN.
    """
    advertised_routes_over_vpn = dashboard.networks.getNetworkSiteToSiteVpn(network_id)
    subnet_to_advertise_list = []
    for i in advertised_routes_over_vpn['subnets']:
        if i['useVpn'] == False and i['localSubnet'] in o365_routes_existing:
            i['useVpn'] = True
            subnet_to_advertise_list.append(i)
    dashboard.networks.updateNetworkSiteToSiteVpn(network_id, mode='hub', subnets=subnet_to_advertise_list)
    for i in subnet_to_advertise_list:
        subnet_vpn_on = i['localSubnet']
        print(f'{subnet_vpn_on} has been successfully advertised!')
    return subnet_to_advertise_list



# TODO: Implement logs into a file.
# TODO: Redo printed information (possibly use pprint)
# Fetch static routes from VPN Hub
o365_routes_existing = get_static_routes(network_id)

# Extract JSON file from Microsoft website - tested
all_ms_routes = get_routes_from_microsoft(ms_url)

# IP address function - filters out IPv6 addresses, leave IPv4 only.
o365_routes_website = filter_ipv4(all_ms_routes)

# Items to compare: o365_routes_existing and o365_routes_website.
subnets_to_remove = compare_subnets(o365_routes_existing, o365_routes_website)
print(f'Subnets to remove ({len(subnets_to_remove)}: {subnets_to_remove}')

subnets_to_inject = compare_subnets(o365_routes_website, o365_routes_existing)
print(f'Subnets to inject ({len(subnets_to_inject)}): {subnets_to_inject}')

# Injecting static routes to VPN Hub.
if subnets_to_inject != []:
    route_injector(subnets_to_inject)
else:
    print('Nothing to inject!')

# DELETE outdated static routes
if subnets_to_remove != []:
    id_to_remove = get_id_to_remove(network_id)
    route_delete(id_to_remove)
else:
    print('Nothing to remove!')

# Get existing subnets again (after adding/removing the routes)
o365_routes_existing = get_static_routes(network_id)

# Advertise static routes to VPN
to_advertise_subnets_over_vpn(network_id, o365_routes_existing)
