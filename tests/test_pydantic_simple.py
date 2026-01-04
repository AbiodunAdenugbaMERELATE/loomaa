"""
Test Pydantic Architecture with Simple Example
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'loomaa'))

from loomaa.models_pydantic import (
    SemanticModel, Table, Column, Measure, Relationship, 
    DataType, TableMode, Cardinality, CrossFilter
)

def test_simple_pydantic_model():
    """Test creating a simple semantic model with Pydantic validation"""
    
    # Create a simple sales table
    sales_table = Table(
        name="sales",
        table_schema="dbo",
        mode=TableMode.DIRECTLAKE,
        description="Simple sales table for testing",
        directlake_resource_id="12345678-1234-1234-1234-123456789012",  # Example GUID
        columns=[
            Column(name="SalesID", dtype=DataType.INT64, description="Sale ID"),
            Column(name="CustomerID", dtype=DataType.INT64, description="Customer ID"),
            Column(name="Amount", dtype=DataType.DECIMAL, description="Sale amount", format_string="$#,##0.00"),
        ],
        measures=[
            Measure(
                name="Total Sales",
                expression="SUM(sales[Amount])",
                description="Total sales amount"
            )
        ]
    )
    
    # Create a simple customer table
    customer_table = Table(
        name="customers",
        table_schema="dbo", 
        mode=TableMode.IMPORT,
        description="Customer dimension table",
        sql_server="test-server.database.windows.net",
        columns=[
            Column(name="CustomerID", dtype=DataType.INT64, description="Customer ID"),
            Column(name="CustomerName", dtype=DataType.STRING, description="Customer name"),
        ]
    )
    
    # Create relationship
    relationship = Relationship(
        from_table=sales_table,
        from_column="CustomerID",
        to_table=customer_table,
        to_column="CustomerID",
        cardinality=Cardinality.MANY_TO_ONE,
        cross_filter_direction=CrossFilter.SINGLE,
        description="Sales to customer lookup"
    )
    
    # Create semantic model
    model = SemanticModel(
        name="Test_Model",
        description="Simple test model",
        tables=[sales_table, customer_table],
        relationships=[relationship]
    )
    
    assert model.table_count == 2
    assert model.relationship_count == 1
    assert model.column_count > 0
    assert model.measure_count > 0

if __name__ == "__main__":
    # Test the model creation
    try:
        model = test_simple_pydantic_model()
        print("✅ Pydantic model created successfully!")
        print(f"Model: {model.name}")
        print(f"Tables: {len(model.tables)}")
        print(f"Relationships: {len(model.relationships)}")
        print(f"Total columns: {model.column_count}")
        print(f"Total measures: {model.measure_count}")
        
        # Test computed properties
        print(f"Database reference for sales table: {model.tables[0].database_reference}")
        print(f"TMDL table name for sales table: {model.tables[0].tmdl_table_name}")
        
    except Exception as e:
        print(f"❌ Error creating model: {e}")
        raise