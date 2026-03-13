import ast


SEMANTIC_NODE_DEFINITIONS = {
    "semantic:django.model": {
        "id": "semantic:django.model",
        "type": "semantic",
        "name": "django.model",
    },
    "semantic:django.form": {
        "id": "semantic:django.form",
        "type": "semantic",
        "name": "django.form",
    },
    "semantic:django.view": {
        "id": "semantic:django.view",
        "type": "semantic",
        "name": "django.view",
    },
}

DJANGO_VIEW_BASE_NAMES = {
    "view",
    "templateview",
    "listview",
    "detailview",
    "createview",
    "updateview",
    "deleteview",
    "formview",
}


def extract_django_semantic_records(file_path, relative_path, module_name, nodes):
    tree = _parse_tree(file_path)
    if not tree or not module_name:
        return {"nodes": [], "edges": []}

    indexes = _build_indexes(nodes, relative_path, module_name)
    extractor = _DjangoSemanticExtractor(
        relative_path=relative_path,
        module_name=module_name,
        indexes=indexes,
    )
    extractor.visit(tree)
    return {
        "nodes": sorted(extractor.nodes.values(), key=lambda node: node["id"]),
        "edges": extractor.edges,
    }


def _parse_tree(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return ast.parse(f.read())
    except (SyntaxError, UnicodeDecodeError, OSError):
        return None


def _build_indexes(nodes, relative_path, module_name):
    all_by_qualname = {}
    local_classes = {}
    local_functions = {}
    local_methods = {}

    for node in nodes.values():
        qualname = node.get("qualname")
        if qualname:
            all_by_qualname.setdefault(qualname, []).append(node)

        if node.get("path") != relative_path:
            continue
        if node.get("type") == "class":
            local_classes[node["name"]] = node
        elif node.get("type") == "function":
            local_functions[node["name"]] = node
        elif node.get("type") == "method":
            local_methods[node["qualname"]] = node

    return {
        "all_by_qualname": all_by_qualname,
        "local_classes": local_classes,
        "local_functions": local_functions,
        "local_methods": local_methods,
        "module_name": module_name,
        "relative_path": relative_path,
    }


class _DjangoSemanticExtractor(ast.NodeVisitor):
    def __init__(self, relative_path, module_name, indexes):
        self.relative_path = relative_path
        self.module_name = module_name
        self.indexes = indexes
        self.nodes = {}
        self.edges = []
        self.imported_symbols = {}
        self.class_stack = []
        self.function_stack = []

    def visit_ImportFrom(self, node):
        base_module = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                continue
            local_name = alias.asname or alias.name
            qualname = ".".join(part for part in [base_module, alias.name] if part)
            self.imported_symbols[local_name] = qualname
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".")[0]
            self.imported_symbols[local_name] = alias.name
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_node = self.indexes["local_classes"].get(node.name)
        if not class_node:
            self.generic_visit(node)
            return

        self.class_stack.append({"ast": node, "node": class_node})

        base_names = [_expr_to_name(base) for base in node.bases]
        is_model = any(self._is_django_model_base(name) for name in base_names if name)
        is_form = any(self._is_django_form_base(name) for name in base_names if name)
        is_view = any(self._is_django_view_base(name) for name in base_names if name)

        if is_model:
            self._add_semantic_edge(class_node["id"], "is_django_model", "semantic:django.model", node.lineno)
        if is_form:
            self._add_semantic_edge(class_node["id"], "is_django_form", "semantic:django.form", node.lineno)
        if is_view:
            self._add_semantic_edge(class_node["id"], "is_django_view", "semantic:django.view", node.lineno)

        for statement in node.body:
            if isinstance(statement, ast.ClassDef) and statement.name == "Meta":
                self._extract_meta_model_binding(class_node["id"], statement)
            elif isinstance(statement, ast.Assign):
                self._extract_class_assignment_semantics(class_node["id"], statement)

        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node):
        self._visit_function_like(node)

    def visit_AsyncFunctionDef(self, node):
        self._visit_function_like(node)

    def visit_Call(self, node):
        current = self.function_stack[-1] if self.function_stack else None
        if current:
            owner_id = current["node"]["id"]
            self._extract_call_semantics(owner_id, node)
        self.generic_visit(node)

    def _visit_function_like(self, node):
        if self.class_stack:
            owner_qualname = f"{self.class_stack[-1]['node']['qualname']}.{node.name}"
            symbol_node = self.indexes["local_methods"].get(owner_qualname)
        else:
            symbol_node = self.indexes["local_functions"].get(node.name)

        if not symbol_node:
            self.generic_visit(node)
            return

        if not self.class_stack and _is_view_module(self.relative_path, self.module_name):
            self._add_semantic_edge(symbol_node["id"], "is_django_view", "semantic:django.view", node.lineno)

        self.function_stack.append({"ast": node, "node": symbol_node})
        self.generic_visit(node)
        self.function_stack.pop()

    def _extract_meta_model_binding(self, owner_id, meta_node):
        for statement in meta_node.body:
            if not isinstance(statement, ast.Assign):
                continue
            target_names = [target.id for target in statement.targets if isinstance(target, ast.Name)]
            if "model" not in target_names:
                continue
            target_id = self._resolve_class_reference(statement.value)
            if target_id:
                self.edges.append(
                    {
                        "from": owner_id,
                        "to": target_id,
                        "type": "binds_model",
                        "line": getattr(statement, "lineno", None),
                        "resolution": "best_effort",
                    }
                )

    def _extract_class_assignment_semantics(self, owner_id, statement):
        for target in statement.targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id == "form_class":
                target_id = self._resolve_class_reference(statement.value)
                if target_id:
                    self.edges.append(
                        {
                            "from": owner_id,
                            "to": target_id,
                            "type": "uses_form",
                            "line": getattr(statement, "lineno", None),
                            "resolution": "best_effort",
                        }
                    )
            elif target.id == "model":
                target_id = self._resolve_class_reference(statement.value)
                if target_id:
                    self.edges.append(
                        {
                            "from": owner_id,
                            "to": target_id,
                            "type": "uses_model",
                            "line": getattr(statement, "lineno", None),
                            "resolution": "best_effort",
                        }
                    )
            elif target.id == "template_name":
                template_node = self._template_node(statement.value)
                if template_node:
                    self.nodes[template_node["id"]] = template_node
                    self.edges.append(
                        {
                            "from": owner_id,
                            "to": template_node["id"],
                            "type": "uses_template",
                            "line": getattr(statement, "lineno", None),
                            "resolution": "literal",
                        }
                    )

    def _extract_call_semantics(self, owner_id, call_node):
        target_name = _expr_to_name(call_node.func)
        if not target_name:
            return

        if target_name == "render":
            if len(call_node.args) >= 2:
                template_node = self._template_node(call_node.args[1])
                if template_node:
                    self.nodes[template_node["id"]] = template_node
                    self.edges.append(
                        {
                            "from": owner_id,
                            "to": template_node["id"],
                            "type": "uses_template",
                            "line": getattr(call_node, "lineno", None),
                            "resolution": "literal",
                        }
                    )
            return

        delegated_target = self._resolve_function_reference(call_node.func)
        if delegated_target and not self._is_framework_function(target_name):
            self.edges.append(
                {
                    "from": owner_id,
                    "to": delegated_target,
                    "type": "delegates_to",
                    "line": getattr(call_node, "lineno", None),
                    "resolution": "best_effort",
                }
            )

        class_target = self._resolve_class_reference(call_node.func)
        if class_target:
            target_node = self._node_by_id(class_target)
            if target_node and self._looks_like_form_node(target_node):
                self.edges.append(
                    {
                        "from": owner_id,
                        "to": class_target,
                        "type": "uses_form",
                        "line": getattr(call_node, "lineno", None),
                        "resolution": "best_effort",
                    }
                )

        for keyword in call_node.keywords:
            if keyword.arg in {"form", "form_class"}:
                target_id = self._resolve_class_reference(keyword.value)
                if target_id:
                    self.edges.append(
                        {
                            "from": owner_id,
                            "to": target_id,
                            "type": "uses_form",
                            "line": getattr(keyword, "lineno", getattr(call_node, "lineno", None)),
                            "resolution": "best_effort",
                        }
                    )
            elif keyword.arg in {"model", "model_class", "profile_model"}:
                target_id = self._resolve_class_reference(keyword.value)
                if target_id:
                    self.edges.append(
                        {
                            "from": owner_id,
                            "to": target_id,
                            "type": "uses_model",
                            "line": getattr(keyword, "lineno", getattr(call_node, "lineno", None)),
                            "resolution": "best_effort",
                        }
                    )
            elif keyword.arg == "template_name":
                template_node = self._template_node(keyword.value)
                if template_node:
                    self.nodes[template_node["id"]] = template_node
                    self.edges.append(
                        {
                            "from": owner_id,
                            "to": template_node["id"],
                            "type": "uses_template",
                            "line": getattr(keyword, "lineno", getattr(call_node, "lineno", None)),
                            "resolution": "literal",
                        }
                    )

    def _resolve_class_reference(self, expr):
        qualname = self._resolve_qualname(expr)
        if not qualname:
            return None

        local_class = self.indexes["local_classes"].get(qualname.split(".")[-1])
        if local_class and local_class.get("qualname") == f"{self.module_name}.{qualname.split('.')[-1]}":
            return local_class["id"]

        for candidate in self.indexes["all_by_qualname"].get(qualname, []):
            if candidate.get("type") == "class":
                return candidate["id"]

        guessed = f"class:{qualname}"
        if guessed in self.indexes["all_by_qualname"]:
            return guessed
        return f"symbol:{qualname}"

    def _resolve_function_reference(self, expr):
        qualname = self._resolve_qualname(expr)
        if not qualname:
            return None

        local_function = self.indexes["local_functions"].get(qualname.split(".")[-1])
        if local_function and local_function.get("qualname") == f"{self.module_name}.{qualname.split('.')[-1]}":
            return local_function["id"]

        for candidate in self.indexes["all_by_qualname"].get(qualname, []):
            if candidate.get("type") == "function":
                return candidate["id"]
        return f"symbol:{qualname}"

    def _resolve_qualname(self, expr):
        name = _expr_to_name(expr)
        if not name:
            return None

        if "." not in name and name in self.imported_symbols:
            return self.imported_symbols[name]
        if "." not in name:
            local_class = self.indexes["local_classes"].get(name)
            if local_class:
                return local_class["qualname"]
            local_function = self.indexes["local_functions"].get(name)
            if local_function:
                return local_function["qualname"]
            return f"{self.module_name}.{name}"

        root_name = name.split(".", 1)[0]
        if root_name in self.imported_symbols:
            return name.replace(root_name, self.imported_symbols[root_name], 1)
        return name

    def _is_django_model_base(self, name):
        normalized = self._resolve_qualname_from_name(name).lower()
        return normalized.endswith("models.model") or normalized.endswith(".model")

    def _is_django_form_base(self, name):
        normalized = self._resolve_qualname_from_name(name).lower()
        return normalized.endswith("forms.modelform") or normalized.endswith("forms.form") or normalized.endswith(".modelform") or normalized.endswith(".form")

    def _is_django_view_base(self, name):
        normalized = self._resolve_qualname_from_name(name).lower()
        return any(normalized.endswith(base_name) for base_name in DJANGO_VIEW_BASE_NAMES)

    def _resolve_qualname_from_name(self, name):
        if not name:
            return ""
        root_name = name.split(".", 1)[0]
        if root_name in self.imported_symbols:
            return name.replace(root_name, self.imported_symbols[root_name], 1)
        return name

    def _is_framework_function(self, target_name):
        normalized = self._resolve_qualname_from_name(target_name)
        return normalized.startswith("django.") or normalized in {
            "render",
            "redirect",
            "get_object_or_404",
        }

    def _add_semantic_edge(self, source_id, edge_type, target_id, line):
        self.nodes[target_id] = SEMANTIC_NODE_DEFINITIONS[target_id]
        self.edges.append(
            {
                "from": source_id,
                "to": target_id,
                "type": edge_type,
                "line": line,
                "resolution": "inferred",
            }
        )

    def _template_node(self, expr):
        if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
            value = expr.value
            if value.endswith(".html"):
                return {
                    "id": f"template:{value}",
                    "type": "template",
                    "name": value.split("/")[-1],
                    "path": value,
                }
        return None

    def _node_by_id(self, node_id):
        for node in self.indexes["all_by_qualname"].values():
            for candidate in node:
                if candidate["id"] == node_id:
                    return candidate
        local_candidates = list(self.indexes["local_classes"].values()) + list(
            self.indexes["local_functions"].values()
        )
        for candidate in local_candidates:
            if candidate["id"] == node_id:
                return candidate
        return None

    def _looks_like_form_node(self, node):
        qualname = str(node.get("qualname", "")).lower()
        name = str(node.get("name", "")).lower()
        return "form" in qualname or name.endswith("form")


def _is_view_module(relative_path, module_name):
    normalized_path = relative_path.replace("\\", "/")
    return normalized_path.endswith("/views.py") or normalized_path == "views.py" or module_name.endswith(".views")


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
