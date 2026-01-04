"""
Pydantic-based semantic modeling classes for Microsoft Fabric
Clean, validated, and maintainable model definitions
"""
from pydantic import BaseModel, Field, computed_field, model_validator
from typing import List, Optional, Literal, Dict, Any, Union
from enum import Enum
import uuid

# =============================================================================
# ENUMS & TYPES
# =============================================================================

class TableMode(str, Enum):
    """Table storage modes"""
    IMPORT = "Import"
    DIRECTLAKE = "DirectLake"

class DataType(str, Enum):
    """Power BI data types"""
    STRING = "string"
    TEXT = "string"          # Alias
    INT64 = "int64" 
    INTEGER = "int64"        # Alias
    DECIMAL = "decimal"
    CURRENCY = "decimal"     # Alias
    DATETIME = "dateTime"
    DATE = "dateTime"        # Alias  
    BOOLEAN = "boolean"
    DOUBLE = "double"

class Cardinality(str, Enum):
    """Relationship cardinalities"""
    MANY_TO_ONE = "manyToOne"
    ONE_TO_MANY = "oneToMany"
    ONE_TO_ONE = "oneToOne"
    MANY_TO_MANY = "manyToMany"

class CrossFilter(str, Enum):
    """Cross-filtering directions"""
    SINGLE = "oneDirection"
    ONE_DIRECTION = "oneDirection"  # Alias
    BOTH = "bothDirections"
    BOTH_DIRECTIONS = "bothDirections"  # Alias
    NONE = "none"

class SummarizeBy(str, Enum):
    """Column summarization options"""
    DEFAULT = "Default"
    NONE = "None"
    SUM = "Sum" 
    AVERAGE = "Average"
    MINIMUM = "Minimum"
    MAXIMUM = "Maximum"
    COUNT = "Count"
    DISTINCT_COUNT = "DistinctCount"

# =============================================================================
# CORE MODEL CLASSES
# =============================================================================

class Column(BaseModel):
    """Table column with validation and computed properties"""
    name: str = Field(..., description="Column name")
    dtype: DataType = Field(..., description="Power BI data type")
    description: str = Field("", description="Column description")
    format_string: Optional[str] = Field(None, description="Display format (e.g., '$#,##0.00')")
    summarize_by: SummarizeBy = Field(SummarizeBy.DEFAULT, description="Default summarization")
    is_hidden: bool = Field(False, description="Hide column from report view")
    sort_by_column: Optional[str] = Field(None, description="Column to sort by")
    data_category: Optional[str] = Field(None, description="Power BI data category (e.g., Years, Months, WebURL)")
    is_name_inferred: bool = Field(False, description="Emit isNameInferred")
    is_data_type_inferred: bool = Field(False, description="Emit isDataTypeInferred")
    # Additional metadata for richer TMDL
    underlying_date_type: Optional[str] = Field(None, description="If a date column, underlying date type (e.g. 'Date')")
    enable_date_variation: bool = Field(False, description="If true and column is dateTime, emit variation block referencing related date table")
    
    model_config = {"use_enum_values": True}

class CalculatedColumn(BaseModel):
    """Calculated column definition (Import mode only)"""
    name: str = Field(..., description="Calculated column name")
    expression: str = Field(..., description="DAX expression")
    description: str = Field("", description="Column description")
    dtype: DataType = Field(DataType.STRING, description="Result data type")
    format_string: Optional[str] = Field(None, description="Display format")
    is_data_type_inferred: bool = Field(True, description="Emit isDataTypeInferred (default true for calc columns)")
    
    model_config = {"use_enum_values": True}

class Measure(BaseModel):
    """DAX measure definition"""
    name: str = Field(..., description="Measure name")
    expression: str = Field(..., description="DAX expression")
    description: str = Field("", description="Measure description")
    format_string: Optional[str] = Field(None, description="Display format")
    folder: Optional[str] = Field(None, description="Display folder")
    is_hidden: bool = Field(False, description="Hide from report view")
    
    model_config = {"use_enum_values": True}

