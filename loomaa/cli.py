"""
Loomaa CLI - Semantic Model as Code for Power BI
Simple, focused CLI for semantic modeling without complex bootstrapping
"""
import os
import sys
import json
import textwrap
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional

import typer

from loomaa.compiler import compile_model
from loomaa.deploy import (
    deploy_complete_semantic_model,
)
from loomaa.utils import write_file, log
from loomaa.validate import validate_model

# Initialize Typer CLI app
app = typer.Typer(help="Loomaa CLI - Semantic Model as Code for Power BI")

# Simple templates for realistic semantic modeling
ENV_TEMPLATE = """# Microsoft Fabric Authentication
FABRIC_TENANT_ID=your-azure-tenant-id
FABRIC_CLIENT_ID=your-service-principal-client-id
FABRIC_CLIENT_SECRET=your-client-secret
FABRIC_WORKSPACE_ID=your-power-bi-workspace-id
FABRIC_XMLA_ENDPOINT=powerbi://api.powerbi.com/v1.0/myorg/your-workspace-name
"""

# Main model definition file for enterprise multi-model structure
MODEL_MAIN_TEMPLATE = '''from models.examples.tables import create_sales_table, create_customer_table, create_product_table
from models.examples.relationships import define_relationships
from models.examples.measures import add_model_measures
from loomaa.model import SemanticModel

def build_examples_model():
    """Build the examples semantic model (sample)"""
    
    # Create semantic model
    model = SemanticModel(name="Examples_Model")
    
    # Add tables (store references for relationships)
    sales_table = create_sales_table()
    customer_table = create_customer_table()
    product_table = create_product_table()
    
    model.add_table(sales_table)
    model.add_table(customer_table)
    model.add_table(product_table)
    
    # Define relationships (separate file for clarity)
    define_relationships(model)
    
    # Add model-level measures (separate file for organization)
    add_model_measures(model)
    
    return model

# Available models in this project
models = {
    "examples": build_examples_model()
}
'''

# Table definitions supporting both Import and DirectLake modes
TABLES_TEMPLATE = '''from loomaa.model import Table, Column, Measure, DataTypes, TableMode

"""
Table Definitions - Learning Examples
Shows DirectLake (live) and Import (cached) table patterns with explicit connections

🔑 DirectLake Resource IDs:
   - Get lakehouse ID: Fabric portal > your lakehouse > Settings > Properties 
   - Get warehouse ID: Fabric portal > your warehouse > Settings > Properties
   - Replace "your-lakehouse-or-warehouse-id-here" with the actual GUID

🔗 Import SQL Server Connections:
   - Get server name: Azure portal > your SQL database > Overview > Server name
   - Format: "your-server-name.database.windows.net"
   - Replace "your-sql-server-name.database.windows.net" with actual server

📊 Table Mode Guide:
   - DirectLake: Live connection, real-time data, no calculated columns
   - Import: Cached data, supports calculated columns and enrichments
"""

def create_sales_table():
    """Sales fact table - DirectLake Mode with live lakehouse/warehouse connection"""
    sales_table = Table(
        name="Sales",
        mode=TableMode.DIRECTLAKE,  # 🚀 Live lakehouse/warehouse data
        description="Real-time sales transactions from lakehouse",
        source_query="dbo.sales_fact",  # schema.table format
        directlake_resource_id="your-lakehouse-or-warehouse-id-here"  # 🔑 Replace with actual GUID
    )
    
    # Define columns that exist in your lakehouse table
    sales_table.add_column(Column("SalesID", DataTypes.INTEGER, "Unique sale identifier"))
    sales_table.add_column(Column("CustomerID", DataTypes.INTEGER, "Customer reference"))
    sales_table.add_column(Column("ProductID", DataTypes.INTEGER, "Product reference"))
    sales_table.add_column(Column("OrderDate", DataTypes.DATETIME, "Sale date"))
    sales_table.add_column(Column("Revenue", DataTypes.CURRENCY, "Sale amount", format_string="$#,##0.00"))
    sales_table.add_column(Column("Quantity", DataTypes.INTEGER, "Items sold"))
    sales_table.add_column(Column("Region", DataTypes.TEXT, "Sales region"))
    
    # Add table-level measures (works with DirectLake)
    total_sales = Measure(
        name="Total Sales",
        expression="SUM(Sales[Revenue])",
        description="Sum of all sales revenue",
        format_string="$#,##0"
    )
    sales_table.add_measure(total_sales)
    
    avg_order_value = Measure(
        name="Average Order Value",
        expression="DIVIDE(SUM(Sales[Revenue]), DISTINCTCOUNT(Sales[SalesID]))",
        description="Average revenue per order",
        format_string="$#,##0.00"
    )
    sales_table.add_measure(avg_order_value)
    
    sales_table.add_measure(total_sales)
    
    return sales_table

def create_customer_table():
    """Customer dimension table - Import Mode with explicit SQL server"""
    customer_table = Table(
        name="Customer",
        mode=TableMode.IMPORT,  # 📊 Traditional import for dimensions
        description="Customer master data with enrichments",
        source_query="SELECT * FROM your_warehouse.dim_customer",  # Update with your SQL
        sql_server="your-sql-server-name.database.windows.net"  # 🔗 Replace with actual server name
    )
    
    # Define columns from your dimension table
    customer_table.add_column(Column("CustomerID", DataTypes.INTEGER, "Primary key"))
    customer_table.add_column(Column("CustomerName", DataTypes.TEXT, "Customer name"))
    customer_table.add_column(Column("City", DataTypes.TEXT, "Customer city"))
    customer_table.add_column(Column("Region", DataTypes.TEXT, "Sales region"))
    customer_table.add_column(Column("Country", DataTypes.TEXT, "Customer country"))
    customer_table.add_column(Column("Segment", DataTypes.TEXT, "Customer segment"))
    
    return customer_table

def create_product_table():
    """Product dimension table - Import Mode with explicit SQL server"""
    product_table = Table(
        name="Product",
        mode=TableMode.IMPORT,  # 📊 Import mode for SQL data
        description="Product master data from SQL warehouse",
        source_query="SELECT * FROM warehouse.dim_product",  # Update with your SQL
        sql_server="your-sql-server-name.database.windows.net"  # 🔗 Replace with actual server name
    )
    
    # Define columns from your SQL table
    product_table.add_column(Column("ProductID", DataTypes.INTEGER, "Primary key"))
    product_table.add_column(Column("ProductName", DataTypes.TEXT, "Product name"))
    product_table.add_column(Column("Category", DataTypes.TEXT, "Product category"))
    product_table.add_column(Column("Brand", DataTypes.TEXT, "Product brand"))
    product_table.add_column(Column("UnitPrice", DataTypes.CURRENCY, "List price", format_string="$#,##0.00"))
    
    return product_table
'''

RELATIONSHIPS_TEMPLATE = '''from loomaa.model import Relationship

def define_relationships(model):
    """Define all model relationships in one place"""
    
    # Sales to Customer (Many-to-One)
    model.add_relationship(
        Relationship(
            from_table="Sales",
            from_column="CustomerID",
            to_table="Customer",
            to_column="CustomerID",
            cardinality="Many-to-One",
            cross_filter_direction="Single",
            description="Sales transactions to customer lookup"
        )
    )
    
    # Sales to Product (Many-to-One)
    model.add_relationship(
        Relationship(
            from_table="Sales",
            from_column="ProductID",
            to_table="Product",
            to_column="ProductID",
            cardinality="Many-to-One",
            cross_filter_direction="Single",
            description="Sales transactions to product lookup"
        )
    )
'''

