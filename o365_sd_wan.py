import requests
import socket
from meraki_sdk.meraki_sdk_client import MerakiSdkClient
from meraki_sdk.models.create_network_static_route_model import CreateNetworkStaticRouteModel
from meraki_sdk.models.update_network_site_to_site_vpn_model import UpdateNetworkSiteToSiteVpnModel

# Input parameters
# TODO: Re-write using user's input

X_CISCO_MERAKI_API_KEY = input('Please, enter Meraki API key:')
CLIENT = MerakiSdkClient(X_CISCO_MERAKI_API_KEY)
NETWORK_ID = 'L_607985949695027090'
DEFAULT_GATEWAY = "192.168.87.2"
LINK = 'https://endpoints.office.com/endpoints/worldwide?clientrequestid=b10c5ed1-bad1-445f-b386-b919946339a7'


# Define the MXStaticRoutesController
mx_static_routes_controller = CLIENT.mx_static_routes
# Define MX controllers
networks_controller = CLIENT.networks


def get_static_routes(network_id):
    """
    This function takes in NetworkID, fetches all static routes via API and returns a list of MS Office 365 routes only
    (the routes with a description "O365 - X.X.X.X").
    """
    static_routes = mx_static_routes_controller.get_network_static_routes(network_id)
    existing_o365_subnets = []
    for i in static_routes:
        if 'O365' in i['name']:
            existing_o365_subnets.append(i['subnet'])
    return existing_o365_subnets


def get_routes_from_microsoft(link):
    """
    This function extracts JSON file from Microsoft website, filters out IP addresses,
    returns the list of unique IP addresses.
    """
    new_routes = []
    data = requests.get(link).json()

    for i in data:
        if 'ips' in i:
            for l in i['ips']:
                new_routes.append(l)
        else:
            pass
    new_routes_unique = list(set(new_routes))
    # OR (Alternative to above)
    # new_routes_unique = list(dict.fromkeys(new_routes))
    return new_routes_unique


def filter_ipv4(input_list):
    """
    This function takes in a list with IPv4 and IPv6, and returns a list with IPv4 only.
    """
    filtered = []
    for e in input_list:
        if is_valid_ipv4_address(e.split('/')[0]):
            filtered.append(e)

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
    collect = {'network_id': NETWORK_ID}
    for subnet in routes_to_inject:
        create_network_static_route = CreateNetworkStaticRouteModel(name=('O365 - ' + subnet.split('/')[0]),
                                                                    subnet=subnet, gateway_ip=DEFAULT_GATEWAY)
        collect['create_network_static_route'] = create_network_static_route
        result = mx_static_routes_controller.create_network_static_route(collect)
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
    collect['network_id'] = NETWORK_ID
    for sr in id_list:
        sr_id = sr
        collect['sr_id'] = sr_id
        mx_static_routes_controller.delete_network_static_route(collect)
    return print('Deleted!')


def get_advertise_over_vpn_routes(network_id):
    """
    This function returns the list of current static routes in VPN.
    """
    advertised_routes_over_vpn = networks_controller.get_network_site_to_site_vpn(network_id)

    for i in advertised_routes_over_vpn['subnets']:
        if i['localSubnet'] in o365_routes_existing:
            i['useVpn'] = True

    return advertised_routes_over_vpn


def to_advertise_vpn(object_list):
    """
    This function advertises O365 routes over Meraki AutoVPN.
    """
    collect = {}
    collect['network_id'] = NETWORK_ID

    update_network_site_to_site_vpn = UpdateNetworkSiteToSiteVpnModel(mode=object_list['mode'],
                                                                      hubs=object_list['hubs'],
                                                                      subnets=object_list['subnets'])
    collect['update_network_site_to_site_vpn'] = update_network_site_to_site_vpn

    result = networks_controller.update_network_site_to_site_vpn(collect)


# Fetch static routes from VPN Hub

o365_routes_existing = get_static_routes(NETWORK_ID)
print(f"Existing MS Office 365 routes: {o365_routes_existing}")

# Extract JSON file from Microsoft website - tested

all_ms_routes = get_routes_from_microsoft(LINK)
print(f'All routes from Microsoft website (unique): {all_ms_routes}')

# IP address function - filters out IPv6 addresses, leave IPv4 only.

o365_routes_website = filter_ipv4(all_ms_routes)
print(f'IPv4 only routes from Microsift website (unique): {o365_routes_website}')
total_routes = len(filter_ipv4(all_ms_routes))
print(f'Number of routes: {total_routes}')

# Items to compare: o365_routes_existing and o365_routes_website.

subnets_to_remove = compare_subnets(o365_routes_existing, o365_routes_website)
print(f'To remove: {subnets_to_remove}')
subnets_to_inject = compare_subnets(o365_routes_website, o365_routes_existing)
print(f'To inject: {subnets_to_inject}')

# Injecting static routes to VPN Hub.
# POST static routes - tested.

route_injector(subnets_to_inject)

# TODO: return real results if API returns a dict.
# sunbets_injected =
# print(f'Injected: {sunbets_injected}')

# DELETE outdated static routes

id_to_remove = get_id_to_remove(NETWORK_ID)
print(f"ID to remove: {id_to_remove}")

route_delete(id_to_remove)
# TODO: return real results if API returns a dict.
# removed_ids =
# print(f'Deleted: {removed_ids}')

# Advertise static routes to VPN
# Get existing networks again (after adding/removing the routes)

o365_routes_existing = get_static_routes(NETWORK_ID)
print(f"Existing MS Office 365 routes (after adding/removing the routes): {o365_routes_existing}")

to_advertise_over_vpn = get_advertise_over_vpn_routes(NETWORK_ID)
print(f'Routes to advertise: {to_advertise_over_vpn}')

advertised_vpn = to_advertise_vpn(to_advertise_over_vpn)
print(f'Advertised: {advertised_vpn}')