class Hierarchy(BaseModel):
    """Table hierarchy definition"""
    name: str = Field(..., description="Hierarchy name")
    levels: List[str] = Field(..., description="Column names in hierarchy order")
    description: str = Field("", description="Hierarchy description")
    is_hidden: bool = Field(False, description="Hide from report view")

class Role(BaseModel):
    """Row-level security role"""
    name: str = Field(..., description="Role name")
    description: str = Field("", description="Role description")
    table_permissions: Dict[str, str] = Field(default_factory=dict, description="Table name -> DAX filter expression")

class Table(BaseModel):
    """Semantic model table with full validation"""
    name: str = Field(..., description="Database table name")
    table_schema: str = Field("dbo", description="Database schema")
    mode: TableMode = Field(..., description="Storage mode (Import/DirectLake)")
    description: str = Field("", description="Table description")
    
    # Column definitions
    columns: List[Column] = Field(default_factory=list, description="Table columns")
    calculated_columns: List[CalculatedColumn] = Field(default_factory=list, description="Calculated columns (Import only)")
    measures: List[Measure] = Field(default_factory=list, description="Table-level measures")
    hierarchies: List[Hierarchy] = Field(default_factory=list, description="Table hierarchies")
    query_group: Optional[str] = Field(None, description="Logical query group (e.g. 'Dimension Tables', 'Fact Tables')")
    
    # DirectLake specific
    directlake_resource_id: Optional[str] = Field(None, description="Lakehouse/Warehouse GUID for DirectLake")
    
    # Import specific
    sql_server: Optional[str] = Field(None, description="SQL Server connection for Import")
    sql_database: Optional[str] = Field(None, description="Database name for Import (e.g., Fabric warehouse name)")
    source_query: Optional[str] = Field(None, description="Custom SQL query (optional)")
    
    # Display properties
    is_hidden: bool = Field(False, description="Hide table from report view")
    show_as_variations_only: bool = Field(False, description="Emit showAsVariationsOnly (used by local date tables)")
    
    model_config = {"use_enum_values": True}
    
    @computed_field
    @property 
    def database_reference(self) -> str:
        """Full database reference: schema.table"""
        return f"{self.table_schema}.{self.name}"
    
    @computed_field
    @property
    def tmdl_table_name(self) -> str:
        """Name to use in TMDL files"""
        # For now, use actual table name - can be enhanced later
        return self.name
        
    @model_validator(mode='after')
    def validate_mode_requirements(self):
        """Validate mode-specific requirements"""
        if self.mode == TableMode.DIRECTLAKE:
            if not self.directlake_resource_id:
                raise ValueError(f"DirectLake table '{self.name}' requires directlake_resource_id")
            if self.calculated_columns:
                raise ValueError(f"DirectLake table '{self.name}' cannot have calculated columns")
                
        if self.mode == TableMode.IMPORT:
            if not self.sql_server:
                raise ValueError(f"Import table '{self.name}' requires sql_server")
                
        return self
    
    def add_column(self, column: Column) -> None:
        """Add a column to the table"""
        self.columns.append(column)
        
    def add_measure(self, measure: Measure) -> None:
        """Add a measure to the table"""
        self.measures.append(measure)
        
    def add_hierarchy(self, hierarchy: Hierarchy) -> None:
        """Add a hierarchy to the table"""
        self.hierarchies.append(hierarchy)

