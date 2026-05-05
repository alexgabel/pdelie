from __future__ import annotations

from datetime import date
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

try:
    import pypandoc
except ImportError:
    pass
else:
    pandoc_path = Path(pypandoc.get_pandoc_path()).parent
    os.environ["PATH"] = f"{pandoc_path}{os.pathsep}{os.environ.get('PATH', '')}"

project = "PDELie"
author = "Alex Gabel"
copyright = f"{date.today().year}, {author}"
release = "0.28.0"
version = "0.28"

extensions = [
    "myst_parser",
    "nbsphinx",
    "nbsphinx_link",
    "sphinx_copybutton",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
master_doc = "index"

exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

html_theme = "pydata_sphinx_theme"
html_title = "PDELie"
html_static_path: list[str] = []
html_theme_options = {
    "github_url": "https://github.com/alexgabel/pdelie",
    "show_toc_level": 2,
    "navbar_align": "left",
}

myst_enable_extensions = [
    "colon_fence",
]

nbsphinx_execute = "never"
nbsphinx_allow_errors = False
nbsphinx_kernel_name = "python3"
nbsphinx_prolog = """
.. note::

   This page renders committed notebook outputs. The Read the Docs build does
   not execute notebook code.
"""

suppress_warnings = [
    # nbsphinx-link stores a custom notebook-format callable in this config.
    "config.cache",
    # Notebooks contain Matplotlib image outputs without explicit alt text.
    "ref.image",
]
