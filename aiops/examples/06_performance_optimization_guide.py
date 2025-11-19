"""Example 6: Performance Analysis and Optimization

This example shows how to analyze and optimize code performance.
"""

import asyncio
import time
from aiops.agents.performance_analyzer import PerformanceAnalyzerAgent
from aiops.agents.db_query_analyzer import DatabaseQueryAnalyzer


async def analyze_code_performance(code: str, language: str = "python"):
    """Analyze code for performance issues."""

    print("⚡ Performance Analysis")
    print("="*60)

    analyzer = PerformanceAnalyzerAgent()

    # Analyze code
    result = await analyzer.execute(code=code, language=language)

    print(f"\n📊 Performance Score: {result.overall_score}/100")
    print(f"🚀 Estimated Speedup: {result.estimated_speedup}")

    # Show issues
    if result.issues:
        print(f"\n🐌 Performance Issues Found: {len(result.issues)}")

        for issue in result.issues:
            print(f"\n  [{issue.severity.upper()}] {issue.category}")
            print(f"  Location: {issue.location}")
            print(f"  Description: {issue.description}")
            print(f"  Impact: {issue.impact}")

    # Show optimizations
    if result.optimizations:
        print(f"\n💡 Optimization Recommendations:")

        for opt in result.optimizations:
            print(f"\n  Target: {opt.target}")
            print(f"  Recommendation: {opt.recommendation}")
            print(f"  Expected Improvement: {opt.estimated_improvement}")
            print(f"  Difficulty: {opt.difficulty}")

    return result


async def optimize_database_queries():
    """Example of database query optimization."""

    print("\n🗄️  Database Query Optimization")
    print("="*60)

    # Example slow query
    slow_query = """
    SELECT u.*, p.title, p.content, c.comment_text
    FROM users u
    LEFT JOIN posts p ON u.id = p.user_id
    LEFT JOIN comments c ON p.id = c.post_id
    WHERE u.created_at > '2024-01-01'
    ORDER BY p.created_at DESC
    LIMIT 100
    """

    # Mock query plan
    query_plan = {
        "query_time_ms": 2500.5,
        "rows_examined": 150000,
        "rows_returned": 100,
        "using_index": False,
        "using_filesort": True,
        "using_temporary": True,
    }

    print(f"\n📝 Analyzing Query:")
    print(slow_query)

    print(f"\n⏱️  Current Performance:")
    print(f"  Query Time: {query_plan['query_time_ms']}ms")
    print(f"  Rows Examined: {query_plan['rows_examined']:,}")
    print(f"  Rows Returned: {query_plan['rows_returned']}")

    # Analyze query
    db_analyzer = DatabaseQueryAnalyzer()
    result = await db_analyzer.execute(
        query=slow_query,
        query_plan=query_plan,
        database_type="postgresql"
    )

    print(f"\n📊 Optimization Score: {result.optimization_score}/100")
    print(f"⏱️  Estimated Time Saved: {result.estimated_time_saved_ms:.1f}ms")

    # Show issues
    if result.issues:
        print(f"\n⚠️  Issues Found:")
        for issue in result.issues:
            print(f"  [{issue.severity.upper()}] {issue.category}")
            print(f"    {issue.description}")
            print(f"    Impact: {issue.impact}")
            print(f"    Fix: {issue.suggestion}")

    # Show index recommendations
    if result.index_recommendations:
        print(f"\n🔑 Index Recommendations:")
        for idx in result.index_recommendations:
            columns_str = ", ".join(idx.columns)
            print(f"\n  Table: {idx.table}")
            print(f"  Columns: {columns_str}")
            print(f"  Type: {idx.index_type}")
            print(f"  Expected Improvement: {idx.estimated_improvement_percent:.0f}%")
            print(f"  Justification: {idx.justification}")

            # Generate SQL
            print(f"\n  SQL:")
            print(f"    CREATE INDEX idx_{idx.table}_{'_'.join(idx.columns)}")
            print(f"    ON {idx.table}({columns_str})")
            if idx.index_type != "BTREE":
                print(f"    USING {idx.index_type};")
            else:
                print(f"    ;")


