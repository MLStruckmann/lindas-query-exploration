#!/usr/bin/env python3
"""Extract lookup tables for municipalities and operators."""

import requests
import csv
from datetime import datetime

class LookupExtractor:
    """Extracts lookup/reference data."""

    def __init__(self):
        self.endpoint = "https://lindas.admin.ch/query"
        self.graph = "https://lindas.admin.ch/elcom/electricityprice"

    def log_message(self, message):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def execute_query(self, query, description):
        """Execute a SPARQL query."""
        self.log_message(f"Executing: {description}")
        
        try:
            response = requests.post(
                self.endpoint,
                data={'query': query},
                headers={'Accept': 'application/sparql-results+json'},
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                bindings = result.get('results', {}).get('bindings', [])
                self.log_message(f"✓ Retrieved {len(bindings)} rows")
                return bindings
            else:
                self.log_message(f"✗ HTTP {response.status_code}: {response.text[:200]}")
                return None

        except Exception as e:
            self.log_message(f"✗ Error: {str(e)}")
            return None

    def get_municipalities(self):
        """Get municipality URI to name mapping."""
        # Note: Municipalities are in a separate graph, so we don't use FROM clause
        query = """
        PREFIX schema: <http://schema.org/>
        
        SELECT DISTINCT ?municipality ?municipalityLabel
        WHERE {
          ?municipality a <https://schema.ld.admin.ch/Municipality> ;
                        schema:name ?municipalityLabel .
        }
        ORDER BY ?municipalityLabel
        """
        
        return self.execute_query(query, "Get municipalities lookup")

    def get_operators(self):
        """Get operator URI to name mapping."""
        query = f"""
        PREFIX schema: <http://schema.org/>
        PREFIX cube: <https://cube.link/>
        
        SELECT DISTINCT ?operator ?operatorLabel
        FROM <{self.graph}>
        WHERE {{
          ?obs a cube:Observation ;
               <https://energy.ld.admin.ch/elcom/electricityprice/dimension/operator> ?operator .
          
          ?operator schema:name ?operatorLabel .
        }}
        ORDER BY ?operatorLabel
        """
        
        return self.execute_query(query, "Get operators lookup")

    def save_to_csv(self, bindings, filename):
        """Save results to CSV."""
        if not bindings:
            self.log_message(f"⚠ No data to save for {filename}")
            return False

        # Extract headers
        headers = sorted(bindings[0].keys())

        # Write CSV
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()

            for binding in bindings:
                row = {k: binding.get(k, {}).get('value', '') for k in headers}
                writer.writerow(row)

        self.log_message(f"✓ Saved {len(bindings)} rows to {filename}")
        return True

    def run(self):
        """Extract all lookup tables."""
        print("\n" + "="*70)
        print("Swiss Electricity Price Data - Lookup Tables Extraction")
        print("="*70)
        print(f"Endpoint: {self.endpoint}")
        print("="*70 + "\n")

        lookups = [
            ("municipalities", self.get_municipalities, "lookup_municipalities.csv"),
            ("operators", self.get_operators, "lookup_operators.csv"),
        ]

        successful = []
        failed = []

        for name, extract_func, filename in lookups:
            print(f"\n{'='*70}")
            print(f"Extracting: {name.title()}")
            print(f"{'='*70}")
            
            data = extract_func()
            
            if data:
                if self.save_to_csv(data, filename):
                    successful.append((name, filename, len(data)))
                else:
                    failed.append(name)
            else:
                failed.append(name)

        # Summary
        print("\n" + "="*70)
        print("EXTRACTION SUMMARY")
        print("="*70)
        print(f"Successfully extracted: {len(successful)} lookup tables")
        
        for name, filename, count in successful:
            print(f"  ✓ {name}: {count} entries → {filename}")
        
        if failed:
            print(f"\nFailed extractions: {', '.join(failed)}")
        
        print("\nGenerated files:")
        for _, filename, _ in successful:
            print(f"  ✓ {filename}")
        
        print("="*70)
        
        return len(successful) == len(lookups)

def main():
    """Main entry point."""
    extractor = LookupExtractor()
    success = extractor.run()
    
    if success:
        print("\n✓ All lookup tables extracted successfully!")
        print("\nYou can now join these lookup tables with your yearly data:")
        print("  - lookup_municipalities.csv: municipality URI → name")
        print("  - lookup_operators.csv: operator URI → name")
        print("\nNote: Categories (H1-H8, C1-C7) and products (standard, cheapest)")
        print("      can be extracted directly from the URI paths.")
        return 0
    else:
        print("\n⚠ Some lookup tables failed to extract.")
        return 1

if __name__ == "__main__":
    exit(main())

