from datetime import datetime

project = "Inclusio"
author = "Sebastien Rousseau"
copyright = f"{datetime.now().year}, {author}"

extensions = [
    "myst_parser",
]

root_doc = "index"

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

html_theme = "furo"
html_static_path = []
