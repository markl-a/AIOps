"""Comprehensive tests for token_tracker module."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from aiops.core.token_tracker import (
    TokenTracker,
    TokenUsage,
    UsageStats,
    MODEL_PRICING,
    get_token_tracker,
    set_token_tracker,
)


class TestModelPricing:
    """Tests for model pricing configuration."""

    def test_gpt4_pricing_exists(self):
        """Test that GPT-4 pricing is defined."""
        assert "gpt-4" in MODEL_PRICING
        assert "input" in MODEL_PRICING["gpt-4"]
        assert "output" in MODEL_PRICING["gpt-4"]

    def test_claude_pricing_exists(self):
        """Test that Claude pricing is defined."""
        assert "claude-3-5-sonnet" in MODEL_PRICING

    def test_pricing_values_positive(self):
        """Test all pricing values are positive."""
        for model, pricing in MODEL_PRICING.items():
            assert pricing["input"] >= 0, f"{model} input price should be >= 0"
            assert pricing["output"] >= 0, f"{model} output price should be >= 0"


class TestTokenUsage:
    """Tests for TokenUsage dataclass."""

    def test_create_token_usage(self):
        """Test creating a TokenUsage instance."""
        usage = TokenUsage(
            timestamp=datetime.utcnow(),
            model="gpt-4",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            input_cost=0.003,
            output_cost=0.003,
            total_cost=0.006,
        )
        assert usage.model == "gpt-4"
        assert usage.total_tokens == 150

    def test_optional_fields(self):
        """Test that optional fields default to None."""
        usage = TokenUsage(
            timestamp=datetime.utcnow(),
            model="gpt-4",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            input_cost=0.003,
            output_cost=0.003,
            total_cost=0.006,
        )
        assert usage.user is None
        assert usage.agent is None
        assert usage.operation is None
        assert usage.metadata is None


class TestTokenTracker:
    """Tests for TokenTracker class."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "token_usage.json"

    @pytest.fixture
    def tracker(self, temp_storage):
        """Create TokenTracker instance."""
        return TokenTracker(storage_file=temp_storage, auto_save=False)

    def test_init(self, temp_storage):
        """Test tracker initialization."""
        tracker = TokenTracker(storage_file=temp_storage)
        assert tracker.total_cost == 0.0
        assert tracker.total_tokens == 0
        assert len(tracker.usage_records) == 0

    def test_init_with_budget(self, temp_storage):
        """Test tracker with budget limit."""
        tracker = TokenTracker(storage_file=temp_storage, budget_limit=10.0)
        assert tracker.budget_limit == 10.0

    def test_track_basic(self, tracker):
        """Test basic token tracking."""
        usage = tracker.track(
            model="gpt-4",
            provider="openai",
            input_tokens=1000,
            output_tokens=500,
        )

        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        assert usage.total_tokens == 1500
        assert len(tracker.usage_records) == 1

    def test_track_with_metadata(self, tracker):
        """Test tracking with optional metadata."""
        usage = tracker.track(
            model="gpt-4",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            user="test_user",
            agent="code_reviewer",
            operation="review",
            metadata={"repo": "test-repo"},
        )

        assert usage.user == "test_user"
        assert usage.agent == "code_reviewer"
        assert usage.metadata == {"repo": "test-repo"}

    def test_cost_calculation(self, tracker):
        """Test that costs are calculated correctly."""
        usage = tracker.track(
            model="gpt-4",
            provider="openai",
            input_tokens=1_000_000,  # 1M tokens
            output_tokens=1_000_000,
        )

        # GPT-4: input=$30/1M, output=$60/1M
        assert usage.input_cost == pytest.approx(30.0, rel=0.01)
        assert usage.output_cost == pytest.approx(60.0, rel=0.01)
        assert usage.total_cost == pytest.approx(90.0, rel=0.01)

    def test_cost_for_unknown_model(self, tracker):
        """Test cost calculation for unknown model."""
        usage = tracker.track(
            model="unknown-model",
            provider="unknown",
            input_tokens=1000,
            output_tokens=500,
        )

        # Unknown model should have zero cost
        assert usage.total_cost == 0.0

    def test_total_tracking(self, tracker):
        """Test that totals are accumulated."""
        tracker.track(model="gpt-4", provider="openai", input_tokens=100, output_tokens=50)
        tracker.track(model="gpt-4", provider="openai", input_tokens=200, output_tokens=100)

        assert tracker.total_tokens == 450  # 150 + 300
        assert len(tracker.usage_records) == 2

    def test_budget_limit_exceeded(self, temp_storage):
        """Test that budget limit raises exception."""
        tracker = TokenTracker(storage_file=temp_storage, budget_limit=0.001)

        with pytest.raises(Exception) as exc_info:
            tracker.track(
                model="gpt-4",
                provider="openai",
                input_tokens=1_000_000,
                output_tokens=1_000_000,
            )

        assert "Budget limit exceeded" in str(exc_info.value)

    def test_budget_allows_within_limit(self, temp_storage):
        """Test that requests within budget are allowed."""
        tracker = TokenTracker(storage_file=temp_storage, budget_limit=100.0)

        # This should not raise
        usage = tracker.track(
            model="gpt-4",
            provider="openai",
            input_tokens=1000,
            output_tokens=500,
        )
        assert usage is not None


