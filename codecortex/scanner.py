import ast
import os


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
    tree = _parse_tree(file_path)
    if not tree:
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


def extract_symbol_records(file_path, module_name):
    tree = _parse_tree(file_path)
    if not tree:
        return {"nodes": [], "edges": []}

    extractor = _SymbolExtractor(module_name)
    extractor.visit(tree)
    return {
        "nodes": extractor.nodes,
        "edges": extractor.edges,
    }


def _parse_tree(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return ast.parse(f.read())
    except (SyntaxError, UnicodeDecodeError, OSError):
        return None


class _SymbolExtractor(ast.NodeVisitor):
    def __init__(self, module_name):
        self.module_name = module_name
        self.nodes = []
        self.edges = []
        self._class_stack = []
        self._function_stack = []
        self._imported_symbols = {}
        self._local_functions = {}
        self._classes = {}
        self._methods_by_class = {}

    def visit_ImportFrom(self, node):
        base_module = node.module or ""
        for alias in node.names:
            local_name = alias.asname or alias.name
            if alias.name == "*":
                continue
            self._imported_symbols[local_name] = {
                "qualified_name": ".".join(part for part in [base_module, alias.name] if part),
            }
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self._visit_function_like(node, async_kind=False)

    def visit_AsyncFunctionDef(self, node):
        self._visit_function_like(node, async_kind=True)

    def visit_ClassDef(self, node):
        qualname = self._qualname(node.name)
        node_id = _symbol_node_id("class", qualname)
        self.nodes.append(
            {
                "id": node_id,
                "type": "class",
                "name": node.name,
                "qualname": qualname,
                "module": self.module_name,
                "line": getattr(node, "lineno", None),
            }
        )
        self._classes[node.name] = qualname

        for decorator in node.decorator_list:
            decorator_name = _expr_to_name(decorator)
            if decorator_name:
                self.edges.append(
                    {
                        "from": node_id,
                        "to": _unresolved_symbol_node_id(decorator_name),
                        "type": "decorated_by",
                        "line": getattr(decorator, "lineno", getattr(node, "lineno", None)),
                        "resolution": "best_effort",
                    }
                )

        for base in node.bases:
            base_name = _expr_to_name(base)
            if base_name:
                self.edges.append(
                    {
                        "from": node_id,
                        "to": _symbol_reference_id(base_name, self.module_name, self._classes),
                        "type": "inherits",
                        "line": getattr(base, "lineno", getattr(node, "lineno", None)),
                        "resolution": "best_effort",
                    }
                )

        self._class_stack.append({"name": node.name, "qualname": qualname, "node_id": node_id})
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_Call(self, node):
        current_function = self._function_stack[-1] if self._function_stack else None
        if current_function:
            target_name, resolution = self._resolve_call_target(node.func, current_function)
            if target_name:
                self.edges.append(
                    {
                        "from": current_function["node_id"],
                        "to": target_name,
                        "type": "calls",
                        "line": getattr(node, "lineno", None),
                        "resolution": resolution,
                    }
                )

        self.generic_visit(node)

    def _visit_function_like(self, node, async_kind):
        current_class = self._class_stack[-1] if self._class_stack else None
        symbol_type = "method" if current_class else "function"
        qualname = self._qualname(node.name)
        node_id = _symbol_node_id(symbol_type, qualname)
        symbol_record = {
            "id": node_id,
            "type": symbol_type,
            "name": node.name,
            "qualname": qualname,
            "module": self.module_name,
            "line": getattr(node, "lineno", None),
        }
        if async_kind:
            symbol_record["async"] = True
        self.nodes.append(symbol_record)

        if current_class:
            self._methods_by_class.setdefault(current_class["qualname"], {})[node.name] = qualname
        else:
            self._local_functions[node.name] = qualname

        for decorator in node.decorator_list:
            decorator_name = _expr_to_name(decorator)
            if decorator_name:
                self.edges.append(
                    {
                        "from": node_id,
                        "to": _unresolved_symbol_node_id(decorator_name),
                        "type": "decorated_by",
                        "line": getattr(decorator, "lineno", getattr(node, "lineno", None)),
                        "resolution": "best_effort",
                    }
                )

        self._function_stack.append(
            {
                "name": node.name,
                "qualname": qualname,
                "node_id": node_id,
                "class_qualname": current_class["qualname"] if current_class else None,
            }
        )
        self.generic_visit(node)
        self._function_stack.pop()

    def _resolve_call_target(self, func_node, current_function):
        if isinstance(func_node, ast.Name):
            local_function = self._local_functions.get(func_node.id)
            if local_function:
                return _symbol_node_id("function", local_function), "local"

            imported_symbol = self._imported_symbols.get(func_node.id)
            if imported_symbol:
                return _symbol_node_id("function", imported_symbol["qualified_name"]), "imported"

            return _unresolved_symbol_node_id(func_node.id), "best_effort"

        if isinstance(func_node, ast.Attribute):
            attr_name = _expr_to_name(func_node)
            if not attr_name:
                return None, None

            if isinstance(func_node.value, ast.Name) and func_node.value.id == "self":
                class_methods = self._methods_by_class.get(current_function["class_qualname"], {})
                method_qualname = class_methods.get(func_node.attr)
                if method_qualname:
                    return _symbol_node_id("method", method_qualname), "self_method"

            imported_root = self._imported_symbols.get(_expr_root_name(func_node.value))
            if imported_root:
                qualified = ".".join(
                    part for part in [imported_root["qualified_name"], func_node.attr] if part
                )
                return _symbol_node_id("function", qualified), "imported_attribute"

            return _unresolved_symbol_node_id(attr_name), "best_effort"

        return None, None

    def _qualname(self, symbol_name):
        parts = [self.module_name]
        if self._class_stack:
            parts.append(self._class_stack[-1]["name"])
        parts.append(symbol_name)
        return ".".join(part for part in parts if part)


def _expr_root_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _expr_root_name(node.value)
    return None


def _expr_to_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _expr_to_name(node.value)
        if base:
            return f"{base}.{node.attr}"
        return node.attr
    if isinstance(node, ast.Call):
        return _expr_to_name(node.func)
    if isinstance(node, ast.Subscript):
        return _expr_to_name(node.value)
    return None


def _symbol_reference_id(symbol_name, module_name, known_classes):
    if symbol_name in known_classes:
        return _symbol_node_id("class", known_classes[symbol_name])
    if "." in symbol_name:
        return _unresolved_symbol_node_id(symbol_name)
    return _unresolved_symbol_node_id(f"{module_name}.{symbol_name}")


def _symbol_node_id(symbol_type, qualname):
    return f"{symbol_type}:{qualname}"


def _unresolved_symbol_node_id(name):
    return f"symbol:{name}"
