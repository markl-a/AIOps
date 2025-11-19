# AIOps Validation Scripts

This directory contains scripts for validating and monitoring the AIOps system.

## Scripts

### 1. Setup Verification (`setup_check.py`)

Verifies that the project is properly set up after initial installation.

```bash
python scripts/setup_check.py
```

**Checks:**
- Project directory structure
- Configuration files
- Core modules
- Environment setup
- Git repository
- Docker installation

**When to use:** After cloning the repository or initial setup

---

### 2. System Validation (`validate_system.py`)

Comprehensive validation of the entire AIOps system.

```bash
python scripts/validate_system.py
```

**Checks:**
- Environment variables
- Python dependencies
- Database connectivity (PostgreSQL)
- Redis connectivity
- LLM provider configuration
- AI agents
- Plugin system
- Webhook handlers
- API structure
- Example files

**When to use:**
- After configuration changes
- Before deployment
- For troubleshooting
- In CI/CD pipelines

---

### 3. Health Check (`health_check.py`)

Quick health check of running services.

```bash
python scripts/health_check.py
```

**Checks:**
- API server health (requires API to be running)
- Database connectivity
- Redis connectivity
- LLM provider configuration

**When to use:**
- During development
- In monitoring/alerting
- In Kubernetes liveness/readiness probes
- For quick status checks

---

## Exit Codes

All scripts return appropriate exit codes:

- **0**: All checks passed
- **1**: Some checks failed

This makes them suitable for use in CI/CD pipelines and automated monitoring.

---

## Integration Examples

### CI/CD Pipeline

```yaml
# .github/workflows/validate.yml
name: Validate
on: [push]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Validate system
        run: python scripts/validate_system.py
```

### Kubernetes Liveness Probe

```yaml
livenessProbe:
  exec:
    command:
    - python
    - /app/scripts/health_check.py
  initialDelaySeconds: 30
  periodSeconds: 60
```

### Makefile Integration

```makefile
.PHONY: validate health setup-check

setup-check:
	@python scripts/setup_check.py

validate:
	@python scripts/validate_system.py

health:
	@python scripts/health_check.py

check: setup-check validate health
```

---

## Colored Output

All scripts use colored terminal output for better readability:

- **Green (✓)**: Passed checks
- **Red (✗)**: Failed checks
- **Yellow (⚠)**: Warnings
- **Blue**: Headers and info

---

## Requirements

Scripts require:
- Python 3.10+
- Project dependencies installed (`pip install -r requirements.txt`)
- Appropriate environment variables configured

For `health_check.py` to fully work:
- API server must be running (`make dev`)
- Database must be accessible
- Redis must be accessible (optional)

---

## Troubleshooting

### "Module not found" errors

Ensure you're running scripts from the project root or that the project root is in your PYTHON_PATH.

### Database connection errors

- Check that DATABASE_URL is set correctly in `.env`
- Ensure PostgreSQL is running (`make docker-up`)
- Verify database credentials

### Redis connection errors

- Check that REDIS_URL is set correctly in `.env`
- Ensure Redis is running (`make docker-up`)
- Redis is optional; warnings can be ignored if not using caching

### API health check failures

- Ensure API server is running (`make dev` or `uvicorn aiops.api.app:app --reload`)
- Check that API is accessible at http://localhost:8000
- Review API logs for errors

---

## Adding Custom Checks

To add custom validation checks to `validate_system.py`:

```python
def check_my_custom_feature() -> Tuple[int, int]:
    """Check my custom feature"""
    print_header("My Custom Feature")

    try:
        # Your validation logic here
        print_success("Feature is working")
        return 1, 0
    except Exception as e:
        print_error(f"Feature failed: {e}")
        return 0, 1

# Add to checks list in main()
checks = [
    # ... existing checks ...
    ("My Custom Feature", check_my_custom_feature),
]
```

---

## Best Practices

1. **Run setup_check.py** after cloning the repository
2. **Run validate_system.py** before committing major changes
3. **Use health_check.py** for monitoring in production
4. **Integrate into CI/CD** for automated validation
5. **Review output** even when all checks pass to understand system state

---

## Support

For issues with validation scripts:
1. Check the troubleshooting section above
2. Review the main README.md
3. Check docs/TROUBLESHOOTING.md
4. Open an issue on GitHub