MEASURES_TEMPLATE = '''from loomaa.model import Measure
from jinja2 import Template

def add_model_measures(model):
    """Add model-level measures (not tied to specific tables)"""
    
    # Complex calculated measures using Jinja for maintainability
    ratio_template = Template("""
    DIVIDE(
        [{{numerator}}],
        [{{denominator}}],
        0
    )""")
    
    # Sales per Customer
    model.add_measure(
        Measure(
            name="Sales per Customer",
            expression=ratio_template.render(
                numerator="Total Sales",
                denominator="Customer Count"
            ),
            description="Average sales amount per customer",
            format_string="$#,##0.00",
            folder="Calculated KPIs"
        )
    )
    
    # Average Order Value
    model.add_measure(
        Measure(
            name="Average Order Value",
            expression="DIVIDE([Total Sales], DISTINCTCOUNT(Sales[SalesOrderID]), 0)",
            description="Average revenue per order",
            format_string="$#,##0.00",
            folder="Calculated KPIs"
        )
    )
'''

REQUIREMENTS_TEMPLATE = """# Loomaa semantic modeling dependencies
streamlit>=1.28.0
plotly>=5.17.0
networkx>=3.2.0
pandas>=2.0.0
requests>=2.31.0
msal>=1.27.0
python-dotenv>=1.0.0

# Core dependencies for model compilation
jinja2>=3.1.0
"""

README_TEMPLATE = '''# {model_name} - Semantic Model

A scalable Loomaa project defining a Power BI semantic model as code, connecting to existing data warehouse tables.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or use a virtual environment (recommended):
   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate  # Windows
   # source .venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

2. **Configure authentication:**
   Edit `.env` with your Microsoft Fabric credentials

3. **Build and view model:**
   ```bash
   loomaa compile  # Generate TMDL artifacts
   loomaa view     # Launch Power BI-style model viewer
   ```

4. **Deploy to Power BI:**
   ```bash
   loomaa deploy   # Push to Fabric workspace
   ```

## How Semantic Models Work

**Key Concept**: Semantic models don't create data - they add business meaning to existing warehouse data.

### Data Sources (Your Existing Tables)
- `warehouse.fact_sales` → Sales transactions  
- `warehouse.dim_customer` → Customer master data
- `warehouse.dim_product` → Product catalog

### Semantic Layer (What Loomaa Creates)
- **Column Metadata**: Business names, descriptions, formatting
- **Measures**: Business calculations using DAX
- **Relationships**: How tables connect logically
- **Organization**: Folders, display names, hierarchies

### Why Define Columns?

Even though we use `SELECT *`, TMDL requires column definitions because:
1. **Semantic metadata**: Descriptions, formatting, data types
2. **Business names**: "SalesAmount" vs "sales_amt_usd" 
3. **Type safety**: Ensures calculations work correctly
4. **Documentation**: Self-documenting model structure

This is exactly how Tabular Editor works with SQL Server/Fabric tables.

## Project Structure (Scalable Design)

```
{project_name}/
├── model.py              # Main model orchestration
├── models/               # Organized model components
│   ├── __init__.py       # Package initialization
│   ├── tables.py         # Table definitions with Jinja templating
│   ├── relationships.py  # All relationship definitions
│   └── measures.py       # Model-level measures
├── .env                  # Authentication (keep secure!)
├── examples/             # Sample CSV data for development
│   ├── customers.csv     # Customer sample data
│   └── products.csv      # Product sample data  
├── compiled/             # Generated TMDL/JSON artifacts
├── requirements.txt      # Python dependencies
└── README.md            # This documentation
```

## Scaling Your Model

### Adding New Tables
1. Add table function to `models/tables.py`
2. Import and add to `model.py`
3. Define relationships in `models/relationships.py`

### Advanced DAX with Jinja
```python
# In models/tables.py
ytd_template = Template("""
TOTALYTD(
    [{{base_measure}}],
    'Calendar'[Date]
)""")

Measure(
    name="Sales YTD",
    expression=ytd_template.render(base_measure="Total Sales")
)
```

### Organizing Measures
- **Table-level measures**: Defined with each table
- **Model-level measures**: Cross-table calculations in `models/measures.py`
- **Use folders**: Group related measures for better UX

### Multiple Models
For large projects:
```
project/
├── sales_model/
│   ├── model.py
│   └── models/
├── finance_model/
│   ├── model.py  
│   └── models/
└── shared/
    └── common_measures.py
```

## Power BI Model Viewer

Run `loomaa view` to launch a browser-based model viewer that shows:
- **Visual relationship diagram** (like Power BI Desktop)
- **Table details** with columns and measures
- **Model statistics** and health metrics
- **Multiple model support** with dropdown selection

## Best Practices

### Semantic Modeling
1. **Connect to existing data** - Don't recreate warehouse tables
2. **Descriptive metadata** - Add descriptions to everything
3. **Business-friendly names** - "Total Sales" not "sum_sales_amt"
4. **Organize with folders** - Group measures logically
5. **Format appropriately** - Currencies, percentages, etc.

### Code Organization
1. **Separate concerns** - Tables, relationships, measures in different files
2. **Use Jinja templates** - For reusable DAX patterns
3. **Document thoroughly** - Future you will thank you
4. **Version control** - Track changes to your semantic model
5. **Test locally** - Always `loomaa view` before deploying

### Performance
1. **DirectLake for real-time** - When possible
2. **Import for performance** - For complex calculations
3. **Optimize DAX** - Use variables, avoid row context
4. **Monitor usage** - Remove unused columns/measures

## Deployment Pipeline

Loomaa semantic models deploy to Power BI Service for consumption by:
- **Power BI Reports** - Interactive dashboards
- **Excel** - Analyze in Excel functionality
- **Third-party tools** - Via XMLA endpoint
- **Custom apps** - Using Power BI REST APIs

## Troubleshooting

### Common Issues
- **Missing dependencies**: Run `pip install -r requirements.txt`
- **Authentication failures**: Check `.env` file and service principal permissions
- **Compilation errors**: Validate DAX syntax and table references
- **Deployment issues**: Verify workspace permissions and XMLA access

### Getting Help
- Check the generated TMDL files in `compiled/` for validation
- Use Power BI Desktop to test DAX expressions
- Review relationships in the model viewer
- Validate source queries against your warehouse

## Learning Resources

- [Power BI Semantic Models](https://docs.microsoft.com/en-us/power-bi/connect-data/service-datasets-understand)
- [DAX Reference](https://docs.microsoft.com/en-us/dax/)
- [Tabular Editor](https://docs.tabulareditor.com/)
- [DirectLake Mode](https://docs.microsoft.com/en-us/power-bi/enterprise/directlake-overview)
'''

