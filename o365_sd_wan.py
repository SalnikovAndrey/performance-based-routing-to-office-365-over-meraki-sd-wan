import requests
import socket
import argparse
import uuid
from meraki_sdk.meraki_sdk_client import MerakiSdkClient
from meraki_sdk.models.create_network_static_route_model import CreateNetworkStaticRouteModel
from meraki_sdk.models.update_network_site_to_site_vpn_model import UpdateNetworkSiteToSiteVpnModel

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

x_cisco_meraki_api_key = args.api
network_id = args.net
default_gateway = args.gw

# Define the MXStaticRoutesController
client = MerakiSdkClient(x_cisco_meraki_api_key)
mx_static_routes_controller = client.mx_static_routes
# Define MX controllers
networks_controller = client.networks


def get_static_routes(network_id):
    """
    This function takes in NetworkID, fetches all static routes via API and returns a list of MS Office 365 routes only
    (the routes with a description "O365 - X.X.X.X").
    """
    static_routes = mx_static_routes_controller.get_network_static_routes(network_id)
    # existing_o365_subnets = filter(lambda i: 'O365' in i['name'], static_routes)
    # existing_o365_subnets = [d['subnet'] for d in existing_o365_subnets]
    existing_o365_subnets = [r['subnet'] for r in static_routes if 'O365' in r['name']]
    print(f"Existing MS Office 365 routes on this VPN Hub (total: {len(existing_o365_subnets)} routes): {existing_o365_subnets}")
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
    print(f'IPv4 routes from Microsoft website (total: {len(filtered)} routes): {filtered}')
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
    collect = {'network_id': network_id}
    for subnet in routes_to_inject:
        create_network_static_route = CreateNetworkStaticRouteModel(name=('O365 - ' + subnet.split('/')[0]),
                                                                    subnet=subnet, gateway_ip=default_gateway)
        collect['create_network_static_route'] = create_network_static_route
        result = mx_static_routes_controller.create_network_static_route(collect)
        print(f'Successfully added: {result}')
    return True


def get_id_to_remove(network_id):
    """
    This function returns a list of StaticRouteIDs to remove
    """
    static_routes = mx_static_routes_controller.get_network_static_routes(network_id)
    id_to_remove = []
    for i in static_routes:
        if i['subnet'] in subnets_to_remove:
            id_to_remove.append(i['id'])
    return id_to_remove


def route_delete(id_list):
    """
    This function removes outdated static routes.
    """
    collect = {}
    collect['network_id'] = network_id
    for sr in id_list:
        sr_id = sr
        collect['sr_id'] = sr_id
        mx_static_routes_controller.delete_network_static_route(collect)
    return print(f'{len(id_list)} outdated routes have been removed!')


def get_advertised_over_vpn_routes(network_id):
    """
    This function returns the list of current static routes in VPN.
    """
    advertised_routes_over_vpn = networks_controller.get_network_site_to_site_vpn(network_id)

    for i in advertised_routes_over_vpn['subnets']:
        if i['localSubnet'] in o365_routes_existing:
            i['useVpn'] = True
    print(f'Routes to advertise over VPN: {advertised_routes_over_vpn}')
    return advertised_routes_over_vpn


def to_advertise_vpn(object_list):
    """
    This function advertises O365 routes over Meraki AutoVPN.
    """
    collect = {}
    collect['network_id'] = network_id

    update_network_site_to_site_vpn = UpdateNetworkSiteToSiteVpnModel(mode=object_list['mode'],
                                                                      hubs=object_list['hubs'],
                                                                      subnets=object_list['subnets'])
    collect['update_network_site_to_site_vpn'] = update_network_site_to_site_vpn
    networks_controller.update_network_site_to_site_vpn(collect)
    print('MS Office 365 routes have been successfully advertised!')

# TODO: Run the script continuously.
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

# Advertise static routes to VPN
# Get existing subnets again (after adding/removing the routes)
o365_routes_existing = get_static_routes(network_id)

# TODO Advertise only routes with 'useVpn': False. If the list is empty, pass. Same as above for adding/removing routes
to_advertise_over_vpn = get_advertised_over_vpn_routes(network_id)
# print(f'Routes to advertise: {to_advertise_over_vpn}')

advertised_vpn = to_advertise_vpn(to_advertise_over_vpn)
# print(f'Advertised: {advertised_vpn}')