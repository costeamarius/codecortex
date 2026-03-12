import os


def default_agents_md():
    return """# CodeCortex Instructions

Use CodeCortex before manually scanning the repository.

## Required workflow

1. Run `cortex status .`
2. If no graph exists, run `cortex scan .`
3. If the graph is out of date, run `cortex update .`

## Discovery

- For repository-wide discovery, run `cortex query <term>`
- For file-level dependency context, run `cortex context <file>`

## Notes

- Prefer CodeCortex output before broad manual repository exploration
- Run commands from the repository root when possible
- Use `.codecortex/graph.json` as the primary repository knowledge source
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
