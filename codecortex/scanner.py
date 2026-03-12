import os
import ast


DEFAULT_IGNORED_DIRS = {
    ".git",
    ".codecortex",
    "venv",
    ".venv",
    "__pycache__",
}


def scan_python_files(repo_path):
    python_files = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORED_DIRS]

        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))

    return python_files


def extract_imports(file_path):
    return [record["module"] for record in extract_import_records(file_path) if record["module"]]


def extract_import_records(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.append(
                    {
                        "module": name.name,
                        "kind": "import",
                        "level": 0,
                        "lineno": getattr(node, "lineno", None),
                    }
                )

        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            imports.append(
                {
                    "module": module_name,
                    "kind": "from",
                    "level": node.level,
                    "lineno": getattr(node, "lineno", None),
                }
            )

    return imports
