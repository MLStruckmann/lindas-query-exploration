#!/usr/bin/env python3
"""
Swiss Electricity Price Data Extractor

Based on working examples from Zazuko and other Swiss open data projects.
This script extracts electricity price data from the LINDAS SPARQL endpoint.

Endpoint: https://lindas.admin.ch/query
Graph: https://lindas.admin.ch/elcom/electricityprice
Documentation: https://energy.ld.admin.ch/elcom/electricityprice

Note: This script requires network access to lindas.admin.ch
If running from a restricted environment, you may need to run it externally.
"""

import requests
import json
import csv
import time
from typing import Dict, List, Optional
from datetime import datetime


class ElComDataExtractor:
    """Extracts electricity price data from LINDAS SPARQL endpoint."""

    def __init__(self, endpoint: str = "https://lindas.admin.ch/query",
                 graph: str = "https://lindas.admin.ch/elcom/electricityprice"):
        self.endpoint = endpoint
        self.graph = graph
        self.log = []

    def log_message(self, message: str, level: str = "INFO"):
        """Log a message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        self.log.append(log_entry)

    def execute_query(self, query: str, description: str = "") -> Optional[Dict]:
        """Execute SPARQL query with error handling."""
        self.log_message(f"Executing: {description}")

        try:
            response = requests.post(
                self.endpoint,
                data={'query': query},
                headers={
                    'Accept': 'application/sparql-results+json',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': 'Python-ElCom-Extractor/1.0'
                },
                timeout=180
            )

            if response.status_code == 200:
                result = response.json()
                bindings = result.get('results', {}).get('bindings', [])
                self.log_message(f"Success: {len(bindings)} results", "SUCCESS")
                return result
            else:
                self.log_message(f"HTTP {response.status_code}: {response.text[:200]}", "ERROR")
                return None

        except requests.exceptions.Timeout:
            self.log_message(f"Query timeout after 180s", "ERROR")
        except Exception as e:
            self.log_message(f"Exception: {str(e)}", "ERROR")

        return None

    def test_connection(self) -> bool:
        """Test basic connectivity to the endpoint."""
        self.log_message("Testing endpoint connectivity...")

        query = """
        PREFIX cube: <https://cube.link/>

        SELECT (COUNT(*) as ?count)
        FROM <https://lindas.admin.ch/elcom/electricityprice>
        WHERE {
          ?obs a cube:Observation .
        }
        LIMIT 1
        """

        result = self.execute_query(query, "Test connection")
        if result:
            count = result['results']['bindings'][0]['count']['value']
            self.log_message(f"Endpoint accessible - found {count} observations")
            return True
        return False

    def get_sample_data(self, limit: int = 5) -> Optional[List]:
        """Get a small sample to understand the data structure."""
        self.log_message(f"Fetching sample data (limit {limit})...")

        query = f"""
        PREFIX schema: <http://schema.org/>
        PREFIX cube: <https://cube.link/>
        PREFIX elcom: <https://energy.ld.admin.ch/elcom/electricityprice/dimension/>

        SELECT *
        FROM <{self.graph}>
        WHERE {{
          ?obs a cube:Observation ;
               elcom:municipality ?municipality ;
               elcom:operator ?operator ;
               elcom:period ?period ;
               elcom:category ?category ;
               elcom:product ?product ;
               <https://energy.ld.admin.ch/elcom/electricityprice/measure/total> ?total .

          OPTIONAL {{ ?obs <https://energy.ld.admin.ch/elcom/electricityprice/measure/gridusage> ?gridusage . }}
          OPTIONAL {{ ?obs <https://energy.ld.admin.ch/elcom/electricityprice/measure/energy> ?energy . }}
          OPTIONAL {{ ?obs <https://energy.ld.admin.ch/elcom/electricityprice/measure/aidfee> ?aidfee . }}
        }}
        LIMIT {limit}
        """

        result = self.execute_query(query, f"Fetching {limit} sample rows")
        if result:
            return result['results']['bindings']
        return None

    def extract_all_data(self, start_year: str = "2021", end_year: str = "2026") -> Optional[List]:
        """
        Extract comprehensive electricity price data.

        Args:
            start_year: First year to include (e.g., "2021")
            end_year: Last year to include (e.g., "2026")

        Returns:
            List of result bindings, or None if query failed
        """
        self.log_message(f"Extracting all data from {start_year} to {end_year}...")

        query = f"""
        PREFIX schema: <http://schema.org/>
        PREFIX cube: <https://cube.link/>
        PREFIX elcom: <https://energy.ld.admin.ch/elcom/electricityprice/dimension/>
        PREFIX measure: <https://energy.ld.admin.ch/elcom/electricityprice/measure/>

        SELECT
          ?municipality
          ?municipalityLabel
          ?operator
          ?operatorLabel
          ?period
          ?category
          ?categoryLabel
          ?product
          ?productLabel
          ?total
          ?gridusage
          ?energy
          ?aidfee
          ?charge
          ?meteringrate
        FROM <{self.graph}>
        WHERE {{
          ?obs a cube:Observation ;
               elcom:municipality ?municipality ;
               elcom:operator ?operator ;
               elcom:period ?period ;
               elcom:category ?category ;
               elcom:product ?product ;
               measure:total ?total .

          # Optional price components
          OPTIONAL {{ ?obs measure:gridusage ?gridusage . }}
          OPTIONAL {{ ?obs measure:energy ?energy . }}
          OPTIONAL {{ ?obs measure:aidfee ?aidfee . }}
          OPTIONAL {{ ?obs measure:charge ?charge . }}
          OPTIONAL {{ ?obs measure:meteringrate ?meteringrate . }}

          # Get human-readable labels
          OPTIONAL {{ ?municipality schema:name ?municipalityLabel . }}
          OPTIONAL {{ ?operator schema:name ?operatorLabel . }}
          OPTIONAL {{ ?category schema:name ?categoryLabel . }}
          OPTIONAL {{ ?product schema:name ?productLabel . }}

          # Filter by year
          FILTER(?period >= "{start_year}" && ?period <= "{end_year}")
        }}
        ORDER BY ?municipalityLabel ?operatorLabel ?period ?categoryLabel ?productLabel
        """

        result = self.execute_query(query, f"Extracting comprehensive data ({start_year}-{end_year})")
        if result:
            return result['results']['bindings']
        return None

    def save_to_csv(self, bindings: List[Dict], filename: str = "electricity_prices.csv"):
        """Save results to CSV file."""
        if not bindings:
            self.log_message("No data to save", "WARNING")
            return False

        self.log_message(f"Saving {len(bindings)} rows to {filename}...")

        # Extract all unique keys from bindings
        headers = set()
        for binding in bindings:
            headers.update(binding.keys())
        headers = sorted(list(headers))

        # Write CSV
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()

            for binding in bindings:
                row = {k: binding.get(k, {}).get('value', '') for k in headers}
                writer.writerow(row)

        self.log_message(f"Successfully saved {len(bindings)} rows to {filename}", "SUCCESS")
        return True

    def save_query(self, query: str, filename: str = "final_query.sparql"):
        """Save query to file."""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(query)
        self.log_message(f"Query saved to {filename}")

    def save_log(self, filename: str = "extraction_log.txt"):
        """Save log to file."""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("Swiss Electricity Price Data Extraction Log\n")
            f.write("="*70 + "\n\n")
            f.write(f"Endpoint: {self.endpoint}\n")
            f.write(f"Graph: {self.graph}\n")
            f.write("="*70 + "\n\n")

            for entry in self.log:
                f.write(entry + "\n")

        print(f"\n✓ Log saved to {filename}")

    def print_sample_results(self, bindings: List[Dict], limit: int = 3):
        """Print sample results to console."""
        print("\n" + "="*70)
        print("Sample Results")
        print("="*70)

        for i, binding in enumerate(bindings[:limit], 1):
            print(f"\nRow {i}:")
            for key, value in sorted(binding.items()):
                val = value.get('value', '')
                # Truncate long URIs
                if len(val) > 80:
                    val = val[:77] + "..."
                print(f"  {key:20s}: {val}")

    def run(self, start_year: str = "2021", end_year: str = "2026"):
        """Run the complete extraction process."""
        print("\n" + "="*70)
        print("Swiss Electricity Price Data Extractor")
        print("="*70)
        print(f"Endpoint: {self.endpoint}")
        print(f"Graph: {self.graph}")
        print(f"Period: {start_year}-{end_year}")
        print("="*70 + "\n")

        try:
            # Step 1: Test connection
            if not self.test_connection():
                print("\n✗ Cannot connect to endpoint. Please check:")
                print("  - Network connectivity")
                print("  - Firewall/proxy settings")
                print("  - Endpoint availability")
                return False

            # Step 2: Get sample data
            print("\n" + "-"*70)
            sample = self.get_sample_data(limit=3)
            if sample:
                self.print_sample_results(sample)

            # Step 3: Extract all data
            print("\n" + "-"*70)
            data = self.extract_all_data(start_year, end_year)

            if not data:
                print("\n✗ Failed to extract data")
                return False

            # Step 4: Save to CSV
            print("\n" + "-"*70)
            self.save_to_csv(data, "electricity_prices.csv")

            # Step 5: Print statistics
            print("\n" + "="*70)
            print("Extraction Complete!")
            print("="*70)
            print(f"Total rows extracted: {len(data)}")

            # Count unique values
            municipalities = set(b.get('municipality', {}).get('value') for b in data)
            years = set(b.get('period', {}).get('value') for b in data)
            operators = set(b.get('operator', {}).get('value') for b in data)

            print(f"Unique municipalities: {len(municipalities)}")
            print(f"Years: {sorted(years)}")
            print(f"Unique operators: {len(operators)}")

            print("\nGenerated files:")
            print("  ✓ electricity_prices.csv")
            print("  ✓ extraction_log.txt")

            # Save artifacts
            self.save_log()

            return True

        except KeyboardInterrupt:
            print("\n\n⚠ Extraction interrupted by user")
            self.save_log()
            return False
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            self.save_log()
            return False


def main():
    """Main entry point."""
    extractor = ElComDataExtractor()
    success = extractor.run(start_year="2021", end_year="2026")

    if success:
        print("\n✓ Data extraction completed successfully!")
        exit(0)
    else:
        print("\n✗ Data extraction failed. Check extraction_log.txt for details.")
        exit(1)


if __name__ == "__main__":
    main()
