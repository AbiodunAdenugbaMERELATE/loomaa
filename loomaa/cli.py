"""Loomaa CLI.

End-user workflow:
    loomaa init
    loomaa compile
    loomaa view
    loomaa deploy
"""
import os
import sys
import typer
from pathlib import Path
from loomaa.utils import write_file
from loomaa.compiler_pydantic import compile_semantic_model

# NOTE: deploy/view are optional at runtime but are part of the default UX.


app = typer.Typer(help="Loomaa CLI - Pydantic Semantic Modeling")


def _load_dotenv_into_environ(env_path: Path = Path(".env")) -> None:
    """Load key/value pairs from a local .env into os.environ.

    We intentionally avoid external deps (python-dotenv) and keep behavior simple:
    - Ignores blank lines and comments
    - Supports KEY=VALUE with optional surrounding quotes
    - Does not overwrite existing environment variables
    """
    try:
        if not env_path.exists():
            return
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"\'')
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        # Best-effort only; compile should still work without .env.
        return


def run(argv=None) -> int:
        """Run the Typer app with an explicit argv list.

        The console entry point calls this to avoid Click/Typer argv issues.
        """
        argv = argv if argv is not None else sys.argv[1:]
        # Typer wraps Click. Passing argv via keyword keeps behavior consistent.
        app(prog_name="loomaa", args=list(argv))
        return 0