class TestTokenTrackerStats:
    """Tests for usage statistics."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "token_usage.json"

    @pytest.fixture
    def tracker_with_data(self, temp_storage):
        """Create tracker with some data."""
        tracker = TokenTracker(storage_file=temp_storage, auto_save=False)

        # Add some usage records
        tracker.track(model="gpt-4", provider="openai",
                     input_tokens=1000, output_tokens=500, user="user1", agent="agent1")
        tracker.track(model="gpt-3.5-turbo", provider="openai",
                     input_tokens=2000, output_tokens=1000, user="user1", agent="agent2")
        tracker.track(model="gpt-4", provider="openai",
                     input_tokens=500, output_tokens=250, user="user2", agent="agent1")

        return tracker

    def test_get_stats_basic(self, tracker_with_data):
        """Test basic statistics retrieval."""
        stats = tracker_with_data.get_stats()

        assert stats.total_requests == 3
        assert stats.total_input_tokens == 3500
        assert stats.total_output_tokens == 1750
        assert stats.total_tokens == 5250

    def test_get_stats_by_model(self, tracker_with_data):
        """Test statistics grouped by model."""
        stats = tracker_with_data.get_stats()

        assert "gpt-4" in stats.by_model
        assert stats.by_model["gpt-4"]["requests"] == 2
        assert "gpt-3.5-turbo" in stats.by_model
        assert stats.by_model["gpt-3.5-turbo"]["requests"] == 1

    def test_get_stats_by_user(self, tracker_with_data):
        """Test statistics grouped by user."""
        stats = tracker_with_data.get_stats()

        assert "user1" in stats.by_user
        assert stats.by_user["user1"]["requests"] == 2
        assert "user2" in stats.by_user
        assert stats.by_user["user2"]["requests"] == 1

    def test_get_stats_by_agent(self, tracker_with_data):
        """Test statistics grouped by agent."""
        stats = tracker_with_data.get_stats()

        assert "agent1" in stats.by_agent
        assert stats.by_agent["agent1"]["requests"] == 2
        assert "agent2" in stats.by_agent
        assert stats.by_agent["agent2"]["requests"] == 1

    def test_get_stats_empty(self, temp_storage):
        """Test statistics with no data."""
        tracker = TokenTracker(storage_file=temp_storage, auto_save=False)
        stats = tracker.get_stats()

        assert stats.total_requests == 0
        assert stats.total_cost == 0.0
        assert stats.average_tokens_per_request == 0.0

    def test_get_stats_with_time_filter(self, tracker_with_data):
        """Test statistics with time filter."""
        future = datetime.utcnow() + timedelta(days=1)
        stats = tracker_with_data.get_stats(start_time=future)

        # No records should match
        assert stats.total_requests == 0


class TestTokenTrackerBudget:
    """Tests for budget status."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "token_usage.json"

    def test_budget_status_disabled(self, temp_storage):
        """Test budget status when no budget set."""
        tracker = TokenTracker(storage_file=temp_storage)
        status = tracker.get_budget_status()

        assert status["budget_enabled"] is False

    def test_budget_status_enabled(self, temp_storage):
        """Test budget status when budget is set."""
        tracker = TokenTracker(storage_file=temp_storage, budget_limit=100.0)
        status = tracker.get_budget_status()

        assert status["budget_enabled"] is True
        assert status["budget_limit"] == 100.0
        assert status["remaining"] == 100.0
        assert status["percentage_used"] == 0.0

    def test_budget_status_after_usage(self, temp_storage):
        """Test budget status after some usage."""
        tracker = TokenTracker(storage_file=temp_storage, budget_limit=100.0, auto_save=False)
        tracker.track(model="gpt-3.5-turbo", provider="openai",
                     input_tokens=100_000, output_tokens=50_000)

        status = tracker.get_budget_status()
        assert status["remaining"] < 100.0
        assert status["percentage_used"] > 0


