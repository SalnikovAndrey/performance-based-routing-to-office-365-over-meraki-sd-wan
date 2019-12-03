import requests
import socket
from pprint import pprint
from meraki_sdk.meraki_sdk_client import MerakiSdkClient
from meraki_sdk.models.create_network_static_route_model import CreateNetworkStaticRouteModel
from meraki_sdk.models.update_network_site_to_site_vpn_model import UpdateNetworkSiteToSiteVpnModel

x_cisco_meraki_api_key = ''
client = MerakiSdkClient(x_cisco_meraki_api_key)
network_id = 'L_607985949695027090'
default_gateway = "192.168.87.2"

# Fetch static routes and create a list of existing routes.
# Define the MXStaticRoutesController

mx_static_routes_controller = client.mx_static_routes

# Fetch static routes from VPN Hub
# This function call API, gets all static routes, and returns a list of the routes with a description "O365 - X.X.X.X".


def get_static_routes(network_id):  # best name for the arguments? Shall the name overlap?
    static_routes = mx_static_routes_controller.get_network_static_routes(network_id)
    existing_o365_subnets = []
    for i in static_routes:
        if 'O365' in i['name']:
            existing_o365_subnets.append(i['subnet'])
    return existing_o365_subnets


print("Existing MS Office 365 routes")
o365_routes_existing = get_static_routes(network_id)
print(o365_routes_existing)

# Extract JSON file from Microsoft website - tested TODO: re-write as a function

link = 'https://endpoints.office.com/endpoints/worldwide?clientrequestid=b10c5ed1-bad1-445f-b386-b919946339a7'


def get_routes_from_microsoft(link):
    new_routes = []
    data = requests.get(link).json()

    for i in data:
        if 'ips' in i:
            for l in i['ips']:
                new_routes.append(l)
        else:
            pass
    new_routes_unique = list(set(new_routes))
    return new_routes_unique

print('All routes from Microsift website (unique):')
all_ms_routes = get_routes_from_microsoft(link)
print(all_ms_routes)

# new_routes_unique = list(set(new_routes))
# OR (Alternative to above)
# new_routes_unique = list(dict.fromkeys(new_routes))

# IP address function - filters out IPv6 addresses, leave IPv4 only.


def filter_ipv4(input_list):
    filtered = []
    for e in input_list:
        if is_valid_ipv4_address(e.split('/')[0]) == True:
            filtered.append(e)

    return filtered


def is_valid_ipv4_address(address):
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


print('IPv4 only routes from Microsift website (unique):')
o365_routes_website = filter_ipv4(all_ms_routes)
print(o365_routes_website)
print('Number of routes:')
total_routes = len(filter_ipv4(all_ms_routes))
print(total_routes)

# Compare lists
# Items to compare: new_routes_unique_ipv4 and existing_routes. TODO: re-write as a function


def compare_subnets(li1, li2):
    return (list(set(li1) - set(li2)))


print('To remove:')
subnets_to_remove = compare_subnets(o365_routes_existing, o365_routes_website)
print(subnets_to_remove)

print('To inject:')
subnets_to_inject = compare_subnets(o365_routes_website, o365_routes_existing)
print(subnets_to_inject)


# Injecting static routes to VPN Hub - tested.

def route_injector(routes_to_inject):
    collect = {}
    collect['network_id'] = network_id
    for subnet in routes_to_inject:
        create_network_static_route = CreateNetworkStaticRouteModel(name=('O365 - ' + subnet.split('/')[0]),
                                                                    subnet=subnet, gateway_ip=default_gateway)
        collect['create_network_static_route'] = create_network_static_route
        result = mx_static_routes_controller.create_network_static_route(collect)
    return True


# POST static routes - tested.
route_injector(subnets_to_inject)
# TODO: return real results
print('Injected!')
print(subnets_to_inject)

# DELETE static routes

def get_id_to_remove(network_id):
    static_routes = mx_static_routes_controller.get_network_static_routes(network_id)
    id_to_remove = []
    for i in static_routes:
        if i['subnet'] in subnets_to_remove:
            id_to_remove.append(i['id'])
    return id_to_remove

print("ID to remove:")
id_to_remove = get_id_to_remove(network_id)
print(id_to_remove)


def route_delete(id_list):

    collect = {}
    collect['network_id'] = network_id
    for sr in id_list:
        sr_id = sr
        collect['sr_id'] = sr_id
        mx_static_routes_controller.delete_network_static_route(collect)
    return print('Deleted!')


route_delete(id_to_remove)
print('Deleted!')
print(id_to_remove)

# Advertise static routes to VPN
# Define controllers

networks_controller = client.networks

# Get existing networks again (after adding/removing the routes)
print("Existing MS Office 365 routes (after adding/removing the routes)")
o365_routes_existing = get_static_routes(network_id)
print(o365_routes_existing)

def get_advertise_over_vpn_routes(network_id):

    advertised_routes_over_vpn = networks_controller.get_network_site_to_site_vpn(network_id)

    for i in advertised_routes_over_vpn['subnets']:
        if i['localSubnet'] in o365_routes_existing:
            i['useVpn'] = True

    return advertised_routes_over_vpn

to_advertise_over_vpn = get_advertise_over_vpn_routes(network_id)
print('Routes to advertise: ')
print(to_advertise_over_vpn)


def to_advertise_vpn(object_list):

    collect = {}
    collect['network_id'] = network_id

    update_network_site_to_site_vpn = UpdateNetworkSiteToSiteVpnModel(mode=object_list['mode'],
                                                                      hubs=object_list['hubs'],
                                                                      subnets=object_list['subnets'])
    collect['update_network_site_to_site_vpn'] = update_network_site_to_site_vpn

    result = networks_controller.update_network_site_to_site_vpn(collect)


print('After applying the function to_advertise_vpn: ')
to_advertise_vpn(to_advertise_over_vpn)


