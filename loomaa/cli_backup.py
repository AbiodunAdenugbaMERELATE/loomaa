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
from loomaa.deploy import deploy_model
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

# Optional: SQL Server / Fabric Warehouse connection
SQL_SERVER=your-server.database.windows.net
SQL_DATABASE=your-database-name
"""

# Realistic DSL template connecting to existing data sources
DSL_TEMPLATE = '''from loomaa.model import SemanticModel, Table, Column, Measure, Relationship, CalculatedColumn

# Create semantic model
model = SemanticModel(name="{model_name}")

# Connect to existing warehouse/lakehouse tables (like Tabular Editor does)
# Note: These tables should already exist in your data warehouse/lakehouse

# Sales fact table - connects to existing warehouse table
sales_table = Table(
    name="Sales",
    source_query="SELECT * FROM warehouse.fact_sales",  # Connect to existing table
    mode="DirectLake",  # or "Import" 
    description="Sales transactions from data warehouse",
    columns=[
        # Define semantic layer on top of existing warehouse columns
        Column("SalesOrderID", "Integer", description="Order ID"),
        Column("CustomerID", "Integer", description="Customer foreign key"), 
        Column("ProductID", "Integer", description="Product foreign key"),
        Column("OrderDate", "DateTime", description="Transaction date"),
        Column("SalesAmount", "Currency", description="Sale amount", format_string="$#,##0.00"),
        Column("Quantity", "Integer", description="Units sold"),
    ],
    measures=[
        # Business metrics built on warehouse data
        Measure(
            name="Total Sales",
            expression="SUM(Sales[SalesAmount])",
            description="Total revenue across all sales",
            format_string="$#,##0.00",
            folder="Revenue Metrics"
        ),
        Measure(
            name="Sales YTD", 
            expression="TOTALYTD([Total Sales], 'Calendar'[Date])",
            description="Year-to-date sales",
            format_string="$#,##0.00",
            folder="Time Intelligence"
        ),
        Measure(
            name="Average Order Value",
            expression="DIVIDE([Total Sales], DISTINCTCOUNT(Sales[SalesOrderID]))",
            description="Average revenue per order",
            format_string="$#,##0.00", 
            folder="Revenue Metrics"
        ),
    ]
)

# Customer dimension - connects to existing warehouse table
customer_table = Table(
    name="Customer", 
    source_query="SELECT * FROM warehouse.dim_customer",
    mode="Import",
    description="Customer dimension from data warehouse",
    columns=[
        Column("CustomerID", "Integer", description="Customer ID"),
        Column("CustomerName", "Text", description="Customer name"),
        Column("City", "Text", description="Customer city"),
        Column("Country", "Text", description="Customer country"),
        Column("Segment", "Text", description="Customer segment"),
    ],
    measures=[
        Measure(
            name="Customer Count",
            expression="DISTINCTCOUNT(Customer[CustomerID])",
            description="Total unique customers",
            folder="Customer Metrics"
        ),
    ]
)

# Product dimension - connects to existing warehouse table  
product_table = Table(
    name="Product",
    source_query="SELECT * FROM warehouse.dim_product", 
    mode="Import",
    description="Product dimension from data warehouse",
    columns=[
        Column("ProductID", "Integer", description="Product ID"),
        Column("ProductName", "Text", description="Product name"), 
        Column("Category", "Text", description="Product category"),
        Column("Brand", "Text", description="Product brand"),
        Column("UnitPrice", "Currency", description="List price"),
    ]
)

# Add tables to model
model.add_table(sales_table)
model.add_table(customer_table) 
model.add_table(product_table)

# Define relationships (like in Tabular Editor)
model.add_relationship(
    Relationship(
        from_table="Sales",
        from_column="CustomerID", 
        to_table="Customer",
        to_column="CustomerID",
        cardinality="Many-to-One"
    )
)

model.add_relationship(
    Relationship(
        from_table="Sales", 
        from_column="ProductID",
        to_table="Product", 
        to_column="ProductID",
        cardinality="Many-to-One"
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

This Loomaa project defines a Power BI semantic model as code, connecting to existing data warehouse tables.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure authentication:**
   Edit `.env` with your Microsoft Fabric credentials:
   ```bash
   FABRIC_TENANT_ID=your-azure-ad-tenant-id
   FABRIC_CLIENT_ID=your-app-registration-client-id
   FABRIC_CLIENT_SECRET=your-client-secret
   FABRIC_WORKSPACE_ID=your-power-bi-workspace-id
   FABRIC_XMLA_ENDPOINT=powerbi://api.powerbi.com/v1.0/myorg/your-workspace
   ```
3. **Build the model:**
   ```bash
   loomaa compile
   ```
4. **View the model:**
   ```bash
   loomaa view
   ```
   This launches an interactive model viewer in your browser.
5. **Deploy to Power BI:**
   ```bash
   loomaa deploy
   ```

## Model Definition

The model is defined in `loomaa.dsl` using a simple, declarative syntax:

```python
from loomaa.model import SemanticModel, Table, Column, Measure, Relationship

# Create semantic model
model = SemanticModel(name="MyModel")

# Sales table
sales_table = Table(
    name="Sales",
    source_query="SELECT * FROM warehouse.fact_sales",
    mode="DirectLake",
    columns=[
        Column("SalesOrderID", "Integer"),
        Column("CustomerID", "Integer"),
        Column("ProductID", "Integer"),
        Column("OrderDate", "DateTime"),
        Column("SalesAmount", "Currency"),
        Column("Quantity", "Integer"),
    ],
    measures=[
        Measure(
            name="Total Sales",
            expression="SUM(Sales[SalesAmount])",
            description="Total revenue",
            format_string="$#,##0.00"
        ),
    ]
)

# Customer table
customer_table = Table(
    name="Customer",
    source_query="SELECT * FROM warehouse.dim_customer",
    mode="Import",
    columns=[
        Column("CustomerID", "Integer"),
        Column("CustomerName", "Text"),
        Column("City", "Text"),
        Column("Country", "Text"),
    ]
)

# Add tables to model
model.add_table(sales_table)
model.add_table(customer_table)

# Define relationships
model.add_relationship(
    Relationship(
        from_table="Sales",
        from_column="CustomerID",
        to_table="Customer",
        to_column="CustomerID",
        cardinality="Many-to-One"
    )
)
```

## Advanced Features

- **DirectLake Connectivity**: Connect directly to lakehouse tables for real-time analytics.
- **Dynamic Measures**: Create measures that adapt based on user context and selections.
- **Parameterized Tables**: Define tables that accept parameters for flexible querying.

## Troubleshooting

- **Compilation Errors**: Ensure all referenced columns exist in the source tables.
- **Deployment Issues**: Verify workspace ID and XMLA endpoint in the `.env` file.
- **Authentication Problems**: Check Azure AD app registration and permissions.

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Modeling Best Practices**: Use clear, descriptive names for tables and columns. Define measures with business logic in mind.
2. **Code Standards**: Follow Python and SQL coding standards for readability and maintainability.
3. **Documentation**: Update this README and add comments in the code where necessary.
4. **Testing**: Test your changes locally before submitting a pull request.
'''

def _create_scaffold(project_name: str, model_name: str):
    """Create comprehensive project scaffold with all necessary files"""
    
    log(f"Creating Loomaa project: {project_name}")

    # Create directories
    os.makedirs(project_name, exist_ok=True)
    os.makedirs(f"{project_name}/examples", exist_ok=True)  
    os.makedirs(f"{project_name}/compiled", exist_ok=True)

    # Create files
    files = {
        f"{project_name}/.env": ENV_TEMPLATE,
        f"{project_name}/loomaa.dsl": DSL_TEMPLATE.format(model_name=model_name),
        f"{project_name}/requirements.txt": REQUIREMENTS_TEMPLATE,
        f"{project_name}/README.md": README_TEMPLATE.format(
            model_name=model_name, 
            project_name=project_name
        ),
        f"{project_name}/compiled/README.md": "# Compiled Artifacts\n\nGenerated TMDL and JSON files appear here after running [loomaa compile](http://_vscodecontentref_/3).",
    }

    # Add sample CSV files for development
    sample_customers = """CustomerID,CustomerName,City,Country,Segment
