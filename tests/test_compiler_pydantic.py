"""
Test Pydantic Compiler - End-to-End Test
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from loomaa.models_pydantic import (
    SemanticModel, Table, Column, Measure, Relationship, 
    DataType, TableMode, Cardinality, CrossFilter
)
from loomaa.compiler_pydantic import compile_semantic_model

def test_compiler():
    """Test compiling a simple semantic model with Pydantic validation"""
    
    # Create the same model as before
    sales_table = Table(
        name="sales",
        table_schema="dbo",
        mode=TableMode.DIRECTLAKE,
        description="Simple sales table for testing",
        directlake_resource_id="12345678-1234-1234-1234-123456789012",
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
    
    relationship = Relationship(
        from_table=sales_table,
        from_column="CustomerID",
        to_table=customer_table,
        to_column="CustomerID",
        cardinality=Cardinality.MANY_TO_ONE,
        cross_filter_direction=CrossFilter.SINGLE,
        description="Sales to customer lookup"
    )
    
    model = SemanticModel(
        name="Test_Model",
        description="Simple test model",
        tables=[sales_table, customer_table],
        relationships=[relationship]
    )
    
    # Test compilation
    print("🔨 Compiling semantic model...")
    output_dir = "test_compiled"
    compile_semantic_model(model, output_dir)
    print(f"✅ Model compiled to: {output_dir}/")
    
    # Check if files were created
    import pathlib
    output_path = pathlib.Path(output_dir)
    if output_path.exists():
        files = list(output_path.rglob("*.tmdl"))
        print(f"📁 Generated {len(files)} TMDL files:")
        for file in files:
            print(f"   - {file.relative_to(output_path)}")
            
        # Show sample content from model.tmdl
        model_file = output_path / "Test_Model.SemanticModel" / "definition" / "model.tmdl"
        if model_file.exists():
            print(f"\n📄 Sample content from model.tmdl:")
            print("-" * 50)
            content = model_file.read_text()[:500]  # First 500 chars
            print(content)
            if len(model_file.read_text()) > 500:
                print("... (truncated)")
            print("-" * 50)
    
    assert model.table_count == 2
    assert model.relationship_count == 1
    assert model.column_count > 0

if __name__ == "__main__":
    try:
        model = test_compiler()
        print("✅ End-to-end test successful!")
        print(f"Model validated: {model.name} with {model.table_count} tables, {model.column_count} columns, {model.measure_count} measures")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise