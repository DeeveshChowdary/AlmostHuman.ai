# AlmostHuman.ai

## Prerequisites

This project uses [uv](https://github.com/astral-sh/uv) for fast Python package management.

### 1. Install `uv`

If you haven't installed `uv` yet, you can do so using one of the following methods:

**macOS and Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
*(Alternatively, you can install it via pip: `pip install uv`)*

### 2. Install Project Dependencies

Run the following command in the project root to install the required dependencies using `uv` and ensure they are synchronized with the `uv.lock` file:

```bash
uv sync
```

### 3. Run the Development Server

Start the FastAPI application with live reloading:

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at:
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **API Documentation (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Sample Endpoint:** [http://127.0.0.1:8000/api/v1/hello/](http://127.0.0.1:8000/api/v1/hello/)