# AGENTS.md

## Project Context

This repository is `job-hunter-kit`, a local-first personal toolkit for supporting ML/Data/AI job applications.

The project is currently in Phase 1:

- Collect job postings from selected sources
- Extract useful job information
- Apply rule-based include / exclude filters
- Generate a structured job opportunity list

Do not jump ahead to CV matching, cover letter generation, ATS review, dashboards, or complex automation unless explicitly requested.

## Working Agreement

Before making changes:

- Read `README.md` and this `AGENTS.md`.
- Understand the current phase and scope.
- Prefer small, focused changes.
- Explain the plan before implementation.
- List the files that will be created or modified.
- Wait for explicit approval before making large structural changes.

When asked to implement something:

- Start with the smallest useful vertical slice.
- Keep the design simple and local-first.
- Avoid unnecessary frameworks, databases, or services.
- Prefer plain files and simple configuration before introducing infrastructure.
- Make filtering and decision rules explicit and configurable.

## Safety Rules

Do not:

- Build a full SaaS platform.
- Add browser automation unless explicitly requested.
- Add scraping logic that depends on login-protected pages unless explicitly requested.
- Add paid APIs or external services without approval.
- Store secrets, API keys, personal CV content, or private application data in the repository.
- Commit generated files, temporary files, or local data unless they are intentionally part of the project.

If a task may involve platform terms, scraping restrictions, personal data, or credentials, explain the risk and propose a safer approach first.

## Technical Direction

Default assumptions unless changed later:

- Language: Python
- Testing: pytest
- Configuration: local config files
- Data storage: local files first
- Interface: CLI first
- Architecture: simple modules before classes or frameworks

Prefer readable and boring code over clever abstractions.

## Expected Project Shape

A possible early structure:

```text
job-hunter-kit/
├── README.md
├── AGENTS.md
├── pyproject.toml
├── src/
│   └── job_hunter_kit/
│       ├── __init__.py
│       ├── config.py
│       ├── models.py
│       └── filters.py
├── tests/
│   └── test_filters.py
└── examples/
    └── search_config.example.yaml
```

This structure is only a guideline. Do not create all files at once unless they are needed for the current vertical slice.

## Development Rules

When writing code:

- Keep functions small and easy to test.
- Use clear names.
- Avoid premature abstractions.
- Add tests for important filtering or parsing logic.
- Prefer explicit inputs and outputs.
- Avoid hidden global state.
- Keep user-specific data out of source code.

When changing behavior:

- Update tests.
- Update README only if usage or project scope changes.
- Keep examples minimal and realistic.

## Testing

If the project has tests, run them after code changes:

```bash
pytest
```

If there are no tests yet, propose the first small test setup before adding complex logic.

## Response Style

When responding about code changes, include:

- What you inspected
- What you plan to change
- Files to create or modify
- Why the change is needed
- How to test it
- Any risks or assumptions

For implementation tasks, prefer this order:

1. Inspect existing files
2. Propose a small plan
3. Implement the smallest useful change
4. Run or explain tests
5. Summarize what changed

## Definition of Done

A task is done when:

- The change matches the current project phase
- The implementation is simple and local-first
- Important logic is covered by tests where reasonable
- The code is readable
- The user can understand how to run or verify the result

