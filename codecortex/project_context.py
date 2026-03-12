import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _run_git(repo_path, args):
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    return completed.stdout.strip()


def get_head_commit(repo_path):
    return _run_git(repo_path, ["rev-parse", "HEAD"])


def get_repo_id(repo_path):
    top_level = _run_git(repo_path, ["rev-parse", "--show-toplevel"])
    repo_root = top_level if top_level else os.path.abspath(repo_path)

    remote_url = _run_git(repo_path, ["config", "--get", "remote.origin.url"])
    source = remote_url if remote_url else repo_root

    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]
    repo_name = os.path.basename(repo_root.rstrip(os.sep)) or "repo"
    return f"{repo_name}-{digest}"


def get_changed_python_files(repo_path, since_commit):
    if not since_commit:
        return None

    changed_output = _run_git(
        repo_path,
        ["diff", "--name-only", since_commit, "--", "*.py"],
    )
    if changed_output is None:
        return None

    untracked_output = _run_git(
        repo_path,
        ["ls-files", "--others", "--exclude-standard", "--", "*.py"],
    )
    if untracked_output is None:
        return None

    changed = {
        path
        for path in changed_output.splitlines()
        if path.strip()
    }
    changed.update(
        path
        for path in untracked_output.splitlines()
        if path.strip()
    )

    return changed


def read_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

