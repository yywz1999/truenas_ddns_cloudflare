import requests
import ipaddress
import subprocess
import re

def get_ipv6_addresses(interface):
    result = subprocess.run(['ip', '-6', 'addr', 'show', interface], stdout=subprocess.PIPE, text=True)
    output = result.stdout
    inet6_groups = re.split(r'\n\s*inet6', output)
    ipv6_addresses = []
    for group in inet6_groups[1:]:
        if 'forever' not in group:
            match = re.search(r'([0-9a-f:]+/[0-9]+)', group)
            if match:
                ipv6_addresses.append(match.group(1))
    ipv6_address = ipv6_addresses[0]
    return ipv6_address.split('/')[0]

def update_ipv6_record(zone_name, subdomain, new_ipv6, api_key):
    try:
        ip = ipaddress.IPv6Address(new_ipv6)
    except ipaddress.AddressValueError:
        raise ValueError(f"Invalid IPv6 address: {new_ipv6}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Fetch zone identifier
    zone_response = requests.get(
        f"https://api.cloudflare.com/client/v4/zones?name={zone_name}", headers=headers
    )

    if zone_response.status_code != 200:
        raise Exception(f"Failed to fetch zone data: {zone_response.status_code}, {zone_response.text}")

    zone_data = zone_response.json()
    if not zone_data.get("success") or not zone_data["result"]:
        raise Exception(f"No zones found for the given domain: {zone_name}")

    zone_identifier = zone_data["result"][0]["id"]

    # Fetch DNS records
    dns_response = requests.get(
        f"https://api.cloudflare.com/client/v4/zones/{zone_identifier}/dns_records", headers=headers
    )

    if dns_response.status_code != 200:
        raise Exception(f"Failed to fetch DNS records: {dns_response.status_code}, {dns_response.text}")

    dns_data = dns_response.json()
    if not dns_data.get("success"):
        raise Exception(f"Cloudflare API error: {dns_data}")

    dns_records = dns_data.get("result", [])

    # Find the AAAA record for the subdomain
    record_to_update = None
    for record in dns_records:
        if record["type"] == "AAAA" and record["name"] == f"{subdomain}.{zone_name}":
            record_to_update = record
            break

    if not record_to_update:
        raise Exception(f"No AAAA record found for {subdomain}.{zone_name}")

    # Update the AAAA record
    update_data = {
        "type": "AAAA",
        "name": f"{subdomain}.{zone_name}",
        "content": new_ipv6,
        "ttl": record_to_update["ttl"],
        "proxied": record_to_update["proxied"]
    }

    update_response = requests.put(
        f"https://api.cloudflare.com/client/v4/zones/{zone_identifier}/dns_records/{record_to_update['id']}",
        headers=headers,
        json=update_data
    )

    if update_response.status_code != 200:
        raise Exception(f"Failed to update DNS record: {update_response.status_code}, {update_response.text}")

    update_result = update_response.json()
    if not update_result.get("success"):
        raise Exception(f"Failed to update DNS record: {update_result}")

    return update_result

if __name__ == "__main__":
    try:
        interface = 'eno1'
        new_ipv6 = get_ipv6_addresses(interface)
        zone_name = "xxx.com" #根域名
        subdomain = "truenas" #子域名
        api_key = "xxxxx-x"

        result = update_ipv6_record(zone_name, subdomain, new_ipv6, api_key)
        print("DNS record updated successfully:", result)
    except Exception as e:
        print(f"Error: {e}")