def _create_scaffold(project_name: str, model_name: str):
    """Create comprehensive learning project with DirectLake + Import examples"""
    
    log(f"Creating Loomaa project: {project_name}")
    
    # Create learning-focused directory structure
    os.makedirs(project_name, exist_ok=True)
    os.makedirs(f"{project_name}/models", exist_ok=True)
    os.makedirs(f"{project_name}/models/examples", exist_ok=True)
    os.makedirs(f"{project_name}/compiled", exist_ok=True)
    
    # Create comprehensive learning project files
    files = {
        f"{project_name}/.env": create_clean_env_template(),
        f"{project_name}/model.py": create_learning_model_template(),
        f"{project_name}/models/__init__.py": "# Models package\n",
        f"{project_name}/models/examples/__init__.py": "# Examples model package\n",
        f"{project_name}/models/examples/tables.py": create_learning_tables_template(),
        f"{project_name}/models/examples/relationships.py": create_learning_relationships_template(),
        f"{project_name}/models/examples/measures.py": create_learning_measures_template(),
        f"{project_name}/models/examples/hierarchies.py": create_learning_hierarchies_template(),
        f"{project_name}/models/examples/roles.py": create_learning_roles_template(),
        f"{project_name}/requirements.txt": create_clean_requirements_template(),
        f"{project_name}/README.md": create_learning_readme_template(project_name),
        f"{project_name}/compiled/README.md": "# Compiled TMDL Files\n\nGenerated TMDL and JSON files appear here after running `loomaa compile`.\n\nFiles:\n- examples.tmdl - Complete semantic model definition\n- examples.json - JSON representation for integration",
    }
    
    # Write all files
    for file_path, content in files.items():
        write_file(file_path, content)
        log(f"Created {file_path}")

def create_clean_env_template():
    """Clean .env template with only authentication variables since connections are now explicit in table declarations"""
    return '''# Microsoft Fabric Authentication
FABRIC_TENANT_ID=your-azure-tenant-id
FABRIC_CLIENT_ID=your-service-principal-client-id
FABRIC_CLIENT_SECRET=your-client-secret
FABRIC_WORKSPACE_ID=your-power-bi-workspace-id
FABRIC_XMLA_ENDPOINT=powerbi://api.powerbi.com/v1.0/myorg/your-workspace-name
'''

def create_learning_model_template():
    """Main model.py showing how to orchestrate different model components"""
    return '''"""
Loomaa Learning Example - Complete Semantic Model
Shows DirectLake + Import hybrid approach with all model elements
"""
from models.examples.tables import create_sales_table, create_customer_table, create_product_table
from models.examples.relationships import define_relationships
from models.examples.measures import add_model_measures
from models.examples.hierarchies import add_hierarchies
from models.examples.roles import add_security_roles
from loomaa.model import SemanticModel

def build_examples_model():
    """
    Complete learning example showing:
    - DirectLake tables (live lakehouse data)
    - Import tables (traditional data warehouse)
    - Relationships between mixed modes
    - Measures with proper DAX
    - Hierarchies for drill-down
    - Row-level security roles
    """
    
    # Create semantic model
    model = SemanticModel(
        name="Learning_Examples", 
        description="Complete Loomaa learning example with DirectLake + Import hybrid"
    )
    
    # Add tables (mix of DirectLake and Import modes)
    model.add_table(create_sales_table())        # DirectLake - live fact data
    model.add_table(create_customer_table())     # Import - enriched dimensions
    model.add_table(create_product_table())      # Import - master data
    
    # Define relationships between tables
    define_relationships(model)
    
    # Add model-level measures
    add_model_measures(model)
    
    # Add hierarchies for drill-down analysis
    add_hierarchies(model)
    
    # Add row-level security (optional)
    add_security_roles(model)
    
    return model

# Available models in this project
models = {
    "examples": build_examples_model()
}

# Next Steps:
# 1. Update table source_query references to match your actual warehouse/lakehouse
# 2. Customize measures and hierarchies for your business logic
# 3. Run: loomaa compile
# 4. Run: loomaa view (to see your model)
# 5. Deploy to Power BI when ready
'''

def create_learning_tables_template():
    """Comprehensive table examples with DirectLake + Import modes"""
    return '''"""
Table Definitions - Learning Examples
Shows DirectLake (live) and Import (cached) table patterns with smart enums
"""
from loomaa.model import Table, Column, Measure, DataTypes, TableMode

def create_sales_table():
    """
    Sales Fact Table - DirectLake Mode
    ✅ Live connection to Fabric lakehouse/warehouse
    ✅ Real-time data, fastest queries  
    ✅ No calculated columns (DirectLake limitation)
    """
    
    sales_table = Table(
        name="sales_fact",  # 🔑 Actual database table name
        schema="dbo",  # 📋 Database schema
        mode=TableMode.DIRECTLAKE,  # 🚀 Live lakehouse/warehouse data
        description="Real-time sales transactions from lakehouse",
        directlake_resource_id="your-lakehouse-or-warehouse-id-here"  # 🔑 Replace with actual GUID
    )
    
    # Define columns that exist in your lakehouse table
    sales_table.add_column(Column("SalesID", DataTypes.INTEGER, "Unique sale identifier"))
    sales_table.add_column(Column("CustomerID", DataTypes.INTEGER, "Customer reference"))
    sales_table.add_column(Column("ProductID", DataTypes.INTEGER, "Product reference"))
    sales_table.add_column(Column("OrderDate", DataTypes.DATETIME, "Sale date"))
    sales_table.add_column(Column("Revenue", DataTypes.CURRENCY, "Sale amount", format_string="$#,##0.00"))
    sales_table.add_column(Column("Quantity", DataTypes.INTEGER, "Items sold"))
    sales_table.add_column(Column("Region", DataTypes.TEXT, "Sales region"))
    
    # Add table-level measures (works with DirectLake)
    total_sales = Measure(
        name="Total Sales",
        expression="SUM(Sales[Revenue])",
        description="Sum of all sales revenue",
        format_string="$#,##0"
    )
    sales_table.add_measure(total_sales)
    
    avg_order_value = Measure(
        name="Average Order Value",
        expression="DIVIDE(SUM(Sales[Revenue]), DISTINCTCOUNT(Sales[SalesID]))",
        description="Average revenue per order",
        format_string="$#,##0.00"
    )
    sales_table.add_measure(avg_order_value)
    
    return sales_table

def create_customer_table():
    """
    Customer Dimension - Import Mode
    ✅ Data copied into model for fast filtering
    ✅ Supports calculated columns
    ✅ Function name used for relationships
    """
    
    customer_table = Table(
        name="dim_customer",  # 🔑 Actual database table name
        schema="your_warehouse",  # 📋 Database schema
        mode=TableMode.IMPORT,  # 📊 Traditional import for dimensions
        description="Customer master data with enrichments",
        sql_server="your-sql-server.database.windows.net"  # 🔗 Replace with your SQL server name
    )
    
    # Define columns from your dimension table
    customer_table.add_column(Column("CustomerID", DataTypes.INTEGER, "Primary key"))
    customer_table.add_column(Column("CustomerName", DataTypes.TEXT, "Customer name"))
    customer_table.add_column(Column("City", DataTypes.TEXT, "Customer city"))
    customer_table.add_column(Column("Region", DataTypes.TEXT, "Sales region"))
    customer_table.add_column(Column("Country", DataTypes.TEXT, "Customer country"))
    customer_table.add_column(Column("Segment", DataTypes.TEXT, "Customer segment"))
    customer_table.add_column(Column("IsActive", DataTypes.BOOLEAN, "Active customer flag"))
    
    # Import mode supports calculated columns (DirectLake doesn't!)
    from loomaa.model import CalculatedColumn
    
    customer_key = CalculatedColumn(
        name="Customer Key",
        expression="[CustomerID] & \\" - \\" & [CustomerName]",
        description="Friendly customer identifier"
    )
    customer_table.calculated_columns.append(customer_key)
    
    return customer_table

def create_product_table():
    """
    Product Dimension - Import Mode
    ✅ Master data with business calculations
    ✅ Product hierarchies and categorization
    """
    
    product_table = Table(
        name="dim_product",  # � Actual database table name
        schema="your_warehouse",  # 📋 Database schema
        mode=TableMode.IMPORT,  # 📊 Import for enriched dimensions
        description="Product master data with custom SQL",
        source_query="SELECT ProductID, ProductName, Category, Brand, UnitPrice FROM your_warehouse.dim_product WHERE IsActive = 1",  # 🔍 Custom SELECT query (optional)
        sql_server="your-sql-server.database.windows.net"  # 🔗 Replace with your SQL server name
    )
    
    # Product attributes
    product_table.add_column(Column("ProductID", DataTypes.INTEGER, "Primary key"))
    product_table.add_column(Column("ProductName", DataTypes.TEXT, "Product name"))
    product_table.add_column(Column("Category", DataTypes.TEXT, "Product category"))
    product_table.add_column(Column("Subcategory", DataTypes.TEXT, "Product subcategory"))
    product_table.add_column(Column("Brand", DataTypes.TEXT, "Product brand"))
    product_table.add_column(Column("UnitPrice", DataTypes.CURRENCY, "List price", format_string="$#,##0.00"))
    product_table.add_column(Column("IsActive", DataTypes.BOOLEAN, "Active product flag"))
    
    # Product-level measures
    avg_unit_price = Measure(
        name="Average Unit Price",
        expression="AVERAGE(Product[UnitPrice])",
        description="Average price across products",
        format_string="$#,##0.00"
    )
    product_table.add_measure(avg_unit_price)
    
    return product_table

# Key Learning Points:
# 
# 🎯 DirectLake vs Import:
#   - DirectLake: Live lakehouse data, no calculated columns, fastest queries
#   - Import: Cached data, supports calculated columns, enrichment possibilities
#
# 🎯 Clean Table Architecture:
#   - name="actual_table_name" (database table name)
#   - schema="your_schema" (database schema) 
#   - Function variable names used for relationships (create_sales_table → create_customer_table)
#   - Compiler uses schema + name for database references
#
# 🎯 Explicit Connections (No Environment Variables!):
#   - DirectLake: directlake_resource_id="your-lakehouse-id" in table declaration
#   - Import: sql_server="your-server.database.windows.net" in table declaration
#   - Full control over which resource each table connects to
#
# 🎯 Smart Enums Prevent Errors:
#   - TableMode.DIRECTLAKE vs old "DirectLake" string 
#   - DataTypes.CURRENCY vs old "Currency" string
#   - IDE autocomplete shows all valid options
#
# 🎯 Hybrid Architecture:
#   - Facts in DirectLake (live operational data)  
#   - Dimensions in Import (enriched, calculated attributes)
#   - Best of both worlds for enterprise semantic models
'''

