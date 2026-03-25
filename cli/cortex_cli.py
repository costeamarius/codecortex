import json
import os
import sys
from typing import Optional

import typer
from codecortex.agent_instructions import write_agents_md
from codecortex.benchmarking import benchmark_impact, benchmark_query, benchmark_symbol
from codecortex.feature_graph import (
    build_feature_entry,
    get_feature,
    normalize_features_store,
    upsert_feature,
)
from codecortex.graph_builder import build_graph, save_graph, update_graph
from codecortex.graph_context import compute_file_context
from codecortex.graph_query import impact_subgraph, search_graph, symbol_subgraph
from codecortex.graph_status import compute_graph_status
from codecortex.memory.constraint_store import build_default_constraints
from codecortex.memory.decision_store import append_decision
from codecortex.memory.state_store import build_initial_runtime_state, build_state_paths
from codecortex.project_context import (
    get_changed_python_files,
    get_head_commit,
    get_repo_id,
    read_json,
    utc_now_iso,
    write_json,
)
from codecortex.semantics_store import (
    append_jsonl,
    get_assertions,
    merge_graph_with_semantics,
    normalize_semantics_store,
    read_jsonl,
    rebuild_semantics_store_from_events,
    upsert_assertion,
)
from codecortex.runtime.gateway import AgentGateway
from codecortex.runtime.capabilities import build_capabilities_snapshot

app = typer.Typer(no_args_is_help=True)
feature_app = typer.Typer(no_args_is_help=True)
benchmark_app = typer.Typer(no_args_is_help=True)
semantics_app = typer.Typer(no_args_is_help=True)
def _cortex_paths(repo_path):
    return build_state_paths(repo_path)


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


def _load_semantics_store(repo_path):
    paths = _cortex_paths(repo_path)
    store = normalize_semantics_store(read_json(paths["semantics"]))
    events = read_jsonl(paths["semantics_journal"])
    if not events:
        return store
    rebuilt_store = rebuild_semantics_store_from_events(events)
    if rebuilt_store.get("assertions") != store.get("assertions"):
        write_json(paths["semantics"], rebuilt_store)
    return rebuilt_store


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


def _print_result(payload: dict):
    print(json.dumps(payload, indent=2))


def _runtime_action_payload(
    *,
    action: str,
    repo: str,
    payload: dict,
    agent_id: Optional[str],
    environment: Optional[str],
):
    return {
        "action": action,
        "repo": repo,
        "payload": payload,
        "agent_id": agent_id,
        "environment": environment,
    }


def _load_action_request_payload(
    request_file: Optional[str],
    stdin: bool,
):
    if bool(request_file) == bool(stdin):
        raise typer.BadParameter("Provide exactly one of --request-file or --stdin.")

    if request_file:
        return read_json(request_file)

    return json.load(sys.stdin)


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
    if not os.path.exists(paths["state"]):
        write_json(paths["state"], build_initial_runtime_state())

    for file_path, empty_payload in (
        (paths["features"], {"schema_version": "1.1", "features": []}),
        (paths["semantics"], {"schema_version": "1.0", "assertions": []}),
        (
            paths["constraints"],
            build_default_constraints(),
        ),
    ):
        if not os.path.exists(file_path):
            write_json(file_path, empty_payload)

    if not os.path.exists(paths["decisions"]):
        with open(paths["decisions"], "w", encoding="utf-8"):
            pass
    if not os.path.exists(paths["semantics_journal"]):
        with open(paths["semantics_journal"], "w", encoding="utf-8"):
            pass

    gitignore_updated = _ensure_gitignore_entry(path, ".codecortex/")
    print(f"Initialized CodeCortex at {paths['dir']}")
    if gitignore_updated:
        print("Added `.codecortex/` to .gitignore")


