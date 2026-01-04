"""
Pydantic-compatible compiler for generating .SemanticModel structures
Maintains exact same output format while using validated Pydantic models
"""
import os
import shutil
import uuid
import json
from typing import List, Dict, Optional, Any

from .models_pydantic import (
    SemanticModel,
    Table,
    Column,
    Measure,
    Relationship,
    TableMode,
    DataType,
    Role,
    SummarizeBy,
    CrossFilter,
    Hierarchy,
)

_STABLE_NAMESPACE = uuid.UUID("7b2f5b0a-0b5d-4f1e-9b86-7b4d7c7f7b51")


def generate_lineage_tag() -> str:
    """Generate a unique lineage tag for TMDL."""
    return str(uuid.uuid4())


def stable_tag(key: str) -> str:
    """Generate a stable tag to allow cross-file references.

    We use UUIDv5 so relationship IDs remain consistent across compiles.
    """
    return str(uuid.uuid5(_STABLE_NAMESPACE, key))

def write_file(file_path: str, content: str):
    """Write content to file, creating directories as needed"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

# =============================================================================
# TMDL GENERATORS (Keep exact same format as before)
# =============================================================================

def generate_platform_file(model_name: str):
    """Generate .platform file."""
    payload = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": model_name},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
    }
    return json.dumps(payload, indent=2)

def generate_pbism_file():
    """Generate definition.pbism file"""
    return """{
  "version": "4.0",
  "settings": {}
}"""

def generate_database_tmdl():
    """Generate database.tmdl file"""
    return """database
	compatibilityLevel: 1604