def create_learning_relationships_template():
    """Learning examples for relationships with smart enums"""
    return '''"""
Relationship Definitions - Learning Examples  
Shows how to connect DirectLake and Import tables with smart enums
"""
from loomaa.model import Relationship, Cardinality, CrossFilter

def define_relationships(model):
    """
    Define relationships between tables
    ✅ Works across DirectLake and Import tables seamlessly
    ✅ Uses smart enums to prevent configuration errors
    """
    
    # Sales to Customer relationship (using function variable names)
    sales_customer_rel = Relationship(
        from_table="create_sales_table",     # 🔗 Function name that creates the table
        from_column="CustomerID", 
        to_table="create_customer_table",    # 🔗 Function name that creates the table
        to_column="CustomerID",
        cardinality=Cardinality.MANY_TO_ONE,      # ✅ Clear and obvious
        cross_filter_direction=CrossFilter.SINGLE, # ✅ Standard fact-to-dim filtering
        description="Link sales transactions to customer details"
    )
    model.add_relationship(sales_customer_rel)
    
    # Sales to Product relationship (using function variable names)
    sales_product_rel = Relationship(
        from_table="create_sales_table",     # 🔗 Function name that creates the table
        from_column="ProductID",
        to_table="create_product_table",     # 🔗 Function name that creates the table
        to_column="ProductID",
        cardinality=Cardinality.MANY_TO_ONE,      # ✅ Many sales per product
        cross_filter_direction=CrossFilter.SINGLE, # ✅ One-way filtering
        description="Link sales transactions to product details"
    )
    model.add_relationship(sales_product_rel)
    
    # Example: Bidirectional relationship (advanced scenario)
    # Uncomment if you need filters to flow both ways:
    #
    # bidirectional_rel = Relationship(
    #     from_table="Customer",
    #     from_column="Region", 
    #     to_table="Region",        # Hypothetical region table
    #     to_column="RegionName",
    #     cardinality=Cardinality.MANY_TO_ONE,
    #     cross_filter_direction=CrossFilter.BOTH,  # ✅ Filters flow both directions
    #     description="Bidirectional customer-region relationship"
    # )
    # model.add_relationship(bidirectional_rel)

# Key Learning Points:
#
# 🎯 Hybrid Relationships Work Seamlessly:
#   - DirectLake fact tables can relate to Import dimensions
#   - Power BI handles the different storage modes automatically
#
# 🎯 Smart Enum Benefits:
#   - Cardinality.MANY_TO_ONE prevents "Many-To-One" vs "manyToOne" confusion
#   - CrossFilter.SINGLE is clearer than "Single" vs "oneDirection"
#   - IDE shows all valid options with autocomplete
#
# 🎯 Relationship Patterns:
#   - Fact-to-Dimension: Usually MANY_TO_ONE with SINGLE filtering
#   - Bridge Tables: Often MANY_TO_MANY relationships
#   - Bidirectional: Use CrossFilter.BOTH sparingly (can impact performance)
'''

def create_learning_measures_template():
    """Learning examples for DAX measures"""
    return '''"""
Measure Definitions - Learning Examples
Shows model-level measures with proper DAX and formatting
"""
from loomaa.model import Measure

def add_model_measures(model):
    """
    Add model-level measures (available across all tables)
    ✅ Professional DAX patterns
    ✅ Proper formatting and descriptions
    """
    
    # Revenue measures
    total_revenue = Measure(
        name="Total Revenue",
        expression="SUM(Sales[Revenue])",
        description="Total sales revenue across all transactions",
        format_string="$#,##0"
    )
    model.add_measure(total_revenue)
    
    # Time intelligence - Previous Year
    revenue_py = Measure(
        name="Revenue PY",
        expression="""
        CALCULATE(
            [Total Revenue],
            SAMEPERIODLASTYEAR(Sales[OrderDate])
        )""",
        description="Revenue for same period last year",
        format_string="$#,##0"
    )
    model.add_measure(revenue_py)
    
    # Growth calculation
    revenue_growth = Measure(
        name="Revenue Growth %",
        expression="""
        VAR CurrentRevenue = [Total Revenue]
        VAR PreviousRevenue = [Revenue PY]
        RETURN
            IF(
                PreviousRevenue = 0,
                BLANK(),
                DIVIDE(CurrentRevenue - PreviousRevenue, PreviousRevenue)
            )""",
        description="Year-over-year revenue growth percentage",
        format_string="0.0%"
    )
    model.add_measure(revenue_growth)
    
    # Customer metrics
    customer_count = Measure(
        name="Customer Count",
        expression="DISTINCTCOUNT(Sales[CustomerID])",
        description="Number of unique customers",
        format_string="#,##0"
    )
    model.add_measure(customer_count)
    
    # Advanced: Sales per Customer
    sales_per_customer = Measure(
        name="Sales per Customer",
        expression="""
        DIVIDE(
            [Total Revenue],
            [Customer Count],
            0
        )""",
        description="Average revenue per customer",
        format_string="$#,##0.00"
    )
    model.add_measure(sales_per_customer)
    
    # Product performance
    avg_selling_price = Measure(
        name="Average Selling Price",
        expression="""
        DIVIDE(
            SUM(Sales[Revenue]),
            SUM(Sales[Quantity]),
            0
        )""",
        description="Average price per unit sold",
        format_string="$#,##0.00"
    )
    model.add_measure(avg_selling_price)

# Key Learning Points:
#
# 🎯 Model-Level vs Table-Level Measures:
#   - Model-level: Available everywhere, good for KPIs
#   - Table-level: Scoped to specific table, good for specific calculations
#
# 🎯 Professional DAX Patterns:
#   - Use VAR for complex calculations (easier to read/debug)
#   - Handle division by zero with DIVIDE() or IF() checks
#   - Time intelligence functions for period comparisons
#
# 🎯 Format Strings:
#   - Currency: "$#,##0" or "$#,##0.00"
#   - Percentages: "0.0%" or "0.00%"  
#   - Numbers: "#,##0" for thousands separators
'''

