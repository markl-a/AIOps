"""
Unit tests for Configuration Drift Detector Agent
"""

import pytest
from aiops.agents.config_drift_detector import (
    ConfigurationDriftDetector,
    ConfigDrift,
    DriftDetectionResult
)


class TestConfigDrift:
    """Tests for ConfigDrift model"""

    def test_create_drift(self):
        """Test creating a config drift"""
        drift = ConfigDrift(
            config_key="database_url",
            expected_value="prod-db.example.com",
            actual_value="staging-db.example.com",
            environment="staging",
            severity="critical",
            impact="Database connection mismatch",
            recommendation="Align database URLs"
        )
        assert drift.config_key == "database_url"
        assert drift.severity == "critical"

    def test_drift_severities(self):
        """Test different severity levels"""
        for severity in ["critical", "high", "medium", "low"]:
            drift = ConfigDrift(
                config_key="test",
                expected_value="a",
                actual_value="b",
                environment="staging",
                severity=severity,
                impact="Test",
                recommendation="Fix"
            )
            assert drift.severity == severity

    def test_drift_with_none_values(self):
        """Test drift with None values"""
        drift = ConfigDrift(
            config_key="missing_key",
            expected_value="some_value",
            actual_value=None,
            environment="staging",
            severity="high",
            impact="Missing config",
            recommendation="Add config"
        )
        assert drift.actual_value is None


class TestDriftDetectionResult:
    """Tests for DriftDetectionResult model"""

    def test_create_result(self):
        """Test creating drift detection result"""
        result = DriftDetectionResult(
            baseline_environment="production",
            compared_environment="staging",
            total_configs=10,
            drifts_detected=2,
            drifts=[],
            drift_score=80.0,
            compliance_status="drifted",
            summary="2 drifts found",
            recommendations=["Fix drifts"]
        )
        assert result.total_configs == 10
        assert result.drift_score == 80.0
        assert result.compliance_status == "drifted"

    def test_result_compliance_statuses(self):
        """Test different compliance statuses"""
        for status in ["compliant", "drifted", "critical_drift"]:
            result = DriftDetectionResult(
                baseline_environment="prod",
                compared_environment="staging",
                total_configs=5,
                drifts_detected=0,
                drifts=[],
                drift_score=100.0,
                compliance_status=status,
                summary="Test",
                recommendations=[]
            )
            assert result.compliance_status == status


