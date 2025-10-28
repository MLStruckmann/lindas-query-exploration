# Swiss Electricity Price Data Extractor

Extracts electricity price data from the Swiss Federal Electricity Commission (ElCom) via the LINDAS SPARQL endpoint.

## Quick Start

```bash
# Install dependencies
pip install requests

# Run the main extractor
python3 sparql_extractor.py
```

This will create:
- `electricity_prices.csv` - Extracted data
- `extraction_log.txt` - Execution log

## Data Source

- **Endpoint**: https://lindas.admin.ch/query
- **Graph**: https://lindas.admin.ch/elcom/electricityprice
- **Documentation**: https://energy.ld.admin.ch/elcom/electricityprice
- **Web Interface**: https://lindas.admin.ch/sparql/

## What Data is Extracted

The script extracts electricity prices for all Swiss municipalities with:

### Dimensions
- **Municipality**: Swiss municipality (commune)
- **Operator**: Electricity provider
- **Period**: Year (2021-2026 by default)
- **Category**: Consumption category (H1-H7 for households, C1-C7 for commercial)
- **Product**: Product type (standard, cheapest, etc.)

### Price Components (in Rp./kWh)
- **total**: Total electricity price
- **gridusage**: Network usage fee (Netznutzung)
- **energy**: Energy cost (Energie)
- **aidfee**: Network surcharge (Netzzuschlag gem. Art. 35 EnG)
- **charge**: Municipal charges (Abgaben an Gemeinwesen)
- **meteringrate**: Metering fee (Messtarif)

## Scripts Included

### 1. `sparql_extractor.py` (Main Script)

Production-ready script for extracting Swiss electricity price data.

**Features**:
- Automatic year discovery
- Flexible property handling
- Comprehensive error handling
- Progress logging
- CSV export with all price components

**Usage**:
```bash
python3 sparql_extractor.py
```

**Customization**:
```python
extractor = FinalElComExtractor()
extractor.run(target_years=["2021", "2022", "2023"], limit=1000)
```

### 2. `sparql_discovery_agent.py`

Iterative discovery agent that explores the endpoint structure step-by-step.

**Features**:
- Discovers available properties
- Tests different query patterns
- Adapts to endpoint responses
- Detailed discovery logging

**Usage**:
```bash
python3 sparql_discovery_agent.py
```

### 3. `sparql_elcom_extractor.py` (Legacy)

Original extraction script based on working examples from Swiss open data projects.

## Manual Testing

### Test 1: Web Interface

Visit https://lindas.admin.ch/sparql/ and run:

```sparql
PREFIX cube: <https://cube.link/>

SELECT *
FROM <https://lindas.admin.ch/elcom/electricityprice>
WHERE {
  ?obs a cube:Observation .
}
LIMIT 5
```

### Test 2: Command Line (curl)

```bash
curl -X POST "https://lindas.admin.ch/query" \
  -H "Accept: application/sparql-results+json" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "query=PREFIX cube: <https://cube.link/>
SELECT * WHERE { ?obs a cube:Observation . } LIMIT 1"
```

### Test 3: Simple Python

```python
import requests

query = """
PREFIX cube: <https://cube.link/>
SELECT * WHERE { ?obs a cube:Observation . } LIMIT 1
"""

response = requests.post(
    "https://lindas.admin.ch/query",
    data={'query': query},
    headers={'Accept': 'application/sparql-results+json'}
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

## Example Queries

### Get Sample Observations

```sparql
PREFIX schema: <http://schema.org/>
PREFIX cube: <https://cube.link/>
PREFIX elcom: <https://energy.ld.admin.ch/elcom/electricityprice/dimension/>

SELECT *
FROM <https://lindas.admin.ch/elcom/electricityprice>
WHERE {
  ?obs a cube:Observation ;
       elcom:municipality ?municipality ;
       elcom:operator ?operator ;
       elcom:period ?period ;
       elcom:category ?category ;
       elcom:product ?product ;
       <https://energy.ld.admin.ch/elcom/electricityprice/measure/total> ?total .
}
LIMIT 10
```

### Get Prices for Specific Year

```sparql
PREFIX cube: <https://cube.link/>
PREFIX elcom: <https://energy.ld.admin.ch/elcom/electricityprice/dimension/>
PREFIX measure: <https://energy.ld.admin.ch/elcom/electricityprice/measure/>