def create_learning_hierarchies_template():
    """Learning examples for hierarchies"""
    return '''"""
Hierarchy Definitions - Learning Examples
Shows drill-down paths for dimensional analysis
"""
from loomaa.model import Hierarchy

def add_hierarchies(model):
    """
    Add hierarchies to enable drill-down analysis
    ✅ Geographic drill-down paths
    ✅ Product categorization hierarchies
    ✅ Time-based hierarchies
    """
    
    # Geographic hierarchy for customer analysis
    geography_hierarchy = Hierarchy(
        name="Customer Geography",
        levels=["Country", "Region", "City"],
        description="Geographic drill-down for customer analysis"
    )
    model.add_hierarchy(geography_hierarchy)
    
    # Product hierarchy for merchandise analysis  
    product_hierarchy = Hierarchy(
        name="Product Breakdown",
        levels=["Category", "Subcategory", "Brand", "ProductName"],
        description="Product classification drill-down path"
    )
    model.add_hierarchy(product_hierarchy)
    
    # Example: Time hierarchy (if you have a date dimension)
    # time_hierarchy = Hierarchy(
    #     name="Time Intelligence", 
    #     levels=["Year", "Quarter", "Month", "Date"],
    #     description="Time-based drill-down for trend analysis"
    # )
    # model.add_hierarchy(time_hierarchy)

# Key Learning Points:
#
# 🎯 Hierarchy Benefits:
#   - Enable natural drill-down in Power BI visuals
#   - Users can expand from Country → Region → City automatically
#   - Improves user experience in reports
#
# 🎯 Hierarchy Design:
#   - Order levels from highest to lowest granularity
#   - Geographic: Country → Region → City
#   - Product: Category → Subcategory → Product
#   - Time: Year → Quarter → Month → Day
#
# 🎯 Best Practices:
#   - Keep hierarchy levels logical and intuitive
#   - Ensure all levels exist in your dimension tables
#   - Test drill-down behavior in Power BI Desktop
'''

def create_learning_roles_template():
    """Learning examples for row-level security"""
    return '''"""
Role Definitions - Learning Examples
Shows row-level security patterns for data access control
"""
from loomaa.model import Role

def add_security_roles(model):
    """
    Add row-level security roles (optional)
    ✅ Regional data access control
    ✅ User-based filtering patterns
    ✅ Professional security design
    """
    
    # Regional sales team role
    regional_sales_role = Role(
        name="Regional Sales Team",
        description="Access to assigned region data only"
    )
    
    # Filter sales data by user's region
    regional_sales_role.add_table_permission(
        table_name="Sales",
        filter_expression="Sales[Region] = USERNAME()"
    )
    
    # Filter customers by same region
    regional_sales_role.add_table_permission(
        table_name="Customer", 
        filter_expression="Customer[Region] = USERNAME()"
    )
    
    # Add team members (replace with actual email addresses)
    regional_sales_role.add_member("north.sales@company.com")
    regional_sales_role.add_member("south.sales@company.com")
    
    model.add_role(regional_sales_role)
    
    # Executive role - full access
    executive_role = Role(
        name="Executive Team",
        description="Full access to all data across regions"
    )
    
    # No table permissions = full access
    executive_role.add_member("ceo@company.com")
    executive_role.add_member("cfo@company.com")
    executive_role.add_member("vp.sales@company.com")
    
    model.add_role(executive_role)
    
    # Customer service role - customers only, no revenue
    customer_service_role = Role(
        name="Customer Service",
        description="Access to customer information only"
    )
    
    # Block access to sensitive revenue data
    customer_service_role.add_table_permission(
        table_name="Sales",
        filter_expression="FALSE()"  # No sales data access
    )
    
    # Full customer access
    # (No filter on Customer table = full access)
    
    customer_service_role.add_member("support@company.com")
    
    model.add_role(customer_service_role)

# Key Learning Points:
#
# 🎯 Row-Level Security (RLS) Patterns:
#   - Regional: Filter by USERNAME() matching region assignments
#   - Departmental: Filter by department or cost center
#   - Customer-specific: Filter by customer relationships
#
# 🎯 Security Design:
#   - No filter = full access to that table
#   - FALSE() = no access to table data
#   - Dynamic filters use USERNAME(), USERPRINCIPALNAME()
#
# 🎯 Role Management:
#   - Test with actual user accounts in Power BI Service
#   - Consider Azure AD group memberships
#   - Document security model for compliance
#
# 🎯 Optional Feature:
#   - Comment out add_security_roles(model) in model.py if not needed
#   - RLS adds complexity - only implement when required
'''

def create_clean_requirements_template():
    """Clean requirements without unnecessary dependencies"""
    return '''# Loomaa Semantic Modeling Framework
loomaa

# Data Processing (if needed for custom transformations)
pandas>=1.5.0

# Visualization (for model viewer)  
streamlit>=1.28.0
plotly>=5.15.0

# Optional: Additional data connectors
# pyodbc>=4.0.35          # SQL Server connections
# azure-identity>=1.14.0   # Azure authentication
'''

