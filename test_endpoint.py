#!/usr/bin/env python3
"""Test different ways to access the LINDAS endpoint."""

import requests
import json
import os

# Try to bypass proxy
proxies = {
    'http': None,
    'https': None,
}

endpoint = "https://lindas.admin.ch/query"

# Simple test query
query = """
PREFIX schema: <http://schema.org/>
PREFIX cube: <https://cube.link/>

SELECT *
FROM <https://lindas.admin.ch/elcom/electricityprice>
WHERE {
  ?obs a cube:Observation .
}
LIMIT 5
"""

print("Testing LINDAS endpoint access...")
print(f"Endpoint: {endpoint}")
print(f"\nQuery:\n{query}")

# Try different methods
methods = [
    {
        "name": "POST with form data",
        "method": "POST",
        "data": {'query': query},
        "headers": {
            'Accept': 'application/sparql-results+json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Python-SPARQL-Client/1.0'
        }
    },
    {
        "name": "POST with form data (no proxy)",
        "method": "POST",
        "data": {'query': query},
        "headers": {
            'Accept': 'application/sparql-results+json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Python-SPARQL-Client/1.0'
        },
        "proxies": proxies
    },
    {
        "name": "GET with query param",
        "method": "GET",
        "params": {'query': query},
        "headers": {
            'Accept': 'application/sparql-results+json',
            'User-Agent': 'Mozilla/5.0'
        }
    },
]

for config in methods:
    print(f"\n{'='*70}")
    print(f"Testing: {config['name']}")
    print('='*70)

    try:
        if config['method'] == 'POST':
            response = requests.post(
                endpoint,
                data=config.get('data'),
                headers=config.get('headers'),
                proxies=config.get('proxies', None),
                timeout=30,
                verify=True
            )
        else:
            response = requests.get(
                endpoint,
                params=config.get('params'),
                headers=config.get('headers'),
                proxies=config.get('proxies', None),
                timeout=30,
                verify=True
            )

        print(f"Status: {response.status_code}")
        print(f"Response length: {len(response.text)} bytes")

        if response.status_code == 200:
            print("✓ SUCCESS!")
            try:
                data = response.json()
                print(f"Results: {len(data.get('results', {}).get('bindings', []))} rows")
                print("\nFirst result:")
                print(json.dumps(data.get('results', {}).get('bindings', [])[0] if data.get('results', {}).get('bindings') else {}, indent=2))
            except:
                print("Response (first 500 chars):")
                print(response.text[:500])
        else:
            print(f"✗ FAILED: {response.status_code}")
            print(f"Response: {response.text[:200]}")

    except Exception as e:
        print(f"✗ ERROR: {e}")
