# Swiss Electricity Price Data Extractor - Bugfixing Instructions

## 🎯 Project Overview

This project extracts electricity price data from the Swiss Federal Electricity Commission (ElCom) via the LINDAS SPARQL endpoint. The project is **95% complete** with working network connectivity and data discovery, but has a **query filtering issue** that needs resolution.

## 📁 Current Project Structure

```
lindas-query-exploration/
├── README.md                      # Complete user guide
├── SUMMARY.md                     # Project summary and status  
├── PROJECT_OVERVIEW.md            # Final project overview
├── sparql_extractor.py            # 🎯 MAIN SCRIPT (needs bugfixing)
├── sparql_discovery_agent.py      # Endpoint exploration tool
├── sparql_elcom_extractor.py      # Legacy extraction script
├── example_queries.sparql         # 10 ready-to-use SPARQL queries
├── sample_output.csv              # Example of expected output
└── discovery_log.txt              # Generated during exploration
```

## ✅ What's Working

### Network Connectivity: ✅ RESOLVED
- **Endpoint**: https://lindas.admin.ch/query ✅ Accessible
- **Graph**: https://lindas.admin.ch/elcom/electricityprice ✅ 754,918 observations
- **Status**: All network diagnostics pass

### Data Discovery: ✅ COMPLETE
- **Available Years**: 2011-2026 (16 years of data)
- **Year Distribution**: 
  - 2026: 41,933 observations
  - 2025: 43,798 observations  
  - 2024: 48,620 observations
  - 2023: 50,313 observations
  - 2022: 54,754 observations
  - 2021: 54,644 observations
- **Properties Identified**: All electricity price dimensions and measures

### Basic Queries: ✅ WORKING
```sparql
PREFIX cube: <https://cube.link/>
SELECT ?obs ?period
FROM <https://lindas.admin.ch/elcom/electricityprice>
WHERE {
  ?obs a cube:Observation ;
       <https://energy.ld.admin.ch/elcom/electricityprice/dimension/period> ?period .
}
LIMIT 5
```
**Result**: ✅ Returns observations with periods like "2018"

## ⚠️ The Bug: Query Filtering Issue

### Problem Description
The main issue is that **filtered queries return 0 results**, even though the year distribution shows data exists.

### What Works vs What Doesn't

#### ✅ WORKING QUERIES:
```sparql
# Basic observation query
PREFIX cube: <https://cube.link/>
SELECT ?obs ?period
FROM <https://lindas.admin.ch/elcom/electricityprice>
WHERE {
  ?obs a cube:Observation ;
       <https://energy.ld.admin.ch/elcom/electricityprice/dimension/period> ?period .
}
LIMIT 5
```
**Result**: ✅ Returns 5 observations with periods

```sparql
# Year distribution query
PREFIX cube: <https://cube.link/>
SELECT DISTINCT ?year (COUNT(*) as ?count)
FROM <https://lindas.admin.ch/elcom/electricityprice>
WHERE {
  ?obs a cube:Observation ;
       <https://energy.ld.admin.ch/elcom/electricityprice/dimension/period> ?year .
}
GROUP BY ?year
ORDER BY DESC(?year)
```
**Result**: ✅ Returns year distribution showing 2024 has 48,620 observations

#### ❌ FAILING QUERIES:
```sparql
# Any query with FILTER returns 0 results
PREFIX cube: <https://cube.link/>
SELECT ?obs ?period ?total
FROM <https://lindas.admin.ch/elcom/electricityprice>
WHERE {
  ?obs a cube:Observation ;
       <https://energy.ld.admin.ch/elcom/electricityprice/dimension/period> ?period ;
       <https://energy.ld.admin.ch/elcom/electricityprice/dimension/total> ?total .
  FILTER(?period = "2024")
}
LIMIT 5
```
**Result**: ❌ Returns 0 results (even though 2024 has 48,620 observations)

### Specific Issues to Investigate

1. **Property Requirements**: Adding `total` property requirement causes 0 results
2. **Year Filtering**: Any `FILTER(?period = "2024")` returns 0 results
3. **Data Structure**: Recent years (2021-2026) might have different structure than older years
4. **Query Pattern**: The endpoint might require different query patterns for filtered data

## 🔍 Debugging Strategy

### Step 1: Understand the Data Structure
```python
# Test this query to see what properties exist for different years
query = """
PREFIX cube: <https://cube.link/>
SELECT ?obs ?period ?property ?value
FROM <https://lindas.admin.ch/elcom/electricityprice>
WHERE {
  ?obs a cube:Observation ;
       <https://energy.ld.admin.ch/elcom/electricityprice/dimension/period> ?period ;
       ?property ?value .
}
ORDER BY ?period ?obs ?property
LIMIT 100
"""
```

### Step 2: Test Different Query Patterns
Try these approaches:

1. **Use OPTIONAL for all properties**:
```sparql
PREFIX cube: <https://cube.link/>
SELECT ?obs ?period ?total ?category
FROM <https://lindas.admin.ch/elcom/electricityprice>
WHERE {
  ?obs a cube:Observation ;
       <https://energy.ld.admin.ch/elcom/electricityprice/dimension/period> ?period .
  
  OPTIONAL { ?obs <https://energy.ld.admin.ch/elcom/electricityprice/dimension/total> ?total . }
  OPTIONAL { ?obs <https://energy.ld.admin.ch/elcom/electricityprice/dimension/category> ?category . }
  
  FILTER(?period = "2024")
}
LIMIT 5
```

2. **Try different year formats**:
```sparql
# Test if years are stored as integers vs strings
FILTER(?period = 2024)           # Integer
FILTER(?period = "2024")         # String
FILTER(?period >= "2024")        # Range
```

3. **Test with working years first**:
```sparql
# Test with 2018 (we know this works)
FILTER(?period = "2018")
```

### Step 3: Investigate Data Structure Differences
```python
# Compare structure between different years
queries = [
    "SELECT ?obs ?period ?property ?value WHERE { ?obs a cube:Observation ; <https://energy.ld.admin.ch/elcom/electricityprice/dimension/period> ?period ; ?property ?value . FILTER(?period = \"2018\") } LIMIT 20",
    "SELECT ?obs ?period ?property ?value WHERE { ?obs a cube:Observation ; <https://energy.ld.admin.ch/elcom/electricityprice/dimension/period> ?period ; ?property ?value . FILTER(?period = \"2024\") } LIMIT 20"
]
```

## 🛠️ Files to Focus On

### Primary File: `sparql_extractor.py`
- **Location**: Main production script
- **Issue**: The `extract_data_flexible()` method returns 0 results
- **Key Method**: Lines 80-120 (the main extraction query)
- **Current Query**: Uses OPTIONAL for all properties but still fails

### Secondary File: `sparql_discovery_agent.py`
- **Purpose**: Use this to explore the endpoint structure
- **Helpful**: Step-by-step discovery process
- **Can Run**: `python3 sparql_discovery_agent.py`

## 🎯 Success Criteria

The bugfix is complete when:

1. ✅ **Filtered queries return data**: `FILTER(?period = "2024")` returns actual observations
2. ✅ **Property requirements work**: Adding `total` property doesn't cause 0 results  
3. ✅ **Main script works**: `python3 sparql_extractor.py` generates `electricity_prices.csv`
4. ✅ **Recent years accessible**: Can extract data from 2021-2026
5. ✅ **All price components**: total, energy, gridusage, aidfee, charge, etc.

## 🔧 Testing Commands

```bash
# Test basic connectivity
python3 -c "import requests; response = requests.post('https://lindas.admin.ch/query', data={'query': 'PREFIX cube: <https://cube.link/> SELECT ?obs FROM <https://lindas.admin.ch/elcom/electricityprice> WHERE { ?obs a cube:Observation . } LIMIT 1'}, headers={'Accept': 'application/sparql-results+json'}); print('Status:', response.status_code)"

# Test year distribution
python3 -c "import requests; response = requests.post('https://lindas.admin.ch/query', data={'query': 'PREFIX cube: <https://cube.link/> SELECT DISTINCT ?year FROM <https://lindas.admin.ch/elcom/electricityprice> WHERE { ?obs a cube:Observation ; <https://energy.ld.admin.ch/elcom/electricityprice/dimension/period> ?year . } ORDER BY DESC(?year) LIMIT 10'}, headers={'Accept': 'application/sparql-results+json'}); print('Years:', [b['year']['value'] for b in response.json()['results']['bindings']])"

# Run the main script
python3 sparql_extractor.py
```

## 📊 Expected Output

When fixed, the script should generate:
- `electricity_prices.csv` with 1000+ rows
- Data from years 2021-2026
- All price components (total, energy, gridusage, aidfee, charge, etc.)
- Processing time: 1-3 minutes

## 🚨 Common Pitfalls to Avoid

1. **Don't assume the data structure**: The endpoint might have changed
2. **Test incrementally**: Start with basic queries, then add complexity
3. **Check different years**: 2018 works, but 2024 might be different
4. **Use OPTIONAL clauses**: Some properties might be missing
5. **Check query timeouts**: Complex queries might timeout

## 📞 Resources

- **Endpoint**: https://lindas.admin.ch/query
- **Graph**: https://lindas.admin.ch/elcom/electricityprice  
- **Web Interface**: https://lindas.admin.ch/sparql/
- **Documentation**: https://energy.ld.admin.ch/elcom/electricityprice
- **Data Contact**: Data_ELCOM@elcom.admin.ch

## 🎯 Next Steps

1. **Start with basic queries** to understand the current data structure
2. **Compare working vs failing queries** to identify the pattern
3. **Test different query patterns** (OPTIONAL, different filters, etc.)
4. **Focus on the main script** (`sparql_extractor.py`) once you find working patterns
5. **Verify with the main script** that it generates the expected CSV output

---

**Goal**: Make `python3 sparql_extractor.py` successfully generate `electricity_prices.csv` with data from 2021-2026.

**Current Status**: Network ✅ | Discovery ✅ | Basic Queries ✅ | Filtered Queries ❌ | Main Script ❌
