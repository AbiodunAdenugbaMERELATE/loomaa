"""
Streamlit-based Power BI Model Viewer
Professional semantic model viewer using Streamlit for clean UI
"""
import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import plotly.express as px
import networkx as nx
import os
from typing import List, Dict, Any


def _normalize_cardinality(value: Any) -> str:
    if value is None:
        return "Many-to-One"
    text = str(value).strip()
    if not text:
        return "Many-to-One"

    normalized = (
        text.replace("RelationshipCardinality.", "")
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
        .lower()
    )

    mapping = {
        "manytoone": "Many-to-One",
        "onetomany": "One-to-Many",
        "onetoone": "One-to-One",
        "manytomany": "Many-to-Many",
    }
    return mapping.get(normalized, text)


def _normalize_cross_filter(value: Any) -> str:
    if value is None:
        return "Single"
    text = str(value).strip()
    if not text:
        return "Single"

    normalized = (
        text.replace("CrossFilterDirection.", "")
        .replace("RelationshipCrossFilteringBehavior.", "")
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
        .lower()
    )

    mapping = {
        "onedirection": "Single",
        "singledirection": "Single",
        "single": "Single",
        "bothdirections": "Both",
        "both": "Both",
        "none": "None",
    }
    return mapping.get(normalized, text)

def create_relationship_diagram(relationships: List[Dict], tables: List[Dict]):
    """Create a clean relationship diagram.

    Tries to present a star-schema-friendly layout: the highest-degree table is centered,
    and other tables are arranged around it.
    """
    
    if not relationships:
        st.info("No relationships defined in this model.")
        return
    
    import math
    
    # Create network graph
    G = nx.Graph()
    
    # Add table nodes
    for table in tables:
        table_name = table.get('name', 'Unknown')
        G.add_node(table_name)
    
    # Add relationship edges
    for rel in relationships:
        from_table = rel.get('from_table', 'Unknown')
        to_table = rel.get('to_table', 'Unknown') 
        G.add_edge(from_table, to_table, 
                  cardinality=_normalize_cardinality(rel.get('cardinality')))

    # Star-friendly layout: center the most connected table
    nodes = list(G.nodes())
    if not nodes:
        st.info("No tables/relationships to visualize.")
        return

    degrees = dict(G.degree())
    center = max(degrees, key=lambda n: degrees.get(n, 0))
    others = [n for n in nodes if n != center]

    pos: Dict[str, tuple[float, float]] = {center: (0.0, 0.0)}
    if others:
        radius = 3.2
        step = (2 * math.pi) / len(others)
        for idx, node in enumerate(sorted(others)):
            angle = idx * step
            pos[node] = (radius * math.cos(angle), radius * math.sin(angle))
    
    # Create plotly figure
    fig = go.Figure()
    
    # Add relationship lines
    for edge in G.edges(data=True):
        from_node, to_node = edge[0], edge[1]
        x0, y0 = pos[from_node]
        x1, y1 = pos[to_node]
        
        # Simple line
        fig.add_trace(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            line={'width': 2, 'color': '#666666'},
            mode='lines',
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Add cardinality label in the middle
        mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2
        cardinality = _normalize_cardinality(edge[2].get('cardinality'))
        
        fig.add_annotation(
            x=mid_x, y=mid_y,
            text=cardinality,
            showarrow=False,
            font={'size': 9, 'color': '#555555'},
            bgcolor='white',
            bordercolor='#cccccc',
            borderwidth=1
        )
    
    # Add rounded square table boxes using shapes
    for node, (x, y) in pos.items():
        # Add rounded rectangle shape
        fig.add_shape(
            type="rect",
            x0=x-0.8, y0=y-0.4, x1=x+0.8, y1=y+0.4,
            fillcolor='white',
            line={'color': '#333333', 'width': 2},
            opacity=1.0
        )
        
        # Add table name text ON TOP of the rectangle
        fig.add_annotation(
            x=x, y=y,
            text=node,
            showarrow=False,
            font={'size': 14, 'color': '#333333', 'family': 'Arial'},
            bgcolor='rgba(255,255,255,0)',  # Transparent background
            bordercolor='rgba(0,0,0,0)',    # No border
        )
    
    # Clean layout - no title
    fig.update_layout(
        showlegend=False,
        height=440,
        xaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False},
        yaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False},
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin={'t': 20, 'l': 20, 'r': 20, 'b': 20}
    )
    
    st.plotly_chart(
        fig, 
        config={'displayModeBar': False, 'staticPlot': False},
        use_container_width=True
    )
    
    # Also show the clean text relationships
    st.markdown("### Relationship Details")
    for rel in relationships:
        from_table = rel.get('from_table', 'Unknown')
        to_table = rel.get('to_table', 'Unknown')
        from_col = rel.get('from_column', '')
        to_col = rel.get('to_column', '')
        cardinality = _normalize_cardinality(rel.get('cardinality'))
        st.write(f"**{from_table}.{from_col}** → **{to_table}.{to_col}** ({cardinality})")

def load_models() -> List[Dict[str, Any]]:
    """Load compiled models from organized model folders"""
    models = []
    compiled_dir = "compiled"
    
    if not os.path.exists(compiled_dir):
        return []
    
    try:
        # Look for model folders (each containing model.json)
        for folder in os.listdir(compiled_dir):
            folder_path = os.path.join(compiled_dir, folder)
            if os.path.isdir(folder_path):
                json_path = os.path.join(folder_path, "model.json")
                if os.path.exists(json_path):
                    try:
                        with open(json_path, "r", encoding='utf-8') as f:
                            model_data = json.load(f)
                            model_data["_folder"] = folder
                            models.append(model_data)
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        st.warning(f"Could not load model from {folder}: {e}")
    except Exception as e:
        st.error(f"Error loading models: {e}")
    
    return models

def render_table_card(table: Dict[str, Any], index: int):
    """Render a single table card with Power BI styling"""
    
    with st.container():
        # Table header with name and badge
        col_header, col_badge = st.columns([4, 1])
        
        with col_header:
            table_name = table.get('name', 'Unknown Table')
            st.markdown(f"### 📊 {table_name}")
        
        with col_badge:
            # Just show table info without assumptions
            columns = table.get('columns', [])
            st.markdown("**📊 Table**")
        
        # Table metadata
        mode = table.get('mode', 'Import')
        st.caption(f"**Mode:** {mode} | **Columns:** {len(columns)}")
        
        if table.get('description'):
            st.info(table.get('description'))
        
        # Column details
        if columns:
            st.markdown("**📋 Columns:**")
            
            # Create columns dataframe
            columns_data = []
            for col in columns:
                col_name = col.get('name', 'Unknown')
                col_type = col.get('dtype', 'Text')
                col_desc = col.get('description', '')
                format_str = col.get('format_string', '')
                
                columns_data.append({
                    '📋 Column': col_name,
                    '🏷️ Type': col_type,
                    '💰 Format': format_str if format_str else '-',
                    '📝 Description': col_desc[:50] + ('...' if len(col_desc) > 50 else '') if col_desc else '-'
                })
            
            df = pd.DataFrame(columns_data)
            st.dataframe(
                df,
                hide_index=True,
                width='stretch',
                column_config={
                    '📋 Column': st.column_config.TextColumn(width="medium"),
                    '🏷️ Type': st.column_config.TextColumn(width="small"),
                    '💰 Format': st.column_config.TextColumn(width="small"),
                    '📝 Description': st.column_config.TextColumn(width="large")
                }
            )
        
        st.divider()