"""

def _infer_query_group(table: Table) -> str:
    if table.query_group:
        return table.query_group
    name = table.name.lower()
    if name.startswith('dim_') or name.startswith('dim'):
        return 'Dimension Tables'
    if 'fact' in name:
        return 'Fact Tables'
    return 'Other Tables'

def generate_model_tmdl(model: SemanticModel):
    """Generate model.tmdl including query groups and reference lines."""
    # Build a stable PBI_QueryOrder list.
    # Fabric/Power BI use this to order Power Query artifacts (including DirectLake expressions).
    directlake_resources: List[str] = []
    for t in model.tables:
        if t.mode == TableMode.DIRECTLAKE and t.directlake_resource_id:
            rid = t.directlake_resource_id
            short_id = rid[:12] if len(rid) > 12 else rid
            name = f"DirectLake - {short_id}"
            if name not in directlake_resources:
                directlake_resources.append(name)

    query_order: List[str] = []
    query_order.extend(directlake_resources)
    query_order.extend([t.name for t in model.tables])
    query_order_json = "[" + ",".join(json.dumps(x) for x in query_order) + "]"

    lines: List[str] = [
        'model Model',
        '\tculture: en-US',
        '\tdefaultPowerBIDataSourceVersion: powerBI_V3',
        '\tsourceQueryCulture: en-US',
        '\tdataAccessOptions',
        '\t\tlegacyRedirects',
        '\t\treturnErrorValuesAsNull',
        '',
        '\tannotation __PBI_TimeIntelligenceEnabled = 1',
        '\tannotation PBIDesktopVersion = 2.133.7221.0 (24.09)',
        '\tannotation PBI_ProTooling = ["DevMode"]',
        f'\tannotation PBI_QueryOrder = {query_order_json}',
        ''
    ]

    # Query Groups
    groups: Dict[str, List[str]] = {}
    for tbl in model.tables:
        groups.setdefault(_infer_query_group(tbl), []).append(tbl.name)
    ordered = [g for g in ['Dimension Tables','Fact Tables','Other Tables'] if g in groups] + [g for g in groups.keys() if g not in {'Dimension Tables','Fact Tables','Other Tables'}]
    order_idx = 0
    for g in ordered:
        lines.append(f"queryGroup '{g}'")
        lines.append("")
        lines.append(f"\tannotation PBI_QueryGroupOrder = {order_idx}")
        lines.append("")
        order_idx += 1

    # Reference tables
    for tbl in model.tables:
        ref_name = tbl.name if ' ' not in tbl.name else f"'{tbl.name}'"
        lines.append(f"ref table {ref_name}")

    # Reference roles
    for role in model.roles:
        safe = role.name.replace("'", "\'")
        lines.append(f"ref role '{safe}'")

    # Culture reference
    lines.append("\nref cultureInfo en-US\n")
    return "\n".join(lines)

def generate_expressions_tmdl(model: SemanticModel):
    """Generate expressions.tmdl for DirectLake connections"""
    directlake_resources = set()
    
    # Collect unique DirectLake resource IDs
    for table in model.tables:
        if table.mode == TableMode.DIRECTLAKE and table.directlake_resource_id:
            directlake_resources.add(table.directlake_resource_id)
    
    if not directlake_resources:
        return ""
        
    # Fabric/Power BI Desktop TMDL export consistently indents the M body two levels
    # deeper than the `expression ... =` line. Fabric parsing appears sensitive to this.
    content: List[str] = []
    
    workspace_id = os.getenv("FABRIC_WORKSPACE_ID", "your-workspace-id")

    for resource_id in directlake_resources:
        # Create short name for expression
        short_id = resource_id[:12] if len(resource_id) > 12 else resource_id
        lineage_tag = generate_lineage_tag()
        
        m_indent = "\t\t"
        # Keep the inner `Source` step aligned with 4 spaces (matches Desktop export)
        content.extend([
            f"expression 'DirectLake - {short_id}' =",
            f"{m_indent}let",
            f"{m_indent}    Source = AzureStorage.DataLake(\"https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{resource_id}\", [HierarchicalNavigation=true])",
            f"{m_indent}in",
            f"{m_indent}    Source",
            f"\tlineageTag: {lineage_tag}",
            "",
            "\tannotation PBI_IncludeFutureArtifacts = False",
            "",
        ])
    
    return "\n".join(content)

def generate_relationships_tmdl(relationships: List[Relationship]):
    """Generate relationships.tmdl with Pydantic relationships

    TMDL relationship block example:
    relationship <lineageTag>
        fromColumn: Sales[CustomerID]
        toColumn: Customer[CustomerID]
        cardinality: manyToOne
        crossFilteringBehavior: oneDirection
        isActive: true
    """
    if not relationships:
        return ""

    def _quote_identifier(name: str) -> str:
        # TMDL examples use single quotes around names with spaces.
        if any(ch.isspace() for ch in name) or "'" in name:
            return "'" + name.replace("'", "\\'") + "'"
        return name

    def _col_ref(table: str, column: str) -> str:
        # Use dot-notation like the reference models: Table.Column
        return f"{_quote_identifier(table)}.{column}"

    lines: List[str] = []
    for rel in relationships:
        rel_tag = stable_tag(
            f"relationship:{rel.from_table_name}[{rel.from_column}]->{rel.to_table_name}[{rel.to_column}]"
        )

        from_table = getattr(rel, 'from_table_name', rel.from_table if isinstance(rel.from_table, str) else str(rel.from_table))
        to_table = getattr(rel, 'to_table_name', rel.to_table if isinstance(rel.to_table, str) else str(rel.to_table))

        lines.append(f"relationship {rel_tag}")

        # Optional behaviors first (matches reference style)
        if getattr(rel, 'join_on_date_behavior', None):
            lines.append(f"\tjoinOnDateBehavior: {rel.join_on_date_behavior}")
        # Only include crossFilteringBehavior when non-default or explicitly set.
        if getattr(rel, 'cross_filter_direction', None) and rel.cross_filter_direction != CrossFilter.SINGLE:
            lines.append(f"\tcrossFilteringBehavior: {rel.cross_filter_direction}")
        if getattr(rel, 'security_filtering_behavior', None):
            lines.append(f"\tsecurityFilteringBehavior: {rel.security_filtering_behavior}")

        lines.append(f"\tfromColumn: {_col_ref(from_table, rel.from_column)}")
        lines.append(f"\ttoColumn: {_col_ref(to_table, rel.to_column)}")
        lines.append("")

    return "\n".join(lines)


def _find_relationship_tag(
    relationships: List[Relationship],
    from_table: str,
    from_column: str,
    to_table: Optional[str] = None,
) -> Optional[str]:
    for rel in relationships:
        if rel.from_table_name != from_table:
            continue
        if rel.from_column != from_column:
            continue
        if to_table is not None and rel.to_table_name != to_table:
            continue
        return stable_tag(
            f"relationship:{rel.from_table_name}[{rel.from_column}]->{rel.to_table_name}[{rel.to_column}]"
        )
    return None

def generate_culture_tmdl():
    """Generate culture file"""
    return """cultureInfo en-US

