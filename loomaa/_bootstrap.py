"""Lightweight bootstrapper for the loomaa console script.

This module intentionally uses only the Python stdlib for its top-level code so
the console entry point can run even if runtime dependencies are missing.
It offers to create a local virtualenv or install dependencies into the current
environment, then delegates to the real CLI in `loomaa.cli`.
"""
from __future__ import annotations

import os
import sys
import subprocess
import venv
from typing import List


RUNTIME_REQUIREMENTS: List[str] = [
    "typer>=0.9.0",
    "pydantic>=2.0.0",
    "msal>=1.27.0",
    "requests>=2.31.0",
    "jinja2>=3.1.0",
    # Viewer deps
    "streamlit>=1.28.0",
    "plotly>=5.17.0",
    "networkx>=3.2.0",
    "pandas>=2.0.0",
]


def _python_in_venv(venv_dir: str) -> str:
    if os.name == "nt":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python")


def _install_packages(python_exe: str, packages: List[str]) -> None:
    cmd = [python_exe, "-m", "pip", "install", "--upgrade"] + packages
    subprocess.check_call(cmd)


def _create_venv_and_install(venv_dir: str) -> None:
    print(f"🔮 Creating Loomaa virtual environment...")
    venv.create(venv_dir, with_pip=True)
    py = _python_in_venv(venv_dir)
    print("📦 Installing dependencies (this takes ~30 seconds)...")
    _install_packages(py, RUNTIME_REQUIREMENTS)
    print("✅ Setup complete! Loomaa is ready to use.")


def _install_into_current_env() -> None:
    print("📦 Installing Loomaa dependencies into current Python environment...")
    _install_packages(sys.executable, RUNTIME_REQUIREMENTS)
    print("✅ Dependencies installed successfully!")


def _check_dependencies() -> bool:
    """Check if runtime dependencies are available"""
    try:
        import typer
        import pydantic
        import msal
        import requests
        import jinja2
        import streamlit
        import plotly
        import networkx
        import pandas
        return True
    except ImportError:
        return False


def main(argv: List[str] | None = None) -> int:
    """Entry point used by console_scripts.

    Professional UX: Automatically handle dependencies without user friction.
    """
    argv = argv if argv is not None else sys.argv[1:]

    # If all dependencies are available, run normally
    if _check_dependencies():
        try:
            from loomaa import cli
            return cli.run(argv)
        except Exception as e:
            print(f"❌ Loomaa CLI error: {e}")
            return 1

    # First-time setup experience
    print("🔮 Welcome to Loomaa - Semantic Model as Code!")
    print("💡 First-time setup: Installing dependencies...")
    print()
    
    # Try installing into current environment first (most common case)
    try:
        _install_into_current_env()
        
        # Verify installation worked
        if _check_dependencies():
            print("🚀 Running your Loomaa command now...")
            from loomaa import cli
            return cli.run(argv)
        else:
            print("⚠️  Installation verification failed.")
            
    except subprocess.CalledProcessError:
        print("⚠️  Installation into current environment failed (permission issue).")
        print("📁 Creating isolated virtual environment instead...")
        
        # Fallback to venv approach
        try:
            venv_dir = os.path.join(os.path.expanduser("~"), ".loomaa")
            _create_venv_and_install(venv_dir)
            
            # Run via venv
            py = _python_in_venv(venv_dir)
            cmd = [py, "-c", "from loomaa import cli; cli.app()", *argv]
            return subprocess.call(cmd)
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            print("🛠️  Manual installation:")
            print("     pip install typer pydantic msal requests jinja2")
            return 2
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
