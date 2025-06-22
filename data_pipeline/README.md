# Data Pipeline

This directory contains the standalone pipeline responsible for ingesting and indexing files for Pegasus.

## Structure

- `source_data/` – folder monitored for incoming raw files.
- `database/` – location of the local ChromaDB database.
- `logs/` – pipeline log files.
- `tests/` – test suite for the pipeline modules.
- `pipeline.py` – main orchestration script.
- `requirements.txt` – Python dependencies for the pipeline.

## Setup

### 1. Install prerequisites
Ensure Python 3.9+ and `ffmpeg` are available. On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip ffmpeg
```

### 2. Create the virtual environment

```bash
cd data_pipeline
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the pipeline

```bash
python pipeline.py
```

Refer to the task files in `../tasks/pipeline/` for details on each step.
