\# Loomaa

Semantic Model as Code for Microsoft Fabric / Power BI.

Loomaa provides an end-to-end workflow:

- `loomaa init` – scaffold an example project
- `loomaa compile` – generate a Fabric/PBIP `.SemanticModel` (TMDL)
- `loomaa view` – local interactive model viewer (Streamlit)
- `loomaa deploy` – deploy to a Fabric workspace via REST API

## Install

End users:

```bash
pip install loomaa
```

## Quickstart

Create a new project:

```bash
loomaa init my-model
cd my-model
```

Fill in `.env` (created by `init`) with your Fabric IDs:

- `FABRIC_TENANT_ID`
- `FABRIC_CLIENT_ID`
- `FABRIC_CLIENT_SECRET`
- `FABRIC_WORKSPACE_ID`
- `FABRIC_DIRECTLAKE_ITEM_ID`
- `FABRIC_SQL_SERVER`
- `FABRIC_SQL_DATABASE`

Compile the model:

```bash
loomaa compile
```

View the model locally:

```bash
loomaa view
```

Deploy to Fabric:

```bash
loomaa deploy
```

## Output

After `loomaa compile`, output is written under `compiled/`:

- `compiled/<model>/model.json` – viewer-friendly JSON
- `compiled/<model>/<model>.SemanticModel/` – Fabric/PBIP semantic model artifact

## Repository Layout

This repository uses a standard Python layout:

- `setup.py` / `requirements.txt` live in this folder
- `loomaa/` (package code) contains the CLI, compiler, deploy, and viewer
- `tests/` contains automated tests

## Contributing

Pull requests are welcome. See CONTRIBUTING for the full guide:

- CONTRIBUTING.md

### Dev setup

```bash
python -m venv .venv
\# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
pytest -q
```

### Notes

- Do not commit `.env` (it contains secrets)
- Generated artifacts like `compiled/`, `test_compiled/`, and `*.egg-info/` should not be committed
)

customer_table.add_column(Column("CustomerID", "Integer", "Primary key", is_key=True))
customer_table.add_column(Column("CustomerName", "Text", "Customer name"))
customer_table.add_column(Column("City", "Text", "Customer city"))
customer_table.add_column(Column("Region", "Text", "Sales region"))
customer_table.add_column(Column("Country", "Text", "Customer country"))

model.add_table(customer_table)

# Product dimension  
product_table = Table(
    name="Product",
    mode="Import",
    description="Product master data",
    source_query="SELECT * FROM dim_product"
)

product_table.add_column(Column("ProductID", "Integer", "Primary key", is_key=True))
product_table.add_column(Column("ProductName", "Text", "Product name"))
product_table.add_column(Column("Category", "Text", "Product category"))
product_table.add_column(Column("Subcategory", "Text", "Product subcategory"))
product_table.add_column(Column("UnitPrice", "Currency", "List price"))

model.add_table(product_table)
```

### Defining Relationships

```python
# Create relationships between tables
customer_rel = Relationship(
    from_table="Sales",
    from_column="CustomerID", 
    to_table="Customer",
    to_column="CustomerID",
    cardinality="Many-to-One",
    cross_filter_direction="Single"
)
model.add_relationship(customer_rel)

product_rel = Relationship(
    from_table="Sales",
    from_column="ProductID",
    to_table="Product", 
    to_column="ProductID",
    cardinality="Many-to-One"
)
model.add_relationship(product_rel)
```

### Creating Hierarchies for Drill-Down

```python
from loomaa.model import Hierarchy

# Geographic hierarchy
geo_hierarchy = Hierarchy(
    name="Geography",
    levels=["Country", "Region", "City"],
    description="Geographic drill-down path"
)
customer_table.hierarchies = [geo_hierarchy]

# Product hierarchy
product_hierarchy = Hierarchy(
    name="Product Breakdown", 
    levels=["Category", "Subcategory", "ProductName"],
    description="Product classification drill-down"
)
product_table.hierarchies = [product_hierarchy]

model.add_hierarchy(geo_hierarchy)
model.add_hierarchy(product_hierarchy)
```

### Adding Model-Level Measures

```python
# Complex DAX measures at model level
avg_order_value = Measure(
    name="Average Order Value",
    expression="""
    AVERAGEX(
        VALUES(Sales[SalesID]),
        [Total Sales]
    )""",
    description="Average value per order",
    format_string="$#,##0.00"
)

