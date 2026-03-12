import json
import os
from typing import Optional

import typer
from codecortex.feature_graph import (
    build_feature_entry,
    get_feature,
    normalize_features_store,
    upsert_feature,
)
from codecortex.graph_builder import build_graph, save_graph, update_graph
from codecortex.graph_context import compute_file_context
from codecortex.graph_status import compute_graph_status
from codecortex.project_context import (
    get_changed_python_files,
    get_head_commit,
    get_repo_id,
    read_json,
    utc_now_iso,
    write_json,
)

app = typer.Typer(no_args_is_help=True)
feature_app = typer.Typer(no_args_is_help=True)
DEFAULT_CONSTRAINTS = [
    (
        "Keep CodeCortex-generated project memory artifacts under .codecortex/ "
        "(for notes use .codecortex/notes/) and avoid writing them into docs/ "
        "or repository root."
    )
]


def _cortex_paths(repo_path):
    cortex_dir = os.path.join(repo_path, ".codecortex")
    return {
        "dir": cortex_dir,
        "graph": os.path.join(cortex_dir, "graph.json"),
        "meta": os.path.join(cortex_dir, "meta.json"),
        "features": os.path.join(cortex_dir, "features.json"),
        "constraints": os.path.join(cortex_dir, "constraints.json"),
        "decisions": os.path.join(cortex_dir, "decisions.jsonl"),
    }


def _base_meta(repo_path):
    return {
        "schema_version": "1.1",
        "repo_id": get_repo_id(repo_path),
        "initialized_at": utc_now_iso(),
        "last_scan_at": None,
        "last_scan_commit": None,
        "last_scan_mode": None,
    }


def _load_meta_or_default(repo_path):
    paths = _cortex_paths(repo_path)
    existing_meta = read_json(paths["meta"])
    if existing_meta:
        return existing_meta
    return _base_meta(repo_path)


def _load_features_store(repo_path):
    paths = _cortex_paths(repo_path)
    return normalize_features_store(read_json(paths["features"]))


def _ensure_gitignore_entry(repo_path: str, entry: str) -> bool:
    gitignore_path = os.path.join(repo_path, ".gitignore")
    existing_lines = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            existing_lines = [line.strip() for line in f.readlines()]

    if entry in existing_lines:
        return False

    needs_newline = False
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "rb") as f:
            content = f.read()
        needs_newline = len(content) > 0 and not content.endswith(b"\n")

    with open(gitignore_path, "a", encoding="utf-8") as f:
        if needs_newline:
            f.write("\n")
        f.write(f"{entry}\n")

    return True


@app.callback()
def main():
    """CodeCortex CLI."""
    return


@app.command()
def init(path: str = typer.Argument(".")):
    paths = _cortex_paths(path)
    os.makedirs(paths["dir"], exist_ok=True)

    meta = _load_meta_or_default(path)
    write_json(paths["meta"], meta)

    for file_path, empty_payload in (
        (paths["features"], {"schema_version": "1.1", "features": []}),
        (
            paths["constraints"],
            {"schema_version": "1.0", "constraints": DEFAULT_CONSTRAINTS},
        ),
    ):
        if not os.path.exists(file_path):
            write_json(file_path, empty_payload)

    if not os.path.exists(paths["decisions"]):
        with open(paths["decisions"], "w", encoding="utf-8"):
            pass

    gitignore_updated = _ensure_gitignore_entry(path, ".codecortex/")
    print(f"Initialized CodeCortex at {paths['dir']}")
    if gitignore_updated:
        print("Added `.codecortex/` to .gitignore")


@app.command()
def scan(path: str = typer.Argument(".")):
    paths = _cortex_paths(path)
    os.makedirs(paths["dir"], exist_ok=True)

    now = utc_now_iso()
    head_commit = get_head_commit(path)
    graph = build_graph(path, generated_at=now, git_commit=head_commit)
    save_graph(graph, path)

    meta = _load_meta_or_default(path)
    meta["last_scan_at"] = now
    meta["last_scan_commit"] = head_commit
    meta["last_scan_mode"] = "full"
    write_json(paths["meta"], meta)

    print("Repository graph generated (full scan).")