def create_learning_readme_template(project_name):
    """Comprehensive learning-focused README"""
    return f'''# {project_name} - Loomaa Learning Project

Complete semantic modeling example showing DirectLake + Import hybrid architecture with smart enums.

## 🎯 What You'll Learn

This project demonstrates:

✅ **DirectLake Tables** - Live lakehouse data connections  
✅ **Import Tables** - Traditional data warehouse patterns  
✅ **Smart Enums** - Error-proof development with IDE support  
✅ **Relationships** - Cross-mode table connections  
✅ **Measures** - Professional DAX patterns  
✅ **Hierarchies** - Drill-down analysis paths  
✅ **Security Roles** - Row-level security implementation  

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure authentication (edit .env)
# Add your Fabric workspace credentials

# 3. Update data sources in models/examples/tables.py
# Replace sample warehouse/lakehouse references with yours

# 4. Compile the model
loomaa compile

# 5. View in browser
loomaa view

# 6. Deploy to Power BI (when ready)
loomaa deploy
```

## 📁 Project Structure

```
{project_name}/
├── model.py                          # Main model orchestration
├── .env                              # Fabric authentication
├── models/examples/
│   ├── tables.py                     # Table definitions (DirectLake + Import)
│   ├── relationships.py              # Cross-table relationships
│   ├── measures.py                   # Model-level DAX measures
│   ├── hierarchies.py                # Drill-down hierarchies
│   └── roles.py                      # Row-level security (optional)
├── compiled/
│   ├── examples.tmdl                 # Generated semantic model
│   └── examples.json                 # JSON representation
└── requirements.txt                  # Python dependencies
```

## 🎓 Learning Path

### 1. **Start with Tables** (`models/examples/tables.py`)
- See DirectLake vs Import patterns
- Learn smart enum usage: `TableMode.DIRECTLAKE`, `DataTypes.CURRENCY`
- Understand when to use each mode

### 2. **Connect with Relationships** (`models/examples/relationships.py`)  
- Learn how DirectLake facts connect to Import dimensions
- Use smart enums: `Cardinality.MANY_TO_ONE`, `CrossFilter.SINGLE`
- Understand cross-filtering behavior

### 3. **Add Business Logic** (`models/examples/measures.py`)
- Professional DAX patterns with VAR statements
- Time intelligence and growth calculations
- Proper formatting and descriptions

### 4. **Enable Drill-Down** (`models/examples/hierarchies.py`)
- Geographic and product hierarchies
- Natural drill-down paths for users
- Improve report user experience

### 5. **Secure Your Data** (`models/examples/roles.py`) 
- Row-level security implementation
- Regional and departmental access patterns
- USERNAME() and dynamic filtering

## 🔄 DirectLake + Import Hybrid Benefits

| Mode | Best For | Capabilities | Limitations |
|------|----------|--------------|-------------|
| **DirectLake** | Live operational data, fact tables | Real-time queries, fastest performance | No calculated columns |
| **Import** | Enriched dimensions, master data | Calculated columns, complex transformations | Data refresh required |

## 🎯 Smart Enums Prevent Errors

**Before (Error-Prone):**
```python
Column("amount", "Currency", ...)          # Typo risk!
Table(mode="DirectLake", ...)              # Case sensitive!
Relationship(..., cardinality="Many-to-One")  # Many variations!
```

**After (Bulletproof):**
```python
Column("amount", DataTypes.CURRENCY, ...)     # IDE autocomplete!
Table(mode=TableMode.DIRECTLAKE, ...)         # Crystal clear!
Relationship(..., cardinality=Cardinality.MANY_TO_ONE)  # Perfect!
```

## 📊 Generated Output

After `loomaa compile`, you get:

- **`examples.tmdl`** - Complete Power BI semantic model definition
- **`examples.json`** - JSON representation for integration
- Production-ready files that can be deployed to Power BI Service

## 🔧 Customization

1. **Update Data Sources**: Edit `source_query` in table definitions
2. **Add Your Tables**: Create new table functions in `tables.py`
3. **Customize Measures**: Add your business KPIs in `measures.py`
4. **Modify Security**: Adjust role filters in `roles.py`

## 🎯 Next Steps

1. **Learn by Example** - Study each file to understand patterns
2. **Customize for Your Data** - Replace sample queries with your warehouse
3. **Test Compilation** - Run `loomaa compile` to see generated TMDL
4. **View Your Model** - Use `loomaa view` to inspect relationships
5. **Deploy to Power BI** - Use `loomaa deploy` when ready for production

## 💡 Key Concepts

- **Hybrid Architecture**: Facts in DirectLake, dimensions in Import
- **Smart Enums**: IDE-assisted development, error prevention
- **Production TMDL**: Real Power BI format, not simplified versions
- **Cross-Mode Relationships**: DirectLake and Import tables work together seamlessly

Happy semantic modeling with Loomaa! 🚀
'''

@app.command() 
def init(
    project_name: str = typer.Argument(..., help="Name of the project directory"),
    model_name: str = typer.Option(None, "--model", "-m", help="Semantic model name"),
):
    """Initialize a new semantic model project"""
    
    if model_name is None:
        model_name = f"{project_name.replace('-', '_').title()} Model"
    
    _create_scaffold(project_name, model_name)
    
    typer.echo(f"✅ Loomaa project '{project_name}' created!")
    typer.echo("")
    typer.echo("🎓 Learning Project Created - Complete DirectLake + Import Example!")
    typer.echo("")
    typer.echo("📋 Next steps:")
    typer.echo(f"   cd {project_name}")
    typer.echo("   pip install -r requirements.txt")
    typer.echo("   # Edit .env with your Fabric credentials")
    typer.echo("   # Update source_query references in models/examples/tables.py")
    typer.echo("   loomaa compile")
    typer.echo("   loomaa view")
    typer.echo("")
    typer.echo("🎯 What you'll learn:")
    typer.echo("   • DirectLake tables (live lakehouse data)")
    typer.echo("   • Import tables (traditional warehouses)")
    typer.echo("   • Smart enums (error-proof development)")
    typer.echo("   • Relationships, measures, hierarchies & security")
    typer.echo("")
    typer.echo("📁 Key files to explore:")
    typer.echo("   • models/examples/tables.py - Table definitions")
    typer.echo("   • models/examples/relationships.py - Cross-table connections")
    typer.echo("   • models/examples/measures.py - DAX measures")
    typer.echo("   • models/examples/hierarchies.py - Drill-down paths")
    typer.echo("   • models/examples/roles.py - Row-level security")

@app.command()
def compile():
    """Compile semantic model to TMDL artifacts"""
    
    if not os.path.exists("model.py"):
        typer.echo("❌ model.py not found. Run 'loomaa init' first.")
        raise typer.Exit(1)
    
    try:
        log("Compiling semantic model...")
        compile_model()
        typer.echo("✅ Model compiled! Check compiled/ directory.")
        typer.echo("💡 Run 'loomaa view' to inspect the model in browser.")
    except Exception as e:
        typer.echo(f"❌ Compilation failed: {e}")
        raise typer.Exit(1)

@app.command()
def view(port: int = typer.Option(8501, "--port", "-p", help="Streamlit port number")):
    """Launch Power BI-style model viewer using Streamlit"""
    
    if not os.path.exists("compiled"):
        typer.echo("❌ Compiled models not found. Run 'loomaa compile' first.")
        raise typer.Exit(1)
    
    try:
        import subprocess
        import sys
        from pathlib import Path
        
        # Get the viewer script path
        viewer_path = Path(__file__).parent / "viewer.py"
        
        typer.echo(f"🔮 Starting Loomaa Model Viewer...")
        typer.echo(f"🌐 Opening browser at: http://localhost:{port}")
        typer.echo(f"💡 Use Ctrl+C to stop the viewer")
        
        # Launch Streamlit viewer
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            str(viewer_path),
            "--server.port", str(port),
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false",
            "--theme.primaryColor", "#3498db",
            "--theme.backgroundColor", "#ffffff",
            "--theme.secondaryBackgroundColor", "#f0f2f6"
        ]
        
        subprocess.run(cmd, cwd=os.getcwd())
        
    except ImportError:
        typer.echo("❌ Streamlit not installed. Installing dependencies...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit", "plotly", "networkx", "pandas"])
            typer.echo("✅ Dependencies installed! Please run the command again.")
        except subprocess.CalledProcessError:
            typer.echo("❌ Failed to install dependencies. Please run: pip install streamlit plotly networkx pandas")
    except KeyboardInterrupt:
        typer.echo("\\n🛑 Model viewer stopped.")
        return
    except Exception as e:
        typer.echo(f"❌ Viewer failed: {e}")
        return

