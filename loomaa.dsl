from loomaa.model import SemanticModel, Table, Column, Measure, Relationship, CalculatedColumn
from jinja2 import Template

# Create semantic model with comprehensive structure
model = SemanticModel(name="Test Sales Model")

# Example: Sales fact table with advanced DAX using Jinja
sales_table = Table(
    name="Sales",
    mode="Import",  # Import or DirectLake
    description="Sales transaction fact table with comprehensive metrics",
    columns=[
        Column("SalesOrderID", "Integer", description="Primary key - unique order identifier"),
        Column("CustomerID", "Integer", description="Foreign key to Customer dimension"),
        Column("ProductID", "Integer", description="Foreign key to Product dimension"),
        Column("OrderDate", "DateTime", description="Date of the sale transaction"),
        Column("SalesAmount", "Currency", description="Revenue amount in local currency", 
               format_string="$#,##0.00"),
        Column("Quantity", "Integer", description="Units sold"),
        Column("UnitPrice", "Currency", description="Price per unit"),
    ],
    measures=[
        Measure(
            name="Total Sales",
            expression="SUM(Sales[SalesAmount])",
            description="Sum of all sales amounts",
            format_string="$#,##0",
            folder="Key Metrics"
        ),
        Measure(
            name="Total Quantity",
            expression="SUM(Sales[Quantity])",
            description="Total units sold across all products",
            format_string="#,##0"
        ),
        # Advanced time intelligence using Jinja templates
        Measure(
            name="Sales YTD",
            expression=Template('''
            TOTALYTD(
                [{base_measure}],
                {date_column}[Date]
            )
            ''').render(base_measure="Total Sales", date_column="'Date'"),
            description="Year-to-date sales calculation",
            folder="Time Intelligence"
        ),
        # Complex DAX with dynamic filtering using Jinja
        Measure(
            name="Sales Growth %",
            expression=Template('''
            VAR CurrentPeriod = [{base_measure}]
            VAR PreviousPeriod = 
                CALCULATE(
                    [{base_measure}],
                    SAMEPERIODLASTYEAR({date_column}[Date])
                )
            RETURN
                DIVIDE(CurrentPeriod - PreviousPeriod, PreviousPeriod, 0)
            ''').render(base_measure="Total Sales", date_column="'Date'"),
            description="Year-over-year sales growth percentage",
            format_string="0.00%",
            folder="Time Intelligence"
        ),
    ],
    calculated_columns=[
        CalculatedColumn(
            name="Profit Margin",
            expression="DIVIDE([SalesAmount] - ([UnitPrice] * [Quantity]), [SalesAmount], 0)",
            description="Calculated profit margin percentage",
            format_string="0.00%"
        )
    ]
)

# Customer dimension table
customer_table = Table(
    name="Customer",
    mode="Import",
    description="Customer dimension with hierarchical attributes",
    columns=[
        Column("CustomerID", "Integer", description="Primary key - unique customer identifier"),
        Column("CustomerName", "Text", description="Full customer name"),
        Column("City", "Text", description="Customer city"),
        Column("State", "Text", description="Customer state/province"),
        Column("Country", "Text", description="Customer country"),
        Column("CustomerSegment", "Text", description="Business segment classification"),
        Column("CustomerType", "Text", description="Individual vs Corporate classification"),
    ],
    measures=[
        Measure(
            name="Customer Count",
            expression="DISTINCTCOUNT(Customer[CustomerID])",
            description="Unique count of customers",
            folder="Customer Metrics"
        ),
        Measure(
            name="Active Customers",
            expression=Template('''
            CALCULATE(
                [Customer Count],
                {sales_table}[OrderDate] >= {period_start},
                {sales_table}[OrderDate] <= {period_end}
            )
            ''').render(
                sales_table="Sales",
                period_start="DATE(YEAR(TODAY())-1, 1, 1)",
                period_end="TODAY()"
            ),
            description="Customers with sales in the last 12 months"
        )
    ]
)

# Product dimension (example of comprehensive product catalog)
product_table = Table(
    name="Product",
    mode="Import",
    description="Product dimension with hierarchical categories",
    columns=[
        Column("ProductID", "Integer", description="Primary key - unique product identifier"),
        Column("ProductName", "Text", description="Product display name"),
        Column("Category", "Text", description="Top-level product category"),
        Column("SubCategory", "Text", description="Product subcategory"),
        Column("Brand", "Text", description="Product brand"),
        Column("UnitCost", "Currency", description="Standard unit cost"),
        Column("ListPrice", "Currency", description="Recommended retail price"),
    ]
)

# Add tables to model
model.add_table(sales_table)
model.add_table(customer_table)
model.add_table(product_table)

# Define relationships with full metadata
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

# Model-level measures (not tied to specific tables)
model.add_measure(
    Measure(
        name="Sales per Customer",
        expression="DIVIDE([Total Sales], [Customer Count], 0)",
        description="Average sales amount per customer",
        format_string="$#,##0.00",
        folder="Calculated KPIs"
    )
)

model.add_measure(
    Measure(
        name="Average Order Value",
        expression="DIVIDE([Total Sales], DISTINCTCOUNT(Sales[SalesOrderID]), 0)",
        description="Average revenue per order",
        format_string="$#,##0.00",
        folder="Calculated KPIs"
    )
)