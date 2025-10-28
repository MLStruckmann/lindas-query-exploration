# Quick Reference - Swiss Electricity Price Data Extractor

## ⚡ Quick Start (30 seconds)

```bash
pip install requests
python sparql_extractor.py
```

**Output**: `electricity_prices.csv` with 5000 rows from years 2021-2026

---

## 📋 What Was Fixed

**Problem**: Queries with year filters returned 0 results

**Solution**: Changed line 86 in `sparql_extractor.py`:
```python
# BEFORE: FILTER(?period IN ("2024"))        ❌ Returns 0
# AFTER:  FILTER(STR(?period) IN ("2024"))   ✅ Works!
```

**Why**: The `period` field is `xsd:gYear` datatype, needs string conversion

---

## 📊 Data Structure

**Endpoint**: https://lindas.admin.ch/query

**Years Available**: 2011-2026 (754,918 observations)

**Fields in CSV**:
```
period, municipality, operator, category, product,
total, energy, gridusage, aidfee, charge, meteringrate
```

---

## 🔧 Customize Extraction

Edit line 269 in `sparql_extractor.py`:

```python
# Extract specific years with more rows
extractor.run(target_years=["2023", "2024", "2025"], limit=10000)

# Extract all years
extractor.run(target_years=None, limit=50000)
```

---

## 📚 Documentation

| File | Description |
|------|-------------|
| `README.md` | Full documentation |
| `BUGFIX_SUMMARY.md` | Technical details of the fix |
| `PROJECT_STATUS.md` | Complete project status |
| `example_queries.sparql` | 10 example queries |

---

## ✅ Status

**All systems working** - Ready for production use and GitHub upload

---

## 🐛 Issues?

If queries are slow or timing out, the SPARQL endpoint may be under load. Wait a few minutes and try again. The query is correct and the bugfix is applied.