SELECT ?municipality ?operator ?total ?gridusage ?energy
FROM <https://lindas.admin.ch/elcom/electricityprice>
WHERE {
  ?obs a cube:Observation ;
       elcom:municipality ?municipality ;
       elcom:operator ?operator ;
       elcom:period "2024" ;
       measure:total ?total ;
       measure:gridusage ?gridusage ;
       measure:energy ?energy .
}
LIMIT 100
```

### Get Prices with Labels

```sparql
PREFIX schema: <http://schema.org/>
PREFIX cube: <https://cube.link/>
PREFIX elcom: <https://energy.ld.admin.ch/elcom/electricityprice/dimension/>
PREFIX measure: <https://energy.ld.admin.ch/elcom/electricityprice/measure/>

SELECT ?municipalityLabel ?operatorLabel ?period ?total
FROM <https://lindas.admin.ch/elcom/electricityprice>
WHERE {
  ?obs a cube:Observation ;
       elcom:municipality ?municipality ;
       elcom:operator ?operator ;
       elcom:period ?period ;
       measure:total ?total .

  ?municipality schema:name ?municipalityLabel .
  ?operator schema:name ?operatorLabel .

  FILTER(?period >= "2023")
}
ORDER BY ?municipalityLabel ?period
LIMIT 100
```

## Expected Output

### Sample CSV Structure

```csv
municipality,municipalityLabel,operator,operatorLabel,period,category,categoryLabel,product,productLabel,total,gridusage,energy,aidfee,charge,meteringrate
https://ld.admin.ch/municipality/1,"Aeugst am Albis",https://energy.ld.admin.ch/elcom/electricityprice/operator/123,"EKZ",2024,https://energy.ld.admin.ch/elcom/electricityprice/category/H4,"H4 (5000 kWh/year)",https://energy.ld.admin.ch/elcom/electricityprice/product/standard,"Standard",21.35,7.82,10.13,2.30,0.85,0.25
```

### Expected Data Volume

- **Municipalities**: ~2,000 Swiss communes
- **Years**: 2021-2026 (6 years)
- **Categories**: ~14 (H1-H7, C1-C7)
- **Products**: ~3 per category
- **Estimated rows**: 100,000-500,000

### Typical Price Ranges

- **Total**: 10-40 Rp./kWh
- **Grid usage**: 5-15 Rp./kWh
- **Energy**: 5-15 Rp./kWh
- **Aid fee**: 1-3 Rp./kWh

## Troubleshooting

### 403 Access Denied

```
HTTP 403: Access denied
```

**Causes**:
- Proxy blocking the endpoint
- Firewall restrictions
- VPN interference

**Solutions**:
1. Check proxy settings: `env | grep -i proxy`
2. Temporarily disable proxy: `unset http_proxy https_proxy`
3. Use a different network
4. Try from outside the restricted environment

### Connection Timeout

```
Query timeout after 180s
```

**Solutions**:
1. Reduce the year range
2. Add more specific filters
3. Use LIMIT clause
4. Try during off-peak hours

### Empty Results

**Solutions**:
1. Check if years exist: Run discovery script
2. Verify property URIs are correct
3. Test with minimal query first
4. Check LINDAS documentation for updates

## References

- **LINDAS Platform**: https://lindas.admin.ch/
- **ElCom Open Data**: https://www.elcom.admin.ch/elcom/en/home/themen/strompreise.html
- **Zazuko Examples**: https://github.com/zazuko/notebooks
- **Swiss Open Data**: https://opendata.swiss/en/dataset

## Contact

For questions about the data:
- Email: Data_ELCOM@elcom.admin.ch

For issues with this script:
- Check the extraction_log.txt file
- Try the test scripts individually
- Verify network access to lindas.admin.ch

## License

This extraction tool is provided as-is. The electricity price data is published by ElCom under Swiss open data guidelines.
