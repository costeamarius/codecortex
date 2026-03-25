# OpenClaw Bootstrap Flow

This document defines the recommended bootstrap flow when CodeCortex is used through OpenClaw.

## Relationship to README

The README provides a short copy-paste prompt that users can give to an OpenClaw agent.

This document is the canonical reference for the full OpenClaw bootstrap flow, including:

- environment-level install
- repository path acquisition
- repository-level activation
- capability discovery
- transition into CodeCortex-aware repo mode

The README prompt should remain short.
The explicit operational flow belongs here.

## Purpose

OpenClaw should act as a thin runner and integration layer.
It should:

- detect whether CodeCortex is available
- determine the target repository
- activate CodeCortex in that repository if needed
- query repo-local capabilities
- follow the repository-defined operating model

OpenClaw should not embed repository behavior or execution logic.

---

## Core Distinction

There are two different setup scopes:

### 1. Environment-level install

This makes the `cortex` CLI available in the OpenClaw environment.

This answers:

> Can this OpenClaw agent use CodeCortex at all?

### 2. Repository-level activation

This enables CodeCortex for one specific repository.

This answers:

> Is this repository prepared for CodeCortex-aware work?

These must not be treated as the same step.

---

## Unified OpenClaw Flow

When a user asks OpenClaw to install or use CodeCortex, OpenClaw should follow this sequence:

1. detect whether `cortex` is already available
2. if not available, install CodeCortex in the OpenClaw environment
3. determine the target repository path
4. if the target repository path is not explicit, ask the user for it
5. detect whether the repository is already CodeCortex-enabled
6. if not enabled, activate it
7. query repo-local capabilities
8. switch into CodeCortex-aware mode for that repository

---

## Step 1 — Detect environment-level availability

OpenClaw should first determine whether CodeCortex is installed in its current environment.

Example check:

```bash
cortex --help
```

If this succeeds, the environment is CodeCortex-capable.

If this fails, OpenClaw should install CodeCortex before attempting repo-level activation.

---

## Step 2 — Install CodeCortex in the OpenClaw environment

Example setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install 'git+https://github.com/costeamarius/codecortex.git'
cortex --help
```

This step only prepares the environment.
It does not activate any repository.

---

## Step 3 — Determine the target repository

After environment-level install, OpenClaw must determine which repository the user wants to work on.

If the repository path is already explicit, OpenClaw may proceed.

If it is not explicit, OpenClaw should ask for clarification.

Examples:

- "Which repository should I activate CodeCortex in?"
- "Please provide the local repository path."
- "Do you mean `~/Documents/landingpage`?"

OpenClaw should avoid assuming the target repository when user intent is ambiguous.

---

## Step 4 — Detect whether the repository is already CodeCortex-enabled

A repository is CodeCortex-enabled only when `.codecortex/meta.json` exists and is valid.

`.codecortex/`, `AGENTS.md`, and other helper markers are advisory only.
OpenClaw may use repo-local detection helpers, but they should resolve to the same canonical rule.

If the repository is already enabled, OpenClaw should not re-bootstrap it unnecessarily.

---

## Step 5 — Activate CodeCortex in the target repository

If the repository is not yet enabled, OpenClaw should run the standard repo bootstrap flow:

```bash
cd <repo>
cortex init .
cortex init-agent .
cortex scan .
cortex status .
```

Expected outputs include:

- `.codecortex/`
- `AGENTS.md`
- initial graph state
- repository status confirming graph presence

---

## Step 6 — Query repo-local capabilities

Once the repository is activated, OpenClaw should query the repo-local capability surface:

```bash
cortex capabilities --path <repo>
```

This is the handoff point between generic OpenClaw behavior and repo-defined CodeCortex behavior.

---

## Step 7 — Switch into CodeCortex-aware repo mode

After capability discovery, OpenClaw should:

- use repo-local CodeCortex retrieval first when appropriate
- use `cortex action` for supported operations
- follow repo-defined operating behavior
- avoid embedding duplicate execution logic outside the repository contract

---

## Decision Logic Summary

OpenClaw should reason about setup using three questions:

### Question 1
Is CodeCortex installed in the current OpenClaw environment?

- no → perform environment-level install
- yes → continue

### Question 2
Which repository is the user targeting?

- unknown → ask the user
- known → continue

### Question 3
Is that repository already CodeCortex-enabled?

- no → perform repo-level activation
- yes → query capabilities and continue

---

## Example User Scenarios

### Scenario A — User asks to install CodeCortex generally

User:
> Install CodeCortex for OpenClaw

Expected OpenClaw behavior:
1. install CodeCortex in the OpenClaw environment if missing
2. report that environment-level install is complete
3. ask which repository should be activated next

### Scenario B — User names a repo directly

User:
> Install CodeCortex in `~/Documents/landingpage`

Expected OpenClaw behavior:
1. ensure CodeCortex exists in the environment
2. target `~/Documents/landingpage`
3. activate CodeCortex there if missing
4. query capabilities
5. proceed in CodeCortex-aware repo mode

### Scenario C — Repo already enabled

User:
> Use CodeCortex in `~/Documents/landingpage`

Expected OpenClaw behavior:
1. ensure `cortex` exists
2. detect repo markers
3. skip redundant bootstrap
4. run `cortex capabilities --path <repo>`
5. proceed with repo-defined behavior

---

## Important Rule

Environment-level install does not imply repository activation.

A successful OpenClaw-level install means:

- the agent can run `cortex`

A successful repository-level activation means:

- that specific repository is prepared for CodeCortex-aware work

OpenClaw should always keep these states separate.

---

## Alignment with CodeCortex Integration Model

This flow is consistent with the OpenClaw integration helpers:

- OpenClaw acts as runner
- CodeCortex remains the owner of repository behavior
- bootstrap may occur if repo-local enablement is missing
- capability discovery is the first repo-local integration surface
