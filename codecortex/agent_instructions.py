import os


def default_agents_md():
    return """# CodeCortex Instructions

If this repository is CodeCortex-enabled, participating agents should adopt the
repository-defined CodeCortex operating model.

## Required startup workflow

1. Run `cortex capabilities --path .`
2. Run `cortex status .`
3. If no graph exists, run `cortex scan .`
4. If the graph is out of date, run `cortex update .`

## Retrieval and discovery

- Prefer CodeCortex retrieval before broad manual repository exploration
- For repository-wide discovery, run `cortex query <term>`
- For file-level dependency context, run `cortex context <file>`
- For symbol-level exploration, run `cortex symbol <qualified_symbol>`
- For dependency impact analysis, run `cortex impact <file_or_symbol>`

## Supported execution path

- Use the runtime gateway via `cortex action`
- Send a structured JSON request envelope into `cortex action --stdin` or `cortex action --request-file <path>`
- For file edits, use action `edit_file` with repo-relative `payload.file` and new `payload.content`
- For command execution, use action `run_command` with `payload.command` as an argv array
- When operating from a participating environment, include `environment` and `agent_id` on mutating requests
- For supported operations, do not bypass the repo-local CodeCortex CLI with direct file writes or environment-specific execution behavior

### Runtime request shape

```json
{
  "action": "edit_file|run_command",
  "repo": ".",
  "agent_id": "agent-identifier",
  "environment": "openclaw|cursor|ide|local_cli|external_agent",
  "payload": {}
}
```

## Notes

- Run commands from the repository root when possible
- Treat CodeCortex as the primary repo-local interface when available
- Use `.codecortex/graph.json` as a repository knowledge artifact, not as a replacement for the CLI contract
"""


def write_agents_md(repo_path, force=False):
    agents_path = os.path.join(repo_path, "AGENTS.md")
    if os.path.exists(agents_path) and not force:
        return {
            "created": False,
            "path": agents_path,
            "reason": "exists",
        }

    with open(agents_path, "w", encoding="utf-8") as f:
        f.write(default_agents_md())

    return {
        "created": True,
        "path": agents_path,
        "reason": "written",
    }
