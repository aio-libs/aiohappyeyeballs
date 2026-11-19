# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from pathlib import Path

PROJECT_ROOT_DIR = Path(__file__).parents[1].resolve()
GITHUB_URL = "https://github.com"
GITHUB_REPO_URL = f"{GITHUB_URL}/aio-libs/aiohappyeyeballs"
GITHUB_SPONSORS_URL = f"{GITHUB_URL}/sponsors"

# Project information
project = "aiohappyeyeballs"
copyright = "2023, J. Nick Koston"
author = "J. Nick Koston"
release = "2.7.2"

# General configuration
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinxcontrib.towncrier.ext",  # provides `towncrier-draft-entries`
]

# The suffix of source filenames.
source_suffix = [
    ".rst",
    ".md",
]
templates_path = [
    "_templates",
]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "changelog.d/**",
]

# Options for HTML output
html_theme = "furo"
html_static_path = ["_static"]

# Roles used by the Towncrier news fragments in docs/changelog.d/
extlinks = {
    "issue": (f"{GITHUB_REPO_URL}/issues/%s", "#%s"),
    "pr": (f"{GITHUB_REPO_URL}/pull/%s", "PR #%s"),
    "commit": (f"{GITHUB_REPO_URL}/commit/%s", "%s"),
    "user": (f"{GITHUB_SPONSORS_URL}/%s", "@%s"),
}

# Options for the sphinxcontrib-towncrier extension
towncrier_draft_autoversion_mode = "draft"
towncrier_draft_include_empty = True
towncrier_draft_working_directory = PROJECT_ROOT_DIR