def generate_star_schema_svg(tables: list, relationships: list):
    """Generate SVG-based star schema diagram like Power BI Model View"""
    
    # Calculate diagram dimensions
    num_tables = len(tables)
    if num_tables == 0:
        return '<div style="text-align: center; padding: 2rem; color: #666;">No tables to display</div>'
    
    # Create a circular layout for star schema
    import math
    
    width, height = 800, 600
    center_x, center_y = width // 2, height // 2
    
    # Identify fact tables (usually contain 'fact' or 'sales' in name)
    fact_tables = [t for t in tables if 'fact' in t['name'].lower() or 'sales' in t['name'].lower()]
    dim_tables = [t for t in tables if t not in fact_tables]
    
    svg_content = f'''
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="3" dy="3" stdDeviation="3" flood-color="#00000040"/>
            </filter>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" 
                    refX="10" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="#107C10" />
            </marker>
        </defs>
    '''
    
    table_positions = {}
    
    # Place fact table(s) in center
    if fact_tables:
        fact_table = fact_tables[0]  # Primary fact table
        fact_x, fact_y = center_x, center_y
        table_positions[fact_table['name']] = (fact_x, fact_y)
        
        # Draw fact table (larger, green)
        svg_content += f'''
        <rect x="{fact_x - 80}" y="{fact_y - 40}" width="160" height="80" 
              rx="8" fill="#107C10" stroke="#0B6A0B" stroke-width="2" filter="url(#shadow)"/>
        <text x="{fact_x}" y="{fact_y - 10}" text-anchor="middle" fill="white" 
              font-family="Segoe UI" font-size="14" font-weight="bold">📈 {fact_table['name']}</text>
        <text x="{fact_x}" y="{fact_y + 8}" text-anchor="middle" fill="white" 
              font-family="Segoe UI" font-size="10" opacity="0.9">{fact_table.get('mode', 'Import')}</text>
        <text x="{fact_x}" y="{fact_y + 22}" text-anchor="middle" fill="white" 
              font-family="Segoe UI" font-size="10" opacity="0.8">
              {len(fact_table.get('columns', []))} cols • {len(fact_table.get('measures', []))} measures</text>
        '''
        
        # Place dimension tables around the fact table
        if dim_tables:
            angle_step = 2 * math.pi / len(dim_tables)
            radius = 200
            
            for i, dim_table in enumerate(dim_tables):
                angle = i * angle_step
                dim_x = center_x + radius * math.cos(angle)
                dim_y = center_y + radius * math.sin(angle)
                table_positions[dim_table['name']] = (dim_x, dim_y)
                
                # Draw dimension table (smaller, blue)
                svg_content += f'''
                <rect x="{dim_x - 60}" y="{dim_y - 30}" width="120" height="60" 
                      rx="6" fill="#0078D4" stroke="#106EBE" stroke-width="2" filter="url(#shadow)"/>
                <text x="{dim_x}" y="{dim_y - 5}" text-anchor="middle" fill="white" 
                      font-family="Segoe UI" font-size="12" font-weight="bold">📊 {dim_table['name']}</text>
                <text x="{dim_x}" y="{dim_y + 10}" text-anchor="middle" fill="white" 
                      font-family="Segoe UI" font-size="9" opacity="0.8">
                      {len(dim_table.get('columns', []))} columns</text>
                '''
                
                # Draw relationship line from dimension to fact
                svg_content += f'''
                <line x1="{dim_x}" y1="{dim_y}" x2="{fact_x}" y2="{fact_y}" 
                      stroke="#107C10" stroke-width="2" marker-end="url(#arrowhead)" opacity="0.7"/>
                '''
    else:
        # No fact tables - arrange all tables in a circle
        if num_tables == 1:
            table = tables[0]
            table_positions[table['name']] = (center_x, center_y)
            svg_content += f'''
            <rect x="{center_x - 70}" y="{center_y - 35}" width="140" height="70" 
                  rx="8" fill="#107C10" stroke="#0B6A0B" stroke-width="2" filter="url(#shadow)"/>
            <text x="{center_x}" y="{center_y - 5}" text-anchor="middle" fill="white" 
                  font-family="Segoe UI" font-size="14" font-weight="bold">📊 {table['name']}</text>
            <text x="{center_x}" y="{center_y + 15}" text-anchor="middle" fill="white" 
                  font-family="Segoe UI" font-size="10" opacity="0.8">
                  {len(table.get('columns', []))} cols • {len(table.get('measures', []))} measures</text>
            '''
        else:
            angle_step = 2 * math.pi / num_tables
            radius = 150
            
            for i, table in enumerate(tables):
                angle = i * angle_step
                table_x = center_x + radius * math.cos(angle)
                table_y = center_y + radius * math.sin(angle)
                table_positions[table['name']] = (table_x, table_y)
                
                color = "#418F41" if 'sales' in table['name'].lower() else "#0078D4"
                svg_content += f'''
                <rect x="{table_x - 60}" y="{table_y - 30}" width="120" height="60" 
                      rx="6" fill="{color}" stroke="{color}" stroke-width="2" filter="url(#shadow)"/>
                <text x="{table_x}" y="{table_y - 5}" text-anchor="middle" fill="white" 
                      font-family="Segoe UI" font-size="12" font-weight="bold">📊 {table['name']}</text>
                <text x="{table_x}" y="{table_y + 10}" text-anchor="middle" fill="white" 
                      font-family="Segoe UI" font-size="9" opacity="0.8">
                      {len(table.get('columns', []))} cols</text>
                '''
    
    # Draw relationship lines for explicit relationships
    for rel in relationships:
        if rel['from_table'] in table_positions and rel['to_table'] in table_positions:
            from_pos = table_positions[rel['from_table']]
            to_pos = table_positions[rel['to_table']]
            
            svg_content += f'''
            <line x1="{from_pos[0]}" y1="{from_pos[1]}" x2="{to_pos[0]}" y2="{to_pos[1]}" 
                  stroke="#107C10" stroke-width="2" marker-end="url(#arrowhead)" opacity="0.7"/>
            <text x="{(from_pos[0] + to_pos[0]) / 2}" y="{(from_pos[1] + to_pos[1]) / 2 - 5}" 
                  text-anchor="middle" font-family="Segoe UI" font-size="8" fill="#107C10" font-weight="bold">
                  {rel.get('cardinality', 'Many-to-One')}
            </text>
            '''
    
    svg_content += '</svg>'
    return svg_content


def generate_relationship_list(relationships: list):
    """Generate HTML list of relationships"""
    if not relationships:
        return '<p style="color: #666; font-style: italic;">No explicit relationships defined in this model.</p>'
    
    relationship_html = ""
    for rel in relationships:
        relationship_html += f'''
        <div style="background: #F8F9FA; padding: 1rem; margin: 0.5rem 0; border-radius: 6px; border-left: 3px solid #107C10;">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <span style="font-weight: 600; color: #323130;">{rel['from_table']}</span>
                <span style="color: #107C10; font-size: 1.2rem;">→</span>
                <span style="font-weight: 600; color: #323130;">{rel['to_table']}</span>
                <span style="background: #107C10; color: white; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.8rem; margin-left: auto;">
                    {rel.get('cardinality', 'Many-to-One')}
                </span>
            </div>
            <div style="margin-top: 0.5rem; color: #605E5C; font-size: 0.9rem;">
                <strong>From:</strong> {rel['from_column']} → <strong>To:</strong> {rel['to_column']}
            </div>
        </div>
        '''
    
    return relationship_html


