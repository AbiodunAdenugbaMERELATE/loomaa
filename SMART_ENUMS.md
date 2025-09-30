# Smart Enums: Making Loomaa User-Friendly

## Before: Error-Prone String Usage ❌

```python
# Easy to make mistakes:
Column("amount", "Currency", ...)      # Is it "Currency" or "currency"?  
Column("date", "DateTime", ...)        # "DateTime" or "dateTime"?
Table(mode="Import", ...)              # "Import" or "import"?
Relationship(..., cardinality="Many-to-One")  # So many variations!
```

## After: Smart Enums ✅

```python
from loomaa.model import DataTypes, TableMode, Cardinality, CrossFilter

# Impossible to get wrong:
Column("amount", DataTypes.CURRENCY, ...)     # IDE shows all options!
Column("date", DataTypes.DATETIME, ...)       # Crystal clear
Table(mode=TableMode.IMPORT, ...)             # Self-documenting  
Relationship(..., cardinality=Cardinality.MANY_TO_ONE)  # Perfect!
```

## Available Enums

### DataTypes
```python
DataTypes.TEXT          # → "string"
DataTypes.STRING        # → "string" (alias)
DataTypes.INTEGER       # → "int64"
DataTypes.INT          # → "int64" (alias)
DataTypes.CURRENCY     # → "decimal"
DataTypes.DECIMAL      # → "decimal" (alias)
DataTypes.DATETIME     # → "dateTime"
DataTypes.DATE         # → "dateTime" (alias)
DataTypes.BOOLEAN      # → "boolean"
DataTypes.DOUBLE       # → "double"
```

### TableMode
```python
TableMode.IMPORT        # → "Import"
TableMode.DIRECTLAKE    # → "DirectLake"
```

### Cardinality
```python
Cardinality.MANY_TO_ONE   # → "manyToOne"
Cardinality.ONE_TO_MANY   # → "oneToMany"
Cardinality.ONE_TO_ONE    # → "oneToOne"
Cardinality.MANY_TO_MANY  # → "manyToMany"
```

### CrossFilter
```python
CrossFilter.SINGLE         # → "oneDirection"
CrossFilter.ONE_DIRECTION  # → "oneDirection" (alias)
CrossFilter.BOTH          # → "bothDirections"
CrossFilter.BOTH_DIRECTIONS # → "bothDirections" (alias)
CrossFilter.NONE          # → "none"
```

## Benefits

✅ **IDE Autocomplete** - See all valid options as you type  
✅ **No Typos** - Impossible to misspell enum values  
✅ **Self-Documenting** - Code intent is crystal clear  
✅ **Error Prevention** - Catch mistakes at development time  
✅ **Backward Compatible** - Old string-based code still works  

## Example Usage

```python
from loomaa.model import *

# Create table with smart enums
sales_table = Table(
    name="Sales",
    mode=TableMode.DIRECTLAKE,  # Live lakehouse data
    source_query="lakehouse.sales_fact"
)

# Add columns with type safety
sales_table.add_column(Column("revenue", DataTypes.CURRENCY, "Sale amount"))
sales_table.add_column(Column("customer_id", DataTypes.INTEGER, "Customer key"))
sales_table.add_column(Column("sale_date", DataTypes.DATETIME, "Transaction date"))

# Create relationships with clear intent
customer_rel = Relationship(
    from_table="Sales",
    from_column="customer_id",
    to_table="Customer",
    to_column="customer_id", 
    cardinality=Cardinality.MANY_TO_ONE,
    cross_filter_direction=CrossFilter.BOTH
)
```

**Result: Clean, readable, error-proof semantic model development!** 🚀