"""
Unit tests for Incident Response Agent
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from aiops.agents.incident_response import (
    IncidentResponseAgent,
    IncidentTimeline,
    RootCauseAnalysis,
    RemediationStep,
    IncidentAnalysisResult
)


class TestIncidentTimeline:
    """Tests for IncidentTimeline model"""

    def test_create_timeline(self):
        """Test creating a timeline event"""
        timeline = IncidentTimeline(
            timestamp="2024-01-15T10:30:00Z",
            event_type="alert",
            description="High CPU usage detected",
            severity="critical",
            source="monitoring"
        )
        assert timeline.timestamp == "2024-01-15T10:30:00Z"
        assert timeline.event_type == "alert"
        assert timeline.severity == "critical"

    def test_timeline_event_types(self):
        """Test different event types"""
        for event_type in ["alert", "action", "change", "resolution"]:
            timeline = IncidentTimeline(
                timestamp="2024-01-15T10:30:00Z",
                event_type=event_type,
                description="Test",
                severity="medium",
                source="test"
            )
            assert timeline.event_type == event_type


class TestRootCauseAnalysis:
    """Tests for RootCauseAnalysis model"""

    def test_create_root_cause(self):
        """Test creating a root cause analysis"""
        rca = RootCauseAnalysis(
            likely_cause="Memory leak in user service",
            confidence=85.0,
            contributing_factors=["High traffic", "Insufficient memory limits"],
            evidence=["OOM killer logs", "Memory usage graphs"],
            similar_incidents=["INC-2023-001"]
        )
        assert rca.likely_cause == "Memory leak in user service"
        assert rca.confidence == 85.0
        assert len(rca.contributing_factors) == 2

    def test_root_cause_confidence_range(self):
        """Test confidence values"""
        for confidence in [0.0, 50.0, 100.0]:
            rca = RootCauseAnalysis(
                likely_cause="Test",
                confidence=confidence,
                contributing_factors=[],
                evidence=[],
                similar_incidents=[]
            )
            assert rca.confidence == confidence


class TestRemediationStep:
    """Tests for RemediationStep model"""

    def test_create_remediation_step(self):
        """Test creating a remediation step"""
        step = RemediationStep(
            step_number=1,
            action="Restart user service",
            command="kubectl rollout restart deployment/user-service",
            expected_outcome="Service recovers with fresh pods",
            rollback_plan="kubectl rollout undo deployment/user-service",
            risk_level="low"
        )
        assert step.step_number == 1
        assert step.action == "Restart user service"
        assert step.risk_level == "low"

    def test_remediation_step_optional_fields(self):
        """Test remediation step without optional fields"""
        step = RemediationStep(
            step_number=1,
            action="Manual investigation",
            command=None,
            expected_outcome="Identify issue",
            rollback_plan=None,
            risk_level="low"
        )
        assert step.command is None
        assert step.rollback_plan is None

    def test_remediation_risk_levels(self):
        """Test different risk levels"""
        for risk in ["low", "medium", "high"]:
            step = RemediationStep(
                step_number=1,
                action="Test",
                command=None,
                expected_outcome="Test",
                rollback_plan=None,
                risk_level=risk
            )
            assert step.risk_level == risk


class TestIncidentAnalysisResult:
    """Tests for IncidentAnalysisResult model"""

    def test_create_analysis_result(self):
        """Test creating an analysis result"""
        result = IncidentAnalysisResult(
            incident_id="INC-2024-001",
            severity="critical",
            title="Database outage",
            description="Primary database became unreachable",
            affected_services=["api", "web"],
            timeline=[],
            root_cause=RootCauseAnalysis(
                likely_cause="Disk full",
                confidence=90.0,
                contributing_factors=[],
                evidence=[],
                similar_incidents=[]
            ),
            remediation_steps=[],
            prevention_measures=["Add disk monitoring"],
            estimated_impact={"users_affected": 1000},
            communication_plan=["Notify customers"],
            executive_summary="Database outage due to disk space"
        )
        assert result.incident_id == "INC-2024-001"
        assert result.severity == "critical"
        assert len(result.affected_services) == 2

    def test_analysis_result_severities(self):
        """Test different severity levels"""
        for severity in ["critical", "high", "medium", "low"]:
            result = IncidentAnalysisResult(
                incident_id="test",
                severity=severity,
                title="Test",
                description="Test",
                affected_services=[],
                timeline=[],
                root_cause=RootCauseAnalysis(
                    likely_cause="Test",
                    confidence=50.0,
                    contributing_factors=[],
                    evidence=[],
                    similar_incidents=[]
                ),
                remediation_steps=[],
                prevention_measures=[],
                estimated_impact={},
                communication_plan=[],
                executive_summary="Test"
            )
            assert result.severity == severity


class TestIncidentResponseAgent:
    """Tests for IncidentResponseAgent"""

    @pytest.fixture
    def agent(self):
        """Create agent instance with mocked LLM"""
        agent = IncidentResponseAgent()
        return agent

    @pytest.fixture
    def mock_structured_response(self):
        """Mock structured response from LLM"""
        return {
            "severity": "critical",
            "title": "Database Connection Failure",
            "description": "Primary database connections exhausted",
            "affected_services": ["api-gateway", "user-service"],
            "timeline": [
                {
                    "timestamp": "2024-01-15T10:00:00Z",
                    "event_type": "alert",
                    "description": "High latency detected",
                    "severity": "warning",
                    "source": "monitoring"
                }
            ],
            "root_cause": {
                "likely_cause": "Connection pool exhausted",
                "confidence": 85.0,
                "contributing_factors": ["Increased traffic", "Slow queries"],
                "evidence": ["Connection count at max", "Query duration increased"],
                "similar_incidents": ["INC-2023-050"]
            },
            "remediation_steps": [
                {
                    "step_number": 1,
                    "action": "Increase connection pool size",
                    "command": "kubectl set env deployment/api DB_POOL_SIZE=50",
                    "expected_outcome": "More connections available",
                    "rollback_plan": "kubectl set env deployment/api DB_POOL_SIZE=20",
                    "risk_level": "low"
                }
            ],
            "prevention_measures": ["Add connection pool monitoring", "Implement connection timeouts"],
            "estimated_impact": {"users_affected": 5000, "revenue_impact": 10000},
            "communication_plan": ["Notify support team", "Post status page update"],
            "executive_summary": "Database connection pool exhausted due to traffic spike"
        }

    @pytest.mark.asyncio
    async def test_execute_basic(self, agent, mock_structured_response):
        """Test basic incident execution"""
        agent._generate_structured_response = AsyncMock(return_value=mock_structured_response)

        incident_data = {
            "title": "Database issues",
            "severity": "critical",
            "services": ["api"]
        }

        result = await agent.execute(incident_data)

        assert isinstance(result, IncidentAnalysisResult)
        assert result.severity == "critical"
        assert len(result.affected_services) == 2
        assert result.root_cause.confidence == 85.0

    @pytest.mark.asyncio
    async def test_execute_with_logs(self, agent, mock_structured_response):
        """Test execution with log data"""
        agent._generate_structured_response = AsyncMock(return_value=mock_structured_response)

        incident_data = {"title": "Test incident"}
        logs = [
            "ERROR: Connection refused to database",
            "ERROR: Query timeout after 30s",
            "WARN: Connection pool at 95% capacity"
        ]

        result = await agent.execute(incident_data, logs=logs)

        # Verify logs were passed to prompt builder
        call_args = agent._generate_structured_response.call_args
        prompt = call_args[0][0]
        assert "Logs" in prompt

    @pytest.mark.asyncio
    async def test_execute_with_metrics(self, agent, mock_structured_response):
        """Test execution with metrics data"""
        agent._generate_structured_response = AsyncMock(return_value=mock_structured_response)

        incident_data = {"title": "Test incident"}
        metrics = {
            "cpu_usage": 95.0,
            "memory_usage": 80.0,
            "request_latency_p99": 5000
        }

        result = await agent.execute(incident_data, metrics=metrics)

        call_args = agent._generate_structured_response.call_args
        prompt = call_args[0][0]
        assert "Metrics" in prompt

    @pytest.mark.asyncio
    async def test_execute_with_alerts(self, agent, mock_structured_response):
        """Test execution with alert history"""
        agent._generate_structured_response = AsyncMock(return_value=mock_structured_response)

        incident_data = {"title": "Test incident"}
        alerts = [
            {"name": "HighCPU", "severity": "critical", "message": "CPU at 95%"},
            {"name": "HighLatency", "severity": "high", "message": "P99 > 5s"}
        ]

        result = await agent.execute(incident_data, alerts=alerts)

        call_args = agent._generate_structured_response.call_args
        prompt = call_args[0][0]
        assert "Alert" in prompt

    @pytest.mark.asyncio
    async def test_execute_generates_incident_id(self, agent, mock_structured_response):
        """Test that incident ID is generated if not provided"""
        agent._generate_structured_response = AsyncMock(return_value=mock_structured_response)

        incident_data = {"title": "Test"}  # No incident_id

        result = await agent.execute(incident_data)

        assert result.incident_id.startswith("INC-")

    @pytest.mark.asyncio
    async def test_execute_uses_provided_incident_id(self, agent, mock_structured_response):
        """Test that provided incident ID is used"""
        agent._generate_structured_response = AsyncMock(return_value=mock_structured_response)

        incident_data = {"incident_id": "INC-CUSTOM-123", "title": "Test"}

        result = await agent.execute(incident_data)

        assert result.incident_id == "INC-CUSTOM-123"

    @pytest.mark.asyncio
    async def test_execute_creates_timeline(self, agent, mock_structured_response):
        """Test that timeline is properly created"""
        agent._generate_structured_response = AsyncMock(return_value=mock_structured_response)

        result = await agent.execute({"title": "Test"})

        assert len(result.timeline) == 1
        assert isinstance(result.timeline[0], IncidentTimeline)
        assert result.timeline[0].event_type == "alert"

    @pytest.mark.asyncio
    async def test_execute_creates_remediation_steps(self, agent, mock_structured_response):
        """Test that remediation steps are properly created"""
        agent._generate_structured_response = AsyncMock(return_value=mock_structured_response)

        result = await agent.execute({"title": "Test"})

        assert len(result.remediation_steps) == 1
        assert isinstance(result.remediation_steps[0], RemediationStep)
        assert result.remediation_steps[0].step_number == 1

    def test_build_analysis_prompt_basic(self, agent):
        """Test basic prompt building"""
        incident_data = {"title": "Test", "severity": "high"}

        prompt = agent._build_analysis_prompt(incident_data, None, None, None)

        assert "Incident Analysis" in prompt
        assert "title" in prompt
        assert "severity" in prompt

    def test_build_analysis_prompt_with_logs(self, agent):
        """Test prompt building with logs"""
        incident_data = {"title": "Test"}
        logs = ["ERROR: Something failed"]

        prompt = agent._build_analysis_prompt(incident_data, logs, None, None)

        assert "Logs" in prompt
        assert "ERROR" in prompt

    def test_build_analysis_prompt_with_metrics(self, agent):
        """Test prompt building with metrics"""
        incident_data = {"title": "Test"}
        metrics = {"cpu": 90}

        prompt = agent._build_analysis_prompt(incident_data, None, metrics, None)

        assert "Metrics" in prompt

    def test_build_analysis_prompt_with_alerts(self, agent):
        """Test prompt building with alerts"""
        incident_data = {"title": "Test"}
        alerts = [{"name": "Alert1", "severity": "high", "message": "Issue"}]

        prompt = agent._build_analysis_prompt(incident_data, None, None, alerts)

        assert "Alert" in prompt
        assert "Alert1" in prompt

    def test_build_analysis_prompt_limits_logs(self, agent):
        """Test that logs are limited to 50 entries"""
        incident_data = {"title": "Test"}
        logs = [f"Log entry {i}" for i in range(100)]

        prompt = agent._build_analysis_prompt(incident_data, logs, None, None)

        # Should only include first 50 logs
        assert "Log entry 49" in prompt
        assert "Log entry 50" not in prompt

    def test_format_incident_data(self, agent):
        """Test incident data formatting"""
        data = {"title": "Test", "severity": "critical", "service": "api"}

        formatted = agent._format_incident_data(data)

        assert "title" in formatted
        assert "severity" in formatted
        assert "critical" in formatted

    def test_format_alerts(self, agent):
        """Test alert formatting"""
        alerts = [
            {"name": "Alert1", "severity": "critical", "message": "High CPU"},
            {"name": "Alert2", "severity": "high", "message": "High Memory"}
        ]

        formatted = agent._format_alerts(alerts)

        assert "Alert1" in formatted
        assert "critical" in formatted.lower()
        assert "Alert2" in formatted

    def test_format_alerts_limits_to_20(self, agent):
        """Test that alerts are limited to 20"""
        alerts = [{"name": f"Alert{i}", "severity": "low", "message": "msg"} for i in range(30)]

        formatted = agent._format_alerts(alerts)

        # Should only include first 20
        assert "Alert19" in formatted
        assert "Alert20" not in formatted

    def test_format_alerts_handles_missing_fields(self, agent):
        """Test alert formatting with missing fields"""
        alerts = [{"name": "Alert1"}]  # Missing severity and message

        formatted = agent._format_alerts(alerts)

        assert "Alert1" in formatted
        assert "unknown" in formatted.lower()

    @pytest.mark.asyncio
    async def test_generate_postmortem(self, agent):
        """Test postmortem generation"""
        agent._generate_response = AsyncMock(return_value="# Postmortem Report\n...")

        analysis = IncidentAnalysisResult(
            incident_id="INC-001",
            severity="critical",
            title="Database Outage",
            description="DB went down",
            affected_services=["api", "web"],
            timeline=[],
            root_cause=RootCauseAnalysis(
                likely_cause="Disk full",
                confidence=90.0,
                contributing_factors=[],
                evidence=[],
                similar_incidents=[]
            ),
            remediation_steps=[],
            prevention_measures=["Add monitoring", "Set up alerts"],
            estimated_impact={},
            communication_plan=[],
            executive_summary="DB outage"
        )

        result = await agent.generate_postmortem(analysis)

        assert result is not None
        agent._generate_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_postmortem_with_notes(self, agent):
        """Test postmortem generation with resolution notes"""
        agent._generate_response = AsyncMock(return_value="# Postmortem")

        analysis = IncidentAnalysisResult(
            incident_id="INC-001",
            severity="high",
            title="Test",
            description="Test",
            affected_services=[],
            timeline=[],
            root_cause=RootCauseAnalysis(
                likely_cause="Test",
                confidence=50.0,
                contributing_factors=[],
                evidence=[],
                similar_incidents=[]
            ),
            remediation_steps=[],
            prevention_measures=[],
            estimated_impact={},
            communication_plan=[],
            executive_summary="Test"
        )

        resolution_notes = "Resolved by restarting the service"

        await agent.generate_postmortem(analysis, resolution_notes=resolution_notes)

        call_args = agent._generate_response.call_args
        prompt = call_args[0][0]
        assert resolution_notes in prompt

    def test_agent_initialization_default(self):
        """Test default agent initialization"""
        agent = IncidentResponseAgent()
        assert agent.name == "IncidentResponse"

    def test_agent_initialization_with_params(self):
        """Test agent initialization with custom parameters"""
        agent = IncidentResponseAgent(
            llm_provider="openai",
            model="gpt-4",
            temperature=0.5
        )
        assert agent.name == "IncidentResponse"

    def test_agent_inherits_from_base(self):
        """Test that agent inherits from BaseAgent"""
        from aiops.agents.base_agent import BaseAgent
        agent = IncidentResponseAgent()
        assert isinstance(agent, BaseAgent)


class TestIncidentResponseEdgeCases:
    """Edge case tests for IncidentResponseAgent"""

    @pytest.fixture
    def agent(self):
        return IncidentResponseAgent()

    @pytest.fixture
    def minimal_response(self):
        """Minimal valid response"""
        return {
            "severity": "low",
            "title": "Test",
            "description": "Test",
            "affected_services": [],
            "timeline": [],
            "root_cause": {
                "likely_cause": "Unknown",
                "confidence": 0.0,
                "contributing_factors": [],
                "evidence": [],
                "similar_incidents": []
            },
            "remediation_steps": [],
            "prevention_measures": [],
            "estimated_impact": {},
            "communication_plan": [],
            "executive_summary": "Test"
        }

    @pytest.mark.asyncio
    async def test_empty_incident_data(self, agent, minimal_response):
        """Test with empty incident data"""
        agent._generate_structured_response = AsyncMock(return_value=minimal_response)

        result = await agent.execute({})

        assert result is not None

    @pytest.mark.asyncio
    async def test_empty_logs_list(self, agent, minimal_response):
        """Test with empty logs list"""
        agent._generate_structured_response = AsyncMock(return_value=minimal_response)

        result = await agent.execute({"title": "Test"}, logs=[])

        assert result is not None

    @pytest.mark.asyncio
    async def test_empty_metrics_dict(self, agent, minimal_response):
        """Test with empty metrics dict"""
        agent._generate_structured_response = AsyncMock(return_value=minimal_response)

        result = await agent.execute({"title": "Test"}, metrics={})

        assert result is not None

    @pytest.mark.asyncio
    async def test_empty_alerts_list(self, agent, minimal_response):
        """Test with empty alerts list"""
        agent._generate_structured_response = AsyncMock(return_value=minimal_response)

        result = await agent.execute({"title": "Test"}, alerts=[])

        assert result is not None

    @pytest.mark.asyncio
    async def test_very_long_logs(self, agent, minimal_response):
        """Test with very long logs"""
        agent._generate_structured_response = AsyncMock(return_value=minimal_response)

        long_logs = [f"{'x' * 1000} log entry {i}" for i in range(100)]

        result = await agent.execute({"title": "Test"}, logs=long_logs)

        assert result is not None

    @pytest.mark.asyncio
    async def test_special_characters_in_data(self, agent, minimal_response):
        """Test with special characters in incident data"""
        agent._generate_structured_response = AsyncMock(return_value=minimal_response)

        incident_data = {
            "title": "Error with \"quotes\" and 'apostrophes'",
            "description": "Line 1\nLine 2\tTabbed",
            "code": "<script>alert('xss')</script>"
        }

        result = await agent.execute(incident_data)

        assert result is not None

    @pytest.mark.asyncio
    async def test_unicode_in_data(self, agent, minimal_response):
        """Test with unicode characters"""
        agent._generate_structured_response = AsyncMock(return_value=minimal_response)

        incident_data = {
            "title": "エラー in production 🔥",
            "description": "服务器崩溃了"
        }

        result = await agent.execute(incident_data)

        assert result is not None

    def test_format_incident_data_empty(self, agent):
        """Test formatting empty incident data"""
        formatted = agent._format_incident_data({})
        assert formatted == ""

    def test_format_alerts_empty(self, agent):
        """Test formatting empty alerts"""
        formatted = agent._format_alerts([])
        assert formatted == ""