"""

def convert_dtype_to_tmdl(dtype: DataType) -> str:
    """Convert Pydantic DataType to TMDL format"""
    return dtype

def _map_summarize_by(dtype: DataType, summarize_by) -> str:
    """Map summarizeBy based on data type and user preference"""
    # If user explicitly set it, respect that.
    # NOTE: `summarize_by` may be an Enum (e.g. SummarizeBy.NONE) or a raw value.
    if summarize_by != SummarizeBy.DEFAULT:
        raw = summarize_by
        if isinstance(raw, SummarizeBy):
            raw = raw.value
        raw_str = str(raw).strip()

        normalized = raw_str.replace("_", "").replace(" ", "").lower()
        # TMDL expects AggregateFunction tokens like: none, sum, average, min, max, count, distinctCount
        mapping = {
            "none": "none",
            "sum": "sum",
            "average": "average",
            "minimum": "min",
            "min": "min",
            "maximum": "max",
            "max": "max",
            "count": "count",
            "distinctcount": "distinctCount",
        }
        return mapping.get(normalized, "none")
    
    # Auto-map based on data type
    dtype_str = str(dtype).lower()
    if dtype_str in ('int64', 'decimal', 'double'):
        return 'sum'
    else:
        return 'none'

def generate_table_tmdl(table: Table, relationships: Optional[List[Relationship]] = None) -> str:
    """Generate individual table TMDL with Pydantic table."""
    relationships = relationships or []
    lineage_tag = stable_tag(f"table:{table.tmdl_table_name}")
    content = [f"table '{table.tmdl_table_name}'"]
    if table.is_hidden:
        content.append("\tisHidden")
    if getattr(table, "show_as_variations_only", False):
        content.append("\tshowAsVariationsOnly")
    content.append(f"\tlineageTag: {lineage_tag}")
    
    # Add sourceLineageTag for DirectLake tables
    if table.mode == TableMode.DIRECTLAKE and table.table_schema and table.name:
        content.append(f"\tsourceLineageTag: [{table.table_schema}].[{table.name}]")
    
    content.append("")
    
    # Add columns
    for column in table.columns:
        col_lineage = stable_tag(f"column:{table.tmdl_table_name}:{column.name}")
        col_name = column.name if ' ' not in column.name else f"'{column.name}'"
        content.append(f"\tcolumn {col_name}")
        content.append(f"\t\tdataType: {convert_dtype_to_tmdl(column.dtype)}")

        if getattr(column, "is_hidden", False):
            content.append("\t\tisHidden")
        if getattr(column, "data_category", None):
            content.append(f"\t\tdataCategory: {column.data_category}")
        if getattr(column, "sort_by_column", None):
            content.append(f"\t\tsortByColumn: {column.sort_by_column}")
        
        # Add formatString if provided
        if column.format_string:
            content.append(f"\t\tformatString: {column.format_string}")
        
        content.append(f"\t\tlineageTag: {col_lineage}")
        
        # Add sourceLineageTag for DirectLake columns
        if table.mode == TableMode.DIRECTLAKE:
            content.append(f"\t\tsourceLineageTag: {column.name}")
        
        # Map summarizeBy correctly
        summarize_value = _map_summarize_by(column.dtype, column.summarize_by)
        content.append(f"\t\tsummarizeBy: {summarize_value}")
        
        if table.mode == TableMode.IMPORT:
            content.append(f"\t\tsourceColumn: {column.name}")
        elif table.mode == TableMode.DIRECTLAKE:
            content.append(f"\t\tsourceColumn: {column.name}")
        
        if getattr(column, "is_name_inferred", False):
            content.append("\t\tisNameInferred")
        if getattr(column, "is_data_type_inferred", False):
            content.append("\t\tisDataTypeInferred")

        # Variation block (optional)
        if getattr(column, "enable_date_variation", False) and str(column.dtype) in ("dateTime", "date"):
            rel_tag = None
            rel_to_table = None
            for rel in relationships:
                if rel.from_table_name == table.name and rel.from_column == column.name:
                    rel_tag = stable_tag(
                        f"relationship:{rel.from_table_name}[{rel.from_column}]->{rel.to_table_name}[{rel.to_column}]"
                    )
                    rel_to_table = rel.to_table_name
                    break
            if rel_tag and rel_to_table:
                content.append("")
                content.append("\t\tvariation Variation")
                content.append("\t\t\tisDefault")
                content.append(f"\t\t\trelationship: {rel_tag}")
                content.append(f"\t\t\tdefaultHierarchy: {rel_to_table}.'Date Hierarchy'")

        content.append("")
        content.append(f"\t\tannotation SummarizationSetBy = Automatic")
        
        # Add UnderlyingDateTimeDataType if date column
        if getattr(column, 'underlying_date_type', None):
            content.append("")
            content.append(f"\t\tannotation UnderlyingDateTimeDataType = {column.underlying_date_type}")
        
        # Add PBI_FormatHint for double types
        if str(column.dtype) == 'double':
            content.append("")
            content.append('\t\tannotation PBI_FormatHint = {"isGeneralNumber":true}')
        
        content.append("")
    
    # Add calculated columns (Import only)
    for calc_col in table.calculated_columns:
        col_lineage = stable_tag(f"calc_column:{table.tmdl_table_name}:{calc_col.name}")
        expr = calc_col.expression.strip()
        
        # Format expression: if multi-line, use triple backticks on new line (CE Accrual style)
        if '\n' in expr:
            content.append(f"\tcolumn '{calc_col.name}' =")
            content.append("\t\t```")
            # Add indented expression lines
            for line in expr.split('\n'):
                content.append(f"\t\t\t{line}")
            content.append("\t\t```")
        else:
            content.append(f"\tcolumn '{calc_col.name}' = {expr}")
        
        content.append(f"\t\tdataType: {convert_dtype_to_tmdl(calc_col.dtype)}")
        
        # Add formatString if provided
        if calc_col.format_string:
            content.append(f"\t\tformatString: {calc_col.format_string}")
        
        content.append(f"\t\tlineageTag: {col_lineage}")
        
        if getattr(calc_col, "is_data_type_inferred", False):
            content.append("\t\tisDataTypeInferred")

        # Map summarizeBy
        summarize_value = _map_summarize_by(calc_col.dtype, SummarizeBy.NONE)
        content.append(f"\t\tsummarizeBy: {summarize_value}")
        content.append("")
        content.append(f"\t\tannotation SummarizationSetBy = Automatic")
        
        # Add PBI_FormatHint for specific types
        if str(calc_col.dtype) == 'double' or (calc_col.format_string and '#' in calc_col.format_string):
            content.append("")
            if 'decimal' in calc_col.format_string.lower() or '#,0' in calc_col.format_string:
                content.append('\t\tannotation PBI_FormatHint = {"isDecimal":true}')
            else:
                content.append('\t\tannotation PBI_FormatHint = {"isGeneralNumber":true}')
        
        content.append("")
    
    # Add hierarchies
    for hierarchy in table.hierarchies:
        hier_tag = stable_tag(f"hierarchy:{table.tmdl_table_name}:{hierarchy.name}")
        content.append(f"\thierarchy '{hierarchy.name}'")
        content.append(f"\t\tlineageTag: {hier_tag}")
        content.append("")
        for level_name in hierarchy.levels:
            level_tag = stable_tag(f"hierarchy_level:{table.tmdl_table_name}:{hierarchy.name}:{level_name}")
            content.append(f"\t\tlevel {level_name}")
            content.append(f"\t\t\tlineageTag: {level_tag}")
            content.append(f"\t\t\tcolumn: {level_name}")
            content.append("")

    # Add measures
    for measure in table.measures:
        measure_lineage = stable_tag(f"measure:{table.tmdl_table_name}:{measure.name}")
        content.append(f"\tmeasure '{measure.name}' = {measure.expression}")
        content.append(f"\t\tlineageTag: {measure_lineage}")
        
        if measure.format_string:
            content.append(f"\t\tformatString: {measure.format_string}")
        content.append("")
    
    # Add partition
    if table.mode == TableMode.DIRECTLAKE:
        content.append(f"\tpartition {table.name} = entity")
        content.append(f"\t\tmode: directLake")
        content.append(f"\t\tsource")
        content.append(f"\t\t\tentityName: {table.name}")
        content.append(f"\t\t\tschemaName: {table.table_schema}")
        
        # Reference the DirectLake expression
        if table.directlake_resource_id:
            short_id = table.directlake_resource_id[:12] if len(table.directlake_resource_id) > 12 else table.directlake_resource_id
            content.append(f"\t\t\texpressionSource: 'DirectLake - {short_id}'")
        
    elif table.mode == TableMode.IMPORT:
        db_name = table.sql_database or "master"
        content.append(f"\tpartition '{table.name}' = m")
        content.append(f"\t\tmode: import")
        content.append(f"\t\tsource =")
        content.append(f"\t\t\tlet")
        
        # Handle custom SQL query vs table reference
        if table.source_query and table.source_query.strip().lower().startswith('select'):
            # Custom SELECT query
            normalized_sql = ' '.join(line.strip() for line in table.source_query.split('\n') if line.strip())
            escaped_sql = normalized_sql.replace('"', '\\"')
            content.append(f"\t\t\t\tSource = Sql.Database(\"{table.sql_server}\", \"{db_name}\"),")
            content.append(f"\t\t\t\tResult = Value.NativeQuery(Source, \"{escaped_sql}\" )")
            content.append(f"\t\t\tin")
            content.append(f"\t\t\t\tResult")
        else:
            # Table reference
            schema = table.table_schema
            table_name = table.name
            
            content.append(f"\t\t\t\tSource = Sql.Database(\"{table.sql_server}\", \"{db_name}\"),")
            content.append(f"\t\t\t\t{table_name} = Source{{[Schema=\"{schema}\",Item=\"{table_name}\"]}}[Data]")
            content.append(f"\t\t\tin")
            content.append(f"\t\t\t\t{table_name}")
    
    content.append("")
    
    content.append(f"\tannotation PBI_ResultType = Table")
    content.append("")
    
    return "\n".join(content)

def generate_model_json(model: SemanticModel) -> str:
    """Generate a viewer/tooling-friendly JSON representation."""

    def col_to_dict(c: Column) -> Dict[str, Any]:
        return {
            "name": c.name,
            "dtype": str(c.dtype),
            "description": c.description,
            "format_string": c.format_string,
            "is_hidden": c.is_hidden,
            "summarize_by": str(c.summarize_by),
            "sort_by_column": c.sort_by_column,
            "data_category": getattr(c, "data_category", None),
        }

    def calc_col_to_dict(c) -> Dict[str, Any]:
        return {
            "name": c.name,
            "dtype": str(c.dtype),
            "description": c.description,
            "format_string": c.format_string,
            "expression": c.expression,
        }

    def measure_to_dict(m: Measure) -> Dict[str, Any]:
        return {
            "name": m.name,
            "expression": m.expression,
            "description": m.description,
            "format_string": m.format_string,
            "folder": m.folder,
            "is_hidden": m.is_hidden,
        }

    def table_to_dict(t: Table) -> Dict[str, Any]:
        return {
            "name": t.name,
            "table_schema": t.table_schema,
            "mode": str(t.mode),
            "description": t.description,
            "columns": [col_to_dict(c) for c in t.columns],
            "calculated_columns": [calc_col_to_dict(c) for c in t.calculated_columns],
            "measures": [measure_to_dict(m) for m in t.measures],
            "hierarchies": [{"name": h.name, "levels": h.levels, "description": h.description} for h in t.hierarchies],
        }

    # Flatten measures for the viewer (it expects model_data['measures'])
    flattened_measures: List[Dict[str, Any]] = []
    for t in model.tables:
        for m in t.measures:
            md = measure_to_dict(m)
            md["table"] = t.name
            flattened_measures.append(md)
    for m in model.measures:
        md = measure_to_dict(m)
        md["table"] = None
        flattened_measures.append(md)

    payload = {
        "name": model.name,
        "description": model.description,
        "compatibilityLevel": 1604,
        "tables": [table_to_dict(t) for t in model.tables],
        "measures": flattened_measures,
        "model_measures": [measure_to_dict(m) for m in model.measures],
        "relationships": [
            {
                "id": stable_tag(
                    f"relationship:{r.from_table_name}[{r.from_column}]->{r.to_table_name}[{r.to_column}]"
                ),
                "from_table": r.from_table_name,
                "from_column": r.from_column,
                "to_table": r.to_table_name,
                "to_column": r.to_column,
                "cardinality": str(r.cardinality),
                "cross_filter_direction": str(r.cross_filter_direction),
                "is_active": r.is_active,
                "join_on_date_behavior": r.join_on_date_behavior,
                "security_filtering_behavior": r.security_filtering_behavior,
                "description": r.description,
            }
            for r in model.relationships
        ],
        "roles": [
            {"name": role.name, "description": role.description, "table_permissions": role.table_permissions}
            for role in model.roles
        ],
        "cultures": model.cultures,
    }
    return json.dumps(payload, indent=2)


def generate_role_tmdl(role: Role) -> str:
    """Generate a role file matching the reference structure."""
    lines: List[str] = [f"role '{role.name}'", "\tmodelPermission: read", ""]
    for table_name, filter_expr in (role.table_permissions or {}).items():
        lines.append(f"\ttablePermission {table_name} = {filter_expr}")
    if role.table_permissions:
        lines.append("")
    lines.append(f"\tannotation PBI_Id = {uuid.uuid4().hex}")
    lines.append("")
    return "\n".join(lines)

def generate_readme(model: SemanticModel) -> str:
    """Generate README.md for the model"""
    table_list = "\n".join([f"- **{table.name}** ({table.mode}) - {table.description}" for table in model.tables])
    
    return f"""# {model.name}

