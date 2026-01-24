# Testing Guide

## Overview

The project has 46 tests with **69% code coverage**, focusing on the generator module.

## Running Tests

### Quick Start

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src

# Or use Makefile
make test
make test-cov
```

### Specific Tests

```bash
# Run specific file
pytest tests/generator/test_models.py

# Run specific class
pytest tests/generator/test_models.py::TestGeneratorConfig

# Run specific test
pytest tests/generator/test_models.py::TestGeneratorConfig::test_default_config

# Run with pattern
pytest tests/ -k "anomaly"
```

## Test Structure

```
tests/
├── conftest.py                    # Shared pytest fixtures
└── generator/
    ├── test_models.py             # GeneratorConfig, AnomalyType (12 tests)
    ├── test_server_state.py       # ServerState class (13 tests)
    ├── test_service_state.py      # ServiceState class (11 tests)
    └── test_generator.py          # DatacenterGenerator (10 tests, mocked Kafka)
```

## What's Tested

### Models (`test_models.py`)
- ✅ Default configuration values
- ✅ Custom configuration
- ✅ Post-init defaults (racks, zones, anomalies)
- ✅ All 8 anomaly types exist
- ✅ Parametrized server/service counts

### Server State (`test_server_state.py`)
- ✅ Initialization
- ✅ Realistic base values (CPU, memory, temp)
- ✅ Metrics structure and bounds
- ✅ All 6 server anomaly types
- ✅ Anomaly duration management
- ✅ Anomaly expiration

### Service State (`test_service_state.py`)
- ✅ Initialization
- ✅ Realistic base values (latency, error rate)
- ✅ Metrics structure (request rate, percentiles)
- ✅ Service anomalies (latency, errors)
- ✅ Valid endpoints
- ✅ Time-based request patterns

### Generator (`test_generator.py`)
- ✅ Initialization with mocked Kafka
- ✅ Server/service creation
- ✅ Event generation
- ✅ Kafka topic routing
- ✅ Anomaly injection probability
- ✅ Enabled anomalies filtering
- ✅ Duration limits
- ✅ Error handling

## Coverage Report

Current coverage: **69%**

```
Name                             Cover   Missing
--------------------------------------------------------------
src/generator/models.py          100%
src/generator/server_state.py    100%
src/generator/service_state.py    97%
src/generator/generator.py        90%    (KeyboardInterrupt, finally)
src/generator/generate.py          0%    (CLI, tested manually)
```

**Not tested**:
- CLI interface (`generate.py`) - tested manually
- Logger setup (`core/logger.py`) - shared utility

## Test Patterns Used

### 1. AAA Pattern (Arrange, Act, Assert)

```python
def test_initialization(self):
    """Test ServerState initialization."""
    # Arrange - setup test data
    server = ServerState(server_id="srv-001", rack_id="R01", zone="marseille-1")

    # Act - execute the code (implicit here)

    # Assert - verify results
    assert server.server_id == "srv-001"
    assert server.rack_id == "R01"
```

### 2. Parametrized Tests

```python
@pytest.mark.parametrize(
    "anomaly_type",
    [AnomalyType.CPU_SPIKE, AnomalyType.MEMORY_LEAK, ...],
)
def test_anomaly_injection(self, anomaly_type):
    """Test that anomaly injection works for all types."""
    server = ServerState(...)
    server.generate_metrics(inject_anomaly=anomaly_type)
    assert server.active_anomaly == anomaly_type
```

### 3. Mocking External Dependencies

```python
@patch("src.generator.generator.KafkaProducer")
def test_initialization(self, mock_producer):
    """Test generator without real Kafka."""
    generator = DatacenterGenerator(config)
    mock_producer.assert_called_once()
```

### 4. Shared Fixtures

```python
# In conftest.py
@pytest.fixture
def basic_config():
    """Reusable config for tests."""
    return GeneratorConfig(num_servers=3, num_services=2)

# In tests
def test_something(basic_config):
    generator = DatacenterGenerator(basic_config)
```

## Adding New Tests

### For New Modules

1. Create `tests/mymodule/test_mymodule.py`
2. Import the module
3. Write test classes with descriptive names
4. Use fixtures from `conftest.py`

### For New Features

1. Add tests BEFORE implementing (TDD)
2. Test happy path and edge cases
3. Mock external dependencies
4. Aim for >80% coverage

### Example Test

```python
"""
Tests for MyNewModule.
"""

import pytest
from src.mymodule import MyClass


class TestMyClass:
    """Tests for MyClass."""

    def test_initialization(self):
        """Test that MyClass initializes correctly."""
        obj = MyClass(param=42)
        assert obj.param == 42

    @pytest.mark.parametrize("value", [1, 10, 100])
    def test_multiple_values(self, value):
        """Test with multiple values."""
        obj = MyClass(param=value)
        assert obj.param == value
```

## Best Practices

✅ **Do**:
- Write descriptive test names
- Add docstrings to tests
- Test edge cases
- Mock external dependencies
- Use fixtures for setup
- Keep tests independent

❌ **Don't**:
- Test implementation details
- Create test interdependencies
- Skip error cases
- Leave tests without assertions
- Use production resources

## CI Integration

Tests run automatically on GitHub Actions:

```yaml
# .github/workflows/ci.yml
- name: Run tests
  run: pytest tests/ --cov=src --cov-report=xml
```

## Troubleshooting

### Tests are slow
```bash
# Use pytest-xdist for parallel execution
pip install pytest-xdist
pytest tests/ -n auto
```

### Coverage is low
```bash
# See what's not covered
pytest tests/ --cov=src --cov-report=term-missing

# Focus on specific module
pytest tests/ --cov=src.generator.models --cov-report=term-missing
```

### Mock not working
```python
# Patch where it's used, not where it's defined
@patch("src.generator.generator.KafkaProducer")  # ✅ Correct
@patch("kafka.KafkaProducer")  # ❌ Wrong
```
