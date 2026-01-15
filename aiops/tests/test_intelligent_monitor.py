"""
Unit tests for Intelligent Monitor Agent
"""

import pytest
from unittest.mock import AsyncMock
from aiops.agents.intelligent_monitor import (
    IntelligentMonitorAgent,
    Alert,
    MonitoringInsight,
    MonitoringAnalysisResult
)


class TestAlert:
    """Tests for Alert model"""

    def test_create_alert(self):
        """Test creating an alert"""
        alert = Alert(
            severity="high",
            title="High CPU Usage",
            description="CPU usage exceeded 90% on web-server-1",
            affected_services=["web-server-1", "load-balancer"],
            metrics={"cpu_percent": 92.5, "duration_minutes": 15},
            recommended_actions=["Scale horizontally", "Check for memory leaks"],
            escalation_needed=True,
            noise_score=10.0
        )
        assert alert.severity == "high"
        assert alert.title == "High CPU Usage"
        assert len(alert.affected_services) == 2
        assert alert.escalation_needed is True
        assert alert.noise_score == 10.0

    def test_alert_severities(self):
        """Test different alert severities"""
        for severity in ["critical", "high", "medium", "low", "info"]:
            alert = Alert(
                severity=severity,
                title="Test Alert",
                description="Test",
                affected_services=[],
                metrics={},
                recommended_actions=[],
                escalation_needed=False,
                noise_score=50.0
            )
            assert alert.severity == severity

    def test_alert_with_metrics(self):
        """Test alert with various metrics"""
        metrics = {
            "latency_p99_ms": 2500,
            "error_rate": 5.2,
            "requests_per_second": 1200
        }
        alert = Alert(
            severity="critical",
            title="Latency Spike",
            description="P99 latency exceeded threshold",
            affected_services=["api-gateway"],
            metrics=metrics,
            recommended_actions=["Check backend services"],
            escalation_needed=True,
            noise_score=5.0
        )
        assert alert.metrics["latency_p99_ms"] == 2500
        assert alert.metrics["error_rate"] == 5.2


class TestMonitoringInsight:
    """Tests for MonitoringInsight model"""

    def test_create_insight(self):
        """Test creating a monitoring insight"""
        insight = MonitoringInsight(
            insight_type="trend",
            title="Increasing Memory Usage",
            description="Memory usage has increased 15% over the past week",
            confidence=85.0,
            actionable=True,
            priority="medium"
        )
        assert insight.insight_type == "trend"
        assert insight.confidence == 85.0
        assert insight.actionable is True

    def test_insight_types(self):
        """Test different insight types"""
        for insight_type in ["trend", "correlation", "prediction", "recommendation"]:
            insight = MonitoringInsight(
                insight_type=insight_type,
                title="Test Insight",
                description="Description",
                confidence=75.0,
                actionable=False,
                priority="low"
            )
            assert insight.insight_type == insight_type

    def test_insight_priorities(self):
        """Test different priorities"""
        for priority in ["high", "medium", "low"]:
            insight = MonitoringInsight(
                insight_type="recommendation",
                title="Test",
                description="Test",
                confidence=50.0,
                actionable=True,
                priority=priority
            )
            assert insight.priority == priority