{model.description}

## Model Structure

### Tables ({model.table_count})
{table_list}

### Relationships ({model.relationship_count})
{len([rel for rel in model.relationships if rel.is_active])} active relationships defined.

### Measures ({model.measure_count})
Includes both table-level and model-level measures.

## Deployment

This semantic model was generated by Loomaa and is ready for deployment to Microsoft Fabric using PowerShell:

```powershell
Import-FabricItem -Path "{model.name}.SemanticModel" -WorkspaceId "your-workspace-id"
```

## Generated Files

- `definition.pbism` - Model metadata
- `definition/model.tmdl` - Model configuration
- `definition/database.tmdl` - Database settings
- `definition/expressions.tmdl` - DirectLake connections
- `definition/relationships.tmdl` - Table relationships
- `definition/tables/*.tmdl` - Individual table definitions
- `definition/cultures/en-US.tmdl` - Localization settings
- `.platform` - Fabric platform metadata
"""

# =============================================================================
# MAIN COMPILER FUNCTION
# =============================================================================

def compile_semantic_model(model: SemanticModel, output_dir: str) -> None:
    """Compile Pydantic SemanticModel to .SemanticModel structure"""
    
    # Validate model first (Pydantic will raise ValidationError if invalid)
    model.model_validate(model.model_dump())
    
    # Create directory structure
    model_dir = os.path.join(output_dir, f"{model.name}.SemanticModel")

    # Clean previous compiled output to avoid stale files being deployed
    if os.path.exists(model_dir):
        shutil.rmtree(model_dir)

    definition_dir = os.path.join(model_dir, "definition")
    tables_dir = os.path.join(definition_dir, "tables")
    cultures_dir = os.path.join(definition_dir, "cultures")
    roles_dir = os.path.join(definition_dir, "roles")
    
    # Generate all files
    model_json = generate_model_json(model)
    write_file(os.path.join(model_dir, ".platform"), generate_platform_file(model.name))
    write_file(os.path.join(model_dir, "definition.pbism"), generate_pbism_file())
    write_file(os.path.join(model_dir, "model.json"), model_json)
    # Also drop a copy alongside compiled/<folder>/model.json for the viewer.
    write_file(os.path.join(output_dir, "model.json"), model_json)
    write_file(os.path.join(model_dir, "README.md"), generate_readme(model))
    
    # Definition files
    write_file(os.path.join(definition_dir, "model.tmdl"), generate_model_tmdl(model))
    write_file(os.path.join(definition_dir, "database.tmdl"), generate_database_tmdl())
    write_file(os.path.join(definition_dir, "expressions.tmdl"), generate_expressions_tmdl(model))
    write_file(os.path.join(definition_dir, "relationships.tmdl"), generate_relationships_tmdl(model.relationships))

    # Roles
    for role in model.roles:
        write_file(os.path.join(roles_dir, f"{role.name}.tmdl"), generate_role_tmdl(role))
    
    # Individual table files
    # NOTE: TMDL measures must live under a table. Instead of emitting a synthetic
    # 'Model Measures' table (which can break deployment if it has an invalid source),
    # we attach model-level measures to the first table for TMDL output.
    tables_for_output = list(model.tables)
    model_level_measures = list(getattr(model, "measures", []) or [])
    if model_level_measures and tables_for_output:
        first = tables_for_output[0].model_copy(deep=True)
        first.measures = list(first.measures) + model_level_measures
        tables_for_output[0] = first

    for table in tables_for_output:
        table_content = generate_table_tmdl(table, relationships=model.relationships)
        write_file(os.path.join(tables_dir, f"{table.tmdl_table_name}.tmdl"), table_content)
    
    # Culture files
    write_file(os.path.join(cultures_dir, "en-US.tmdl"), generate_culture_tmdl())
    
    print(f"✅ Model '{model.name}' compiled successfully!")
    print(f"📁 Output: {model_dir}")
    print(f"📊 {model.table_count} tables, {model.relationship_count} relationships, {model.measure_count} measures")