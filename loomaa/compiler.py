import os
import json
import uuid
from loomaa.utils import write_file

def generate_lineage_tag():
    """Generate a unique lineage tag for Power BI objects"""
    return str(uuid.uuid4())

def generate_platform_file(model_name):
    """Generate .platform file for PBIP format with correct displayName"""
    return '''{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
  "metadata": {
    "type": "SemanticModel",
    "displayName": "''' + model_name + '''"
  },
  "config": {
    "version": "2.0",
    "logicalId": "''' + str(uuid.uuid4()) + '''"
  }
}'''

def generate_pbism_file(model_name):
    """Generate definition.pbism file matching CE Accrual format"""
    return '''{
  "version": "4.0",
  "settings": {}
}'''

def generate_database_tmdl(model):
    """Generate database.tmdl file matching CE Accrual format"""
    return '''database
	compatibilityLevel: 1604

'''

def generate_model_tmdl(model):
    """Generate model.tmdl matching CE Accrual format with tabs"""
    content = '''model Model
\tculture: en-US
\tdefaultPowerBIDataSourceVersion: powerBI_V3
\tsourceQueryCulture: en-US
\tdataAccessOptions
\t\tlegacyRedirects
\t\treturnErrorValuesAsNull

\tannotation __PBI_TimeIntelligenceEnabled = 1
\tannotation PBIDesktopVersion = 2.133.7221.0 (24.09)
\tannotation PBI_ProTooling = ["DevMode"]

'''
    return content

def generate_expressions_tmdl(model):
    """Generate DirectLake expressions dynamically based on table resource IDs"""
    workspace_id = os.getenv("FABRIC_WORKSPACE_ID", "your-workspace-id")
    
    # Collect unique DirectLake resource IDs from all tables
    directlake_resources = set()
    for table in getattr(model, 'tables', []):
        table_mode = getattr(table, 'mode', 'import')
        if hasattr(table_mode, 'value'):
            table_mode = table_mode.value.lower()
        if 'directlake' in str(table_mode).lower():
            resource_id = getattr(table, 'directlake_resource_id', None)
            if resource_id:
                directlake_resources.add(resource_id)
    
    if not directlake_resources:
        return "/// No DirectLake connections needed\n\n"
    
    content = "/// DirectLake connections to OneLake resources\n\n"
    
    # Generate expression for each unique DirectLake resource
    for resource_id in directlake_resources:
        expression_name = f"DirectLake - {resource_id[:8]}"  # Use first 8 chars as identifier
        content += f'''expression '{expression_name}' =
\tlet
\t\tSource = AzureStorage.DataLake("https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{resource_id}", [HierarchicalNavigation=true])
\tin
\t\tSource
\tlineageTag: {generate_lineage_tag()}

\tannotation PBI_IncludeFutureArtifacts = False

'''
    
    return content

def generate_relationships_tmdl(relationships, model=None):
    """Generate relationships.tmdl content given a list of relationship objects."""
    if not relationships:
        return ""
    lines = []
    for rel in relationships:
        rel_tag = generate_lineage_tag()
        lines.append(f"relationship {rel_tag}")
        
        # Get the correct table names for relationships (use display_name or actual TMDL name)
        from_table_name = get_relationship_table_name(rel.from_table, model)
        to_table_name = get_relationship_table_name(rel.to_table, model)
        
        lines.append(f"\tfromColumn: {from_table_name}[{rel.from_column}]")
        lines.append(f"\ttoColumn: {to_table_name}[{rel.to_column}]")
        # Cardinality mapping
        card = getattr(rel, 'cardinality', 'manyToOne')
        if hasattr(card, 'value'):
            card = card.value
        # Power BI infers cardinality automatically, only specify cross-filtering if not default
        cross = getattr(rel, 'cross_filter_direction', 'oneDirection')
        if hasattr(cross, 'value'):
            cross = cross.value
        if cross != 'oneDirection':
            lines.append(f"\tcrossFilteringBehavior: {cross}")
        lines.append("")
    
    return "\n".join(lines)
    return "\n".join(lines)