class TestTokenTrackerPersistence:
    """Tests for data persistence."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "token_usage.json"

    def test_save_and_load(self, temp_storage):
        """Test saving and loading data."""
        # Create and populate tracker
        tracker1 = TokenTracker(storage_file=temp_storage, auto_save=True)
        tracker1.track(model="gpt-4", provider="openai", input_tokens=1000, output_tokens=500)

        # Create new tracker that should load data
        tracker2 = TokenTracker(storage_file=temp_storage)

        assert tracker2.total_tokens == 1500
        assert len(tracker2.usage_records) == 1

    def test_load_from_nonexistent_file(self, temp_storage):
        """Test loading from file that doesn't exist."""
        tracker = TokenTracker(storage_file=temp_storage)
        assert len(tracker.usage_records) == 0

    def test_reset(self, temp_storage):
        """Test reset clears all data."""
        tracker = TokenTracker(storage_file=temp_storage, auto_save=True)
        tracker.track(model="gpt-4", provider="openai", input_tokens=1000, output_tokens=500)
        tracker.reset()

        assert tracker.total_cost == 0.0
        assert tracker.total_tokens == 0
        assert len(tracker.usage_records) == 0


class TestGlobalTracker:
    """Tests for global tracker functions."""

    @pytest.fixture(autouse=True)
    def reset_global_tracker(self):
        """Reset global tracker before each test."""
        import aiops.core.token_tracker as module
        module._global_tracker = None
        yield
        module._global_tracker = None

    def test_get_token_tracker_creates_default(self):
        """Test that get_token_tracker creates a default instance."""
        tracker = get_token_tracker()
        assert isinstance(tracker, TokenTracker)

    def test_get_token_tracker_returns_same_instance(self):
        """Test that get_token_tracker returns the same instance."""
        tracker1 = get_token_tracker()
        tracker2 = get_token_tracker()
        assert tracker1 is tracker2

    def test_set_token_tracker(self):
        """Test setting a custom tracker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom = TokenTracker(storage_file=Path(tmpdir) / "custom.json")
            set_token_tracker(custom)

            retrieved = get_token_tracker()
            assert retrieved is custom


class TestThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_tracking(self):
        """Test concurrent tracking operations."""
        import threading

        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = TokenTracker(
                storage_file=Path(tmpdir) / "tokens.json",
                auto_save=False,
            )

            errors = []

            def track_tokens(n):
                try:
                    for i in range(10):
                        tracker.track(
                            model="gpt-4",
                            provider="openai",
                            input_tokens=100,
                            output_tokens=50,
                            user=f"user_{n}",
                        )
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=track_tokens, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0
            assert len(tracker.usage_records) == 50
            assert tracker.total_tokens == 50 * 150


class TestEdgeCases:
    """Edge case tests."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "token_usage.json"

    def test_zero_tokens(self, temp_storage):
        """Test tracking zero tokens."""
        tracker = TokenTracker(storage_file=temp_storage, auto_save=False)
        usage = tracker.track(model="gpt-4", provider="openai",
                             input_tokens=0, output_tokens=0)

        assert usage.total_tokens == 0
        assert usage.total_cost == 0.0

    def test_very_large_token_count(self, temp_storage):
        """Test tracking very large token counts."""
        tracker = TokenTracker(storage_file=temp_storage, auto_save=False)
        usage = tracker.track(
            model="gpt-4",
            provider="openai",
            input_tokens=100_000_000,
            output_tokens=100_000_000,
        )

        assert usage.total_tokens == 200_000_000

    def test_empty_user_and_agent(self, temp_storage):
        """Test tracking without user or agent."""
        tracker = TokenTracker(storage_file=temp_storage, auto_save=False)
        stats = tracker.get_stats()

        # Empty by_user and by_agent
        assert len(stats.by_user) == 0
        assert len(stats.by_agent) == 0

    def test_corrupted_storage_file(self, temp_storage):
        """Test handling of corrupted storage file."""
        # Write corrupted JSON
        with open(temp_storage, "w") as f:
            f.write("not valid json{{{")

        # Should not raise, just start fresh
        tracker = TokenTracker(storage_file=temp_storage)
        assert len(tracker.usage_records) == 0
