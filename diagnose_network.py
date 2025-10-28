#!/usr/bin/env python3
"""
Network Diagnostics for LINDAS SPARQL Endpoint Access

This script helps diagnose why you cannot access the LINDAS endpoint.
Run this before running the data extraction scripts.
"""

import os
import sys
import socket
import requests
from urllib.parse import urlparse


def print_section(title):
    """Print a section header."""
    print("\n" + "="*70)
    print(title)
    print("="*70)


def check_proxy_settings():
    """Check if proxy environment variables are set."""
    print_section("1. Checking Proxy Settings")

    proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'no_proxy', 'NO_PROXY']
    proxies_found = False

    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            proxies_found = True
            print(f"  {var}: {value}")

    if not proxies_found:
        print("  ✓ No proxy environment variables detected")
        return False
    else:
        print("\n  ⚠ WARNING: Proxies detected. These may block LINDAS access.")
        print("  To disable: unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY")
        return True


def check_dns_resolution():
    """Check if lindas.admin.ch can be resolved."""
    print_section("2. Checking DNS Resolution")

    endpoints = [
        'lindas.admin.ch',
        'ld.admin.ch',
        'energy.ld.admin.ch'
    ]

    all_resolved = True
    for endpoint in endpoints:
        try:
            ip = socket.gethostbyname(endpoint)
            print(f"  ✓ {endpoint:25s} → {ip}")
        except socket.gaierror as e:
            print(f"  ✗ {endpoint:25s} → FAILED: {e}")
            all_resolved = False

    return all_resolved


def check_https_connection():
    """Check if HTTPS connection can be established."""
    print_section("3. Checking HTTPS Connection")

    endpoints = [
        'https://lindas.admin.ch',
        'https://ld.admin.ch',
    ]

    all_connected = True
    for endpoint in endpoints:
        try:
            response = requests.head(endpoint, timeout=10, allow_redirects=True)
            print(f"  ✓ {endpoint:40s} → HTTP {response.status_code}")
        except requests.exceptions.SSLError as e:
            print(f"  ✗ {endpoint:40s} → SSL ERROR: {str(e)[:50]}")
            all_connected = False
        except requests.exceptions.ConnectionError as e:
            print(f"  ✗ {endpoint:40s} → CONNECTION ERROR: {str(e)[:50]}")
            all_connected = False
        except Exception as e:
            print(f"  ✗ {endpoint:40s} → ERROR: {str(e)[:50]}")
            all_connected = False

    return all_connected


def test_sparql_endpoint():
    """Test the SPARQL endpoint with a minimal query."""
    print_section("4. Testing SPARQL Endpoint")

    endpoint = "https://lindas.admin.ch/query"
    query = "SELECT * WHERE { ?s ?p ?o } LIMIT 1"

    methods = [
        ("POST with form data", "POST", {'query': query}, {'Accept': 'application/sparql-results+json'}),
        ("GET with query param", "GET", None, {'Accept': 'application/sparql-results+json'}),
    ]

    success = False
    for method_name, method, data, headers in methods:
        print(f"\n  Testing: {method_name}")
        try:
            if method == "POST":
                response = requests.post(endpoint, data=data, headers=headers, timeout=10)
            else:
                response = requests.get(endpoint, params={'query': query}, headers=headers, timeout=10)

            print(f"    Status: {response.status_code}")

            if response.status_code == 200:
                print(f"    ✓ SUCCESS! Endpoint is accessible.")
                try:
                    result = response.json()
                    bindings = result.get('results', {}).get('bindings', [])
                    print(f"    Results: {len(bindings)} rows")
                    success = True
                    break
                except:
                    print(f"    Response: {response.text[:100]}")
            elif response.status_code == 403:
                print(f"    ✗ FORBIDDEN (403): Access denied")
                print(f"    Response: {response.text[:100]}")
            else:
                print(f"    ✗ HTTP {response.status_code}: {response.text[:100]}")

        except requests.exceptions.Timeout:
            print(f"    ✗ TIMEOUT after 10 seconds")
        except Exception as e:
            print(f"    ✗ ERROR: {str(e)[:100]}")

    return success