def convert_dtype_to_power_bi(dtype):
    """Convert DSL data types to Power BI TMDL data types"""
    dtype_map = {
        'string': 'string',
        'text': 'string', 
        'int': 'int64',
        'integer': 'int64',
        'int64': 'int64',  # Add this - actual DataTypes.INTEGER value
        'float': 'double',
        'double': 'double',  # Add this - actual DataTypes.DOUBLE value
        'currency': 'decimal',
        'decimal': 'decimal',  # Add this - actual DataTypes.CURRENCY value
        'datetime': 'dateTime',
        'dateTime': 'dateTime',  # Add this - actual DataTypes.DATETIME value
        'date': 'dateTime',
        'bool': 'boolean',
        'boolean': 'boolean'
    }
    return dtype_map.get(dtype.lower(), 'string')

def generate_culture_tmdl():
    """Generate culture file matching CE Accrual format"""
    return '''cultureInfo en-US

'''

def generate_role_tmdl(role_name, description=""):
    """Generate role TMDL file"""
    lineage_tag = generate_lineage_tag()
    return f'''role '{role_name}'
  modelPermission: read
  lineageTag: {lineage_tag}

  annotation PBI_Id = {generate_lineage_tag()}

'''

def generate_model_json(model):
    """Generate a lightweight JSON representation of the model for reference."""
    def table_to_dict(table):
        return {
            "name": table.name,
            "mode": getattr(table, 'mode', 'import'),
            "source_query": getattr(table, 'source_query', ''),
            "columns": [
                {"name": c.name, "dtype": getattr(c, 'dtype', 'string')} for c in getattr(table, 'columns', [])
            ],
            "measures": [
                {"name": m.name, "expression": m.expression} for m in getattr(table, 'measures', [])
            ]
        }
    model_dict = {
        "name": getattr(model, 'name', 'Model'),
        "tables": [table_to_dict(t) for t in getattr(model, 'tables', [])],
        "measures": [
            {"name": m.name, "expression": m.expression} for m in getattr(model, 'measures', [])
        ],
        "relationships": [
            {
                "from_table": r.from_table,
                "from_column": r.from_column,
                "to_table": r.to_table,
                "to_column": r.to_column,
                "cardinality": getattr(r, 'cardinality', 'manyToOne'),
                "cross_filter_direction": getattr(r, 'cross_filter_direction', 'oneDirection'),
                "is_active": getattr(r, 'is_active', True)
            } for r in getattr(model, 'relationships', [])
        ]
    }
    return json.dumps(model_dict, indent=2)

def create_complete_semantic_model_structure(semantic_model_dir, model_name, json_content, model):
    """Create complete .SemanticModel structure matching CE Accrual reference format."""
    import shutil
    if os.path.exists(semantic_model_dir):
        shutil.rmtree(semantic_model_dir)
    os.makedirs(semantic_model_dir)
    
    definition_dir = os.path.join(semantic_model_dir, 'definition')
    os.makedirs(definition_dir, exist_ok=True)
    
    # Generate all files with correct format
    write_file(os.path.join(definition_dir, 'model.tmdl'), generate_model_tmdl(model))
    write_file(os.path.join(definition_dir, 'database.tmdl'), generate_database_tmdl(model))
    write_file(os.path.join(definition_dir, 'expressions.tmdl'), generate_expressions_tmdl(model))
    write_file(os.path.join(definition_dir, 'relationships.tmdl'), generate_relationships_tmdl(getattr(model, 'relationships', []), model))
    
    # Individual table files
    tables_dir = os.path.join(definition_dir, 'tables')
    os.makedirs(tables_dir, exist_ok=True)
    for table in getattr(model, 'tables', []):
        table_content = generate_individual_table_tmdl(table)
        if table_content:
            write_file(os.path.join(tables_dir, f"{table.name}.tmdl"), table_content)
    
    # Cultures
    cultures_dir = os.path.join(definition_dir, 'cultures')
    os.makedirs(cultures_dir, exist_ok=True)
    write_file(os.path.join(cultures_dir, 'en-US.tmdl'), generate_culture_tmdl())
    
    # Root files  
    write_file(os.path.join(semantic_model_dir, 'definition.pbism'), generate_pbism_file(model_name))
    write_file(os.path.join(semantic_model_dir, '.platform'), generate_platform_file(model_name))
    
    # Reference files
    write_file(os.path.join(semantic_model_dir, 'model.json'), json_content)
    readme = generate_model_readme(model, model_name)
    write_file(os.path.join(semantic_model_dir, 'README.md'), readme)

