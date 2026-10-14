# Development Guide

## Local Setup

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Or .\venv\Scripts\Activate.ps1 on Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -e .[dev]
   ```

3. **Run tests:**
   ```bash
   pytest
   ```

## Docker Environment

The Docker environment includes a PostgreSQL database and the API service.

1. **Start services:**
   ```bash
   docker-compose up -d
   ```

2. **Run tests via Docker:**
   ```bash
   docker-compose run api pytest
   ```

## CLI Usage

The CLI is available as `nexus` when the virtual environment is active.
```bash
nexus --help
```

## Running the API locally

You can run the FastAPI development server using Uvicorn:
`ash
uvicorn nexus.api.main:app --reload --port 8000
`
Then visit http://localhost:8000/docs to view the OpenAPI specification.
