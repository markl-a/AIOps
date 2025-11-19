# AIOps Performance Benchmarks

Performance benchmarks and load tests for measuring AIOps system performance.

## Benchmark Suite (`benchmark_suite.py`)

Comprehensive benchmarks for measuring component performance.

### Usage

```bash
# Run full benchmark suite (100 iterations each)
python benchmarks/benchmark_suite.py

# Run quick benchmarks (10 iterations each)
python benchmarks/benchmark_suite.py --quick
```

### Benchmarks Included

1. **Cache Benchmarks**
   - Cache write operations
   - Cache read operations
   - Tests Redis performance when available

2. **Agent Benchmarks**
   - AI agent execution times (mocked)
   - Measures agent invocation overhead

3. **Webhook Benchmarks**
   - Webhook event parsing
   - Measures webhook handler performance

4. **Concurrency Benchmarks**
   - 10 concurrent operations
   - 50 concurrent operations
   - 100 concurrent operations
   - Tests async operation handling

### Output

The benchmark suite provides:

- **Latency Statistics**: Min, Mean, Median, P95, P99, Max
- **Throughput**: Operations per second
- **Success Rate**: Percentage of successful operations
- **Error Summary**: Grouped error messages

Results are saved to `benchmark_results.json` for historical comparison.

### Example Output

```
🏁 AIOps Performance Benchmark Suite
======================================================================

📦 Cache Benchmarks

🏃 Running: Cache Write (100 iterations)
  Progress: 10/100
  Progress: 20/100
  ...
  ✓ Completed
    Mean: 2.35ms
    P95: 3.12ms
    Throughput: 425.53 ops/sec

📊 BENCHMARK SUMMARY
======================================================================

Cache Write:
  Iterations: 100
  Total Time: 0.23s
  Latency:
    Min:        1.52ms
    Mean:       2.35ms
    Median:     2.28ms
    P95:        3.12ms
    P99:        3.45ms
    Max:        4.01ms
  Throughput: 425.53 ops/sec
  Success Rate: 100.00%
```

---

## Load Testing (`load_test.py`)

Simulates realistic API load to measure performance under stress.

### Usage

```bash
# Light load test (30s, 10 RPS)
python benchmarks/load_test.py

# Medium load test (60s, 20 RPS)
python benchmarks/load_test.py --scenario medium

# Heavy load test (90s, 50 RPS)
python benchmarks/load_test.py --scenario heavy

# Custom parameters
python benchmarks/load_test.py --duration 120 --rps 100 --url http://api.example.com
```

### Scenarios

1. **Light** (default)
   - Duration: 30 seconds
   - RPS: 10
   - Use for: Quick performance checks

2. **Medium**
   - Duration: 60 seconds
   - RPS: 20
   - Use for: Standard load testing

3. **Heavy**
   - Duration: 90 seconds
   - RPS: 50
   - Use for: Stress testing

### Test Scenarios

**Health Check Endpoint**
- Continuously hits `/health` endpoint
- Measures basic API responsiveness

**Mixed API Endpoints**
- Tests multiple endpoints:
  - `/` - Root endpoint
  - `/health` - Health check
  - `/api/v1/llm/providers` - LLM providers
  - `/api/v1/webhooks/status` - Webhook status
- Simulates realistic traffic patterns

### Output

```
⚡ AIOps API Load Testing
======================================================================
Scenario: LIGHT
Target: http://localhost:8000
Duration: 30s
RPS: 10

🔥 Running scenario: Health Check Endpoint
   Duration: 30s
   Target RPS: 10
   Requests: 1 different endpoints
   Progress: 10s / 30s (100 requests)
   Progress: 20s / 30s (200 requests)

📊 Results for Health Check Endpoint:
   Total Requests: 300
   Successful: 300 (100.0%)
   Failed: 0
   Actual RPS: 10.02
   Latency:
     Min:        12.45ms
     Mean:       25.67ms
     Median:     23.12ms
     P95:        45.23ms
     P99:        56.78ms
     Max:        89.12ms
   Status Codes:
     200: 300 (100.0%)
```