def compile_model():
    """
    Compile semantic models to TMDL and JSON formats
    Based on real Power BI TMDL structure analysis
    """
    model_path = "model.py"
    compiled_dir = "compiled"
    
    if not os.path.exists(model_path):
        print("[loomaa] model.py not found. Run 'loomaa init' first.")
        return
        
    print("[loomaa] Executing model.py to build semantic model...")
    
    # Execute model.py and extract models
    scope = {}
    try:
        import sys
        if os.getcwd() not in sys.path:
            sys.path.insert(0, os.getcwd())
        with open(model_path, 'r', encoding='utf-8') as f:
            code = f.read()
        exec(code, scope)
        models = scope.get('models')
        if models is None:
            model = scope.get('model')
            if model is None:
                print("[loomaa] No 'models' dictionary or 'model' object found in model.py.")
                return
            models = {"main": model}
    except Exception as e:
        print(f"[loomaa] Error executing model.py: {e}")
        return
    
    os.makedirs(compiled_dir, exist_ok=True)

    # Generate artifacts for each model
    for model_name, model in models.items():
        print(f"[loomaa] Compiling model '{model_name}' to .SemanticModel structure...")
        json_content = generate_model_json(model)
        semantic_model_dir = os.path.join(compiled_dir, f"{model_name}.SemanticModel")
        create_complete_semantic_model_structure(semantic_model_dir, model_name, json_content, model)

    return True

def generate_model_readme(model, model_name):
    """Generate README.md file for each model"""
    
    table_count = len(getattr(model, 'tables', []))
    relationship_count = len(getattr(model, 'relationships', []))
    measure_count = len(getattr(model, 'measures', []))
    
    # Count table-level measures
    table_measure_count = 0
    for table in getattr(model, 'tables', []):
        table_measure_count += len(getattr(table, 'measures', []))
    
    total_measures = measure_count + table_measure_count
    
    return f'''# {getattr(model, 'name', model_name)} - Semantic Model

Generated by **Loomaa** semantic modeling framework.

## 📊 Model Overview

- **Tables:** {table_count}
- **Relationships:** {relationship_count} 
- **Measures:** {total_measures} ({measure_count} model-level, {table_measure_count} table-level)
- **Description:** {getattr(model, 'description', 'No description provided')}

## 🏗️ Architecture

### Tables
{chr(10).join([f"- **{table.name}** ({getattr(table, 'mode', 'Import')}) - {getattr(table, 'description', 'No description')}" for table in getattr(model, 'tables', [])])}

### Relationships
{chr(10).join([f"- {rel.from_table}[{rel.from_column}] → {rel.to_table}[{rel.to_column}] ({getattr(rel, 'cardinality', 'manyToOne')})" for rel in getattr(model, 'relationships', [])])}

## 🚀 Deployment

### Power BI Desktop
1. Open Power BI Desktop
2. File → Import → From Folder
3. Select this model folder
4. Import `model.tmdl`

### Fabric Deployment  
```bash
# Copy to Fabric workspace
cp model.tmdl your-workspace/semantic-models/{model_name}.tmdl
```

## 📁 Files

- **`model.tmdl`** - TMDL definition (deployable to Power BI)
- **`model.json`** - JSON representation (for tooling/APIs)
- **`README.md`** - This documentation

---
*Generated by Loomaa v1.0 - Professional semantic modeling for Power BI*
'''

def get_tmdl_table_name(table):
    """Get the TMDL table name - always use schema.name for database tables"""
    schema = getattr(table, 'schema', 'dbo')
    name = table.name
    
    # For database tables, use schema.name format
    if schema and schema.lower() != 'dbo':
        return f"{schema}.{name}"
    else:
        return name

def get_relationship_table_name(table_variable_name, model):
    """Get table name for relationships using variable name mapping"""
    # In the new approach, relationships use variable names which map to table objects
    # The compiler should maintain a mapping of variable names to table objects
    # For now, return the variable name directly - the model should handle this mapping
    return table_variable_name

