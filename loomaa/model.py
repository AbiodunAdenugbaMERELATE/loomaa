"""
Loomaa semantic model definitions for Power BI
Enhanced with comprehensive metadata and Tabular Editor-style features
"""
from typing import List, Optional, Dict, Any
from enum import Enum

# Smart Enums for User-Friendly API
class DataTypes:
    """Power BI data types - use these instead of strings to prevent typos"""
    TEXT = "string"
    STRING = "string"  # Alias for TEXT
    INTEGER = "int64"
    INT = "int64"  # Alias for INTEGER
    CURRENCY = "decimal"
    DECIMAL = "decimal"  # Alias for CURRENCY
    DATETIME = "dateTime"
    DATE = "dateTime"  # Alias for DATETIME
    BOOLEAN = "boolean"
    BOOL = "boolean"  # Alias for BOOLEAN
    DOUBLE = "double"
    FLOAT = "double"  # Alias for DOUBLE

class TableMode:
    """Table storage modes - only tested and validated modes"""
    IMPORT = "Import"
    DIRECTLAKE = "DirectLake"

class Cardinality:
    """Relationship cardinalities - Power BI standard format"""
    MANY_TO_ONE = "manyToOne"
    ONE_TO_MANY = "oneToMany"
    ONE_TO_ONE = "oneToOne"  
    MANY_TO_MANY = "manyToMany"

class CrossFilter:
    """Cross-filtering directions for relationships"""
    SINGLE = "oneDirection"
    ONE_DIRECTION = "oneDirection"  # Alias for SINGLE
    BOTH = "bothDirections"
    BOTH_DIRECTIONS = "bothDirections"  # Alias for BOTH
    NONE = "none"

class SummarizeBy:
    """Column summarization options"""
    DEFAULT = "Default"
    NONE = "None"
    SUM = "Sum"
    AVERAGE = "Average"
    MINIMUM = "Minimum"
    MAXIMUM = "Maximum"
    COUNT = "Count"
    DISTINCT_COUNT = "DistinctCount"

class SemanticModel:
    """
    Main semantic model class representing a Power BI dataset.
    Supports all major semantic modeling features.
    """
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.tables: List[Table] = []
        self.relationships: List[Relationship] = []
        self.hierarchies: List[Hierarchy] = []
        self.calculated_tables: List[CalculatedTable] = []
        self.perspectives: List[str] = []
        self.measures: List[Measure] = []  # Model-level measures
        self.roles: List[Role] = []  # Row-level security roles
        self.cultures: List[str] = []  # Localization
        
    def add_table(self, table: 'Table'):
        """Add a table to the model"""
        self.tables.append(table)
        
    def add_relationship(self, relationship: 'Relationship'):
        """Add a relationship to the model"""
        self.relationships.append(relationship)
        
    def add_hierarchy(self, hierarchy: 'Hierarchy'):
        """Add a hierarchy to the model"""
        self.hierarchies.append(hierarchy)
        
    def add_measure(self, measure: 'Measure'):
        """Add a model-level measure"""
        self.measures.append(measure)
        
    def add_role(self, role: 'Role'):
        """Add a row-level security role"""
        self.roles.append(role)
        
    def get_table(self, name: str) -> Optional['Table']:
        """Get table by name"""
        for table in self.tables:
            if table.name == name:
                return table
        return None

class DirectLakeSource(Enum):
    """DirectLake source types"""
    LAKEHOUSE = "lakehouse"
    WAREHOUSE = "warehouse"

class Table:
    """
    Table definition with comprehensive metadata.
    Supports Import and DirectLake storage modes.
    """
    def __init__(self, name: str, mode: str = TableMode.IMPORT, description: str = "", 
                 columns: Optional[List['Column']] = None, 
                 measures: Optional[List['Measure']] = None,
                 source_query: Optional[str] = None,
                 calculated_columns: Optional[List['CalculatedColumn']] = None,
                 directlake_source: DirectLakeSource = DirectLakeSource.LAKEHOUSE,
                 directlake_resource_id: Optional[str] = None,
                 sql_server: Optional[str] = None,
                 schema: Optional[str] = None):
        self.name = name  # Actual database table name
        # Accept both enum values and strings for backward compatibility
        if hasattr(mode, '__class__') and hasattr(mode.__class__, '__name__'):
            self.mode = mode  # It's already a string from enum
        else:
            self.mode = mode  # Direct string
        self.description = description
        self.columns = columns or []
        self.measures = measures or []
        self.calculated_columns = calculated_columns or []
        self.calculated_tables = []
        self.data = []  # For Import mode
        self.partitions = []  # Partition definitions
        self.source_query = source_query  # SQL query or data source
        
        # Database schema and connection parameters
        self.schema = schema or "dbo"  # Database schema (defaults to dbo)
        self.sql_server = sql_server  # SQL server for Import mode
        self.directlake_resource_id = directlake_resource_id  # Resource ID for DirectLake mode
        self.is_hidden = False
        self.directlake_source = directlake_source  # Deprecated: use directlake_resource_id
        self.directlake_resource_id = directlake_resource_id  # GUID of lakehouse/warehouse
        self.sql_server = sql_server  # SQL server endpoint for Import mode
        
    def add_column(self, column: 'Column'):
        """Add a column to the table"""
        self.columns.append(column)
        
    def add_measure(self, measure: 'Measure'):
        """Add a measure to the table"""
        self.measures.append(measure)

