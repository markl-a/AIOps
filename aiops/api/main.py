"""FastAPI application for AIOps framework."""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio

from aiops import __version__
from aiops.core.logger import setup_logger, get_logger
from aiops.agents.code_reviewer import CodeReviewAgent, CodeReviewResult
from aiops.agents.test_generator import TestGeneratorAgent, TestSuite
from aiops.agents.log_analyzer import LogAnalyzerAgent, LogAnalysisResult
from aiops.agents.cicd_optimizer import CICDOptimizerAgent, PipelineOptimization
from aiops.agents.doc_generator import DocGeneratorAgent
from aiops.agents.performance_analyzer import PerformanceAnalyzerAgent, PerformanceAnalysisResult
from aiops.agents.anomaly_detector import AnomalyDetectorAgent, AnomalyDetectionResult
from aiops.agents.auto_fixer import AutoFixerAgent, AutoFixResult
from aiops.agents.intelligent_monitor import IntelligentMonitorAgent, MonitoringAnalysisResult

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create FastAPI application."""
    setup_logger()

    app = FastAPI(
        title="AIOps Framework API",
        description="AI-powered DevOps automation API",
        version=__version__,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

    # Routes
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "AIOps Framework API",
            "version": __version__,
            "status": "running",
        }

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.post("/api/v1/code/review", response_model=CodeReviewResult)
    async def review_code(request: CodeReviewRequest):
        """Review code and provide feedback."""
        try:
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
    async def generate_tests(request: TestGenerationRequest):
        """Generate tests for code."""
        try:
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
    async def analyze_logs(request: LogAnalysisRequest):
        """Analyze logs and provide insights."""
        try:
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
    async def optimize_pipeline(request: PipelineOptimizationRequest):
        """Optimize CI/CD pipeline."""
        try:
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
    async def generate_docs(request: DocGenerationRequest):
        """Generate documentation."""
        try:
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
    async def analyze_performance(request: PerformanceAnalysisRequest):
        """Analyze code performance."""
        try:
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
    async def detect_anomalies(request: AnomalyDetectionRequest):
        """Detect anomalies in metrics."""
        try:
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
    async def auto_fix(request: AutoFixRequest):
        """Generate automated fixes for issues."""
        try:
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
    async def analyze_monitoring(request: MonitoringRequest):
        """Analyze monitoring data."""
        try:
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