customer_count = Measure(
    name="Customer Count",
    expression="DISTINCTCOUNT(Sales[CustomerID])",
    description="Number of unique customers"
)

# Time intelligence measures
sales_ly = Measure(
    name="Sales Last Year",
    expression="CALCULATE([Total Sales], SAMEPERIODLASTYEAR('Calendar'[Date]))",
    description="Sales for same period last year"
)

model.add_measure(avg_order_value)
model.add_measure(customer_count)  
model.add_measure(sales_ly)
```

### Row-Level Security (Optional)

```python
from loomaa.model import Role

# Create role with data filtering
sales_role = Role(
    name="Sales Team", 
    description="Access to assigned region data only"
)
sales_role.add_table_permission("Sales", "[Region] = USERNAME()")
sales_role.add_table_permission("Customer", "[Region] = USERNAME()")

admin_role = Role(
    name="Admin",
    description="Full data access"  
)
# Admin role has no filters = full access

model.add_role(sales_role)
model.add_role(admin_role)
```

### Complete Model Function

```python
def build_import_model():
    """Complete Import mode semantic model"""
    model = SemanticModel(name="Sales Import Model")
    
    # Add all tables, relationships, measures, hierarchies
    # ... (code from above sections)
    
    return model

# Export for Loomaa compiler
models = {
    "sales_import": build_import_model()
}
```

### Generated Output

When you run `loomaa compile`, you get production-ready Power BI files:

```
compiled/
├── sales_import.SemanticModel/          # Power BI Project structure
│   ├── definition.pbism                 # Model metadata
│   ├── .platform                       # Platform info
│   └── definition/
│       ├── database.tmdl                # Database settings
│       ├── model.tmdl                   # Model configuration  
│       ├── relationships.tmdl           # All relationships
│       ├── tables/
│       │   ├── Sales.tmdl              # Individual table definitions
│       │   ├── Customer.tmdl
│       │   └── Product.tmdl
│       ├── cultures/
│       │   └── en-US.tmdl              # Localization
│       └── roles/                       # Row-level security (if defined)
│           ├── Sales Team.tmdl
│           └── Admin.tmdl
└── sales_import_legacy/                 # Backward compatibility
    ├── model.tmdl                       # Single file format
    └── model.json                       # JSON representation
```

This structure can be opened directly in Power BI Desktop or deployed to Power BI Service via XMLA endpoints.

**Next Stage: DirectLake Mode** - Stage 2 will add native Fabric lakehouse/warehouse integration for real-time analytics without data import.

## Core Semantic Modeling Elements

Loomaa supports the 4 fundamental elements of semantic modeling:

1. **📊 Tables** - Data sources (fact and dimension tables)
2. **🔗 Relationships** - How tables connect to each other  
3. **📏 Measures** - Business calculations and KPIs
4. **🏗️ Hierarchies** - Drill-down paths for analysis

Each element is defined in Python with full metadata support.

## Data Connection Patterns

### Fabric Warehouse/Lakehouse (Same Workspace)
```python
# DirectLake - fastest for Fabric data
sales_table = Table(
    name="Sales",
    source_query="fact_sales",  # Just table name
    mode="DirectLake",
    description="Sales data from Fabric warehouse"
)

# Import mode - copy data into model
customer_table = Table(
    name="Customer",
    source_query="SELECT * FROM dim_customer WHERE is_active = 1",
    mode="Import"
)
```

### Cross-Workspace or External Sources
```python
# Import from external SQL Server
external_table = Table(
    name="External Data",
    source_query="SELECT * FROM external_db.fact_table",
    mode="Import",
    connection_string="Data Source=server.database.windows.net;Initial Catalog=db;"
)
```

### CSV Files (Development/Testing)
```python
# CSV files in models/examples/ directory
csv_table = Table(
    name="Sample Data",
    source_query="sample_data.csv",
    mode="Import"  # CSV files are always Import
)
```

**Authentication Notes:**
- Uses **Azure AD tokens** (no SQL usernames/passwords)
- **DirectLake** requires **Fabric Premium/F64+ capacity**

## Advanced Features

### Jinja2 Templating for DAX

Loomaa supports Jinja2 templating for dynamic DAX generation:

```python
from jinja2 import Template