@app.command()
def create_clean_viewer():
    """Create a clean, modern semantic model viewer for Microsoft Fabric semantic layer"""
    
    from fastapi.responses import HTMLResponse
    
    # Professional HTML template for analytics engineers
    html_content = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Loomaa - Professional Semantic Model Viewer</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
                background: #ffffff;
                color: #1f2937;
                line-height: 1.6;
                min-height: 100vh;
            }
            
            .header {
                background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
                color: white;
                padding: 3rem 0;
                text-align: center;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            }
            
            .header h1 {
                font-size: 3rem;
                font-weight: 700;
                margin-bottom: 0.5rem;
                background: linear-gradient(45deg, #ffffff, #e5e7eb);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .header p {
                font-size: 1.25rem;
                opacity: 0.9;
                font-weight: 300;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 4rem 2rem;
            }
            
            .welcome-card {
                background: white;
                border-radius: 16px;
                padding: 3rem;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
                text-align: center;
                border: 1px solid #e5e7eb;
            }
            
            .welcome-card h2 {
                font-size: 2rem;
                font-weight: 600;
                color: #1f2937;
                margin-bottom: 1rem;
            }
            
            .welcome-card p {
                font-size: 1.125rem;
                color: #6b7280;
                margin-bottom: 2rem;
                max-width: 600px;
                margin-left: auto;
                margin-right: auto;
            }
            
            .feature-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 2rem;
                margin-top: 3rem;
            }
            
            .feature-card {
                background: white;
                border-radius: 12px;
                padding: 2rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                border: 1px solid #e5e7eb;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            
            .feature-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
            }
            
            .feature-icon {
                font-size: 2.5rem;
                margin-bottom: 1rem;
                display: block;
            }
            
            .feature-title {
                font-size: 1.25rem;
                font-weight: 600;
                color: #1f2937;
                margin-bottom: 0.5rem;
            }
            
            .feature-desc {
                color: #6b7280;
                font-size: 0.95rem;
            }
            
            .footer {
                background: #1f2937;
                color: white;
                text-align: center;
                padding: 2rem;
                margin-top: 4rem;
            }
            
            .footer-title {
                font-size: 1.5rem;
                font-weight: 600;
                margin-bottom: 0.5rem;
            }
            
            .footer-subtitle {
                opacity: 0.8;
                font-size: 0.95rem;
            }
            
            @media (max-width: 768px) {
                .header h1 { font-size: 2rem; }
                .header p { font-size: 1rem; }
                .container { padding: 2rem 1rem; }
                .welcome-card { padding: 2rem; }
                .feature-grid { grid-template-columns: 1fr; gap: 1rem; }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔮 Loomaa</h1>
            <p>Modern Semantic Model Viewer</p>
        </div>
        
        <div class="container">
            <div class="welcome-card">
                <h2>Welcome to Your Analytics Platform</h2>
                <p>
                    Experience enterprise-grade semantic modeling with clean, professional design. 
                    Built for analytics engineers who demand excellence in both functionality and user experience.
                </p>
                
                <div class="feature-grid">
                    <div class="feature-card">
                        <span class="feature-icon">📊</span>
                        <h3 class="feature-title">Model Overview</h3>
                        <p class="feature-desc">
                            Comprehensive view of your semantic models with intuitive navigation and detailed insights.
                        </p>
                    </div>
                    
                    <div class="feature-card">
                        <span class="feature-icon">🔗</span>
                        <h3 class="feature-title">Relationship Mapping</h3>
                        <p class="feature-desc">
                            Visualize complex relationships between tables and understand your data model architecture.
                        </p>
                    </div>
                    
                    <div class="feature-card">
                        <span class="feature-icon">📈</span>
                        <h3 class="feature-title">Measure Analysis</h3>
                        <p class="feature-desc">
                            Explore DAX measures, calculations, and business logic with professional presentation.
                        </p>
                    </div>
                    
                    <div class="feature-card">
                        <span class="feature-icon">⚡</span>
                        <h3 class="feature-title">Performance Focused</h3>
                        <p class="feature-desc">
                            Lightning-fast interface designed for productivity and enterprise-scale operations.
                        </p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <div class="footer-title">Loomaa</div>
            <div class="footer-subtitle">Professional Analytics by Abiodun Adenugba</div>
        </div>
    </body>
    </html>
    '''
    
    return HTMLResponse(html_content)


@app.command()
def validate():
    """Validate semantic model with warehouse/lakehouse context"""
    
    if not os.path.exists("model.py"):
        typer.echo("❌ model.py not found. Run 'loomaa init' first.")
        raise typer.Exit(1)
    
    try:
        # Import and validate the model
        sys.path.insert(0, os.getcwd())
        import model as model_module
        models = model_module.models
        
        # Validate each model
        for model_name, model in models.items():
            typer.echo(f"Validating model: {model_name}")
            
            # Use the validate_model function from validate.py
            validation_result = validate_model(model)
            
            if validation_result.get('valid', True):
                typer.echo("✅ Model validation completed successfully")
                typer.echo(f"📊 Found {len(model.tables)} tables, {len(model.measures)} measures")
                
                # Check for warnings
                warnings = validation_result.get('warnings', [])
                for warning in warnings:
                    typer.echo(f"⚠️  {warning}")
            else:
                errors = validation_result.get('errors', [])
                for error in errors:
                    typer.echo(f"❌ {error}")
                raise typer.Exit(1)
        
    except Exception as e:
        typer.echo(f"❌ Validation failed: {e}")
        raise typer.Exit(1)
@app.command()
def deploy(
    clean: bool = typer.Option(
        False, "--clean", help="Delete existing model first (clean redeploy). Default is in-place update"
    )
):
    """Deploy compiled semantic models to Fabric using PowerShell and .SemanticModel structure.
    
    Uses the proven PowerShell deployment method that matches the pipeline reference.
    """

    if not os.path.exists(".env"):
        typer.echo("❌ .env file not found. Configure authentication first.")
        raise typer.Exit(1)
    if not os.path.exists("compiled"):
        typer.echo("❌ Compiled models not found. Run 'loomaa compile' first.")
        raise typer.Exit(1)

    semantic_model_folders = [d for d in os.listdir("compiled") if d.endswith(".SemanticModel") and os.path.isdir(os.path.join("compiled", d))]
    if not semantic_model_folders:
        typer.echo("❌ No .SemanticModel folders found. Run 'loomaa compile' first.")
        raise typer.Exit(1)

    # Build deployment plan - PowerShell only
    deployment_plan = []
    for folder in semantic_model_folders:
        model_name = folder.replace(".SemanticModel", "")
        semantic_model_path = os.path.join("compiled", folder)
        
        # Validate .SemanticModel structure
        definition_path = os.path.join(semantic_model_path, "definition", "model.tmdl")
        if not os.path.exists(definition_path):
            typer.echo(f"❌ Invalid .SemanticModel structure for model: {model_name}")
            raise typer.Exit(1)
        deployment_plan.append((model_name, semantic_model_path))

    typer.echo(f"🚀 Deploying {len(deployment_plan)} model(s) using PowerShell + .SemanticModel:")
    for model_name, _ in deployment_plan:
        typer.echo(f"   • {model_name}{' + clean' if clean else ''}")

    successful, failed = [], []
    for model_name, semantic_model_path in deployment_plan:
        try:
            log(f"Deploying (PowerShell) {model_name}")
            deploy_complete_semantic_model(model_name, semantic_model_path)
            successful.append(model_name)
            typer.echo(f"✅ {model_name} deployed")
        except Exception as e:
            failed.append((model_name, str(e)))
            typer.echo(f"❌ {model_name} failed: {e}")

    # Summary
    if successful:
        typer.echo(f"✅ Successfully deployed {len(successful)} model(s)")
        for m in successful:
            typer.echo(f"   • {m}")
    if failed:
        typer.echo(f"❌ {len(failed)} model(s) failed:")
        for m, err in failed:
            typer.echo(f"   • {m}: {err}")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()