# Configuration Guide

## Files

### `pyproject.toml`

Modern Python project configuration (PEP 518/621). Contains:

- Project metadata (name, version, dependencies)
- Tool configurations (ruff, pytest, mypy)
- Build system specification

**Key sections**:
```toml
[project]
requires-python = ">=3.12"
dependencies = ["structlog", "kafka-python", "python-dotenv"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pytest]
testpaths = ["tests"]
```

### `.ruff.toml`

Ruff linter configuration. Duplicates some `pyproject.toml` settings.

**When to use**: Standalone Ruff config if you prefer separation.

### `requirements.txt` vs `requirements-dev.txt`

**Production** (`requirements.txt`):
- Minimal dependencies to run the code
- structlog, kafka-python, python-dotenv

**Development** (`requirements-dev.txt`):
- Tools for development only
- ruff, pytest, mypy
- Not installed in production

### Makefile

Shortcuts for common commands. Optional but convenient for teams.

**Example**:
```makefile
lint:
    ruff check src/

fix:
    ruff check --fix src/
    ruff format src/
```

## Environment Variables

Create a `.env` file:

```bash
# Logging
LOG_LEVEL=INFO

# Kafka (optional overrides)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=datacenter-metrics
```

Variables are loaded via `python-dotenv`.
