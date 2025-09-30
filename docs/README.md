# Documentation

## Quick Links

- **[GENERATOR.md](GENERATOR.md)** - Complete generator documentation
  - Architecture, usage, configs, anomaly types, metrics
  
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development guide
  - Setup, ruff, testing workflow, pre-commit hooks
  
- **[TESTING.md](TESTING.md)** - Testing guide ⭐ NEW
  - 46 tests, 69% coverage, patterns, best practices
  
- **[CONFIGURATION.md](CONFIGURATION.md)** - Configuration files explained
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
