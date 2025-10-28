#!/usr/bin/env python3
"""Working Swiss Electricity Price Data Extractor - Final Version."""

import requests
import json
import csv
from datetime import datetime

class FinalElComExtractor:
    """Final working extractor based on actual data structure."""

    def __init__(self):
        self.endpoint = "https://lindas.admin.ch/query"
        self.graph = "https://lindas.admin.ch/elcom/electricityprice"
        self.log = []

    def log_message(self, message, level="INFO"):
        """Log a message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        self.log.append(log_entry)

    def execute_query(self, query, description=""):
        """Execute SPARQL query."""
        self.log_message(f"Executing: {description}")

        try:
            response = requests.post(
                self.endpoint,
                data={'query': query},
                headers={'Accept': 'application/sparql-results+json'},
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

        except Exception as e:
            self.log_message(f"Exception: {str(e)}", "ERROR")
            return None

    def get_available_years(self):
        """Get years that actually have data."""
        query = """
        PREFIX cube: <https://cube.link/>
        SELECT DISTINCT ?year (COUNT(*) as ?count)
        FROM <https://lindas.admin.ch/elcom/electricityprice>
        WHERE {
          ?obs a cube:Observation ;
               <https://energy.ld.admin.ch/elcom/electricityprice/dimension/period> ?year .
        }
        GROUP BY ?year
        ORDER BY DESC(?year)
        """
        
        result = self.execute_query(query, "Get available years with counts")
        if result:
            years_data = []
            for binding in result['results']['bindings']:
                year = binding['year']['value']
                count = int(binding['count']['value'])
                years_data.append({'year': year, 'count': count})
            
            print(f"\nAvailable years:")
            for data in years_data:
                print(f"  {data['year']}: {data['count']} observations")
            
            return years_data
        return []

    def extract_data_flexible(self, years=None, limit=None):
        """Extract data with flexible property requirements."""
        
        # Build year filter
        # Note: period is stored as xsd:gYear, so we need to convert to string
        year_filter = ""
        if years:
            year_list = ", ".join([f'"{y}"' for y in years])
            year_filter = f"FILTER(STR(?period) IN ({year_list}))"
        
        # Build limit clause
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        query = f"""
        PREFIX cube: <https://cube.link/>
        
        SELECT 
          ?obs
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
          ?annualmeteringcost
        FROM <https://lindas.admin.ch/elcom/electricityprice>
        WHERE {{
          ?obs a cube:Observation ;
               <https://energy.ld.admin.ch/elcom/electricityprice/dimension/period> ?period ;
               <https://energy.ld.admin.ch/elcom/electricityprice/dimension/total> ?total .
          
          # Optional dimensions - keep query fast by not fetching labels
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
          OPTIONAL {{ ?obs <https://energy.ld.admin.ch/elcom/electricityprice/dimension/annualmeteringcost> ?annualmeteringcost . }}
          
          {year_filter}
        }}
        ORDER BY ?period ?municipality ?category ?product
        {limit_clause}
        """
        
        result = self.execute_query(query, f"Extract data with flexible properties")
        if result:
            return result['results']['bindings']
        return []

    def save_to_csv(self, bindings, filename="electricity_prices.csv"):
        """Save results to CSV."""
        if not bindings:
            self.log_message("No data to save", "WARNING")
            return False

        self.log_message(f"Saving {len(bindings)} rows to {filename}...")

        # Extract headers
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

    def save_log(self, filename="extraction_log.txt"):
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

    def run(self, target_years=None, limit=1000):
        """Run the extraction process."""
        print("\n" + "="*70)
        print("Final Swiss Electricity Price Data Extractor")
        print("="*70)
        print(f"Endpoint: {self.endpoint}")
        print(f"Graph: {self.graph}")
        print("="*70 + "\n")

        try:
            # Step 1: Get available years
            print("Step 1: Discovering available years...")
            years_data = self.get_available_years()
            
            if not years_data:
                print("✗ Could not get year information")
                return False

            # Step 2: Determine which years to extract
            if target_years:
                available_years = [y['year'] for y in years_data]
                valid_years = [y for y in target_years if y in available_years]
                print(f"\nTarget years: {target_years}")
                print(f"Available years: {available_years}")
                print(f"Valid years to extract: {valid_years}")
                
                if not valid_years:
                    print("✗ None of the target years are available")
                    return False
            else:
                # Use all available years
                valid_years = [y['year'] for y in years_data]
                print(f"\nExtracting all available years: {valid_years}")

            # Step 3: Extract data
            print(f"\nStep 2: Extracting data for years: {valid_years}")
            print(f"Limit: {limit} rows")
            
            data = self.extract_data_flexible(years=valid_years, limit=limit)

            if not data:
                print("✗ Failed to extract data")
                return False

            # Step 4: Save to CSV
            print(f"\nStep 3: Saving data to CSV...")
            self.save_to_csv(data, "electricity_prices.csv")

            # Step 5: Print statistics
            print("\n" + "="*70)
            print("Extraction Complete!")
            print("="*70)
            print(f"Total rows extracted: {len(data)}")

            # Count unique values
            periods = set(b.get('period', {}).get('value') for b in data)
            categories = set(b.get('category', {}).get('value') for b in data if b.get('category'))
            products = set(b.get('product', {}).get('value') for b in data if b.get('product'))

            print(f"Years in data: {sorted(periods)}")
            print(f"Unique categories: {len(categories)}")
            print(f"Unique products: {len(products)}")

            # Show sample data
            print(f"\nSample data (first 3 rows):")
            for i, binding in enumerate(data[:3]):
                print(f"\nRow {i+1}:")
                for key, value in binding.items():
                    val = value.get('value', '')
                    if len(val) > 80:
                        val = val[:77] + "..."
                    print(f"  {key}: {val}")

            print("\nGenerated files:")
            print("  ✓ electricity_prices.csv")
            print("  ✓ extraction_log.txt")

            # Save artifacts
            self.save_log()

            return True

        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            self.save_log()
            return False

def main():
    """Main entry point."""
    extractor = FinalElComExtractor()
    
    # Extract data with a reasonable limit first
    success = extractor.run(target_years=["2021", "2022", "2023", "2024", "2025", "2026"], limit=5000)

    if success:
        print("\n✓ Data extraction completed successfully!")
        exit(0)
    else:
        print("\n✗ Data extraction failed. Check extraction_log.txt for details.")
        exit(1)

if __name__ == "__main__":
    main()