class Relationship(BaseModel):
    """Relationship between tables with full validation"""
    from_table: Union[str, 'Table'] = Field(..., description="Source table name or Table object")
    from_column: str = Field(..., description="Source column name")
    to_table: Union[str, 'Table'] = Field(..., description="Target table name or Table object") 
    to_column: str = Field(..., description="Target column name")
    cardinality: Cardinality = Field(Cardinality.MANY_TO_ONE, description="Relationship cardinality")
    cross_filter_direction: CrossFilter = Field(CrossFilter.SINGLE, description="Cross-filtering direction")
    is_active: bool = Field(True, description="Active relationship")
    description: str = Field("", description="Relationship description")
    # Advanced optional behaviors (seen in reference model)
    join_on_date_behavior: Optional[Literal['datePartOnly']] = Field(None, description="Date join behavior if applicable")
    security_filtering_behavior: Optional[Literal['bothDirections','oneDirection','none']] = Field(None, description="Security filtering behavior")
    
    @computed_field
    @property
    def from_table_name(self) -> str:
        """Get the from table name as string"""
        return self.from_table.name if isinstance(self.from_table, Table) else self.from_table
        
    @computed_field
    @property
    def to_table_name(self) -> str:
        """Get the to table name as string"""
        return self.to_table.name if isinstance(self.to_table, Table) else self.to_table
    
    model_config = {"use_enum_values": True}

class SemanticModel(BaseModel):
    """Complete semantic model with validation and computed properties"""
    name: str = Field(..., description="Model name")
    description: str = Field("", description="Model description")
    
    # Core components
    tables: List[Table] = Field(default_factory=list, description="Model tables")
    relationships: List[Relationship] = Field(default_factory=list, description="Table relationships")
    measures: List[Measure] = Field(default_factory=list, description="Model-level measures")
    roles: List[Role] = Field(default_factory=list, description="Security roles")
    
    # Metadata
    cultures: List[str] = Field(default_factory=lambda: ["en-US"], description="Supported cultures")
    
    model_config = {"use_enum_values": True}
    
    @computed_field
    @property
    def table_count(self) -> int:
        """Number of tables in model"""
        return len(self.tables)
        
    @computed_field  
    @property
    def relationship_count(self) -> int:
        """Number of relationships in model"""
        return len(self.relationships)
    
    @computed_field
    @property
    def column_count(self) -> int:
        """Total columns across all tables"""
        return sum(len(table.columns) for table in self.tables)
        
    @computed_field
    @property
    def measure_count(self) -> int:
        """Total measures (table + model level)"""
        table_measures = sum(len(table.measures) for table in self.tables)
        return table_measures + len(self.measures)
    
    @model_validator(mode='after')
    def validate_relationships(self):
        """Validate that all relationships reference existing tables and columns"""
        table_map = {table.name: table for table in self.tables}
        
        for rel in self.relationships:
            # Use computed properties to get table names
            from_table_name = rel.from_table_name
            to_table_name = rel.to_table_name
            
            # Check from_table exists
            if from_table_name not in table_map:
                raise ValueError(f"Relationship references unknown from_table: '{from_table_name}'")
                
            # Check to_table exists  
            if to_table_name not in table_map:
                raise ValueError(f"Relationship references unknown to_table: '{to_table_name}'")
                
            # Check from_column exists
            from_table = table_map[from_table_name]
            from_columns = {col.name for col in from_table.columns}
            if rel.from_column not in from_columns:
                raise ValueError(f"Relationship references unknown from_column: '{from_table_name}[{rel.from_column}]'")
                
            # Check to_column exists
            to_table = table_map[to_table_name]
            to_columns = {col.name for col in to_table.columns}
            if rel.to_column not in to_columns:
                raise ValueError(f"Relationship references unknown to_column: '{to_table_name}[{rel.to_column}]'")
                
        return self
    
    def add_table(self, table: Table) -> None:
        """Add a table to the model"""
        self.tables.append(table)
        
    def add_relationship(self, relationship: Relationship) -> None:
        """Add a relationship to the model"""
        self.relationships.append(relationship)
        
    def add_measure(self, measure: Measure) -> None:
        """Add a model-level measure"""
        self.measures.append(measure)
        
    def add_role(self, role: Role) -> None:
        """Add a security role"""
        self.roles.append(role)
        
    def get_table(self, name: str) -> Optional[Table]:
        """Get table by name"""  
        for table in self.tables:
            if table.name == name:
                return table
        return None

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_lineage_tag() -> str:
    """Generate a unique lineage tag for TMDL"""
    return str(uuid.uuid4())