class TestMonitoringAnalysisResult:
    """Tests for MonitoringAnalysisResult model"""

    def test_create_result(self):
        """Test creating analysis result"""
        result = MonitoringAnalysisResult(
            overall_health="healthy",
            health_score=95.0,
            alerts=[],
            insights=[],
            summary="System is operating normally",
            recommendations=[]
        )
        assert result.overall_health == "healthy"
        assert result.health_score == 95.0

    def test_result_with_alerts_and_insights(self):
        """Test result with alerts and insights"""
        alert = Alert(
            severity="medium",
            title="Test Alert",
            description="Test",
            affected_services=["svc-1"],
            metrics={},
            recommended_actions=["Action 1"],
            escalation_needed=False,
            noise_score=20.0
        )
        insight = MonitoringInsight(
            insight_type="trend",
            title="Test Insight",
            description="Test",
            confidence=80.0,
            actionable=True,
            priority="medium"
        )
        result = MonitoringAnalysisResult(
            overall_health="degraded",
            health_score=75.0,
            alerts=[alert],
            insights=[insight],
            summary="Some issues detected",
            recommendations=["Review alert", "Monitor trend"]
        )
        assert len(result.alerts) == 1
        assert len(result.insights) == 1
        assert len(result.recommendations) == 2

    def test_health_states(self):
        """Test different health states"""
        for health in ["healthy", "degraded", "critical"]:
            result = MonitoringAnalysisResult(
                overall_health=health,
                health_score=50.0,
                alerts=[],
                insights=[],
                summary="Test",
                recommendations=[]
            )
            assert result.overall_health == health


