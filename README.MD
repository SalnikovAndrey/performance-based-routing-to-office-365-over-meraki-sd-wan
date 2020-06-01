# Performance-based routing to MS Office 365 over Cisco Meraki SD-WAN.

## Objective

***What does the script do?***

This script optimises routing to Microsoft Office 365 over Cisco Meraki SD-WAN.

***How does the script do it?***

The script checks MS online documentation, fetches up-to-date routes and automatically injects them into VPN Hub.
As a result, performance-based routing to Office 365 is enabled .

Implementation:
- The script retrieves up-to-date MS Office 365 IP addresses from the official Microsoft online documentation, 
- Compares with currently configured IP addresses, 
- Injects the new routes to Meraki Auto VPN, 
- Deletes outdated routes from Meraki Auto VPN.

![Solution](pics/solution.png)

![Automation](pics/automation.png)

[Presentation](https://drive.google.com/file/d/1qcDZy6B9cohqhohY-DjEE23dpp6GzFXr/view?usp=sharing)

## Installation

'''pip3 install meraki'''

## Usage

This script has to be applied on the VPN Hub (MX has to be in Routed mode).
The script must be executed with the following flags:

1. API Key (-a): 
2. Default gateway (-g):
3. NetworkID (VPN Concentrator) (-n):

python3 o365_sd_wan.py -a {API key} -n {NetworkID} -g {IP address}


	- Get your OrganisationID:
	https://dashboard.meraki.com/api/v0/organizations
	- Get your NetworkID:
	https://dashboard.meraki.com/api/v0/organizations/{OrganisationID}/networks
	
Important note:
The script injects routes with the description "O365 - X.X.X.X". Please, make sure that these descriptions remain unmodified and there are no other descriptions that contain the prefix "O365".

Example:
python3 o365_sd_wan.py -a sdfh&8sdkfj2345234LKJFSDhjsdf -n L_13847134355 -g 192.168.1.1

