#!/usr/bin/env python3
"""Extract complete electricity price data for each year individually."""

import requests
import csv
from datetime import datetime

class YearlyExtractor:
    """Extracts data year by year."""

    def __init__(self):
        self.endpoint = "https://lindas.admin.ch/query"
        self.graph = "https://lindas.admin.ch/elcom/electricityprice"
        self.years = ["2021", "2022", "2023", "2024", "2025", "2026"]

    def log_message(self, message):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def extract_year(self, year):
        """Extract all data for a specific year."""
        self.log_message(f"Extracting data for year {year}...")
        
        query = f"""
        PREFIX cube: <https://cube.link/>
        
        SELECT 
          ?period 
          ?municipality
          ?operator
          ?category 
          ?product
          ?total 
          ?energy 
          ?gridusage 
          ?aidfee 
          ?charge 
          ?meteringrate
        FROM <{self.graph}>
        WHERE {{
          ?obs a cube:Observation ;
               <https://energy.ld.admin.ch/elcom/electricityprice/dimension/period> ?period ;
               <https://energy.ld.admin.ch/elcom/electricityprice/dimension/total> ?total .
          
          # Optional dimensions
          OPTIONAL {{ ?obs <https://energy.ld.admin.ch/elcom/electricityprice/dimension/municipality> ?municipality . }}
          OPTIONAL {{ ?obs <https://energy.ld.admin.ch/elcom/electricityprice/dimension/operator> ?operator . }}
          OPTIONAL {{ ?obs <https://energy.ld.admin.ch/elcom/electricityprice/dimension/category> ?category . }}
          OPTIONAL {{ ?obs <https://energy.ld.admin.ch/elcom/electricityprice/dimension/product> ?product . }}
          
          # Optional price components
          OPTIONAL {{ ?obs <https://energy.ld.admin.ch/elcom/electricityprice/dimension/energy> ?energy . }}
          OPTIONAL {{ ?obs <https://energy.ld.admin.ch/elcom/electricityprice/dimension/gridusage> ?gridusage . }}
          OPTIONAL {{ ?obs <https://energy.ld.admin.ch/elcom/electricityprice/dimension/aidfee> ?aidfee . }}
          OPTIONAL {{ ?obs <https://energy.ld.admin.ch/elcom/electricityprice/dimension/charge> ?charge . }}
          OPTIONAL {{ ?obs <https://energy.ld.admin.ch/elcom/electricityprice/dimension/meteringrate> ?meteringrate . }}
          
          # Filter for specific year
          FILTER(STR(?period) = "{year}")
        }}
        ORDER BY ?municipality ?operator ?category ?product
        """
        
        try:
            response = requests.post(
                self.endpoint,
                data={'query': query},
                headers={'Accept': 'application/sparql-results+json'},
                timeout=300  # 5 minutes timeout for large queries
            )

            if response.status_code == 200:
                result = response.json()
                bindings = result.get('results', {}).get('bindings', [])
                self.log_message(f"✓ Successfully retrieved {len(bindings)} rows for {year}")
                return bindings
            else:
                self.log_message(f"✗ HTTP {response.status_code}: {response.text[:200]}")
                return None

        except Exception as e:
            self.log_message(f"✗ Error: {str(e)}")
            return None

    def save_to_csv(self, bindings, filename):
        """Save results to CSV."""
        if not bindings:
            self.log_message(f"⚠ No data to save for {filename}")
            return False

        # Extract headers from first binding
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
        """Extract data for all years."""
        print("\n" + "="*70)
        print("Swiss Electricity Price Data - Yearly Extraction")
        print("="*70)
        print(f"Endpoint: {self.endpoint}")
        print(f"Years: {', '.join(self.years)}")
        print("="*70 + "\n")

        total_rows = 0
        successful_years = []
        failed_years = []

        for year in self.years:
            print(f"\n{'='*70}")
            print(f"Processing Year: {year}")
            print(f"{'='*70}")
            
            # Extract data
            data = self.extract_year(year)
            
            if data:
                # Save to CSV
                filename = f"electricity_prices_{year}.csv"
                if self.save_to_csv(data, filename):
                    total_rows += len(data)
                    successful_years.append(year)
                else:
                    failed_years.append(year)
            else:
                failed_years.append(year)
                self.log_message(f"✗ Failed to extract data for {year}")

        # Summary
        print("\n" + "="*70)
        print("EXTRACTION SUMMARY")
        print("="*70)
        print(f"Successfully extracted: {len(successful_years)} years")
        if successful_years:
            print(f"  Years: {', '.join(successful_years)}")
        print(f"Total rows extracted: {total_rows:,}")
        
        if failed_years:
            print(f"\nFailed extractions: {len(failed_years)} years")
            print(f"  Years: {', '.join(failed_years)}")
        
        print("\nGenerated files:")
        for year in successful_years:
            print(f"  ✓ electricity_prices_{year}.csv")
        
        print("="*70)
        
        return len(successful_years) == len(self.years)

def main():
    """Main entry point."""
    extractor = YearlyExtractor()
    success = extractor.run()
    
    if success:
        print("\n✓ All years extracted successfully!")
        return 0
    else:
        print("\n⚠ Some years failed to extract. Check the logs above.")
        return 1

if __name__ == "__main__":
    exit(main())