class TestConfigurationDriftDetector:
    """Tests for ConfigurationDriftDetector"""

    @pytest.fixture
    def detector(self):
        """Create detector instance"""
        return ConfigurationDriftDetector()

    @pytest.mark.asyncio
    async def test_detect_drift_no_drifts(self, detector):
        """Test detection with no drifts"""
        baseline = {"key1": "value1", "key2": "value2"}
        target = {"key1": "value1", "key2": "value2"}

        result = await detector.detect_drift(baseline, target)

        assert result.drifts_detected == 0
        assert result.drift_score == 100.0
        assert result.compliance_status == "compliant"

    @pytest.mark.asyncio
    async def test_detect_drift_value_mismatch(self, detector):
        """Test detection of value mismatch"""
        baseline = {"config_a": "value1"}
        target = {"config_a": "value2"}

        result = await detector.detect_drift(baseline, target)

        assert result.drifts_detected == 1
        assert result.drifts[0].config_key == "config_a"
        assert result.drifts[0].expected_value == "value1"
        assert result.drifts[0].actual_value == "value2"

    @pytest.mark.asyncio
    async def test_detect_drift_missing_in_target(self, detector):
        """Test detection of missing config in target"""
        baseline = {"key1": "value1", "key2": "value2"}
        target = {"key1": "value1"}

        result = await detector.detect_drift(baseline, target)

        assert result.drifts_detected == 1
        missing_drift = result.drifts[0]
        assert missing_drift.config_key == "key2"
        assert missing_drift.actual_value is None

    @pytest.mark.asyncio
    async def test_detect_drift_extra_in_target(self, detector):
        """Test detection of extra config in target"""
        baseline = {"key1": "value1"}
        target = {"key1": "value1", "extra_key": "extra_value"}

        result = await detector.detect_drift(baseline, target)

        assert result.drifts_detected == 1
        extra_drift = result.drifts[0]
        assert extra_drift.config_key == "extra_key"
        assert extra_drift.expected_value is None

    @pytest.mark.asyncio
    async def test_detect_drift_critical_key(self, detector):
        """Test critical key detection"""
        baseline = {"database_url": "prod-db"}
        target = {"database_url": "staging-db"}

        result = await detector.detect_drift(baseline, target)

        assert result.drifts_detected == 1
        assert result.drifts[0].severity == "critical"
        assert result.compliance_status == "critical_drift"

    @pytest.mark.asyncio
    async def test_detect_drift_custom_critical_keys(self, detector):
        """Test with custom critical keys"""
        baseline = {"my_critical_config": "value1"}
        target = {"my_critical_config": "value2"}

        result = await detector.detect_drift(
            baseline, target,
            critical_keys=["my_critical"]
        )

        assert result.drifts[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_detect_drift_numeric_difference(self, detector):
        """Test numeric value difference detection"""
        baseline = {"timeout": 100}
        target = {"timeout": 200}

        result = await detector.detect_drift(baseline, target)

        assert result.drifts_detected == 1
        # 100% difference should be high severity
        assert result.drifts[0].severity == "high"

    @pytest.mark.asyncio
    async def test_detect_drift_small_numeric_difference(self, detector):
        """Test small numeric difference detection"""
        baseline = {"timeout": 100}
        target = {"timeout": 110}

        result = await detector.detect_drift(baseline, target)

        assert result.drifts_detected == 1
        # 10% difference should be medium severity
        assert result.drifts[0].severity == "medium"

    @pytest.mark.asyncio
    async def test_detect_drift_zero_baseline(self, detector):
        """Test with zero baseline value"""
        baseline = {"count": 0}
        target = {"count": 10}

        result = await detector.detect_drift(baseline, target)

        assert result.drifts_detected == 1
        # 100% difference when baseline is 0
        assert result.drifts[0].severity == "high"

    @pytest.mark.asyncio
    async def test_detect_drift_environment_names(self, detector):
        """Test custom environment names"""
        baseline = {"key": "value1"}
        target = {"key": "value2"}

        result = await detector.detect_drift(
            baseline, target,
            baseline_env="main",
            target_env="feature-branch"
        )

        assert result.baseline_environment == "main"
        assert result.compared_environment == "feature-branch"

    @pytest.mark.asyncio
    async def test_drift_score_calculation(self, detector):
        """Test drift score calculation"""
        # 1 out of 4 configs drifted = 75% score
        baseline = {"a": 1, "b": 2, "c": 3, "d": 4}
        target = {"a": 1, "b": 2, "c": 3, "d": 5}

        result = await detector.detect_drift(baseline, target)

        assert result.drift_score == 75.0

    @pytest.mark.asyncio
    async def test_empty_configs(self, detector):
        """Test with empty configurations"""
        result = await detector.detect_drift({}, {})

        assert result.drifts_detected == 0
        assert result.drift_score == 100.0
        assert result.compliance_status == "compliant"

    def test_generate_recommendations_no_drifts(self, detector):
        """Test recommendations with no drifts"""
        recommendations = detector._generate_recommendations([], "prod", "staging")
        assert len(recommendations) == 0

    def test_generate_recommendations_critical_drifts(self, detector):
        """Test recommendations with critical drifts"""
        drifts = [
            ConfigDrift(
                config_key="database_url",
                expected_value="a",
                actual_value="b",
                environment="staging",
                severity="critical",
                impact="Bad",
                recommendation="Fix"
            )
        ]
        recommendations = detector._generate_recommendations(drifts, "prod", "staging")

        assert len(recommendations) > 0
        assert any("URGENT" in r for r in recommendations)

    def test_generate_recommendations_database_drift(self, detector):
        """Test recommendations for database config drift"""
        drifts = [
            ConfigDrift(
                config_key="database_connection",
                expected_value="a",
                actual_value="b",
                environment="staging",
                severity="high",
                impact="DB mismatch",
                recommendation="Fix"
            )
        ]
        recommendations = detector._generate_recommendations(drifts, "prod", "staging")

        assert any("database" in r.lower() for r in recommendations)

    def test_generate_recommendations_secret_drift(self, detector):
        """Test recommendations for secret config drift"""
        drifts = [
            ConfigDrift(
                config_key="api_secret_key",
                expected_value="a",
                actual_value="b",
                environment="staging",
                severity="high",
                impact="Secret mismatch",
                recommendation="Fix"
            )
        ]
        recommendations = detector._generate_recommendations(drifts, "prod", "staging")

        assert any("secret" in r.lower() for r in recommendations)

    def test_generate_recommendations_max_six(self, detector):
        """Test that recommendations are limited to 6"""
        drifts = [
            ConfigDrift(
                config_key=f"key_{i}",
                expected_value="a",
                actual_value="b",
                environment="staging",
                severity="critical",
                impact="Bad",
                recommendation="Fix"
            )
            for i in range(10)
        ]
        recommendations = detector._generate_recommendations(drifts, "prod", "staging")

        assert len(recommendations) <= 6

    def test_generate_summary_compliant(self, detector):
        """Test summary for compliant state"""
        summary = detector._generate_summary("prod", "staging", 10, 0, 100.0, 0)

        assert "prod" in summary
        assert "staging" in summary
        assert "100.0" in summary
        assert "well-aligned" in summary

    def test_generate_summary_minor_drift(self, detector):
        """Test summary for minor drift"""
        summary = detector._generate_summary("prod", "staging", 10, 1, 90.0, 0)

        assert "Minor" in summary or "review" in summary.lower()

    def test_generate_summary_significant_drift(self, detector):
        """Test summary for significant drift"""
        summary = detector._generate_summary("prod", "staging", 10, 5, 50.0, 0)

        assert "remediation" in summary.lower() or "Significant" in summary

    def test_generate_summary_critical_drift(self, detector):
        """Test summary with critical drifts"""
        summary = detector._generate_summary("prod", "staging", 10, 3, 70.0, 2)

        assert "CRITICAL" in summary
        assert "2" in summary

    def test_detector_initialization(self):
        """Test detector initialization"""
        detector = ConfigurationDriftDetector()
        assert detector.llm_factory is None

        mock_factory = object()
        detector_with_factory = ConfigurationDriftDetector(llm_factory=mock_factory)
        assert detector_with_factory.llm_factory is mock_factory


class TestConfigDriftEdgeCases:
    """Edge case tests"""

    @pytest.fixture
    def detector(self):
        return ConfigurationDriftDetector()

    @pytest.mark.asyncio
    async def test_nested_config_comparison(self, detector):
        """Test with nested configurations (compared as-is)"""
        baseline = {"nested": {"a": 1, "b": 2}}
        target = {"nested": {"a": 1, "b": 3}}

        result = await detector.detect_drift(baseline, target)

        # Nested objects compared as whole
        assert result.drifts_detected == 1

    @pytest.mark.asyncio
    async def test_list_config_comparison(self, detector):
        """Test with list configurations"""
        baseline = {"list_config": [1, 2, 3]}
        target = {"list_config": [1, 2, 3, 4]}

        result = await detector.detect_drift(baseline, target)

        assert result.drifts_detected == 1

    @pytest.mark.asyncio
    async def test_bool_config_comparison(self, detector):
        """Test with boolean configurations"""
        baseline = {"enabled": True}
        target = {"enabled": False}

        result = await detector.detect_drift(baseline, target)

        assert result.drifts_detected == 1

    @pytest.mark.asyncio
    async def test_none_value_comparison(self, detector):
        """Test comparing None values"""
        baseline = {"optional": None}
        target = {"optional": "value"}

        result = await detector.detect_drift(baseline, target)

        assert result.drifts_detected == 1

    @pytest.mark.asyncio
    async def test_special_characters_in_keys(self, detector):
        """Test config keys with special characters"""
        baseline = {"config.key.with.dots": "value1"}
        target = {"config.key.with.dots": "value2"}

        result = await detector.detect_drift(baseline, target)

        assert result.drifts_detected == 1
        assert result.drifts[0].config_key == "config.key.with.dots"

    @pytest.mark.asyncio
    async def test_unicode_values(self, detector):
        """Test with unicode values"""
        baseline = {"message": "Hello 世界"}
        target = {"message": "Hello World"}

        result = await detector.detect_drift(baseline, target)

        assert result.drifts_detected == 1

    @pytest.mark.asyncio
    async def test_large_config_set(self, detector):
        """Test with large configuration set"""
        baseline = {f"key_{i}": f"value_{i}" for i in range(100)}
        target = {f"key_{i}": f"value_{i}" for i in range(100)}
        target["key_50"] = "different"

        result = await detector.detect_drift(baseline, target)

        assert result.total_configs == 100
        assert result.drifts_detected == 1

    @pytest.mark.asyncio
    async def test_empty_string_vs_none(self, detector):
        """Test empty string vs None comparison"""
        baseline = {"empty": ""}
        target = {"empty": None}

        result = await detector.detect_drift(baseline, target)

        assert result.drifts_detected == 1