class TestIntelligentMonitorAgent:
    """Tests for IntelligentMonitorAgent"""

    @pytest.fixture
    def agent(self):
        """Create agent instance"""
        return IntelligentMonitorAgent()

    @pytest.fixture
    def mock_analysis_result(self):
        """Mock analysis result"""
        return MonitoringAnalysisResult(
            overall_health="degraded",
            health_score=72.0,
            alerts=[
                Alert(
                    severity="high",
                    title="Memory Pressure",
                    description="Memory usage at 92%",
                    affected_services=["db-primary"],
                    metrics={"memory_percent": 92},
                    recommended_actions=["Add memory", "Optimize queries"],
                    escalation_needed=True,
                    noise_score=5.0
                )
            ],
            insights=[
                MonitoringInsight(
                    insight_type="trend",
                    title="Growing Memory Usage",
                    description="Memory has been increasing steadily",
                    confidence=90.0,
                    actionable=True,
                    priority="high"
                )
            ],
            summary="System experiencing memory pressure",
            recommendations=["Scale database vertically", "Review recent deployments"]
        )

    @pytest.mark.asyncio
    async def test_execute_basic(self, agent, mock_analysis_result):
        """Test basic execution"""
        agent._generate_structured_response = AsyncMock(return_value=mock_analysis_result)

        metrics = {
            "cpu_percent": 45,
            "memory_percent": 92,
            "disk_percent": 60
        }
        result = await agent.execute(metrics=metrics)

        assert isinstance(result, MonitoringAnalysisResult)
        assert result.overall_health == "degraded"
        assert len(result.alerts) > 0

    @pytest.mark.asyncio
    async def test_execute_with_logs(self, agent, mock_analysis_result):
        """Test execution with logs"""
        agent._generate_structured_response = AsyncMock(return_value=mock_analysis_result)

        metrics = {"cpu": 50}
        logs = "2024-01-15 ERROR: Connection refused\n2024-01-15 WARN: Timeout"

        result = await agent.execute(metrics=metrics, logs=logs)

        assert result is not None
        call_args = agent._generate_structured_response.call_args
        prompt = call_args[1]["prompt"]
        assert "Logs" in prompt

    @pytest.mark.asyncio
    async def test_execute_with_historical_data(self, agent, mock_analysis_result):
        """Test execution with historical data"""
        agent._generate_structured_response = AsyncMock(return_value=mock_analysis_result)

        current_metrics = {"cpu": 80}
        historical = {"cpu_7d_avg": 50, "cpu_30d_avg": 45}

        result = await agent.execute(
            metrics=current_metrics,
            historical_data=historical
        )

        assert result is not None
        call_args = agent._generate_structured_response.call_args
        prompt = call_args[1]["prompt"]
        assert "Historical" in prompt

    @pytest.mark.asyncio
    async def test_execute_error_handling(self, agent):
        """Test error handling"""
        agent._generate_structured_response = AsyncMock(
            side_effect=Exception("API error")
        )

        result = await agent.execute(metrics={"cpu": 50})

        assert result.overall_health == "unknown"
        assert result.health_score == 0
        assert "failed" in result.summary.lower()

    def test_create_system_prompt(self, agent):
        """Test system prompt creation"""
        prompt = agent._create_system_prompt()

        assert "SRE" in prompt
        assert "Alert" in prompt
        assert "Pattern" in prompt
        assert "Severity" in prompt

    def test_create_user_prompt(self, agent):
        """Test user prompt creation"""
        metrics = {"cpu": 80, "memory": 70}
        prompt = agent._create_user_prompt(metrics)

        assert "Current Metrics" in prompt
        assert "cpu: 80" in prompt or "cpu" in prompt.lower()

    def test_create_user_prompt_with_all_data(self, agent):
        """Test user prompt with all data types"""
        metrics = {"cpu": 80}
        logs = "ERROR: Something failed"
        historical = {"cpu_avg": 50}

        prompt = agent._create_user_prompt(metrics, logs, historical)

        assert "Logs" in prompt
        assert "Historical" in prompt

    def test_format_metrics(self, agent):
        """Test metrics formatting"""
        simple_metrics = {"cpu": 80, "memory": 70}
        formatted = agent._format_metrics(simple_metrics)
        assert "cpu: 80" in formatted

    def test_format_nested_metrics(self, agent):
        """Test formatting nested metrics"""
        nested_metrics = {
            "cpu": {"user": 40, "system": 20},
            "memory": 70
        }
        formatted = agent._format_metrics(nested_metrics)
        assert "cpu:" in formatted
        assert "memory: 70" in formatted

    @pytest.mark.asyncio
    async def test_analyze_alert_quality(self, agent):
        """Test alert quality analysis"""
        agent._generate_response = AsyncMock(
            return_value="Alert quality analysis: 30% false positive rate..."
        )

        alert_history = [
            {"name": "Alert 1", "outcome": "true_positive"},
            {"name": "Alert 2", "outcome": "false_positive"},
            {"name": "Alert 3", "outcome": "true_positive"}
        ]

        result = await agent.analyze_alert_quality(alert_history)

        assert "analysis" in result
        assert "quality_score" in result

    @pytest.mark.asyncio
    async def test_analyze_alert_quality_error(self, agent):
        """Test alert quality analysis error handling"""
        agent._generate_response = AsyncMock(side_effect=Exception("Error"))

        result = await agent.analyze_alert_quality([])

        assert "failed" in result["analysis"].lower()
        assert result["quality_score"] == 0

    @pytest.mark.asyncio
    async def test_generate_capacity_insights(self, agent):
        """Test capacity insights generation"""
        agent._generate_response = AsyncMock(
            return_value="Capacity forecast: 30 days until threshold..."
        )

        resource_usage = {"cpu": 75, "memory": 80, "disk": 60}
        growth_data = {"cpu_growth_rate": 2, "memory_growth_rate": 3}

        result = await agent.generate_capacity_insights(
            resource_usage,
            growth_data
        )

        assert "insights" in result
        assert "urgency" in result

    @pytest.mark.asyncio
    async def test_generate_capacity_insights_error(self, agent):
        """Test capacity insights error handling"""
        agent._generate_response = AsyncMock(side_effect=Exception("Error"))

        result = await agent.generate_capacity_insights({"cpu": 50})

        assert "failed" in result["insights"].lower()
        assert result["urgency"] == "unknown"

    @pytest.mark.asyncio
    async def test_correlate_incidents(self, agent):
        """Test incident correlation"""
        agent._generate_response = AsyncMock(
            return_value="Common root cause: Database connection pool exhaustion"
        )

        incidents = [
            {"title": "API timeout", "time": "10:00"},
            {"title": "DB connection error", "time": "09:58"},
            {"title": "High latency", "time": "10:02"}
        ]

        result = await agent.correlate_incidents(incidents)

        assert "correlations" in result
        assert "common_patterns" in result

    @pytest.mark.asyncio
    async def test_correlate_incidents_error(self, agent):
        """Test incident correlation error handling"""
        agent._generate_response = AsyncMock(side_effect=Exception("Error"))

        result = await agent.correlate_incidents([])

        assert "failed" in result["correlations"].lower()

    def test_agent_initialization(self):
        """Test agent initialization"""
        agent = IntelligentMonitorAgent()
        assert agent.name == "IntelligentMonitorAgent"

    def test_agent_inherits_from_base(self):
        """Test agent inherits from BaseAgent"""
        from aiops.agents.base_agent import BaseAgent
        agent = IntelligentMonitorAgent()
        assert isinstance(agent, BaseAgent)