@app.command()
def init(project_name: str = typer.Argument("loomaa-project")):
    """Initialize a new Loomaa project.

    The semantic model folder name is ALWAYS 'example' (constant learning scaffold) regardless
    of the project root directory name provided. This avoids confusion between project root
    and model name.
    """

    model_dir_name = "example"
    project_path = Path(project_name)

    if project_path.exists():
        typer.echo(f"[ERROR] Directory '{project_name}' already exists")
        raise typer.Exit(1)

    typer.echo(f"Creating Loomaa project: {project_name}")

    # Create production folder structure
    project_path.mkdir(parents=True)
    (project_path / "models").mkdir()
    (project_path / "models" / model_dir_name).mkdir()  # fixed model folder
    (project_path / "compiled").mkdir()
    
    typer.echo("  [OK] Created project structure")
    
    # ------------------------------------------------------------------
    # .env template (restored to align with deploy.py expectations)
    # ------------------------------------------------------------------
    env_template = """# Loomaa / Fabric Authentication & Connection Settings
# Fill these before running deployment commands.

FABRIC_TENANT_ID=
FABRIC_CLIENT_ID=
FABRIC_CLIENT_SECRET=
FABRIC_WORKSPACE_ID=

# DirectLake source
# This is the Fabric *itemId GUID* for your Lakehouse/Warehouse.
# You can copy it from the OneLake URL:
#   https://onelake.dfs.fabric.microsoft.com/<workspaceId>/<itemId>
FABRIC_DIRECTLAKE_ITEM_ID=

# Warehouse SQL endpoint (for Import-mode tables)
# You can copy this from the Warehouse connection details.
FABRIC_SQL_SERVER=

# Database name used by Power Query when connecting via Sql.Database.
# In Fabric this is typically your Warehouse name.
FABRIC_SQL_DATABASE=

# (Keep this file out of source control – add to .gitignore)
"""

    # Model file in its own folder
    model_content = '''"""Example Semantic Model (learning scaffold)

Fixed model folder name: 'example'

This scaffold is designed to match the built-in Microsoft Fabric **Sample Warehouse**
experience (tables like dbo.Trip, dbo.Medallion, dbo.Date, dbo.Time).

Goal UX:
1) Create a new Fabric Warehouse using "Warehouse sample" / "Use sample database"
2) Put your Fabric IDs into `.env`
3) `loomaa compile` then `loomaa deploy`

This sample intentionally includes the core Semantic Model building blocks:
- Multiple DirectLake tables
- Relationships
- Measures (table + model-level)
- Calculated column
- Hierarchy
- RLS role
"""

from .tables import (
    create_trip_table,
    create_medallion_table,
    create_date_table,
    create_time_table,
)
from .relationships import create_relationships
from .measures import model_measures
from .roles import roles
from loomaa.models_pydantic import SemanticModel


def build_model():
    trip = create_trip_table()
    medallion = create_medallion_table()
    date = create_date_table()
    time = create_time_table()

    relationships = create_relationships(trip, medallion, date, time)

    return SemanticModel(
        name="example",
        description="Loomaa example model built on the Fabric Sample Warehouse tables (Trip/Medallion/Date/Time).",
        tables=[trip, medallion, date, time],
        relationships=relationships,
        measures=model_measures,
        roles=roles,
    )


model = build_model()
'''

    # Model-level measures file
    measures_content = '''"""Model-level measures

These measures are not tied to a single table.
"""

from loomaa.models_pydantic import Measure


model_measures = [
    Measure(
        name="Miles per Trip",
        expression="DIVIDE([Total Miles], [Trip Count], 0)",
        description="Average trip distance (miles)",
        format_string="0.00",
        folder="KPI",
    ),
]
'''

    # Roles file
    roles_content = '''"""Security roles (Row-Level Security)

Each Role contains a table_permissions mapping: table_name -> DAX filter expression.
This is a simple example you can replace with your own logic.
"""

from loomaa.models_pydantic import Role


roles = [
    Role(
        name="My Medallion",
        description="Example RLS: restricts to a single MedallionCode.",
        table_permissions={
            "Medallion": 'Medallion[MedallionCode] = "000000"'
        },
    )
]
'''
    
    # Tables file
    tables_content = '''"""Table definitions for the example model.

This scaffold aligns with the Fabric Sample Warehouse tables.

Includes:
- DirectLake fact table (Trip)
- Import dimensions (Medallion/Date/Time)
- Table measures
- Calculated column (on Medallion)
- Hierarchy (on Date)
"""

import os

from loomaa.models_pydantic import (
    Table,
    Column,
    Measure,
    CalculatedColumn,
    DataType,
    TableMode,
    Hierarchy,
)


def _directlake_item_id() -> str:
    # In Fabric OneLake, the DirectLake expression uses:
    #   https://onelake.dfs.fabric.microsoft.com/<workspaceId>/<itemId>
    value = (os.getenv("FABRIC_DIRECTLAKE_ITEM_ID") or "").strip()
    # Keep compile working even when `.env` exists but values are blank.
    # Users must replace this with the real itemId GUID before deploying.
    return value or "00000000-0000-0000-0000-000000000000"


def _sql_server() -> str:
    value = (os.getenv("FABRIC_SQL_SERVER") or "").strip()
    return value or "your-warehouse-sql-endpoint"


def _sql_database() -> str:
    value = (os.getenv("FABRIC_SQL_DATABASE") or "").strip()
    return value or "your-warehouse-name"


def create_trip_table() -> Table:
    return Table(
        name="Trip",
        table_schema="dbo",
        mode=TableMode.DIRECTLAKE,
        description="Trips (fact) from the Fabric Sample Warehouse",
        directlake_resource_id=_directlake_item_id(),
        columns=[
            Column(name="MedallionID", dtype=DataType.INT64, description="Medallion key"),
            Column(name="DateID", dtype=DataType.INT64, description="Date key"),
            Column(name="PickupTimeID", dtype=DataType.INT64, description="Pickup time key"),
            Column(name="TripDistanceMiles", dtype=DataType.DECIMAL, description="Trip distance (miles)"),
            Column(name="PassengerCount", dtype=DataType.INT64, description="Passengers"),
        ],
        measures=[
            Measure(
                name="Trip Count",
                expression="COUNTROWS(Trip)",
                description="Number of trips",
            ),
            Measure(
                name="Total Miles",
                expression="SUM(Trip[TripDistanceMiles])",
                description="Total trip distance (miles)",
                format_string="0.00",
            ),
        ],
        query_group="Fact Tables",
    )


def create_medallion_table() -> Table:
    return Table(
        name="Medallion",
        table_schema="dbo",
        mode=TableMode.IMPORT,
        description="Medallion dimension from the Fabric Sample Warehouse",
        sql_server=_sql_server(),
        sql_database=_sql_database(),
        columns=[
            Column(name="MedallionID", dtype=DataType.INT64, description="Medallion key"),
            Column(name="MedallionCode", dtype=DataType.STRING, description="Medallion code"),
        ],
        calculated_columns=[
            CalculatedColumn(
                name="MedallionCode (Upper)",
                expression="UPPER(Medallion[MedallionCode])",
                description="Calculated column example",
                dtype=DataType.STRING,
            )
        ],
        query_group="Dimension Tables",
    )


def create_date_table() -> Table:
    return Table(
        name="Date",
        table_schema="dbo",
        mode=TableMode.IMPORT,
        description="Date dimension from the Fabric Sample Warehouse",
        sql_server=_sql_server(),
        sql_database=_sql_database(),
        columns=[
            Column(name="DateID", dtype=DataType.INT64, description="Date key"),
            Column(name="IsWeekday", dtype=DataType.BOOLEAN, description="Weekday flag"),
            Column(name="IsHolidayUSA", dtype=DataType.BOOLEAN, description="US holiday flag"),
        ],
        hierarchies=[
            Hierarchy(
                name="Date Hierarchy",
                levels=["DateID"],
                description="Placeholder hierarchy (replace with Year/Month/Day columns if present)",
            )
        ],
        query_group="Dimension Tables",
    )


def create_time_table() -> Table:
    return Table(
        name="Time",
        table_schema="dbo",
        mode=TableMode.IMPORT,
        description="Time dimension from the Fabric Sample Warehouse",
        sql_server=_sql_server(),
        sql_database=_sql_database(),
        columns=[
            Column(name="TimeID", dtype=DataType.INT64, description="Time key"),
            Column(name="HourlyBucket", dtype=DataType.STRING, description="Hourly bucket label"),
        ],
        query_group="Dimension Tables",
    )
'''
    
    # Relationships file
    relationships_content = '''"""Model relationships for the example model."""

from loomaa.models_pydantic import Relationship, Cardinality, CrossFilter


def create_relationships(trip, medallion, date, time):
    return [
        Relationship(
            from_table=trip,
            from_column="MedallionID",
            to_table=medallion,
            to_column="MedallionID",
            cardinality=Cardinality.MANY_TO_ONE,
            cross_filter_direction=CrossFilter.SINGLE,
            description="Trip -> Medallion",
        ),
        Relationship(
            from_table=trip,
            from_column="DateID",
            to_table=date,
            to_column="DateID",
            cardinality=Cardinality.MANY_TO_ONE,
            cross_filter_direction=CrossFilter.SINGLE,
            description="Trip -> Date",
        ),
        Relationship(
            from_table=trip,
            from_column="PickupTimeID",
            to_table=time,
            to_column="TimeID",
            cardinality=Cardinality.MANY_TO_ONE,
            cross_filter_direction=CrossFilter.SINGLE,
            description="Trip -> Time",
        ),
    ]
'''
    
    # Requirements (project scaffold)
    # Users can also skip this and just `pip install loomaa`.
    requirements_content = """# Loomaa project requirements
#
# If Loomaa is published to PyPI, this is all you need.
loomaa>=0.1.0
"""

    gitignore_content = """# Loomaa
.env
compiled/
__pycache__/
.venv/
*.pyc
"""

    compiled_readme = """# Compiled Artifacts

This folder is created by `loomaa compile`.

Expected structure after compiling the example model:

- `compiled/example/example.SemanticModel/` (deployable Fabric item)
- `compiled/example/model.json` (viewer + tooling metadata)
"""

    example_readme = """# Example Model

This example is created automatically by `loomaa init` so you can learn Loomaa by reading real code before compiling.

This scaffold is designed to work naturally with the **Fabric Sample Warehouse**.

What it contains:
- Fact table: `dbo.Trip` (DirectLake)
- Dimensions: `dbo.Medallion`, `dbo.Date`, `dbo.Time` (Import)
- Relationships from Trip -> dimensions
- Table measures + model-level measure
- Calculated column example
- Hierarchy example
- RLS role example

Files:
- `tables.py` – tables/columns/measures
- `relationships.py` – relationships
- `measures.py` – model-level measures
- `roles.py` – RLS roles
"""
    
    # Write model files in proper folder structure
    write_file(project_path / "models" / "__init__.py", "")
    write_file(project_path / "models" / model_dir_name / "__init__.py", model_content)
    write_file(project_path / "models" / model_dir_name / "tables.py", tables_content)
    write_file(project_path / "models" / model_dir_name / "relationships.py", relationships_content)
    write_file(project_path / "models" / model_dir_name / "measures.py", measures_content)
    write_file(project_path / "models" / model_dir_name / "roles.py", roles_content)
    write_file(project_path / "models" / model_dir_name / "README.md", example_readme)
    write_file(project_path / "compiled" / "README.md", compiled_readme)
    write_file(project_path / "requirements.txt", requirements_content)
    write_file(project_path / ".gitignore", gitignore_content)
    write_file(
        project_path / "README.md",
        f"""# {project_name}

Loomaa project scaffold.

Quick start:
1. Review the example model code in `models/example/` (no compile needed to learn).
2. Fill in `.env` (required for deploy, optional for compile/view).
3. Compile: `loomaa compile`
4. View: `loomaa view`
5. Deploy: `loomaa deploy`

Notes:
- `loomaa compile` and `loomaa view` can run even if `.env` is blank.
- `loomaa deploy` requires real `FABRIC_*` values in `.env`.

Security:
- Do not commit `.env`.
""",
    )
    write_file(project_path / ".env", env_template)
    
    typer.echo("  [OK] Created model files")
    
    typer.echo(f"[OK] Project '{project_name}' created successfully!")
    typer.echo("")
    typer.echo("Next steps:")
    typer.echo(f"  1. cd {project_name}")
    typer.echo("  2. pip install -r requirements.txt  (or: pip install loomaa)")
    typer.echo("  3. Fill in .env (required for deploy)")
    typer.echo("  4. loomaa compile")
    typer.echo("  5. loomaa view")
    typer.echo("  6. loomaa deploy")
    typer.echo("")
    typer.echo("Project Structure:")  
    typer.echo(f"  {project_name}/")
    typer.echo(f"  ├── models/example/             # Example model folder (fixed)")
    typer.echo("  ├── compiled/                   # Generated TMDL files")
    typer.echo("  ├── requirements.txt            # Install Loomaa")
    typer.echo("  └── .env                        # Fabric auth + connections (DO NOT COMMIT)")
    typer.echo("")
    typer.echo("Security: Add '.env' to your global/project .gitignore if not already.")
    typer.echo("Populate FABRIC_* values before running any deploy commands.")

