Readme.md

# Performance-based routing to MS Office 365 over Cisco Meraki SD-WAN.

Cisco Meraki SD-WAN solution supports a performance-based routing over Meraki AutoVPN but not over the Internet uplinks. 
This script makes it possible to enable performance-based routing to MS Office 365 via Meraki SD-WAN. 

Implementation:

- The script retreives up-to-date MS Office 365 IP addresses from the official Microsoft online documentation, 
- Compares with currently configured IP addresses, 
- Injects the new routes to Meraki Auto VPN, 
- Deletes outdated routes from Meraki Auto VPN.

The diagram that expains a use case is located below. 
TODO: Create a diagram.

## Installation

pip install meraki_sdk

## Usage

This script will apply changes on the VPN Hub in VPN concentrator mode (the only supported mode).

These are the parameters that you need to feed the script with:

1. API Key;
2. Dafault gateway;
3. Network ID (VPN Concentrator):
	- Get your OrganisationID:
	https://dashboard.meraki.com/api/v0/organizations

	- Get your NetworkID:
	https://dashboard.meraki.com/api/v0/organizations/{OrganisationID}/networks

Important note:

The script injects routes with the description "O365 - X.X.X.X". It is important to make sure that these descriptions are not modified and there are no other descriptions contain the prefix "O365"

## History

TODO: Write history

## License

TODO: Write license