# AI Service

Python AI service skeleton for stream reading, detection pipeline placeholders, and backend event reporting.

## Requirements

- Python 3.14 verified locally

## Quick Start

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

## Endpoints

- Health check: `http://127.0.0.1:9000/health`

## Notes

- This `requirements.txt` belongs only to the AI service directory
- Running `pip install -r requirements.txt` from the repository root will fail because the root directory does not contain that file
