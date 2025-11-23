"""FastAPI application for AIOps framework."""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import timedelta
import asyncio
import os

from aiops import __version__
from aiops.core.logger import setup_logger, get_logger
from aiops.core.token_tracker import get_token_tracker
from aiops.core.security_validator import SecurityValidator
from aiops.agents.code_reviewer import CodeReviewAgent, CodeReviewResult
from aiops.agents.test_generator import TestGeneratorAgent, TestSuite
from aiops.agents.log_analyzer import LogAnalyzerAgent, LogAnalysisResult
from aiops.agents.cicd_optimizer import CICDOptimizerAgent, PipelineOptimization
from aiops.agents.doc_generator import DocGeneratorAgent
from aiops.agents.performance_analyzer import PerformanceAnalyzerAgent, PerformanceAnalysisResult
from aiops.agents.anomaly_detector import AnomalyDetectorAgent, AnomalyDetectionResult
from aiops.agents.auto_fixer import AutoFixerAgent, AutoFixResult
from aiops.agents.intelligent_monitor import IntelligentMonitorAgent, MonitoringAnalysisResult

# Import security components
from aiops.api.auth import (
    get_current_user,
    require_admin,
    require_user,
    require_readonly,
    create_access_token,
    api_key_manager,
    UserRole,
)
from aiops.api.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    RequestValidationMiddleware,
    CORSMiddleware as CustomCORSMiddleware,
    MetricsMiddleware,
)

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create FastAPI application."""
    setup_logger()

    # Validate security configuration on startup
    logger.info("Validating security configuration...")
    try:
        SecurityValidator.validate_and_raise()
        logger.info("✅ Security configuration validated successfully")
    except ValueError as e:
        logger.error(f"❌ Security validation failed: {e}")
        raise

    # Get configuration from environment
    enable_auth = os.getenv("ENABLE_AUTH", "true").lower() == "true"
    enable_rate_limit = os.getenv("ENABLE_RATE_LIMIT", "true").lower() == "true"
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")

    app = FastAPI(
        title="AIOps Framework API",
        description="AI-powered DevOps automation API with enterprise security",
        version=__version__,
        docs_url="/docs" if not enable_auth else None,  # Disable docs in production
        redoc_url="/redoc" if not enable_auth else None,
    )

    # Add middleware (order matters - last added is executed first)
    # 1. Metrics collection (outermost)
    metrics_middleware = MetricsMiddleware(app)
    app.add_middleware(MetricsMiddleware)

    # 2. Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # 3. Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # 4. Request validation
    app.add_middleware(RequestValidationMiddleware)

    # 5. Rate limiting
    if enable_rate_limit:
        app.add_middleware(
            RateLimitMiddleware,
            default_limit=int(os.getenv("RATE_LIMIT", "100")),
            window_seconds=60,
            enabled=True,
        )

    # 6. CORS (innermost, closest to app)
    app.add_middleware(
        CustomCORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    # Store middleware references for metrics endpoint
    app.state.metrics_middleware = metrics_middleware

    # Request models
    class CodeReviewRequest(BaseModel):
        code: str
        language: str = "python"
        context: Optional[str] = None
        standards: Optional[List[str]] = None

    class TestGenerationRequest(BaseModel):
        code: str
        language: str = "python"
        test_framework: Optional[str] = None
        context: Optional[str] = None

    class LogAnalysisRequest(BaseModel):
        logs: str
        context: Optional[str] = None
        focus_areas: Optional[List[str]] = None

    class PipelineOptimizationRequest(BaseModel):
        pipeline_config: str
        pipeline_logs: Optional[str] = None
        metrics: Optional[Dict[str, Any]] = None

    class DocGenerationRequest(BaseModel):
        code: str
        doc_type: str = "function"
        language: str = "python"
        existing_docs: Optional[str] = None

    class PerformanceAnalysisRequest(BaseModel):
        code: str
        language: str = "python"
        profiling_data: Optional[Dict[str, Any]] = None
        metrics: Optional[Dict[str, Any]] = None

    class AnomalyDetectionRequest(BaseModel):
        metrics: Dict[str, Any]
        baseline: Optional[Dict[str, Any]] = None
        context: Optional[str] = None

    class AutoFixRequest(BaseModel):
        issue_description: str
        logs: Optional[str] = None
        system_state: Optional[Dict[str, Any]] = None
        auto_apply: bool = False

    class MonitoringRequest(BaseModel):
        metrics: Dict[str, Any]
        logs: Optional[str] = None
        historical_data: Optional[Dict[str, Any]] = None

    # Auth models
    class LoginRequest(BaseModel):
        username: str
        password: str

    class TokenResponse(BaseModel):
        access_token: str
        token_type: str = "bearer"
        expires_in: int

    class APIKeyCreateRequest(BaseModel):
        name: str
        role: UserRole = UserRole.USER
        rate_limit: int = 100

    class APIKeyResponse(BaseModel):
        api_key: str
        name: str
        role: UserRole
        rate_limit: int
        message: str = "Save this key securely. It won't be shown again."

    # Public Routes (no auth required)
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "AIOps Framework API",
            "version": __version__,
            "status": "running",
            "auth_enabled": enable_auth,
            "docs_url": "/docs" if not enable_auth else None,
        }

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}

    # Auth Management Routes
    @app.post("/api/v1/auth/token", response_model=TokenResponse)
    async def login(request: LoginRequest):
        """
        Create access token.

        For production, integrate with your user management system.
        """
        # Get admin password from environment (validated at startup)
        admin_password = os.getenv("ADMIN_PASSWORD")
        if not admin_password:
            # This should never happen if security validation passed
            logger.error("ADMIN_PASSWORD not set despite security validation")
            raise HTTPException(status_code=500, detail="Server configuration error")

        # Simple admin authentication (replace with proper user management in production)
        if request.username == "admin" and request.password == admin_password:
            access_token = create_access_token(
                data={"sub": request.username, "role": UserRole.ADMIN}
            )
            return TokenResponse(
                access_token=access_token,
                expires_in=60 * int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
            )

        # Invalid credentials
        logger.warning(f"Failed login attempt for user: {request.username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    @app.post("/api/v1/auth/apikey", response_model=APIKeyResponse)
    async def create_apikey(
        request: APIKeyCreateRequest,
        current_user: Dict[str, Any] = Depends(require_admin),
    ):
        """
        Create a new API key (admin only).

        Returns the API key - save it securely as it won't be shown again.
        """
        api_key = api_key_manager.create_api_key(
            name=request.name, role=request.role, rate_limit=request.rate_limit
        )

        logger.info(f"API key created by {current_user['username']}: {request.name}")

        return APIKeyResponse(
            api_key=api_key,
            name=request.name,
            role=request.role,
            rate_limit=request.rate_limit,
        )

    @app.get("/api/v1/auth/apikeys")
    async def list_apikeys(current_user: Dict[str, Any] = Depends(require_admin)):
        """List all API keys (admin only)."""
        keys = api_key_manager.list_api_keys()
        return {
            "total": len(keys),
            "keys": [
                {
                    "name": key.name,
                    "role": key.role,
                    "created_at": key.created_at,
                    "last_used": key.last_used,
                    "rate_limit": key.rate_limit,
                    "enabled": key.enabled,
                }
                for key in keys
            ],
        }

    @app.get("/api/v1/metrics")
    async def get_metrics(current_user: Dict[str, Any] = Depends(require_readonly)):
        """Get API metrics (requires authentication)."""
        return app.state.metrics_middleware.get_metrics()

    @app.get("/api/v1/tokens/usage")
    async def get_token_usage(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        current_user: Dict[str, Any] = Depends(require_readonly),
    ):
        """
        Get token usage statistics (requires authentication).

        Args:
            start_time: ISO format datetime string (optional)
            end_time: ISO format datetime string (optional)
        """
        tracker = get_token_tracker()

        # Parse datetime filters
        from datetime import datetime
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None

        stats = tracker.get_stats(start_time=start_dt, end_time=end_dt)

        return {
            "stats": {
                "total_requests": stats.total_requests,
                "total_input_tokens": stats.total_input_tokens,
                "total_output_tokens": stats.total_output_tokens,
                "total_tokens": stats.total_tokens,
                "total_cost": round(stats.total_cost, 4),
                "average_tokens_per_request": round(stats.average_tokens_per_request, 2),
                "average_cost_per_request": round(stats.average_cost_per_request, 4),
            },
            "by_model": {
                k: {
                    **v,
                    "cost": round(v["cost"], 4),
                }
                for k, v in stats.by_model.items()
            },
            "by_user": {
                k: {
                    **v,
                    "cost": round(v["cost"], 4),
                }
                for k, v in stats.by_user.items()
            },
            "by_agent": {
                k: {
                    **v,
                    "cost": round(v["cost"], 4),
                }
                for k, v in stats.by_agent.items()
            },
        }

    @app.get("/api/v1/tokens/budget")
    async def get_token_budget(current_user: Dict[str, Any] = Depends(require_readonly)):
        """Get budget status (requires authentication)."""
        tracker = get_token_tracker()
        return tracker.get_budget_status()

    @app.post("/api/v1/tokens/reset")
    async def reset_token_usage(current_user: Dict[str, Any] = Depends(require_admin)):
        """Reset token usage statistics (admin only)."""
        tracker = get_token_tracker()
        tracker.reset()
        logger.info(f"Token usage reset by {current_user['username']}")
        return {"message": "Token usage statistics have been reset"}

    # AI Agent Endpoints (require authentication)
    @app.post("/api/v1/code/review", response_model=CodeReviewResult)
    async def review_code(
        request: CodeReviewRequest,
        current_user: Dict[str, Any] = Depends(get_current_user) if enable_auth else None,
    ):
        """Review code and provide feedback (requires authentication)."""
        try:
            logger.info(f"Code review requested by {current_user.get('username') if current_user else 'anonymous'}")
            agent = CodeReviewAgent()
            result = await agent.execute(
                code=request.code,
                language=request.language,
                context=request.context,
                standards=request.standards,
            )
            return result
        except Exception as e:
            logger.error(f"Code review failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/tests/generate", response_model=TestSuite)
    async def generate_tests(
        request: TestGenerationRequest,
        current_user: Dict[str, Any] = Depends(get_current_user) if enable_auth else None,
    ):
        """Generate tests for code (requires authentication)."""
        try:
            logger.info(f"Test generation requested by {current_user.get('username') if current_user else 'anonymous'}")
            agent = TestGeneratorAgent()
            result = await agent.execute(
                code=request.code,
                language=request.language,
                test_framework=request.test_framework,
                context=request.context,
            )
            return result
        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/logs/analyze", response_model=LogAnalysisResult)
    async def analyze_logs(
        request: LogAnalysisRequest,
        current_user: Dict[str, Any] = Depends(get_current_user) if enable_auth else None,
    ):
        """Analyze logs and provide insights (requires authentication)."""
        try:
            logger.info(f"Log analysis requested by {current_user.get('username') if current_user else 'anonymous'}")
            agent = LogAnalyzerAgent()
            result = await agent.execute(
                logs=request.logs,
                context=request.context,
                focus_areas=request.focus_areas,
            )
            return result
        except Exception as e:
            logger.error(f"Log analysis failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/cicd/optimize", response_model=PipelineOptimization)
    async def optimize_pipeline(
        request: PipelineOptimizationRequest,
        current_user: Dict[str, Any] = Depends(get_current_user) if enable_auth else None,
    ):
        """Optimize CI/CD pipeline (requires authentication)."""
        try:
            logger.info(f"Pipeline optimization requested by {current_user.get('username') if current_user else 'anonymous'}")
            agent = CICDOptimizerAgent()
            result = await agent.execute(
                pipeline_config=request.pipeline_config,
                pipeline_logs=request.pipeline_logs,
                metrics=request.metrics,
            )
            return result
        except Exception as e:
            logger.error(f"Pipeline optimization failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/docs/generate")
    async def generate_docs(
        request: DocGenerationRequest,
        current_user: Dict[str, Any] = Depends(get_current_user) if enable_auth else None,
    ):
        """Generate documentation (requires authentication)."""
        try:
            logger.info(f"Doc generation requested by {current_user.get('username') if current_user else 'anonymous'}")
            agent = DocGeneratorAgent()
            result = await agent.execute(
                code=request.code,
                doc_type=request.doc_type,
                language=request.language,
                existing_docs=request.existing_docs,
            )
            return {"documentation": result}
        except Exception as e:
            logger.error(f"Documentation generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/performance/analyze", response_model=PerformanceAnalysisResult)
    async def analyze_performance(
        request: PerformanceAnalysisRequest,
        current_user: Dict[str, Any] = Depends(get_current_user) if enable_auth else None,
    ):
        """Analyze code performance (requires authentication)."""
        try:
            logger.info(f"Performance analysis requested by {current_user.get('username') if current_user else 'anonymous'}")
            agent = PerformanceAnalyzerAgent()
            result = await agent.execute(
                code=request.code,
                language=request.language,
                profiling_data=request.profiling_data,
                metrics=request.metrics,
            )
            return result
        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/anomalies/detect", response_model=AnomalyDetectionResult)
    async def detect_anomalies(
        request: AnomalyDetectionRequest,
        current_user: Dict[str, Any] = Depends(get_current_user) if enable_auth else None,
    ):
        """Detect anomalies in metrics (requires authentication)."""
        try:
            logger.info(f"Anomaly detection requested by {current_user.get('username') if current_user else 'anonymous'}")
            agent = AnomalyDetectorAgent()
            result = await agent.execute(
                metrics=request.metrics,
                baseline=request.baseline,
                context=request.context,
            )
            return result
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/fix/auto", response_model=AutoFixResult)
    async def auto_fix(
        request: AutoFixRequest,
        current_user: Dict[str, Any] = Depends(require_user) if enable_auth else None,
    ):
        """Generate automated fixes for issues (requires USER role)."""
        try:
            logger.info(f"Auto-fix requested by {current_user.get('username') if current_user else 'anonymous'}")
            agent = AutoFixerAgent()
            result = await agent.execute(
                issue_description=request.issue_description,
                logs=request.logs,
                system_state=request.system_state,
                auto_apply=request.auto_apply,
            )
            return result
        except Exception as e:
            logger.error(f"Auto-fix failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/monitoring/analyze", response_model=MonitoringAnalysisResult)
    async def analyze_monitoring(
        request: MonitoringRequest,
        current_user: Dict[str, Any] = Depends(get_current_user) if enable_auth else None,
    ):
        """Analyze monitoring data (requires authentication)."""
        try:
            logger.info(f"Monitoring analysis requested by {current_user.get('username') if current_user else 'anonymous'}")
            agent = IntelligentMonitorAgent()
            result = await agent.execute(
                metrics=request.metrics,
                logs=request.logs,
                historical_data=request.historical_data,
            )
            return result
        except Exception as e:
            logger.error(f"Monitoring analysis failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