class TestIntelligentMonitorEdgeCases:
    """Edge case tests"""

    @pytest.fixture
    def agent(self):
        return IntelligentMonitorAgent()

    @pytest.mark.asyncio
    async def test_empty_metrics(self, agent):
        """Test with empty metrics"""
        agent._generate_structured_response = AsyncMock(
            return_value=MonitoringAnalysisResult(
                overall_health="healthy",
                health_score=100.0,
                alerts=[],
                insights=[],
                summary="No data available",
                recommendations=[]
            )
        )

        result = await agent.execute(metrics={})
        assert result is not None

    @pytest.mark.asyncio
    async def test_many_alerts(self, agent):
        """Test with many alerts"""
        alerts = [
            Alert(
                severity="medium",
                title=f"Alert {i}",
                description=f"Description {i}",
                affected_services=[f"service-{i}"],
                metrics={},
                recommended_actions=[],
                escalation_needed=False,
                noise_score=30.0
            )
            for i in range(20)
        ]

        agent._generate_structured_response = AsyncMock(
            return_value=MonitoringAnalysisResult(
                overall_health="degraded",
                health_score=30.0,
                alerts=alerts,
                insights=[],
                summary="Many issues detected",
                recommendations=["Review all alerts"]
            )
        )

        result = await agent.execute(metrics={"status": "bad"})
        assert len(result.alerts) == 20

    @pytest.mark.asyncio
    async def test_critical_health(self, agent):
        """Test critical health state"""
        agent._generate_structured_response = AsyncMock(
            return_value=MonitoringAnalysisResult(
                overall_health="critical",
                health_score=5.0,
                alerts=[
                    Alert(
                        severity="critical",
                        title="System Down",
                        description="All services unreachable",
                        affected_services=["all"],
                        metrics={},
                        recommended_actions=["Immediate intervention required"],
                        escalation_needed=True,
                        noise_score=0.0
                    )
                ],
                insights=[],
                summary="System is in critical state",
                recommendations=["Escalate immediately"]
            )
        )

        result = await agent.execute(metrics={"status": "down"})

        assert result.overall_health == "critical"
        assert result.health_score < 10
        assert result.alerts[0].escalation_needed is True

    @pytest.mark.asyncio
    async def test_long_logs(self, agent):
        """Test with very long logs"""
        agent._generate_structured_response = AsyncMock(
            return_value=MonitoringAnalysisResult(
                overall_health="healthy",
                health_score=90.0,
                alerts=[],
                insights=[],
                summary="OK",
                recommendations=[]
            )
        )

        long_logs = "Log entry\n" * 5000  # Very long logs

        result = await agent.execute(
            metrics={"cpu": 50},
            logs=long_logs
        )

        assert result is not None
        # Logs should be truncated in prompt
        call_args = agent._generate_structured_response.call_args
        prompt = call_args[1]["prompt"]
        assert len(prompt) < len(long_logs)

    @pytest.mark.asyncio
    async def test_alert_quality_many_alerts(self, agent):
        """Test alert quality analysis with many alerts"""
        agent._generate_response = AsyncMock(return_value="Analysis complete")

        # More than 50 alerts (limit in the method)
        alert_history = [{"name": f"Alert {i}"} for i in range(100)]

        result = await agent.analyze_alert_quality(alert_history)

        # Should only process first 50
        call_args = agent._generate_response.call_args
        prompt = call_args[0][0]
        assert "50 more alerts" in prompt