# Reusable time intelligence pattern
ytd_template = Template('''
TOTALYTD(
    [{{base_measure}}],
    {{date_table}}[Date]
)
''')

# Generate YTD measure
sales_ytd = Measure(
    name="Sales YTD",
    expression=ytd_template.render(
        base_measure="Total Sales",
        date_table="'Calendar'"
    )
)
```

### Advanced Relationship Patterns

Define relationships with comprehensive metadata:

```python
model.add_relationship(
    Relationship(
        from_table="Sales",
        from_column="CustomerID",
        to_table="Customer", 
        to_column="CustomerID",
        cardinality="Many-to-One",
        cross_filter_direction="Single",
        description="Sales to Customer lookup relationship"
    )
)
```

### Hierarchies for Drill-Down Analysis

Define drill-down hierarchies for dimensional analysis:

```python
# Product hierarchy for category drill-down
product_hierarchy = Hierarchy(
    name="Product Hierarchy",
    levels=["Category", "Brand", "ProductName"],
    description="Product category to brand to product drill-down"
)
model.add_hierarchy(product_hierarchy)

# Geographic hierarchy for location analysis
geo_hierarchy = Hierarchy(
    name="Geography",
    levels=["Country", "City"],
    description="Geographic drill-down from country to city"
)
model.add_hierarchy(geo_hierarchy)
```

### Calculated Columns and Tables

```python
# Calculated column
profit_margin = CalculatedColumn(
    name="Profit Margin %",
    expression="DIVIDE([Revenue] - [Cost], [Revenue], 0)",
    format_string="0.00%",
    description="Calculated profit margin percentage"
)

# Calculated table (for complex aggregations)
monthly_summary = CalculatedTable(
    name="Monthly Summary",
    expression='''
    SUMMARIZE(
        Sales,
        'Calendar'[Year],
        'Calendar'[Month],
        "Total Sales", SUM(Sales[SalesAmount]),
        "Order Count", DISTINCTCOUNT(Sales[OrderID])
    )
    '''
)
```

## Command Reference

| Command | Description |
|---------|-------------|
| `loomaa init <project>` | Initialize new semantic model project |
| `loomaa compile` | Build model artifacts (TMDL & JSON) |
| `loomaa view` | Launch interactive model viewer |
| `loomaa validate` | Check model integrity & DAX validation |
| `loomaa deploy` | Deploy model to Power BI Service |
| `loomaa template <name>` | Generate from predefined templates |

## Best Practices

### Semantic Modeling
- **Descriptive Names**: Use clear, business-friendly names for all objects
- **Documentation**: Add descriptions to tables, columns, and measures
- **Folder Organization**: Group measures logically using folders
- **Format Strings**: Apply appropriate formatting for currencies, percentages, etc.
- **Relationships**: Define proper cardinality and cross-filter directions

### DAX Development
- **Use Jinja Templates**: For reusable DAX patterns and complex logic
- **Variable Usage**: Use VAR statements for readable, maintainable DAX
- **Context Transition**: Be explicit about filter context in calculations
- **Error Handling**: Use DIVIDE() instead of / to handle division by zero

### Development Workflow
1. **Design First**: Plan your model structure before coding
2. **Incremental Build**: Build and test incrementally
3. **Local Testing**: Use `loomaa view` to verify before deployment
4. **Version Control**: Track changes in your semantic model code

## Troubleshooting

### Authentication Issues
- Verify your Azure AD app registration has proper permissions
- Check that XMLA endpoint is enabled in Power BI Admin Portal
- Ensure workspace is in Premium/Fabric capacity

### Compilation Errors
- Run `loomaa validate` to check for syntax errors
- Verify all referenced columns exist in their respective tables
- Check DAX syntax using Power BI Desktop first

### Deployment Issues
- Confirm target workspace exists and you have edit permissions
- Check network connectivity to Power BI Service
- Verify XMLA endpoint URL format is correct

## Contributing

This semantic model follows Loomaa conventions for maintainable, scalable Power BI models. 
When adding new measures or tables, please:

1. Add comprehensive descriptions
2. Use appropriate formatting
3. Organize measures into logical folders
4. Test locally before deploying
5. Document any complex business logic