def generate_individual_table_tmdl(table):
    """Generate individual table TMDL file with correct naming for Import/DirectLake"""
    lineage_tag = generate_lineage_tag()
    
    # Determine the TMDL table name based on mode and source
    tmdl_table_name = get_tmdl_table_name(table)
    
    content = [f"table '{tmdl_table_name}'"]
    content.append(f"\tlineageTag: {lineage_tag}")
    
    # Add sourceLineageTag for DirectLake tables
    table_mode = getattr(table, 'mode', 'import')
    if hasattr(table_mode, 'value'):
        table_mode = table_mode.value.lower()
    
    if 'directlake' in str(table_mode).lower():
        source_query = getattr(table, 'source_query', '') or ''
        if source_query:
            # Extract schema.table from source_query for sourceLineageTag
            if '.' in source_query:
                parts = source_query.split('.')
                if len(parts) >= 2:
                    schema = parts[-2] if len(parts) >= 2 else 'dbo'
                    table_name = parts[-1]
                    content.append(f"\tsourceLineageTag: [{schema}].[{table_name}]")
    
    content.append("")
    
    # Add columns with sourceLineageTag
    for column in getattr(table, 'columns', []):
        col_lineage = generate_lineage_tag()
        content.append(f"\tcolumn '{column.name}'")
        content.append(f"\t\tdataType: {convert_dtype_to_power_bi(column.dtype)}")
        content.append(f"\t\tlineageTag: {col_lineage}")
        
        # Add sourceLineageTag for DirectLake columns
        if 'directlake' in str(table_mode).lower():
            content.append(f"\t\tsourceLineageTag: {column.name}")
        
        content.append(f"\t\tsummarizeBy: none")
        content.append(f"\t\tsourceColumn: {column.name}")
        content.append("")
        content.append(f"\t\tannotation SummarizationSetBy = Automatic")
        content.append("")
    
    # Add measures
    for measure in getattr(table, 'measures', []):
        measure_lineage = generate_lineage_tag()
        content.append(f"\tmeasure '{measure.name}' = {measure.expression}")
        content.append(f"\t\tlineageTag: {measure_lineage}")
        content.append("")
    
    # Add partition with correct DirectLake format
    if 'directlake' in str(table_mode).lower():
        source_query = getattr(table, 'source_query', '') or ''
        resource_id = getattr(table, 'directlake_resource_id', None)
        
        if '.' in source_query:
            parts = source_query.split('.')
            schema = parts[-2] if len(parts) >= 2 else 'dbo'  
            entity_name = parts[-1]
        else:
            schema = 'dbo'
            entity_name = source_query or table.name.replace(' ', '_')
        
        # Use resource ID for expression source name
        if resource_id:
            expression_source = f"DirectLake - {resource_id[:8]}"
        else:
            expression_source = "DirectLake - Default"
            
        content.append(f"\tpartition {table.name.replace(' ', '_')} = entity")
        content.append(f"\t\tmode: directLake")
        content.append(f"\t\tsource")
        content.append(f"\t\t\tentityName: {entity_name}")
        content.append(f"\t\t\tschemaName: {schema}")
        content.append(f"\t\t\texpressionSource: '{expression_source}'")
    else:
        # Import mode partition (existing logic)
        source_query = getattr(table, 'source_query', '') or ''
        # Get SQL server from table declaration or fallback to environment variable
        table_sql_server = getattr(table, 'sql_server', None)
        server = table_sql_server or os.getenv("FABRIC_SQL_SERVER", "your-server.datawarehouse.fabric.microsoft.com")
        content.append(f"\tpartition '{table.name}' = m")
        content.append(f"\t\tmode: import")
        content.append(f"\t\tsource =")
        content.append(f"\t\t\tlet")
        if source_query.strip().lower().startswith('select '):
            # Normalize multi-line SQL to single line for TMDL compatibility
            normalized_sql = ' '.join(line.strip() for line in source_query.split('\n') if line.strip())
            esc = normalized_sql.replace('"', '\\"')
            content.append(f"\t\t\t\tSource = Sql.Database(\"{server}\", \"master\"),")
            content.append(f"\t\t\t\tResult = Value.NativeQuery(Source, \"{esc}\" )")
            content.append(f"\t\t\tin")
            content.append(f"\t\t\t\tResult")
        else:
            parts = source_query.split('.') if source_query else []
            if len(parts) == 3:
                database, schema, table_name = parts
            elif len(parts) == 2:
                database = None
                schema, table_name = parts
            else:
                database = None
                schema = 'dbo'
                table_name = table.name.replace(' ', '_')
            db_for_connection = database or 'master'
            content.append(f"\t\t\t\tSource = Sql.Database(\"{server}\", \"{db_for_connection}\"),")
            content.append(f"\t\t\t\t{table_name} = Source{{[Schema=\"{schema}\",Item=\"{table_name}\"]}}[Data]")
            content.append(f"\t\t\tin")
            content.append(f"\t\t\t\t{table_name}")
    
    content.append("")
    content.append(f"\tannotation PBI_ResultType = Table")
    content.append("")
    
    return '\n'.join(content)