---

## Performance Targets

### Latency Targets

- **API Endpoints**: < 100ms (P95)
- **Health Check**: < 10ms (P95)
- **Cache Operations**: < 5ms (P95)
- **Webhook Parsing**: < 10ms (P95)
- **Agent Execution**: < 2000ms (P95, varies by agent)

### Throughput Targets

- **Health Check**: > 1000 RPS
- **Read Operations**: > 500 RPS
- **Write Operations**: > 100 RPS
- **Agent Execution**: > 10 ops/sec

### Resource Targets

- **Memory**: < 512MB idle, < 2GB under load
- **CPU**: < 10% idle, < 80% under load
- **Database Connections**: < 50 concurrent
- **Open Files**: < 1000

---

## Continuous Performance Monitoring

### Integration with CI/CD

```yaml
# .github/workflows/performance.yml
name: Performance Tests
on: [push, pull_request]
jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run benchmarks
        run: python benchmarks/benchmark_suite.py --quick
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: benchmark-results
          path: benchmarks/benchmark_results.json
```

### Historical Comparison

Track performance over time by comparing benchmark results:

```python
import json

# Load current results
with open('benchmark_results.json') as f:
    current = json.load(f)

# Load baseline
with open('benchmark_baseline.json') as f:
    baseline = json.load(f)

# Compare
for curr_bench in current['benchmarks']:
    name = curr_bench['name']
    base_bench = next(b for b in baseline['benchmarks'] if b['name'] == name)

    curr_p95 = curr_bench['latency_ms']['p95']
    base_p95 = base_bench['latency_ms']['p95']

    regression = (curr_p95 - base_p95) / base_p95 * 100

    if regression > 10:  # More than 10% slower
        print(f"⚠️  Performance regression in {name}: +{regression:.1f}%")
```

---

## Profiling

For detailed performance analysis, use Python profilers:

### cProfile

```bash
python -m cProfile -o profile.stats benchmarks/benchmark_suite.py
python -m pstats profile.stats
```

### py-spy

```bash
# Install
pip install py-spy

# Profile running process
py-spy top --pid <PID>

# Generate flame graph
py-spy record -o profile.svg --pid <PID>
```

### memory_profiler

```bash
# Install
pip install memory_profiler

# Add @profile decorator to functions
python -m memory_profiler benchmarks/benchmark_suite.py
```

---

## Best Practices

1. **Establish Baseline**
   - Run benchmarks on a clean system
   - Save results as baseline
   - Compare all future runs against baseline

2. **Consistent Environment**
   - Run on same hardware
   - Same system load
   - Same data volumes

3. **Multiple Runs**
   - Run benchmarks multiple times
   - Calculate average and variance
   - Discard outliers

4. **Monitor System Resources**
   - CPU usage
   - Memory consumption
   - Network I/O
   - Disk I/O

5. **Test Realistic Scenarios**
   - Use production-like data
   - Simulate actual usage patterns
   - Test peak load scenarios

6. **Automate**
   - Run benchmarks in CI/CD
   - Alert on regressions
   - Track trends over time

---

## Troubleshooting

### High Latency

1. Check database query performance
2. Verify Redis is running (for cache tests)
3. Check network latency
4. Review database connection pool size
5. Monitor for CPU/memory bottlenecks

### Low Throughput

1. Increase concurrency
2. Optimize database queries
3. Enable caching
4. Scale horizontally
5. Profile and optimize hot paths

### High Error Rate

1. Check API logs
2. Verify database connectivity
3. Check rate limits
4. Review resource constraints
5. Test with smaller load

---

## Future Improvements

- [ ] Database query benchmarks
- [ ] End-to-end workflow benchmarks
- [ ] Real LLM provider latency tests
- [ ] Distributed load testing
- [ ] Memory leak detection
- [ ] CPU profiling integration
- [ ] Automated regression detection
- [ ] Performance dashboard