@app.command()
def update(path: str = typer.Argument(".")):
    paths = _cortex_paths(path)
    os.makedirs(paths["dir"], exist_ok=True)

    meta = _load_meta_or_default(path)
    existing_graph = read_json(paths["graph"])
    changed_files = get_changed_python_files(path, meta.get("last_scan_commit"))
    now = utc_now_iso()
    head_commit = get_head_commit(path)

    if not existing_graph:
        graph = build_graph(path, generated_at=now, git_commit=head_commit)
        mode = "full"
        changed_count = None
    elif changed_files is None:
        graph = build_graph(path, generated_at=now, git_commit=head_commit)
        mode = "full_fallback"
        changed_count = None
    else:
        graph = update_graph(
            existing_graph=existing_graph,
            repo_path=path,
            changed_files=changed_files,
            generated_at=now,
            git_commit=head_commit,
        )
        mode = "incremental"
        changed_count = len(changed_files)

    save_graph(graph, path)

    meta["last_scan_at"] = now
    meta["last_scan_commit"] = head_commit
    meta["last_scan_mode"] = mode
    if changed_count is not None:
        meta["last_changed_python_files"] = changed_count
    write_json(paths["meta"], meta)

    if changed_count is None:
        print(f"Repository graph updated ({mode}).")
    else:
        print(f"Repository graph updated ({mode}, changed_python_files={changed_count}).")


@app.command()
def status(path: str = typer.Argument(".")):
    paths = _cortex_paths(path)
    status_data = compute_graph_status(
        repo_path=path,
        graph_path=paths["graph"],
        meta_path=paths["meta"],
    )

    if not status_data["graph_present"]:
        print("No repository graph found.")
        print("Run: cortex scan")
        raise typer.Exit(code=1)

    print("CodeCortex status")
    print("")
    print("Graph: present")
    print(f"Nodes: {status_data['nodes_count']}")
    print(f"Edges: {status_data['edges_count']}")
    print(f"Files: {status_data['files_count']}")
    print(f"Modules: {status_data['modules_count']}")
    if status_data.get("last_scan_at"):
        print(f"Last scan at: {status_data['last_scan_at']}")

    print("")
    print(f"Last scan commit: {status_data.get('last_scan_commit') or 'unknown'}")
    print(f"Current commit:   {status_data.get('current_commit') or 'unknown'}")
    print(f"Status: {status_data['sync_status']}")


@app.command()
def query(
    term: str = typer.Argument(...),
    path: str = typer.Option(".", "--path"),
    node_type: Optional[str] = typer.Option(None, "--type"),
):
    graph_path = _cortex_paths(path)["graph"]
    graph = read_json(graph_path)
    if not graph:
        print("Graph not found. Run `cortex scan` first.")
        raise typer.Exit(code=1)

    lowered_term = term.lower()
    matches = []
    for node in graph.get("nodes", []):
        if node_type and node.get("type") != node_type:
            continue
        searchable_values = [
            str(node.get("id", "")).lower(),
            str(node.get("path", "")).lower(),
            str(node.get("name", "")).lower(),
        ]
        if any(lowered_term in value for value in searchable_values):
            matches.append(node)

    matched_ids = {node["id"] for node in matches}
    relations = [
        edge
        for edge in graph.get("edges", [])
        if edge["from"] in matched_ids or edge["to"] in matched_ids
    ]

    payload = {
        "term": term,
        "node_type": node_type,
        "matches": matches,
        "relations": relations,
        "graph_metadata": {
            "schema_version": graph.get("schema_version"),
            "generated_at": graph.get("generated_at"),
            "git_commit": graph.get("git_commit"),
        },
    }
    print(json.dumps(payload, indent=2))


