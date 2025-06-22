# Pegasus Backend

This directory contains the FastAPI backend that exposes the chat and webhook endpoints for Pegasus.

## Setup

1. Create a virtual environment and install dependencies:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Run the application locally:

```bash
python main.py
```

The server will be available at `http://127.0.0.1:8000`.

## Docker Usage

Build and run the Docker image:

```bash
docker build -t pegasus-backend .
docker run -p 8000:8000 pegasus-backend
```

## Tests

Run the unit tests with `pytest`:

```bash
pytest
```