def main():
    """Main Streamlit application"""
    
    # Page configuration
    st.set_page_config(
        page_title="Loomaa Model Viewer",
        page_icon="L",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': """
            # Loomaa Model Viewer
            Professional semantic model viewer for Microsoft Fabric.
            
            **Features:**
            - Interactive model exploration
            - Power BI-style interface
            - Relationship visualization
            - DAX measure viewer
            """
        }
    )
    
    # Custom CSS for professional black on gray with white content theme
    st.markdown("""
    <style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom styling - Black on Gray with White Content */
    .main > div {
        padding: 0.5rem 2rem;
        background-color: #f8f9fa;
        color: #212529;
    }
    
    .stMetric {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        color: #212529;
        border: 1px solid #dee2e6;
    }
    
    .stMetric > div {
        color: #212529 !important;
    }
    
    .stSelectbox > div > div {
        background: white;
        border-radius: 8px;
        border: 2px solid #dee2e6;
        color: #212529;
    }
    
    .model-header {
        background: linear-gradient(135deg, #212529 0%, #343a40 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 15px;
        margin: -0.5rem -2rem 1rem -2rem;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
        color: #495057;
        background-color: white;
        border: 1px solid #dee2e6;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #212529;
        color: white;
        border-color: #212529;
    }
    
    .stContainer > div {
        border: 1px solid #dee2e6;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        color: #212529;
    }
    
    /* Sidebar styling (stable selectors) */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
        color: #212529;
        border-right: 1px solid #dee2e6;
    }

    /* Make sidebar content breathe a bit */
    [data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Content areas should be white */
    .stDataFrame {
        background: white;
        border-radius: 8px;
    }
    
    /* Table header styling - darker headers */
    .stDataFrame thead tr th {
        background-color: #343a40 !important;
        color: white !important;
        font-weight: 600 !important;
        border-bottom: 2px solid #212529 !important;
        padding: 12px 16px !important;
    }
    
    .stDataFrame tbody tr td {
        padding: 10px 16px !important;
        border-bottom: 1px solid #dee2e6 !important;
    }
    
    .stDataFrame tbody tr:hover {
        background-color: #f8f9fa !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header section
    st.markdown("""
    <div class="model-header">
        <h1>Loomaa Model Viewer</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Load models
    with st.spinner("Loading compiled models..."):
        models = load_models()
    
    if not models:
        st.error("No compiled models found.")
        st.info("""
        **To get started:**
        1. Run `loomaa compile` in your project directory
        2. Ensure you have a `compiled/` folder with model.json files
        3. Refresh this page
        """)
        st.stop()
    
    # Sidebar - Model Selection & Info
    with st.sidebar:
        st.markdown("## Model Selection")
        
        model_names = [m.get('name', f"Model {i+1}") for i, m in enumerate(models)]
        selected_model_name = st.selectbox(
            "Choose a semantic model:",
            model_names,
            help="Select which compiled model to explore"
        )
        
        # Get selected model data
        selected_model = models[model_names.index(selected_model_name)]
        
        st.divider()
        
        # Quick statistics (removed Model Information to prevent sidebar scrolling)
        tables = selected_model.get('tables', [])
        measures = selected_model.get('measures', [])
        relationships = selected_model.get('relationships', [])
        total_columns = sum(len(table.get('columns', [])) for table in tables)
        
        # Minimal sidebar - no stats to prevent scrolling
        st.divider()
        st.markdown("### Actions")
        if st.button("Refresh models", help="Reload models from compiled folder"):
            st.rerun()
    
    # Main content area
    model_data = selected_model
    tables = model_data.get('tables', [])
    measures = model_data.get('measures', [])
    relationships = model_data.get('relationships', [])
    total_columns = sum(len(table.get('columns', [])) for table in tables)
    
    # Overview metrics row
    st.markdown("## Model Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📊 Tables", 
            len(tables), 
            help="Number of tables in this semantic model"
        )
    
    with col2:
        st.metric(
            "📈 Measures", 
            len(measures), 
            help="Number of DAX measures for calculations"
        )
    
    with col3:
        st.metric(
            "🔗 Relationships", 
            len(relationships), 
            help="Relationships connecting tables"
        )
    
    with col4:
        st.metric(
            "📋 Total Columns", 
            total_columns, 
            help="Sum of all columns across tables"
        )
    
    st.divider()
    
    # Main tabbed interface - Power BI Model View style
    tab1, tab2, tab3 = st.tabs(["Tables", "Relationships", "Measures"])
    
    with tab1:
        st.markdown("## Table Explorer")
        
        if not tables:
            st.info("📋 No tables found in this model.")
        else:
            # Search and filter
            search_term = st.text_input("Search tables:", placeholder="Type to filter tables...")
            
            filtered_tables = tables
            if search_term:
                filtered_tables = [
                    table for table in tables 
                    if search_term.lower() in table.get('name', '').lower()
                    or search_term.lower() in str(table.get('columns', [])).lower()
                ]
            
            if not filtered_tables:
                st.warning(f"No tables match '{search_term}'")
            else:
                st.caption(f"Showing {len(filtered_tables)} of {len(tables)} tables")
                
                # Display tables in a clean layout
                for i, table in enumerate(filtered_tables):
                    render_table_card(table, i)
    
    with tab2:
        if relationships:
            # Interactive relationship diagram
            st.markdown("### Visual Relationship Map")
            create_relationship_diagram(relationships, tables)
            
            st.divider()
            
            # Relationship details table
            st.markdown("### Relationship Details")
            
            rel_data = []
            for rel in relationships:
                rel_data.append({
                    '🗂️ From Table': rel.get('from_table', 'Unknown'),
                    '📋 From Column': rel.get('from_column', 'Unknown'),
                    '🗂️ To Table': rel.get('to_table', 'Unknown'),
                    '📋 To Column': rel.get('to_column', 'Unknown'),
                    '🔢 Cardinality': _normalize_cardinality(rel.get('cardinality')),
                    '🔄 Cross Filter': _normalize_cross_filter(rel.get('cross_filter_direction')),
                    '✅ Active': bool(rel.get('is_active', True))
                })
            
            df_relationships = pd.DataFrame(rel_data)
            st.dataframe(
                df_relationships,
                hide_index=True,
                width='stretch',
                column_config={
                    '🔢 Cardinality': st.column_config.SelectboxColumn(
                        options=['One-to-Many', 'Many-to-One', 'One-to-One', 'Many-to-Many']
                    ),
                    '🔄 Cross Filter': st.column_config.SelectboxColumn(
                        options=['Single', 'Both', 'None']
                    ),
                    '✅ Active': st.column_config.CheckboxColumn()
                }
            )
            
        else:
            st.info("No relationships defined in this model.")
            st.markdown("""
            **💡 Tip:** Relationships connect your tables and enable cross-filtering in reports.
            Add relationships in your model.py file to see them here.
            """)
    
    with tab3:
        st.markdown("## Measure Library")
        
        if measures:
            # Search measures
            measure_search = st.text_input("Search measures:", placeholder="Type to filter measures...")
            
            filtered_measures = measures
            if measure_search:
                filtered_measures = [
                    measure for measure in measures
                    if measure_search.lower() in measure.get('name', '').lower()
                    or measure_search.lower() in measure.get('expression', '').lower()
                ]
            
            if not filtered_measures:
                st.warning(f"No measures match '{measure_search}'")
            else:
                st.caption(f"Showing {len(filtered_measures)} of {len(measures)} measures")
                
                # Display measures
                for measure in filtered_measures:
                    measure_name = measure.get('name', 'Unknown Measure')
                    expression = measure.get('expression', 'No expression defined')
                    
                    with st.expander(f"📈 **{measure_name}**", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown("**🧮 DAX Expression:**")
                            st.code(expression, language='dax', line_numbers=True)
                            
                            if measure.get('description'):
                                st.markdown("**📝 Description:**")
                                st.info(measure.get('description'))
                        
                        with col2:
                            st.markdown("**⚙️ Properties:**")
                            
                            format_string = measure.get('format_string', 'Default')
                            st.text(f"🎨 Format: {format_string}")
                            
                            folder = measure.get('folder')
                            if folder:
                                st.text(f"📁 Folder: {folder}")
                            
                            data_type = measure.get('data_type', 'Variant')
                            st.text(f"🏷️ Type: {data_type}")
                            
                            is_hidden = measure.get('is_hidden', False)
                            visibility = "🙈 Hidden" if is_hidden else "👁️ Visible"
                            st.text(f"👀 {visibility}")
                        
                        st.divider()
        else:
            st.info("📈 No measures found in this model.")
            st.markdown("""
            **💡 Tip:** Measures contain your business calculations and KPIs.
            Add measures to your model.py file to see them here.
            """)
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; padding: 1.5rem; color: #666; background: #f8f9fa; border-radius: 12px; margin-top: 1rem;'>
        <h4 style='color: #2c3e50; margin-bottom: 0.5rem;'>Loomaa</h4>
        <p style='margin-bottom: 0.5rem;'><strong>Semantic Model as Code for Microsoft Fabric</strong></p>
        <p style='font-size: 0.9rem; opacity: 0.8;'>Created by <strong>Abiodun Adenugba</strong></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()