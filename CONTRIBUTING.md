# Contributing to AIOps

Thank you for your interest in contributing to AIOps! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/AIOps.git`
3. Add upstream remote: `git remote add upstream https://github.com/ORIGINAL_OWNER/AIOps.git`

## Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Copy environment file
cp .env.example .env
# Edit .env with your configuration
```

## Making Changes

1. Create a new branch: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Run tests: `pytest`
4. Run linting: `make lint`
5. Commit your changes with a descriptive message

### Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example: `feat(agents): add new performance analyzer agent`

## Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass
4. Update CHANGELOG.md
5. Request review from maintainers

## Coding Standards

- Follow PEP 8 style guide
- Use type hints for all functions
- Write docstrings for all public functions and classes
- Keep functions focused and under 50 lines when possible
- Use meaningful variable and function names

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=aiops --cov-report=html

# Run specific test file
pytest aiops/tests/test_specific.py

# Run tests matching a pattern
pytest -k "test_pattern"
```

### Test Requirements

- All new features must have tests
- Maintain minimum 70% code coverage
- Use pytest fixtures for common setup
- Mock external services (LLM APIs, databases)

## Questions?

If you have questions, please open an issue or reach out to the maintainers.