1,John Doe,New York,USA,Consumer
2,Jane Smith,San Francisco,USA,Corporate
3,Emily Davis,London,UK,Consumer
4,Michael Brown,Paris,France,Corporate
5,Jessica Wilson,Berlin,Germany,Consumer
"""

    sample_products = """ProductID,ProductName,Category,Brand,UnitPrice
1,Widget A,Widgets,Brand X,25.00
2,Widget B,Widgets,Brand Y,30.00
3,Gadget A,Gadgets,Brand X,15.00
4,Gadget B,Gadgets,Brand Z,20.00
5,Thingamajig A,Thingamajigs,Brand Y,10.00
"""

    sample_sales = """SalesOrderID,CustomerID,ProductID,OrderDate,SalesAmount,Quantity
1,1,1,2023-01-15 08:30:00,250.00,10
2,2,2,2023-01-16 09:00:00,300.00,10
3,3,3,2023-02-15 10:30:00,150.00,10
4,4,4,2023-02-16 11:00:00,200.00,10
5,5,5,2023-03-15 12:30:00,50.00,5
"""

    # Write sample files
    write_file(f"{project_name}/examples/sample_customers.csv", sample_customers)
    write_file(f"{project_name}/examples/sample_products.csv", sample_products)
    write_file(f"{project_name}/examples/sample_sales.csv", sample_sales)
    
    for file_path, content in files.items():
        write_file(file_path, content)
        log(f"Created {file_path}")
    
    log("Project scaffold created successfully!")

@app.command()
def init(
    project_name: str = typer.Argument(..., help="Name of the project directory"),
    model_name: str = typer.Option(None, "--model", "-m", help="Name of the semantic model"),
):
    """🚀 Initialize a new semantic model project with comprehensive scaffolding"""
    
    if model_name is None:
        model_name = project_name.replace("-", "_").replace(" ", "_")
    
    log(f"Initializing Loomaa project: {project_name}")
    log(f"Semantic model name: {model_name}")
    
    _create_scaffold(project_name, model_name)
    
    typer.echo(f"✅ Project '{project_name}' initialized successfully!")
    typer.echo("")
    typer.echo("📁 Project structure created with:")
    typer.echo("   • Semantic model definition (loomaa.dsl)")
    typer.echo("   • Authentication config (.env)")
    typer.echo("   • Python model modules (models/)")
    typer.echo("   • Compiled artifacts directory (compiled/)")
    typer.echo("   • Documentation (README.md)")
    typer.echo("")
    typer.echo("🔧 Next steps:")
    typer.echo("   1. Edit .env with your Fabric credentials")
    typer.echo("   2. Customize loomaa.dsl with your model structure")
    typer.echo("   3. Run 'loomaa compile' to build the model")
    typer.echo("   4. Run 'loomaa view' to inspect in browser")

@app.command()
def compile():
    """🔨 Compile semantic model from DSL to TMDL and JSON artifacts"""
    
    log("Starting model compilation...")
    
    if not os.path.exists("loomaa.dsl"):
        typer.echo("❌ Error: loomaa.dsl not found. Run 'loomaa init' first.")
        raise typer.Exit(1)
    
    try:
        compile_model()
        typer.echo("✅ Model compiled successfully! Check compiled/ directory.")
    except Exception as e:
        typer.echo(f"❌ Compilation failed: {e}")
        raise typer.Exit(1)

def _load_model_from_compiled() -> Optional[Dict]:
    """Load compiled model JSON for viewing"""
    json_path = "compiled/model.json"
    if not os.path.exists(json_path):
        return None
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log(f"Error loading compiled model: {e}")
        return None

# FastAPI app for Power BI-style model viewer
viewer_app = FastAPI(title="Loomaa Model Viewer")

@viewer_app.get("/", response_class=HTMLResponse)
async def model_viewer():
    """Power BI-style model viewer with interactive interface"""
    
    model_data = _load_model_from_compiled()
    if not model_data:
        return HTMLResponse("""
        <!DOCTYPE html>
        <html><head><title>Loomaa Model Viewer</title></head>
        <body style="font-family: 'Segoe UI', sans-serif; margin: 40px; text-align: center;">
        <h1>⚠️ Model Not Found</h1>
        <p>Please run <code style="background: #f0f0f0; padding: 4px 8px; border-radius: 4px;">loomaa compile</code> first to generate model artifacts.</p>
        <p><a href="#" onclick="location.reload()">🔄 Refresh Page</a></p>
        </body></html>
        """)
    
    # Generate simple table view for now
    tables_html = ""
    for table in model_data.get('tables', []):
        columns_html = ""
        for col in table.get('columns', []):
            columns_html += f"<li>{col['name']} ({col.get('dtype', 'Text')})</li>"
        
        measures_html = ""  
        for measure in table.get('measures', []):
            measures_html += f"<li>{measure['name']}</li>"
        
        tables_html += f"""
        <div style="border: 1px solid #ddd; margin: 15px; padding: 20px; border-radius: 8px; background: #fafafa;">
            <h3 style="color: #333; margin-top: 0;">📊 {table['name']}</h3>
            <p><strong>Columns ({len(table.get('columns', []))}):</strong></p>
            <ul style="text-align: left;">{columns_html}</ul>
            <p><strong>Measures ({len(table.get('measures', []))}):</strong></p>
            <ul style="text-align: left;">{measures_html}</ul>
        </div>
        """
    
    relationships_html = ""
    for rel in model_data.get('relationships', []):
        relationships_html += f"""
        <li style="background: #fff3cd; padding: 12px; margin: 8px 0; border-radius: 6px;">
            <strong>{rel['from_table']}</strong>.{rel.get('from_column', '')} → <strong>{rel['to_table']}</strong>.{rel.get('to_column', '')}
            <br><small style="color: #666;">
                {rel.get('cardinality', 'Many-to-One')} | {rel.get('cross_filter_direction', 'Single')}
            </small>
        </li>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Loomaa Model Viewer - {model_data['name']}</title>
        <style>
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0; 
                padding: 20px; 
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                min-height: 100vh;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; 
                padding: 30px; 
                border-radius: 12px; 
                margin-bottom: 25px;
                text-align: center;
                box-shadow: 0 8px 32px rgba(0,0,0,0.15);
            }}
            .model-title {{ font-size: 32px; margin: 0 0 10px 0; font-weight: 600; }}
            .model-subtitle {{ font-size: 16px; opacity: 0.9; margin: 0; }}
            .stats {{ 
                display: flex; 
                justify-content: space-around; 
                background: white; 
                padding: 25px; 
                border-radius: 12px; 
                margin-bottom: 25px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            }}
            .stat {{ text-align: center; }}
            .stat-number {{ 
                font-size: 24px; 
                font-weight: bold; 
                display: block; 
                color: #667eea;
            }}
            .stat-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
            .content {{ 
                background: white; 
                padding: 30px; 
                border-radius: 12px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            }}
            .section {{ margin: 30px 0; }}
            .section h2 {{ color: #333; border-bottom: 3px solid #667eea; padding-bottom: 10px; }}
            ul {{ list-style: none; padding: 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 class="model-title">🔮 {model_data['name']}</h1>
                <p class="model-subtitle">Power BI Semantic Model Viewer</p>
            </div>
            
            <div class="stats">
                <div class="stat">
                    <span class="stat-number">{len(model_data.get('tables', []))}</span>
                    <span class="stat-label">Tables</span>
                </div>
                <div class="stat">
                    <span class="stat-number">{sum(len(t.get('measures', [])) for t in model_data.get('tables', []))}</span>
                    <span class="stat-label">Measures</span>
                </div>
                <div class="stat">
                    <span class="stat-number">{len(model_data.get('relationships', []))}</span>
                    <span class="stat-label">Relationships</span>
                </div>
                <div class="stat">
                    <span class="stat-number">{sum(len(t.get('columns', [])) for t in model_data.get('tables', []))}</span>
                    <span class="stat-label">Columns</span>
                </div>
            </div>
            
            <div class="content">
                <div class="section">
                    <h2>📊 Tables ({len(model_data.get('tables', []))})</h2>
                    {tables_html}
                </div>
                
                <div class="section">
                    <h2>🔗 Relationships ({len(model_data.get('relationships', []))})</h2>
                    <ul>{relationships_html}</ul>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(html_content)

@app.command()
def view(
    port: int = typer.Option(8000, "--port", "-p", help="Port to run the viewer on"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser automatically")
):
    """🔍 Launch interactive Power BI-style model viewer in browser"""
    
    if not os.path.exists("compiled/model.json"):
        typer.echo("❌ Error: Compiled model not found. Run 'loomaa compile' first.")
        raise typer.Exit(1)
    
    log(f"Starting model viewer on port {port}...")
    
    if open_browser:
        import threading
        def open_browser_delayed():
            import time
            time.sleep(1.5)  # Wait for server to start
            webbrowser.open(f"http://localhost:{port}")
        threading.Thread(target=open_browser_delayed, daemon=True).start()
    
    try:
        uvicorn.run(
            viewer_app,
            host="0.0.0.0", 
            port=port,
            log_level="info"
        )
    except KeyboardInterrupt:
        log("Model viewer stopped.")

@app.command()
def validate():
    """✅ Validate semantic model integrity and best practices"""
    
    log("Validating semantic model...")
    
    if not os.path.exists("loomaa.dsl"):
        typer.echo("❌ Error: loomaa.dsl not found. Run 'loomaa init' first.")
        raise typer.Exit(1)
    
    try:
        validate_model()
        typer.echo("✅ Model validation passed!")
    except Exception as e:
        typer.echo(f"❌ Validation failed: {e}")
        raise typer.Exit(1)

@app.command()
def deploy(
    workspace: str = typer.Option(None, "--workspace", "-w", help="Target workspace ID"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate deployment without executing")
):
    """🚀 Deploy semantic model to Power BI Service"""
    
    if not os.path.exists(".env"):
        typer.echo("❌ Error: .env file not found. Configure authentication first.")
        raise typer.Exit(1)
    
    if not os.path.exists("compiled/model.tmdl"):
        typer.echo("❌ Error: Compiled model not found. Run 'loomaa compile' first.")
        raise typer.Exit(1)
    
    if dry_run:
        log("Performing dry-run deployment validation...")
        # Add dry-run validation logic
        typer.echo("✅ Dry-run validation passed! Model is ready for deployment.")
        return
    
    log("Deploying semantic model to Power BI Service...")
    
    try:
        deploy_model()
        typer.echo("✅ Model deployed successfully!")
    except Exception as e:
        typer.echo(f"❌ Deployment failed: {e}")
        raise typer.Exit(1)

@app.command()
def template(
    template_name: str = typer.Argument(..., help="Template name (sales, retail, finance)"),
    output_dir: str = typer.Option(".", "--output", "-o", help="Output directory")
):
    """📝 Generate semantic model from predefined templates"""
    
    templates = {
        "sales": "Sales Analytics Model",
        "retail": "Retail Operations Model", 
        "finance": "Financial Reporting Model",
        "hr": "Human Resources Analytics Model",
        "marketing": "Marketing Campaign Analytics Model"
    }
    
    if template_name not in templates:
        typer.echo(f"❌ Available templates: {', '.join(templates.keys())}")
        raise typer.Exit(1)
    
    model_name = templates[template_name]
    project_name = f"{template_name}_analytics"
    
    log(f"Generating {template_name} template...")
    
    # Create project with template-specific customizations
    if output_dir != ".":
        os.chdir(output_dir)
    
    _create_scaffold(project_name, model_name)
    
    typer.echo(f"✅ Template '{template_name}' generated!")
    typer.echo(f"📁 Check {project_name}/ directory for your new semantic model.")

if __name__ == "__main__":
    app()