async def common_performance_patterns():
    """Demonstrate analysis of common performance anti-patterns."""

    print("\n🔍 Common Performance Anti-Patterns")
    print("="*60)

    # Anti-pattern 1: N+1 queries
    print("\n1️⃣  N+1 Query Pattern")
    print("-" * 60)

    n_plus_one = """
    def get_users_with_posts():
        users = User.objects.all()  # 1 query
        for user in users:
            posts = Post.objects.filter(user=user)  # N queries
            print(f"{user.name}: {posts.count()} posts")
    """

    result1 = await analyze_code_performance(n_plus_one)

    print("\n✅ Optimized Version:")
    print("""
    def get_users_with_posts_optimized():
        # Single query with prefetch
        users = User.objects.prefetch_related('posts').all()
        for user in users:
            print(f"{user.name}: {user.posts.count()} posts")
    """)

    # Anti-pattern 2: O(n²) complexity
    print("\n2️⃣  O(n²) Time Complexity")
    print("-" * 60)

    quadratic = """
    def find_duplicates(items):
        duplicates = []
        for i in range(len(items)):
            for j in range(i+1, len(items)):
                if items[i] == items[j]:
                    duplicates.append(items[i])
        return duplicates
    """

    result2 = await analyze_code_performance(quadratic)

    print("\n✅ Optimized Version (O(n)):")
    print("""
    def find_duplicates_optimized(items):
        seen = set()
        duplicates = set()
        for item in items:
            if item in seen:
                duplicates.add(item)
            else:
                seen.add(item)
        return list(duplicates)
    """)

    # Anti-pattern 3: Unbounded loops
    print("\n3️⃣  Unbounded Resource Usage")
    print("-" * 60)

    unbounded = """
    def process_large_file(filename):
        # Loads entire file into memory
        with open(filename, 'r') as f:
            data = f.read()  # ❌ May cause OOM for large files

        for line in data.split('\\n'):
            process_line(line)
    """

    result3 = await analyze_code_performance(unbounded)

    print("\n✅ Optimized Version (Streaming):")
    print("""
    def process_large_file_optimized(filename):
        # Stream file line by line
        with open(filename, 'r') as f:
            for line in f:  # ✅ Memory efficient
                process_line(line.strip())
    """)


async def benchmark_code_changes():
    """Example of benchmarking code changes."""

    print("\n⏱️  Benchmarking Code Changes")
    print("="*60)

    # Original slow version
    def slow_version():
        result = []
        for i in range(1000):
            if i % 2 == 0:
                result.append(i ** 2)
        return result

    # Optimized version
    def fast_version():
        return [i ** 2 for i in range(1000) if i % 2 == 0]

    # Benchmark
    iterations = 1000

    # Time slow version
    start = time.time()
    for _ in range(iterations):
        slow_version()
    slow_time = (time.time() - start) * 1000  # Convert to ms

    # Time fast version
    start = time.time()
    for _ in range(iterations):
        fast_version()
    fast_time = (time.time() - start) * 1000

    improvement = ((slow_time - fast_time) / slow_time) * 100
    speedup = slow_time / fast_time

    print(f"\nResults ({iterations} iterations):")
    print(f"  Original: {slow_time:.2f}ms")
    print(f"  Optimized: {fast_time:.2f}ms")
    print(f"  Improvement: {improvement:.1f}%")
    print(f"  Speedup: {speedup:.2f}x")


if __name__ == "__main__":
    print("🚀 Performance Optimization Examples")
    print("="*60)

    # Run examples
    asyncio.run(common_performance_patterns())

    print("\n" + "="*60 + "\n")
    asyncio.run(optimize_database_queries())

    print("\n" + "="*60 + "\n")
    asyncio.run(benchmark_code_changes())

    print("\n✅ All performance analysis examples complete!\n")