def test_graph_access():
    """Test access to the electricity price graph."""
    print_section("5. Testing ElCom Graph Access")

    endpoint = "https://lindas.admin.ch/query"
    query = """
    PREFIX cube: <https://cube.link/>

    SELECT (COUNT(*) as ?count)
    FROM <https://lindas.admin.ch/elcom/electricityprice>
    WHERE {
      ?obs a cube:Observation .
    }
    LIMIT 1
    """

    try:
        response = requests.post(
            endpoint,
            data={'query': query},
            headers={'Accept': 'application/sparql-results+json'},
            timeout=30
        )

        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            count = result['results']['bindings'][0]['count']['value']
            print(f"  ✓ SUCCESS! Found {count} observations in the electricity price graph.")
            print(f"  The endpoint is working correctly!")
            return True
        else:
            print(f"  ✗ HTTP {response.status_code}: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"  ✗ ERROR: {str(e)}")
        return False


def provide_recommendations(proxy_detected, dns_ok, https_ok, sparql_ok, graph_ok):
    """Provide recommendations based on test results."""
    print_section("Diagnosis Summary")

    tests = [
        ("DNS Resolution", dns_ok),
        ("HTTPS Connection", https_ok),
        ("SPARQL Endpoint", sparql_ok),
        ("ElCom Graph Access", graph_ok),
    ]

    print("\nTest Results:")
    for test_name, result in tests:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status:8s} {test_name}")

    print("\n" + "-"*70)

    if graph_ok:
        print("\n✓ SUCCESS! You have full access to the LINDAS endpoint.")
        print("\nYou can now run:")
        print("  python3 sparql_elcom_extractor.py")
        return True

    elif sparql_ok and not graph_ok:
        print("\n⚠ PARTIAL ACCESS: SPARQL endpoint works but graph access fails.")
        print("\nPossible causes:")
        print("  - The graph URL is incorrect")
        print("  - The graph requires authentication")
        print("  - Temporary service issue")
        print("\nTry:")
        print("  - Check LINDAS documentation for graph URL changes")
        print("  - Try again later")

    elif https_ok and not sparql_ok:
        print("\n⚠ HTTPS works but SPARQL queries are blocked.")
        print("\nPossible causes:")
        print("  - Proxy is blocking SPARQL queries")
        print("  - WAF/firewall rules")
        print("  - Missing authentication")
        print("\nTry:")
        print("  1. Disable proxy: unset http_proxy https_proxy")
        print("  2. Use different network")
        print("  3. Contact your network administrator")

    elif dns_ok and not https_ok:
        print("\n⚠ DNS works but HTTPS connection fails.")
        print("\nPossible causes:")
        print("  - Firewall blocking HTTPS to lindas.admin.ch")
        print("  - SSL/TLS certificate issues")
        print("  - Network policy restrictions")
        print("\nTry:")
        print("  1. Check firewall settings")
        print("  2. Verify SSL certificates")
        print("  3. Use different network")

    elif not dns_ok:
        print("\n✗ CRITICAL: Cannot resolve lindas.admin.ch DNS.")
        print("\nPossible causes:")
        print("  - Network disconnected")
        print("  - DNS server issues")
        print("  - Hosts file blocking")
        print("\nTry:")
        print("  1. Check internet connection: ping 8.8.8.8")
        print("  2. Check DNS: nslookup lindas.admin.ch")
        print("  3. Try different DNS server")

    if proxy_detected:
        print("\n⚠ PROXY DETECTED!")
        print("\nThe proxy may be blocking access to LINDAS.")
        print("\nTo disable proxy:")
        print("  export http_proxy=")
        print("  export https_proxy=")
        print("  export HTTP_PROXY=")
        print("  export HTTPS_PROXY=")
        print("\nOr run without proxy:")
        print("  env -u http_proxy -u https_proxy python3 sparql_elcom_extractor.py")

    print("\n" + "="*70)
    return False


def main():
    """Run all diagnostic tests."""
    print("\n" + "="*70)
    print("LINDAS SPARQL Endpoint Network Diagnostics")
    print("="*70)
    print("\nThis tool will help diagnose network access issues.")
    print("Running tests...")

    proxy_detected = check_proxy_settings()
    dns_ok = check_dns_resolution()
    https_ok = check_https_connection()
    sparql_ok = test_sparql_endpoint()
    graph_ok = test_graph_access()

    ready = provide_recommendations(proxy_detected, dns_ok, https_ok, sparql_ok, graph_ok)

    if ready:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
