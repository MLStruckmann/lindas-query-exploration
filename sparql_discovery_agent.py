#!/usr/bin/env python3
"""
SPARQL Discovery Agent for Swiss Electricity Price Data

This script iteratively discovers the structure of the LINDAS SPARQL endpoint
and extracts electricity price data to CSV.
"""

import requests
import json
import csv
import time
from typing import Dict, List, Optional, Any
from datetime import datetime


class SPARQLDiscoveryAgent:
    """Agent that discovers SPARQL endpoint structure and extracts data."""

    def __init__(self, endpoint: str, graph: str):
        self.endpoint = endpoint
        self.graph = graph
        self.log = []
        self.discovered_properties = {}
        self.available_years = []
        self.working_dimensions = []

    def log_step(self, step: str, message: str, success: bool = True):
        """Log a discovery step."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "✓" if success else "✗"
        log_entry = f"[{timestamp}] {status} {step}: {message}"
        print(log_entry)
        self.log.append(log_entry)

    def execute_query(self, query: str, description: str, max_retries: int = 3) -> Optional[Dict]:
        """Execute SPARQL query with error handling and retries."""
        self.log_step("QUERY", f"{description}")

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.endpoint,
                    data={'query': query},
                    headers={
                        'Accept': 'application/sparql-results+json',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    timeout=120
                )

                if response.status_code == 200:
                    result = response.json()
                    bindings = result.get('results', {}).get('bindings', [])
                    self.log_step("SUCCESS", f"{description} - Got {len(bindings)} results", True)
                    return result
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    self.log_step("ERROR", f"{description} - {error_msg}", False)

            except requests.exceptions.Timeout:
                self.log_step("TIMEOUT", f"{description} - Attempt {attempt + 1}/{max_retries}", False)
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

            except Exception as e:
                self.log_step("ERROR", f"{description} - {str(e)}", False)
                break

        return None

    def step1_test_access(self) -> bool:
        """Step 1: Test basic endpoint and graph access."""
        print("\n" + "="*70)
        print("STEP 1: Testing Basic Access")
        print("="*70)

        # Try without FROM clause first (some endpoints prefer GRAPH)
        query1 = f"""
        SELECT (COUNT(*) as ?count)
        WHERE {{
          GRAPH <{self.graph}> {{
            ?s ?p ?o .
          }}
        }}
        LIMIT 1
        """

        result = self.execute_query(query1, "Testing with GRAPH clause")
        if result:
            try:
                count = result['results']['bindings'][0]['count']['value']
                self.log_step("STEP1", f"Graph accessible - contains {count} triples")
                return True
            except:
                pass

        # Try simpler query without any graph specification
        query2 = """
        SELECT (COUNT(*) as ?count)
        WHERE { ?s ?p ?o . }
        LIMIT 1
        """

        result = self.execute_query(query2, "Testing without graph specification")
        if result:
            try:
                count = result['results']['bindings'][0]['count']['value']
                self.log_step("STEP1", f"Endpoint accessible - contains {count} triples")
                return True
            except:
                pass

        # Try just selecting one thing
        query3 = """
        PREFIX cube: <https://cube.link/>
        SELECT ?s
        WHERE { ?s a cube:Observation . }
        LIMIT 1
        """

        result = self.execute_query(query3, "Testing basic observation query")
        if result:
            self.log_step("STEP1", f"Found cube observations")
            return True

        return False

    def step2_discover_properties(self) -> bool:
        """Step 2: Discover all properties used in observations."""
        print("\n" + "="*70)
        print("STEP 2: Discovering Observation Properties")
        print("="*70)

        # Try with GRAPH clause
        query1 = f"""
        PREFIX cube: <https://cube.link/>

        SELECT DISTINCT ?property
        WHERE {{
          GRAPH <{self.graph}> {{
            ?obs a cube:Observation .
            ?obs ?property ?value .
          }}
        }}
        ORDER BY ?property
        LIMIT 100
        """

        result = self.execute_query(query1, "Discovering observation properties with GRAPH")
        if not result:
            # Try without GRAPH clause
            query2 = """
            PREFIX cube: <https://cube.link/>

            SELECT DISTINCT ?property
            WHERE {
              ?obs a cube:Observation .
              ?obs ?property ?value .
            }
            ORDER BY ?property
            LIMIT 100
            """
            result = self.execute_query(query2, "Discovering observation properties without GRAPH")

        if result:
            properties = [b['property']['value'] for b in result['results']['bindings']]
            self.discovered_properties = {p.split('/')[-1]: p for p in properties}

            print(f"\nDiscovered {len(properties)} properties:")
            for prop in properties:
                print(f"  - {prop}")

            self.log_step("STEP2", f"Discovered {len(properties)} properties")
            return True
        return False

    def step3_test_dimensions(self) -> bool:
        """Step 3: Test each dimension to see what's available and required."""
        print("\n" + "="*70)
        print("STEP 3: Testing Individual Dimensions")
        print("="*70)

        # Expected dimensions based on documentation
        test_dimensions = [
            'municipality', 'operator', 'period', 'category', 'product',
            'total', 'gridusage', 'energy', 'aidfee', 'charge', 'meteringrate'
        ]

        base_uri = "https://energy.ld.admin.ch/elcom/electricityprice"

        for dim in test_dimensions:
            # Try different URI patterns
            uri_patterns = [
                f"{base_uri}/dimension/{dim}",
                f"{base_uri}/measure/{dim}",
                f"{base_uri}/{dim}",
            ]

            for uri in uri_patterns:
                query = f"""
                PREFIX cube: <https://cube.link/>

                SELECT (COUNT(*) as ?count)
                WHERE {{
                  GRAPH <{self.graph}> {{
                    ?obs a cube:Observation ;
                         <{uri}> ?value .
                  }}
                }}
                """

                result = self.execute_query(query, f"Testing dimension: {dim} with URI pattern", max_retries=1)
                if result:
                    try:
                        count = int(result['results']['bindings'][0]['count']['value'])
                        if count > 0:
                            self.working_dimensions.append({'name': dim, 'uri': uri, 'count': count})
                            print(f"  ✓ {dim}: {uri} ({count} observations)")
                            break
                    except:
                        pass

        self.log_step("STEP3", f"Found {len(self.working_dimensions)} working dimensions")
        return len(self.working_dimensions) > 0

    def step4_get_years(self) -> bool:
        """Step 4: Discover available years in the dataset."""
        print("\n" + "="*70)
        print("STEP 4: Discovering Available Years")
        print("="*70)

        # Find the period dimension
        period_dim = next((d for d in self.working_dimensions if 'period' in d['name'].lower()), None)

        if not period_dim:
            self.log_step("STEP4", "Could not find period dimension", False)
            return False

        query = f"""
        PREFIX cube: <https://cube.link/>

        SELECT DISTINCT ?year
        WHERE {{
          GRAPH <{self.graph}> {{
            ?obs a cube:Observation ;
                 <{period_dim['uri']}> ?year .
          }}
        }}
        ORDER BY DESC(?year)
        LIMIT 20
        """

        result = self.execute_query(query, "Discovering available years")
        if result:
            years = [b['year']['value'] for b in result['results']['bindings']]
            self.available_years = years

            print(f"\nAvailable years: {', '.join(years)}")
            self.log_step("STEP4", f"Found {len(years)} years: {', '.join(years[:5])}")
            return True
        return False

    def step5_test_simple_query(self) -> bool:
        """Step 5: Test a simple query with a few fields."""
        print("\n" + "="*70)
        print("STEP 5: Testing Simple Query")
        print("="*70)

        # Build a simple query with the first few dimensions
        test_dims = self.working_dimensions[:min(5, len(self.working_dimensions))]

        select_clause = "SELECT DISTINCT"
        where_patterns = []

        for dim in test_dims:
            var_name = dim['name']
            select_clause += f" ?{var_name}"
            where_patterns.append(f"    <{dim['uri']}> ?{var_name} ;")

        # Remove last semicolon
        where_patterns[-1] = where_patterns[-1].rstrip(';') + ' .'

        query = f"""
        PREFIX cube: <https://cube.link/>

        {select_clause}
        WHERE {{
          GRAPH <{self.graph}> {{
            ?obs a cube:Observation ;
{chr(10).join(where_patterns)}
          }}
        }}
        LIMIT 10
        """

        result = self.execute_query(query, "Testing simple query with subset of fields")
        if result:
            bindings = result['results']['bindings']
            print(f"\nSample results ({len(bindings)} rows):")
            if bindings:
                print(json.dumps(bindings[0], indent=2))
            self.log_step("STEP5", f"Simple query successful - got {len(bindings)} sample rows")
            return True
        return False

    def step6_build_comprehensive(self) -> Optional[str]:
        """Step 6: Build comprehensive query with all dimensions and filters."""
        print("\n" + "="*70)
        print("STEP 6: Building Comprehensive Query")
        print("="*70)

        if not self.working_dimensions:
            self.log_step("STEP6", "No working dimensions found", False)
            return None

        # Categorize dimensions into required and optional
        required_dims = []
        optional_dims = []

        for dim in self.working_dimensions:
            name = dim['name']
            # Dimensions like charge and meteringrate might be optional
            if name in ['charge', 'meteringrate']:
                optional_dims.append(dim)
            else:
                required_dims.append(dim)

        # Build SELECT clause
        select_vars = []
        for dim in required_dims + optional_dims:
            select_vars.append(f"?{dim['name']}")
        select_clause = "SELECT " + " ".join(select_vars)

        # Build WHERE clause
        where_patterns = []
        for dim in required_dims:
            where_patterns.append(f"    <{dim['uri']}> ?{dim['name']} ;")

        # Remove last semicolon and add period
        if where_patterns:
            where_patterns[-1] = where_patterns[-1].rstrip(';') + ' .'

        # Add optional patterns (these go inside the GRAPH clause)
        optional_patterns = []
        for dim in optional_dims:
            optional_patterns.append(f"    OPTIONAL {{ ?obs <{dim['uri']}> ?{dim['name']} . }}")

        # Add year filter if we have years
        filter_clause = ""
        if self.available_years:
            period_dim = next((d for d in required_dims if 'period' in d['name'].lower()), None)
            if period_dim:
                # Get years from 2021 onwards
                recent_years = [y for y in self.available_years if y >= "2021"]
                if recent_years:
                    year_list = ", ".join([f'"{y}"' for y in recent_years])
                    filter_clause = f'    FILTER(?{period_dim["name"]} IN ({year_list}))'

        query = f"""
        PREFIX cube: <https://cube.link/>

        {select_clause}
        WHERE {{
          GRAPH <{self.graph}> {{
            ?obs a cube:Observation ;
{chr(10).join(where_patterns)}
{chr(10).join(optional_patterns)}
{filter_clause}
          }}
}}
ORDER BY ?municipality ?operator ?period ?category ?product
"""

        print("\nComprehensive query built:")
        print(query)

        self.log_step("STEP6", "Comprehensive query constructed")
        return query

    def step7_export_csv(self, query: str, filename: str) -> bool:
        """Step 7: Execute comprehensive query and export to CSV."""
        print("\n" + "="*70)
        print("STEP 7: Exporting Data to CSV")
        print("="*70)

        result = self.execute_query(query, "Executing comprehensive query for export")
        if not result:
            return False

        bindings = result['results']['bindings']

        if not bindings:
            self.log_step("STEP7", "No data returned from query", False)
            return False

        # Extract headers from first row
        headers = list(bindings[0].keys())

        # Write to CSV
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()

            for binding in bindings:
                row = {k: v.get('value', '') for k, v in binding.items()}
                writer.writerow(row)

        self.log_step("STEP7", f"Exported {len(bindings)} rows to {filename}")
        print(f"\n✓ Successfully exported {len(bindings)} rows to {filename}")

        # Show sample data
        print(f"\nSample data (first 3 rows):")
        for i, binding in enumerate(bindings[:3]):
            print(f"\nRow {i+1}:")
            for key, value in binding.items():
                print(f"  {key}: {value.get('value', '')}")

        return True

    def save_artifacts(self, final_query: Optional[str]):
        """Save discovery log and final query to files."""
        # Save discovery log
        with open('discovery_log.txt', 'w', encoding='utf-8') as f:
            f.write("SPARQL Discovery Agent Log\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Endpoint: {self.endpoint}\n")
            f.write(f"Graph: {self.graph}\n\n")
            f.write("=" * 70 + "\n\n")

            for entry in self.log:
                f.write(entry + "\n")

            f.write("\n" + "=" * 70 + "\n")
            f.write("Discovery Summary\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"Discovered Properties ({len(self.discovered_properties)}):\n")
            for name, uri in self.discovered_properties.items():
                f.write(f"  - {name}: {uri}\n")

            f.write(f"\nWorking Dimensions ({len(self.working_dimensions)}):\n")
            for dim in self.working_dimensions:
                f.write(f"  - {dim['name']}: {dim['uri']} ({dim['count']} observations)\n")

            f.write(f"\nAvailable Years ({len(self.available_years)}):\n")
            f.write(f"  {', '.join(self.available_years)}\n")

        print("\n✓ Discovery log saved to discovery_log.txt")

        # Save final query
        if final_query:
            with open('final_query.sparql', 'w', encoding='utf-8') as f:
                f.write(final_query)
            print("✓ Final query saved to final_query.sparql")

    def run_discovery(self):
        """Run the complete discovery process."""
        print("\n" + "="*70)
        print("SPARQL Discovery Agent for Swiss Electricity Prices")
        print("="*70)
        print(f"\nEndpoint: {self.endpoint}")
        print(f"Graph: {self.graph}")
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # Step 1: Test access
            if not self.step1_test_access():
                print("\n✗ Failed to access endpoint. Aborting.")
                return

            # Step 2: Discover properties
            if not self.step2_discover_properties():
                print("\n✗ Failed to discover properties. Aborting.")
                return

            # Step 3: Test dimensions
            if not self.step3_test_dimensions():
                print("\n✗ Failed to identify working dimensions. Aborting.")
                return

            # Step 4: Get available years
            self.step4_get_years()  # Non-critical if it fails

            # Step 5: Test simple query
            if not self.step5_test_simple_query():
                print("\n⚠ Warning: Simple query test failed. Continuing anyway...")

            # Step 6: Build comprehensive query
            final_query = self.step6_build_comprehensive()
            if not final_query:
                print("\n✗ Failed to build comprehensive query. Aborting.")
                return

            # Step 7: Export to CSV
            if not self.step7_export_csv(final_query, 'electricity_prices.csv'):
                print("\n✗ Failed to export data to CSV.")
                return

            # Save artifacts
            self.save_artifacts(final_query)

            print("\n" + "="*70)
            print("✓ Discovery Complete!")
            print("="*70)
            print("\nGenerated files:")
            print("  - electricity_prices.csv (extracted data)")
            print("  - final_query.sparql (working SPARQL query)")
            print("  - discovery_log.txt (discovery process log)")

        except KeyboardInterrupt:
            print("\n\n⚠ Discovery interrupted by user")
            self.save_artifacts(None)
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            self.save_artifacts(None)


if __name__ == "__main__":
    agent = SPARQLDiscoveryAgent(
        endpoint="https://lindas.admin.ch/query",
        graph="https://lindas.admin.ch/elcom/electricityprice"
    )
    agent.run_discovery()
