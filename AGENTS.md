## Python environments

AIService must use the repository environment:

`ai-service/.venv/Scripts/python.exe`

Backend must use:

`backend/.venv/Scripts/python.exe`

Do not use system Python or Python 3.14 for AIService.

Do not create additional `.venv`, `venv`, or `env` directories without an explicit request.

Do not rely on a previously activated PowerShell environment. Invoke the required virtual-environment interpreter directly or use the scripts under `scripts/`.

Before changing Python dependencies, run `scripts/check-python-env.ps1`.

AIService requires Python 3.11.
