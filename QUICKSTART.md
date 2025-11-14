# Quick Start Guide

Welcome to AIOps Framework! This guide will help you get started in 5 minutes.

## Installation

```bash
# Install from source
git clone https://github.com/markl-a/AIOps.git
cd AIOps
pip install -e .
```

## Configuration

```bash
# Create .env file
cp .env.example .env

# Add your API key to .env
echo "OPENAI_API_KEY=your_key_here" >> .env
# OR
echo "ANTHROPIC_API_KEY=your_key_here" >> .env
```

## First Steps

### 1. Code Review

```bash
# Create a sample Python file
cat > sample.py << 'EOF'
def process_data(items):
    result = []
    for i in range(len(items)):
        if items[i] != None:
            result.append(items[i] * 2)
    return result
EOF

# Review it
aiops review sample.py
```

### 2. Generate Tests

```bash
# Generate tests for the same file
aiops generate-tests sample.py --output test_sample.py

# View the generated tests
cat test_sample.py
```

### 3. Analyze Logs

```bash
# Create sample log file
cat > app.log << 'EOF'
2024-01-10 10:15:23 ERROR Failed to connect to database
2024-01-10 10:15:24 WARN Retrying connection
2024-01-10 10:15:29 ERROR Failed to connect to database
2024-01-10 10:15:41 CRITICAL Database connection failed
EOF

# Analyze logs
aiops analyze-logs app.log
```

### 4. Use Python SDK

```python
# Create example.py
import asyncio
from aiops.agents.code_reviewer import CodeReviewAgent

async def main():
    agent = CodeReviewAgent()

    code = """
    def hello_world():
        print("Hello, World!")
    """

    result = await agent.execute(code=code, language="python")
    print(f"Score: {result.overall_score}/100")

asyncio.run(main())
```

Run it:
```bash
python example.py
```

### 5. Start API Server

```bash
# Start server
python -m aiops.api.main

# In another terminal, test it
curl -X POST http://localhost:8000/api/v1/code/review \
  -H "Content-Type: application/json" \
  -d '{"code": "def hello(): pass", "language": "python"}'
```

## Next Steps

- Read the [full documentation](README.md)
- Check out [examples](aiops/examples/)
- Join our community

## Need Help?

- [GitHub Issues](https://github.com/markl-a/AIOps/issues)
- [Documentation](README.md)

Happy automating! 🚀
