def validate_model(model):
    """
    Validate a semantic model for DAX syntax, table references, and relationships
    
    Args:
        model: SemanticModel object or dict representation
        
    Returns:
        dict: Validation results with 'valid', 'errors', and 'warnings' keys
    """
    errors = []
    warnings = []
    
    # Handle both SemanticModel objects and dictionaries
    if hasattr(model, 'tables'):  # SemanticModel object
        tables = model.tables
        measures = model.measures
        relationships = getattr(model, 'relationships', [])
    else:  # Dictionary format
        tables = model.get('tables', [])
        measures = model.get('measures', [])
        relationships = model.get('relationships', [])
    
    # Validate tables
    table_names = set()
    for table in tables:
        if hasattr(table, 'name'):  # Table object
            table_name = table.name
            table_columns = getattr(table, 'columns', [])
        else:  # Dictionary format
            table_name = table.get('name', 'Unknown')
            table_columns = table.get('columns', [])
            
        if not table_name:
            errors.append("Table missing name")
            continue
            
        if table_name in table_names:
            errors.append(f"Duplicate table name: {table_name}")
        table_names.add(table_name)
        
        # Validate columns
        column_names = set()
        for column in table_columns:
            if hasattr(column, 'name'):  # Column object
                column_name = column.name
            else:  # Dictionary format
                column_name = column.get('name', 'Unknown')
                
            if column_name in column_names:
                errors.append(f"Duplicate column name in table {table_name}: {column_name}")
            column_names.add(column_name)
    
    # Validate measures
    measure_names = set()
    for measure in measures:
        if hasattr(measure, 'name'):  # Measure object
            measure_name = measure.name
            dax_expression = getattr(measure, 'expression', '')
        else:  # Dictionary format
            measure_name = measure.get('name', 'Unknown')
            dax_expression = measure.get('expression', '')
            
        if not measure_name:
            errors.append("Measure missing name")
            continue
            
        if measure_name in measure_names:
            errors.append(f"Duplicate measure name: {measure_name}")
        measure_names.add(measure_name)
        
        # Basic DAX validation
        if not dax_expression:
            warnings.append(f"Measure {measure_name} has empty expression")
        else:
            # Check for common DAX syntax issues
            if not dax_expression.strip().endswith(')') and '(' in dax_expression:
                warnings.append(f"Measure {measure_name} may have unbalanced parentheses")
    
    # Validate relationships
    for relationship in relationships:
        if hasattr(relationship, 'from_table'):  # Relationship object
            from_table = relationship.from_table
            to_table = relationship.to_table
            from_column = getattr(relationship, 'from_column', '')
            to_column = getattr(relationship, 'to_column', '')
        else:  # Dictionary format
            from_table = relationship.get('from_table', '')
            to_table = relationship.get('to_table', '')
            from_column = relationship.get('from_column', '')
            to_column = relationship.get('to_column', '')
        
        if from_table not in table_names:
            errors.append(f"Relationship references unknown table: {from_table}")
        if to_table not in table_names:
            errors.append(f"Relationship references unknown table: {to_table}")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }
