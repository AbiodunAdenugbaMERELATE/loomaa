#!/usr/bin/env python3
"""
Main entry point for the loomaa package when run as a module.
"""

from .cli import run

if __name__ == "__main__":
    raise SystemExit(run())