class Column:
    """
    Column definition with data types and formatting.
    Supports all Power BI data types and formatting options.
    """
    def __init__(self, name: str, dtype: str, description: str = "", 
                 format_string: str = "", is_hidden: bool = False, summarize_by: str = SummarizeBy.DEFAULT):
        self.name = name
        # Accept both enum values and strings for backward compatibility
        if hasattr(dtype, '__class__') and hasattr(dtype.__class__, '__name__'):
            self.dtype = dtype  # It's already a string from enum
        else:
            self.dtype = dtype  # Direct string
        self.description = description
        self.format_string = format_string
        self.is_hidden = is_hidden
        self.is_key = False
        self.sort_by_column: Optional[str] = None
        self.data_category: Optional[str] = None  # Geography, WebURL, etc.
        self.summarize_by = "Default"  # Default, None, Sum, etc.

class Measure:
    """
    DAX measure definition with comprehensive metadata.
    Supports folders, descriptions, and formatting.
    """
    def __init__(self, name: str, expression: str, description: str = "",
                 format_string: str = "", folder: str = "", is_hidden: bool = False):
        self.name = name
        self.expression = expression
        self.description = description
        self.format_string = format_string
        self.folder = folder  # Display folder for organization
        self.is_hidden = is_hidden
        self.kpi_status_expression: Optional[str] = None
        self.kpi_target_expression: Optional[str] = None
        self.kpi_trend_expression: Optional[str] = None

class CalculatedColumn:
    """
    DAX calculated column definition.
    Computed columns that become part of the table structure.
    """
    def __init__(self, name: str, expression: str, description: str = "",
                 format_string: str = "", is_hidden: bool = False):
        self.name = name
        self.expression = expression  # DAX expression
        self.dax_expression = expression  # Alias for compiler compatibility
        self.description = description
        self.format_string = format_string
        self.is_hidden = is_hidden
        self.data_type: Optional[str] = None  # Will be inferred

class CalculatedTable:
    """
    DAX calculated table definition.
    Virtual tables computed via DAX expressions.
    """
    def __init__(self, name: str, expression: str, description: str = ""):
        self.name = name
        self.expression = expression  # DAX table expression
        self.dax_expression = expression  # Alias for compiler compatibility
        self.description = description
        self.is_hidden = False

class Relationship:
    """
    Relationship definition between tables.
    Supports all Power BI relationship types and directions.
    """
    def __init__(self, from_table: str, from_column: str, to_table: str, 
                 to_column: str, cardinality: str = Cardinality.MANY_TO_ONE,
                 cross_filter_direction: str = CrossFilter.SINGLE, is_active: bool = True,
                 description: str = ""):
        self.from_table = from_table
        self.from_column = from_column
        self.to_table = to_table
        self.to_column = to_column
        # Accept both enum values and strings for backward compatibility
        self.cardinality = cardinality
        self.cross_filter_direction = cross_filter_direction
        self.is_active = is_active
        self.description = description
        
class Hierarchy:
    """
    Dimension hierarchy definition.
    Defines drill-down paths for dimensional analysis.
    """
    def __init__(self, name: str, levels: List[str], description: str = ""):
        self.name = name
        self.levels = levels  # List of column names
        self.description = description
        self.is_hidden = False

class Role:
    """
    Row-level security role definition.
    Defines data access permissions for different user groups.
    """
    def __init__(self, name: str, description: str = "", table_permissions: Optional[Dict[str, str]] = None):
        self.name = name
        self.description = description
        self.table_permissions = table_permissions or {}  # Dict of table_name: DAX_filter_expression
        self.members = []  # List of users/groups in this role
        
    def add_table_permission(self, table_name: str, filter_expression: str):
        """Add a table permission with DAX filter expression"""
        self.table_permissions[table_name] = filter_expression
        
    def add_member(self, member: str):
        """Add a user or group to this role"""
        self.members.append(member)

# Legacy aliases for backward compatibility
Model = SemanticModel  # Keep old Model class name working