@app.command()
def context(
    file: str = typer.Argument(...),
    path: str = typer.Option(".", "--path"),
):
    paths = _cortex_paths(path)
    payload = compute_file_context(
        repo_path=path,
        graph_path=paths["graph"],
        file_path=file,
    )

    if not payload.get("graph_present"):
        print("Graph not found. Run `cortex scan` first.")
        raise typer.Exit(code=1)

    if not payload.get("file_found"):
        print(f"File '{payload.get('file')}' is not present in the current graph.")
        print("Run `cortex scan` or `cortex update` and try again.")
        raise typer.Exit(code=1)

    print(json.dumps(payload, indent=2))


@app.command()
def remember(
    title: str = typer.Argument(...),
    summary: str = typer.Argument(...),
    path: str = typer.Option(".", "--path"),
):
    paths = _cortex_paths(path)
    os.makedirs(paths["dir"], exist_ok=True)

    entry = {
        "timestamp": utc_now_iso(),
        "git_commit": get_head_commit(path),
        "title": title,
        "summary": summary,
    }

    with open(paths["decisions"], "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    print("Decision stored in .codecortex/decisions.jsonl")


@feature_app.command("build")
def feature_build(
    name: str = typer.Argument(...),
    seed: str = typer.Option("", "--seed", help="Comma separated seed terms."),
    max_files: int = typer.Option(200, "--max-files", min=1),
    path: str = typer.Option(".", "--path"),
):
    paths = _cortex_paths(path)
    graph = read_json(paths["graph"])
    if not graph:
        print("Graph not found. Run `cortex scan` first.")
        raise typer.Exit(code=1)

    seed_terms = [part.strip() for part in seed.split(",")] if seed else []
    store = _load_features_store(path)
    now = utc_now_iso()
    head_commit = get_head_commit(path)
    feature = build_feature_entry(
        graph=graph,
        existing_features=store.get("features", []),
        name=name,
        seed_terms=seed_terms,
        max_files=max_files,
        timestamp=now,
        git_commit=head_commit,
    )
    if not feature:
        print("No nodes matched feature seeds/name. Try broader `--seed` terms.")
        raise typer.Exit(code=1)

    upsert_feature(store, feature)
    write_json(paths["features"], store)
    print(
        f"Feature '{name}' stored with {len(feature['files'])} files and "
        f"{len(feature['modules'])} modules."
    )


@feature_app.command("show")
def feature_show(
    name: str = typer.Argument(...),
    path: str = typer.Option(".", "--path"),
):
    store = _load_features_store(path)
    feature = get_feature(store, name)
    if not feature:
        print(f"Feature '{name}' not found.")
        raise typer.Exit(code=1)
    print(json.dumps(feature, indent=2))


@feature_app.command("refresh")
def feature_refresh(
    name: str = typer.Argument(...),
    path: str = typer.Option(".", "--path"),
):
    paths = _cortex_paths(path)
    graph = read_json(paths["graph"])
    if not graph:
        print("Graph not found. Run `cortex scan` first.")
        raise typer.Exit(code=1)

    store = _load_features_store(path)
    existing = get_feature(store, name)
    if not existing:
        print(f"Feature '{name}' not found. Use `feature build` first.")
        raise typer.Exit(code=1)

    feature = build_feature_entry(
        graph=graph,
        existing_features=store.get("features", []),
        name=name,
        seed_terms=existing.get("seed_terms", []),
        max_files=int(existing.get("max_files", 200)),
        timestamp=utc_now_iso(),
        git_commit=get_head_commit(path),
    )
    if not feature:
        print("Feature refresh failed because no nodes matched stored seeds.")
        raise typer.Exit(code=1)

    upsert_feature(store, feature)
    write_json(paths["features"], store)
    print(
        f"Feature '{name}' refreshed with {len(feature['files'])} files and "
        f"{len(feature['modules'])} modules."
    )


app.add_typer(feature_app, name="feature")

def run():
    app()


if __name__ == "__main__":
    run()
