# CLAUDE.md

## Project

Slack (and Google Chat) integration for Blackduck Coverity on Polaris. Fetches issues from all Polaris projects a service account can access and posts a summary to a webhook.

## Python compatibility

Supported range: **>= 3.5, <= 3.14**

`asyncio.run()` was added in Python 3.7. For 3.5–3.6 the code falls back to `asyncio.new_event_loop()` + `run_until_complete()` + `loop.close()` — see `GetProjectsAndIssues` in `polaris.py`. Do not revert this to `asyncio.get_event_loop()`, which raises `RuntimeError` in Python 3.14.

## Linting

Run flake8 via Docker to avoid polluting the local environment:

```bash
docker run --rm -v "$(pwd):/code" --workdir //code python:3.X-slim \
  sh -c "pip install flake8 -q && python -m flake8 --exclude=venv,venv2,.git,__pycache__ ."
```

Replace `3.X` with the target version (3.10–3.14 all pass clean).

On Windows with Git Bash use `//code` (double slash) to prevent path mangling.