@app.command()
def compile():
    """Compile semantic models to TMDL (supports folder-based models)"""

    # Ensure model code (models/*) can read FABRIC_* settings via os.getenv without
    # requiring the user to manually export environment variables.
    _load_dotenv_into_environ(Path(".env"))
    
    models_dir = Path("models")
    if not models_dir.exists():
        typer.echo("[ERROR] models/ directory not found. Run 'loomaa init' first.")
        raise typer.Exit(1)
    
    # Find all model folders
    model_folders = [d for d in models_dir.iterdir() if d.is_dir() and d.name != "__pycache__"]
    
    if not model_folders:
        typer.echo("[ERROR] No model folders found in models/ directory.")
        raise typer.Exit(1)
    
    typer.echo(f"Found {len(model_folders)} model(s) to compile...")
    
    try:
        sys.path.insert(0, os.getcwd())
        
        for model_folder in model_folders:
            model_name = model_folder.name
            typer.echo(f"Compiling model: {model_name}")
            
            # Import the model from its folder
            module_path = f"models.{model_name}"
            model_module = __import__(module_path, fromlist=['model'])
            
            # Get the model object
            if hasattr(model_module, 'model'):
                model_obj = model_module.model
                compile_semantic_model(model_obj, f"compiled/{model_name}")
                typer.echo(f"  [OK] {model_name} compiled successfully")
            else:
                typer.echo(f"  [ERROR] No 'model' found in {module_path}")
        
        typer.echo("[OK] All models compiled! Check compiled/ directory.")
        
    except Exception as e:
        typer.echo(f"[ERROR] Compilation failed: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@app.command()
def view(port: int = 8501):
    """Launch the local semantic model viewer."""
    try:
        import subprocess

        viewer_path = Path(__file__).with_name("viewer.py")
        cmd = [sys.executable, "-m", "streamlit", "run", str(viewer_path), "--server.port", str(port)]
        raise typer.Exit(subprocess.call(cmd))
    except FileNotFoundError as e:
        typer.echo(f"[ERROR] Could not start viewer: {e}")
        raise typer.Exit(1)


@app.command()
def deploy():
    """Deploy compiled semantic model(s) to Fabric / Power BI service."""
    from loomaa.deploy import deploy_complete_semantic_model

    compiled_dir = Path("compiled")
    if not compiled_dir.exists():
        typer.echo("[ERROR] compiled/ not found. Run 'loomaa compile' first.")
        raise typer.Exit(1)

    # Each compiled/<model_folder>/ should contain exactly one *.SemanticModel directory.
    model_folders = [d for d in compiled_dir.iterdir() if d.is_dir()]
    if not model_folders:
        typer.echo("[ERROR] No compiled models found. Run 'loomaa compile' first.")
        raise typer.Exit(1)

    for folder in model_folders:
        semantic_dirs = [d for d in folder.iterdir() if d.is_dir() and d.name.endswith(".SemanticModel")]
        if not semantic_dirs:
            typer.echo(f"[WARN] No .SemanticModel directory found under {folder}")
            continue
        if len(semantic_dirs) > 1:
            typer.echo(f"[WARN] Multiple .SemanticModel directories under {folder}; deploying the first")

        semantic_dir = semantic_dirs[0]
        model_name = semantic_dir.name[: -len(".SemanticModel")]
        typer.echo(f"Deploying: {model_name}")
        deploy_complete_semantic_model(model_name, str(semantic_dir))

    typer.echo("[OK] Deploy complete")

if __name__ == "__main__":
    raise SystemExit(run())