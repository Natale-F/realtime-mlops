# Development Guide

## Setup

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Or use pyproject.toml
pip install -e ".[dev]"
```

## Code Quality with Ruff

[Ruff](https://github.com/astral-sh/ruff) is an ultra-fast Python linter (replaces Flake8, isort, etc.)

### Commands

```bash
# Check code
ruff check src/

# Auto-fix issues
ruff check --fix src/

# Format code
ruff format src/

# Check formatting only
ruff format --check src/
```

### Using Makefile

```bash
make help          # Show all commands
make lint          # Check code
make fix           # Auto-fix + format
make test          # Run tests
make check         # All checks (lint + format)
make ci-check      # Full CI validation
```

### Configuration

Ruff is configured in:
- `pyproject.toml` - Project-wide settings
- `.ruff.toml` - Ruff-specific options

**Key settings**:
- Line length: 100
- Target: Python 3.12
- Rules: E, W, F, I, N, UP, B, C4, SIM

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/generator/test_models.py

# Run specific test class or function
pytest tests/generator/test_models.py::TestGeneratorConfig::test_default_config
```

### Test Coverage

```bash
# Run with coverage report
pytest tests/ --cov=src --cov-report=html

# Or use Makefile
make test-cov

# View HTML report
open htmlcov/index.html
```

**Current Coverage**: 69% (46 tests, all passing ✅)

### Test Structure

```
tests/
├── conftest.py                    # Shared fixtures
└── generator/
    ├── test_models.py             # Config & enums (12 tests)
    ├── test_server_state.py       # ServerState (13 tests)
    ├── test_service_state.py      # ServiceState (11 tests)
    └── test_generator.py          # DatacenterGenerator (10 tests)
```

### Writing Tests

**Good practices used**:
- ✅ Descriptive test names (`test_what_it_does`)
- ✅ Docstrings for each test
- ✅ Parametrized tests (`@pytest.mark.parametrize`)
- ✅ Mocking external dependencies (Kafka)
- ✅ Fixtures for reusable test data
- ✅ Clear AAA pattern (Arrange, Act, Assert)

**Example test**:
```python
def test_generate_metrics_structure(self):
    """Test that generated metrics have the correct structure."""
    # Arrange
    server = ServerState(server_id="srv-001", rack_id="R01", zone="marseille-1")

    # Act
    metrics = server.generate_metrics()

    # Assert
    assert metrics["type"] == "server_metric"
    assert "cpu_usage_percent" in metrics
```

## Type Checking

```bash
# Run mypy
mypy src/

# Or via Makefile
make type-check
```

## Pre-commit Hooks

Optional git hooks to check code before commit:

```bash
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

## Workflow

1. **Create branch**: `git checkout -b feature/my-feature`
2. **Write code & tests**
3. **Check quality**: `make check`
4. **Auto-fix**: `make fix`
5. **Commit**: `git commit -m "feat: my feature"`
6. **Run full CI**: `make ci-check`
