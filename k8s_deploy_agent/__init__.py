"""Source-tree import shim for the flat package layout."""

from __future__ import annotations

from pathlib import Path

__version__ = "0.1.0"

# The installable package is mapped to the repository root in pyproject.toml.
# Add that root to this package's search path so direct local execution can
# import modules such as k8s_deploy_agent.cli without requiring installation.
__path__.append(str(Path(__file__).resolve().parent.parent))