@app.command("init-agent")
def init_agent(
    path: str = typer.Argument("."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing AGENTS.md."),
):
    result = write_agents_md(path, force=force)
    if not result["created"]:
        print(f"AGENTS.md already exists at {result['path']}")
        print("Use `cortex init-agent --force` to overwrite it.")
        raise typer.Exit(code=1)

    print(f"Created AGENTS.md at {result['path']}")
    print("Repository AI agents can now be instructed to use CodeCortex.")


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
    print(f"Classes: {status_data['classes_count']}")
    print(f"Functions: {status_data['functions_count']}")
    print(f"Methods: {status_data['methods_count']}")
    if status_data.get("last_scan_at"):
        print(f"Last scan at: {status_data['last_scan_at']}")

    print("")
    print(f"Last scan commit: {status_data.get('last_scan_commit') or 'unknown'}")
    print(f"Current commit:   {status_data.get('current_commit') or 'unknown'}")
    print(f"Status: {status_data['sync_status']}")


@app.command()
def capabilities(path: str = typer.Option(".", "--path")):
    _print_result(build_capabilities_snapshot(path))


@app.command("action")
def action_command(
    request_file: Optional[str] = typer.Option(None, "--request-file"),
    stdin: bool = typer.Option(False, "--stdin"),
):
    payload = _load_action_request_payload(request_file=request_file, stdin=stdin)
    response = AgentGateway().handle_action(payload)
    _print_result(response.to_dict())


@app.command("edit-file")
def edit_file_command(
    file: str = typer.Option(..., "--file"),
    content: str = typer.Option(..., "--content"),
    path: str = typer.Option(".", "--path"),
    agent_id: Optional[str] = typer.Option(None, "--agent-id"),
    environment: Optional[str] = typer.Option(None, "--environment"),
    validate: bool = typer.Option(True, "--validate/--no-validate"),
    lock_ttl_seconds: int = typer.Option(30, "--lock-ttl-seconds"),
    auto_update_graph: bool = typer.Option(
        False,
        "--auto-update-graph",
        help="Incrementally refresh .codecortex/graph.json after a successful Python edit when a graph already exists.",
    ),
):
    response = AgentGateway().handle_action(
        _runtime_action_payload(
            action="edit_file",
            repo=path,
            agent_id=agent_id,
            environment=environment,
            payload={
                "file": file,
                "content": content,
                "validate": validate,
                "lock_ttl_seconds": lock_ttl_seconds,
                "auto_update_graph": auto_update_graph,
            },
        )
    )
    _print_result(response.to_dict())


@app.command("run-command")
def run_command_cli(
    command: str = typer.Option(..., "--command", help="Shell command string executed via `bash -lc` in v1."),
    path: str = typer.Option(".", "--path"),
    agent_id: Optional[str] = typer.Option(None, "--agent-id"),
    environment: Optional[str] = typer.Option(None, "--environment"),
    timeout_seconds: Optional[int] = typer.Option(None, "--timeout-seconds"),
    auto_update_graph: bool = typer.Option(
        False,
        "--auto-update-graph",
        help="Incrementally refresh .codecortex/graph.json after a successful command that changed Python files.",
    ),
):
    response = AgentGateway().handle_action(
        _runtime_action_payload(
            action="run_command",
            repo=path,
            agent_id=agent_id,
            environment=environment,
            payload={
                "command": ["bash", "-lc", command],
                "timeout_seconds": timeout_seconds,
                "auto_update_graph": auto_update_graph,
            },
        )
    )
    _print_result(response.to_dict())


@app.command()
def query(
    term: str = typer.Argument(...),
    path: str = typer.Option(".", "--path"),
    node_type: Optional[str] = typer.Option(None, "--type"),
    edge_type: Optional[str] = typer.Option(None, "--edge"),
    limit: int = typer.Option(10, "--limit", min=1),
):
    graph_path = _cortex_paths(path)["graph"]
    graph = read_json(graph_path)
    if not graph:
        print("Graph not found. Run `cortex scan` first.")
        raise typer.Exit(code=1)
    graph = merge_graph_with_semantics(graph, _load_semantics_store(path))

    payload = search_graph(
        graph=graph,
        term=term,
        node_type=node_type,
        edge_type=edge_type,
        limit=limit,
    )
    payload["graph_metadata"] = {
        "schema_version": graph.get("schema_version"),
        "generated_at": graph.get("generated_at"),
        "git_commit": graph.get("git_commit"),
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
def symbol(
    name: str = typer.Argument(...),
    path: str = typer.Option(".", "--path"),
    depth: int = typer.Option(1, "--depth", min=0),
    edge_type: Optional[str] = typer.Option(None, "--edge"),
    limit: int = typer.Option(25, "--limit", min=1),
):
    graph_path = _cortex_paths(path)["graph"]
    graph = read_json(graph_path)
    if not graph:
        print("Graph not found. Run `cortex scan` first.")
        raise typer.Exit(code=1)
    graph = merge_graph_with_semantics(graph, _load_semantics_store(path))

    payload = symbol_subgraph(
        graph=graph,
        symbol=name,
        depth=depth,
        edge_type=edge_type,
        limit=limit,
    )
    if not payload:
        print(f"Symbol '{name}' not found.")
        raise typer.Exit(code=1)

    payload["graph_metadata"] = {
        "schema_version": graph.get("schema_version"),
        "generated_at": graph.get("generated_at"),
        "git_commit": graph.get("git_commit"),
    }
    print(json.dumps(payload, indent=2))


@app.command()
def impact(
    target: str = typer.Argument(...),
    path: str = typer.Option(".", "--path"),
    depth: int = typer.Option(2, "--depth", min=0),
    edge_type: Optional[str] = typer.Option(None, "--edge"),
    limit: int = typer.Option(40, "--limit", min=1),
):
    graph_path = _cortex_paths(path)["graph"]
    graph = read_json(graph_path)
    if not graph:
        print("Graph not found. Run `cortex scan` first.")
        raise typer.Exit(code=1)
    graph = merge_graph_with_semantics(graph, _load_semantics_store(path))

    payload = impact_subgraph(
        graph=graph,
        target=target,
        depth=depth,
        edge_type=edge_type,
        limit=limit,
    )
    if not payload:
        print(f"Target '{target}' not found.")
        raise typer.Exit(code=1)

    payload["graph_metadata"] = {
        "schema_version": graph.get("schema_version"),
        "generated_at": graph.get("generated_at"),
        "git_commit": graph.get("git_commit"),
    }
    print(json.dumps(payload, indent=2))


@app.command()
def remember(
    title: str = typer.Argument(...),
    summary: str = typer.Argument(...),
    path: str = typer.Option(".", "--path"),
):
    paths = _cortex_paths(path)
    os.makedirs(paths["dir"], exist_ok=True)

    entry = append_decision(
        paths["decisions"],
        {
            "timestamp": utc_now_iso(),
            "git_commit": get_head_commit(path),
            "title": title,
            "summary": summary,
        },
    )

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
    graph = merge_graph_with_semantics(graph, _load_semantics_store(path))

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
    graph = merge_graph_with_semantics(graph, _load_semantics_store(path))

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
app.add_typer(benchmark_app, name="benchmark")
app.add_typer(semantics_app, name="semantics")


@semantics_app.command("add")
def semantics_add(
    assertion_id: str = typer.Argument(..., help="Stable assertion id."),
    subject: str = typer.Argument(...),
    predicate: str = typer.Argument(...),
    object_id: str = typer.Argument(...),
    path: str = typer.Option(".", "--path"),
    source: str = typer.Option("agent_inferred", "--source"),
    confidence: str = typer.Option("high", "--confidence"),
    note: Optional[str] = typer.Option(None, "--note"),
    line: Optional[int] = typer.Option(None, "--line"),
):
    paths = _cortex_paths(path)
    os.makedirs(paths["dir"], exist_ok=True)
    store = _load_semantics_store(path)
    assertion = {
        "id": assertion_id,
        "subject": subject,
        "predicate": predicate,
        "object": object_id,
        "source": source,
        "confidence": confidence,
        "note": note,
        "line": line,
        "updated_at": utc_now_iso(),
        "git_commit": get_head_commit(path),
    }
    append_jsonl(
        paths["semantics_journal"],
        {
            "type": "upsert_assertion",
            "assertion": assertion,
        },
    )
    upsert_assertion(store, assertion)
    write_json(paths["semantics"], store)
    print(f"Semantic assertion '{assertion_id}' stored.")


@semantics_app.command("show")
def semantics_show(
    path: str = typer.Option(".", "--path"),
    subject: Optional[str] = typer.Option(None, "--subject"),
    predicate: Optional[str] = typer.Option(None, "--predicate"),
    object_id: Optional[str] = typer.Option(None, "--object"),
):
    store = _load_semantics_store(path)
    assertions = get_assertions(store, subject=subject, predicate=predicate, object_id=object_id)
    print(
        json.dumps(
            {
                "schema_version": store.get("schema_version"),
                "count": len(assertions),
                "assertions": assertions,
            },
            indent=2,
        )
    )


@semantics_app.command("rebuild")
def semantics_rebuild(
    path: str = typer.Option(".", "--path"),
):
    paths = _cortex_paths(path)
    events = read_jsonl(paths["semantics_journal"])
    store = rebuild_semantics_store_from_events(events)
    write_json(paths["semantics"], store)
    print(
        f"Rebuilt semantics store from journal with {len(store.get('assertions', []))} assertions."
    )


@benchmark_app.command("query")
def benchmark_query_command(
    term: str = typer.Argument(...),
    path: str = typer.Option(".", "--path"),
    node_type: Optional[str] = typer.Option(None, "--type"),
    edge_type: Optional[str] = typer.Option(None, "--edge"),
    limit: int = typer.Option(10, "--limit", min=1),
):
    graph_path = _cortex_paths(path)["graph"]
    graph = read_json(graph_path)
    if not graph:
        print("Graph not found. Run `cortex scan` first.")
        raise typer.Exit(code=1)
    graph = merge_graph_with_semantics(graph, _load_semantics_store(path))

    payload = benchmark_query(
        graph=graph,
        term=term,
        node_type=node_type,
        edge_type=edge_type,
        limit=limit,
    )
    payload["graph_metadata"] = {
        "schema_version": graph.get("schema_version"),
        "generated_at": graph.get("generated_at"),
        "git_commit": graph.get("git_commit"),
    }
    print(json.dumps(payload, indent=2))


@benchmark_app.command("symbol")
def benchmark_symbol_command(
    name: str = typer.Argument(...),
    path: str = typer.Option(".", "--path"),
    depth: int = typer.Option(1, "--depth", min=0),
    edge_type: Optional[str] = typer.Option(None, "--edge"),
    limit: int = typer.Option(25, "--limit", min=1),
):
    graph_path = _cortex_paths(path)["graph"]
    graph = read_json(graph_path)
    if not graph:
        print("Graph not found. Run `cortex scan` first.")
        raise typer.Exit(code=1)
    graph = merge_graph_with_semantics(graph, _load_semantics_store(path))

    payload = benchmark_symbol(
        graph=graph,
        symbol=name,
        depth=depth,
        edge_type=edge_type,
        limit=limit,
    )
    if not payload:
        print(f"Symbol '{name}' not found.")
        raise typer.Exit(code=1)

    payload["graph_metadata"] = {
        "schema_version": graph.get("schema_version"),
        "generated_at": graph.get("generated_at"),
        "git_commit": graph.get("git_commit"),
    }
    print(json.dumps(payload, indent=2))


@benchmark_app.command("impact")
def benchmark_impact_command(
    target: str = typer.Argument(...),
    path: str = typer.Option(".", "--path"),
    depth: int = typer.Option(2, "--depth", min=0),
    edge_type: Optional[str] = typer.Option(None, "--edge"),
    limit: int = typer.Option(40, "--limit", min=1),
):
    graph_path = _cortex_paths(path)["graph"]
    graph = read_json(graph_path)
    if not graph:
        print("Graph not found. Run `cortex scan` first.")
        raise typer.Exit(code=1)
    graph = merge_graph_with_semantics(graph, _load_semantics_store(path))

    payload = benchmark_impact(
        graph=graph,
        target=target,
        depth=depth,
        edge_type=edge_type,
        limit=limit,
    )
    if not payload:
        print(f"Target '{target}' not found.")
        raise typer.Exit(code=1)

    payload["graph_metadata"] = {
        "schema_version": graph.get("schema_version"),
        "generated_at": graph.get("generated_at"),
        "git_commit": graph.get("git_commit"),
    }
    print(json.dumps(payload, indent=2))


def run():
    app()


if __name__ == "__main__":
    run()
