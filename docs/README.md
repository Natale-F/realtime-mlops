# Documentation

## Quick Links

- **[generator.md](generator.md)** - Complete generator documentation
  - Architecture, usage, configs, anomaly types, metrics

- **[dev_pratices.md](dev_pratices.md)** - Development guide
  - Setup, ruff, testing workflow, pre-commit hooks

- **[testing.md](testing.md)** - Testing guide ⭐ NEW
  - 46 tests, 69% coverage, patterns, best practices

- **[config.md](config.md)** - Configuration files explained
  - pyproject.toml, requirements.txt, Makefile, .env

- **[consumer.md](consumer.md)** - Consumer files explained
  - pyproject.toml, requirements.txt, Makefile, .env


## Quick Start

```bash
# Generator
python -m src.generator.generate --config normal

# Development
make help
make fix

# Tests (46 tests, 69% coverage)
make test
make test-cov
```

See main [README.md](../README.md) for project overview.
