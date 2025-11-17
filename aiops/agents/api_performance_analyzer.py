"""
API Performance Analyzer Agent

Analyzes API performance, identifies bottlenecks, suggests caching strategies,
and provides optimization recommendations for REST/GraphQL APIs.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class APIEndpoint(BaseModel):
    """API endpoint performance data"""
    method: str = Field(description="HTTP method (GET, POST, etc.)")
    path: str = Field(description="API path")
    avg_latency_ms: float = Field(description="Average latency in milliseconds")
    p95_latency_ms: float = Field(description="95th percentile latency")
    p99_latency_ms: float = Field(description="99th percentile latency")
    requests_per_minute: float = Field(description="Request rate")
    error_rate: float = Field(description="Error rate percentage")
    avg_response_size_kb: float = Field(description="Average response size in KB")


class APIOptimization(BaseModel):
    """API optimization recommendation"""
    endpoint: str = Field(description="Affected endpoint")
    issue_type: str = Field(description="Type of issue")
    severity: str = Field(description="critical, high, medium, low")
    current_performance: Dict[str, float] = Field(description="Current metrics")
    expected_improvement: str = Field(description="Expected improvement")
    recommendations: List[str] = Field(description="Specific recommendations")
    implementation_effort: str = Field(description="easy, medium, hard")


class APIPerformanceResult(BaseModel):
    """API performance analysis result"""
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    api_type: str = Field(description="REST, GraphQL, gRPC")
    endpoints_analyzed: int = Field(description="Number of endpoints analyzed")
    endpoints: List[APIEndpoint] = Field(description="Endpoint performance data")
    optimizations: List[APIOptimization] = Field(description="Optimization recommendations")
    performance_score: float = Field(description="Overall performance score 0-100")
    summary: str = Field(description="Summary")
    caching_opportunities: List[str] = Field(description="Caching recommendations")


class APIPerformanceAnalyzer:
    """API performance analyzer agent"""

    def __init__(self, llm_factory=None):
        self.llm_factory = llm_factory
        logger.info("API Performance Analyzer initialized")

    async def analyze_api(
        self,
        endpoints: List[Dict[str, Any]],
        api_type: str = "REST"
    ) -> APIPerformanceResult:
        """Analyze API performance"""

        endpoint_models = []
        optimizations = []
        caching_opportunities = []

        for ep in endpoints:
            endpoint = APIEndpoint(
                method=ep.get('method', 'GET'),
                path=ep.get('path', '/'),
                avg_latency_ms=ep.get('avg_latency_ms', 0),
                p95_latency_ms=ep.get('p95_latency_ms', 0),
                p99_latency_ms=ep.get('p99_latency_ms', 0),
                requests_per_minute=ep.get('requests_per_minute', 0),
                error_rate=ep.get('error_rate', 0),
                avg_response_size_kb=ep.get('avg_response_size_kb', 0)
            )
            endpoint_models.append(endpoint)

            endpoint_path = f"{endpoint.method} {endpoint.path}"

            # Check latency issues
            if endpoint.p99_latency_ms > 1000:
                optimizations.append(APIOptimization(
                    endpoint=endpoint_path,
                    issue_type="high_latency",
                    severity="high",
                    current_performance={
                        "p99_latency_ms": endpoint.p99_latency_ms,
                        "avg_latency_ms": endpoint.avg_latency_ms
                    },
                    expected_improvement="50-80% latency reduction",
                    recommendations=[
                        "Add database indexes on queried columns",
                        "Implement response caching (Redis/Memcached)",
                        "Optimize N+1 queries with eager loading",
                        "Add database query timeout limits",
                        "Consider pagination for large result sets"
                    ],
                    implementation_effort="medium"
                ))

            # Check for caching opportunities
            if endpoint.method == "GET" and endpoint.requests_per_minute > 100:
                caching_opportunities.append(
                    f"{endpoint_path} - High traffic ({endpoint.requests_per_minute:.0f} req/min), "
                    f"implement caching with 5-15 min TTL"
                )

                optimizations.append(APIOptimization(
                    endpoint=endpoint_path,
                    issue_type="missing_cache",
                    severity="medium",
                    current_performance={
                        "requests_per_minute": endpoint.requests_per_minute,
                        "avg_latency_ms": endpoint.avg_latency_ms
                    },
                    expected_improvement="70-90% latency reduction, reduced DB load",
                    recommendations=[
                        "Implement Redis caching layer",
                        "Use ETag/If-None-Match for conditional requests",
                        "Add Cache-Control headers",
                        "Implement stale-while-revalidate pattern",
                        f"Suggested TTL: {self._suggest_cache_ttl(endpoint)}"
                    ],
                    implementation_effort="easy"
                ))

            # Check response size
            if endpoint.avg_response_size_kb > 500:
                optimizations.append(APIOptimization(
                    endpoint=endpoint_path,
                    issue_type="large_response",
                    severity="medium",
                    current_performance={
                        "avg_response_size_kb": endpoint.avg_response_size_kb
                    },
                    expected_improvement="50-70% bandwidth reduction",
                    recommendations=[
                        "Enable gzip/brotli compression",
                        "Implement field filtering (GraphQL-style)",
                        "Add pagination (limit/offset or cursor-based)",
                        "Remove unnecessary fields from response",
                        "Consider using Protocol Buffers for binary data"
                    ],
                    implementation_effort="easy"
                ))

            # Check error rate
            if endpoint.error_rate > 1.0:
                optimizations.append(APIOptimization(
                    endpoint=endpoint_path,
                    issue_type="high_error_rate",
                    severity="critical" if endpoint.error_rate > 5 else "high",
                    current_performance={
                        "error_rate": endpoint.error_rate
                    },
                    expected_improvement="Reduce errors to <0.1%",
                    recommendations=[
                        "Implement input validation and sanitization",
                        "Add proper error handling and logging",
                        "Implement circuit breaker for dependencies",
                        "Add request rate limiting",
                        "Improve monitoring and alerting"
                    ],
                    implementation_effort="medium"
                ))

            # Check for slow mutations
            if endpoint.method in ['POST', 'PUT', 'PATCH'] and endpoint.avg_latency_ms > 500:
                optimizations.append(APIOptimization(
                    endpoint=endpoint_path,
                    issue_type="slow_mutation",
                    severity="medium",
                    current_performance={
                        "avg_latency_ms": endpoint.avg_latency_ms
                    },
                    expected_improvement="Async processing, immediate response",
                    recommendations=[
                        "Process asynchronously using message queue",
                        "Return 202 Accepted with job ID",
                        "Implement webhook/polling for status",
                        "Batch similar operations",
                        "Optimize database transactions"
                    ],
                    implementation_effort="hard"
                ))

        # Calculate performance score
        performance_score = self._calculate_performance_score(endpoint_models)

        # Generate summary
        summary = self._generate_summary(api_type, len(endpoints), performance_score, len(optimizations))

        return APIPerformanceResult(
            api_type=api_type,
            endpoints_analyzed=len(endpoints),
            endpoints=endpoint_models,
            optimizations=optimizations,
            performance_score=performance_score,
            summary=summary,
            caching_opportunities=caching_opportunities
        )

    def _suggest_cache_ttl(self, endpoint: APIEndpoint) -> str:
        """Suggest cache TTL based on endpoint characteristics"""
        if 'user' in endpoint.path or 'profile' in endpoint.path:
            return "5-10 minutes"
        elif 'list' in endpoint.path or 'search' in endpoint.path:
            return "2-5 minutes"
        elif 'config' in endpoint.path or 'settings' in endpoint.path:
            return "30-60 minutes"
        else:
            return "10-15 minutes"

    def _calculate_performance_score(self, endpoints: List[APIEndpoint]) -> float:
        """Calculate overall performance score"""
        if not endpoints:
            return 100.0

        total_score = 0.0

        for ep in endpoints:
            score = 100.0

            # Penalize high latency
            if ep.p99_latency_ms > 2000:
                score -= 30
            elif ep.p99_latency_ms > 1000:
                score -= 20
            elif ep.p99_latency_ms > 500:
                score -= 10

            # Penalize high error rate
            if ep.error_rate > 5:
                score -= 40
            elif ep.error_rate > 1:
                score -= 20
            elif ep.error_rate > 0.5:
                score -= 10

            # Penalize large responses
            if ep.avg_response_size_kb > 1000:
                score -= 15
            elif ep.avg_response_size_kb > 500:
                score -= 10

            total_score += max(0, score)

        return total_score / len(endpoints)

    def _generate_summary(self, api_type: str, count: int, score: float, optimizations: int) -> str:
        """Generate summary"""
        summary = f"{api_type} API Performance Analysis\n\n"
        summary += f"Endpoints analyzed: {count}\n"
        summary += f"Performance score: {score:.1f}/100\n"
        summary += f"Optimizations found: {optimizations}\n\n"

        if score >= 85:
            summary += "✓ API performance is excellent"
        elif score >= 70:
            summary += "⚠ API performance is good but has improvement opportunities"
        elif score >= 50:
            summary += "⚠ API performance needs improvement"
        else:
            summary += "✗ Critical performance issues detected"

        return summary
