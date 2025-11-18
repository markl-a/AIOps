"""Token usage tracking and budget management for LLM calls."""

import time
import json
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict
import threading

from aiops.core.logger import get_logger

logger = get_logger(__name__)


# Model pricing (per 1M tokens) - Update as needed
MODEL_PRICING = {
    # OpenAI GPT-4
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4-turbo-preview": {"input": 10.0, "output": 30.0},
    "gpt-4-32k": {"input": 60.0, "output": 120.0},

    # OpenAI GPT-3.5
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    "gpt-3.5-turbo-16k": {"input": 3.0, "output": 4.0},

    # Anthropic Claude 3.5
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},

    # Anthropic Claude 3
    "claude-3-opus": {"input": 15.0, "output": 75.0},
    "claude-3-sonnet": {"input": 3.0, "output": 15.0},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
}


@dataclass
class TokenUsage:
    """Token usage record."""
    timestamp: datetime
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    user: Optional[str] = None
    agent: Optional[str] = None
    operation: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class UsageStats:
    """Usage statistics."""
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost: float
    average_tokens_per_request: float
    average_cost_per_request: float
    by_model: Dict[str, Dict[str, Any]]
    by_user: Dict[str, Dict[str, Any]]
    by_agent: Dict[str, Dict[str, Any]]


class TokenTracker:
    """
    Track token usage and costs for LLM calls.

    Features:
    - Real-time token usage tracking
    - Cost calculation based on model pricing
    - Budget limits and alerts
    - Usage statistics and reporting
    - Persistent storage
    """

    def __init__(
        self,
        storage_file: Optional[Path] = None,
        budget_limit: Optional[float] = None,
        auto_save: bool = True,
    ):
        """
        Initialize token tracker.

        Args:
            storage_file: File to persist usage data
            budget_limit: Optional budget limit in USD
            auto_save: Auto-save after each tracking
        """
        self.storage_file = storage_file or Path(".aiops_token_usage.json")
        self.budget_limit = budget_limit
        self.auto_save = auto_save

        # In-memory storage
        self.usage_records: List[TokenUsage] = []
        self.total_cost = 0.0
        self.total_tokens = 0

        # Thread safety
        self._lock = threading.Lock()

        # Load existing data
        self._load_data()

        logger.info(f"Token tracker initialized. Current total cost: ${self.total_cost:.4f}")

    def track(
        self,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        user: Optional[str] = None,
        agent: Optional[str] = None,
        operation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TokenUsage:
        """
        Track token usage for an LLM call.

        Args:
            model: Model name
            provider: Provider name (openai, anthropic, etc.)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            user: Username (if applicable)
            agent: Agent name (if applicable)
            operation: Operation type (if applicable)
            metadata: Additional metadata

        Returns:
            TokenUsage record

        Raises:
            Exception: If budget limit exceeded
        """
        with self._lock:
            # Calculate cost
            pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
            input_cost = (input_tokens / 1_000_000) * pricing["input"]
            output_cost = (output_tokens / 1_000_000) * pricing["output"]
            total_cost = input_cost + output_cost

            # Check budget
            if self.budget_limit and (self.total_cost + total_cost) > self.budget_limit:
                remaining = self.budget_limit - self.total_cost
                logger.error(
                    f"Budget limit exceeded! "
                    f"Current: ${self.total_cost:.4f}, "
                    f"Limit: ${self.budget_limit:.4f}, "
                    f"Remaining: ${remaining:.4f}, "
                    f"Request cost: ${total_cost:.4f}"
                )
                raise Exception(
                    f"Budget limit exceeded. "
                    f"Remaining budget: ${remaining:.4f}, "
                    f"Request cost: ${total_cost:.4f}"
                )

            # Create usage record
            usage = TokenUsage(
                timestamp=datetime.utcnow(),
                model=model,
                provider=provider,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                input_cost=input_cost,
                output_cost=output_cost,
                total_cost=total_cost,
                user=user,
                agent=agent,
                operation=operation,
                metadata=metadata,
            )

            # Update totals
            self.usage_records.append(usage)
            self.total_cost += total_cost
            self.total_tokens += usage.total_tokens

            # Log usage
            logger.info(
                f"Token usage tracked: {model} | "
                f"Tokens: {input_tokens}/{output_tokens} | "
                f"Cost: ${total_cost:.4f} | "
                f"Total cost: ${self.total_cost:.4f}"
            )

            # Auto-save
            if self.auto_save:
                self._save_data()

            return usage

    def get_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> UsageStats:
        """
        Get usage statistics for a time period.

        Args:
            start_time: Start time filter
            end_time: End time filter

        Returns:
            UsageStats object
        """
        with self._lock:
            # Filter records
            records = self.usage_records
            if start_time:
                records = [r for r in records if r.timestamp >= start_time]
            if end_time:
                records = [r for r in records if r.timestamp <= end_time]

            if not records:
                return UsageStats(
                    total_requests=0,
                    total_input_tokens=0,
                    total_output_tokens=0,
                    total_tokens=0,
                    total_cost=0.0,
                    average_tokens_per_request=0.0,
                    average_cost_per_request=0.0,
                    by_model={},
                    by_user={},
                    by_agent={},
                )

            # Calculate aggregates
            total_requests = len(records)
            total_input_tokens = sum(r.input_tokens for r in records)
            total_output_tokens = sum(r.output_tokens for r in records)
            total_tokens = sum(r.total_tokens for r in records)
            total_cost = sum(r.total_cost for r in records)

            # Group by model
            by_model = defaultdict(lambda: {
                "requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0
            })
            for r in records:
                by_model[r.model]["requests"] += 1
                by_model[r.model]["input_tokens"] += r.input_tokens
                by_model[r.model]["output_tokens"] += r.output_tokens
                by_model[r.model]["total_tokens"] += r.total_tokens
                by_model[r.model]["cost"] += r.total_cost

            # Group by user
            by_user = defaultdict(lambda: {
                "requests": 0,
                "tokens": 0,
                "cost": 0.0
            })
            for r in records:
                if r.user:
                    by_user[r.user]["requests"] += 1
                    by_user[r.user]["tokens"] += r.total_tokens
                    by_user[r.user]["cost"] += r.total_cost

            # Group by agent
            by_agent = defaultdict(lambda: {
                "requests": 0,
                "tokens": 0,
                "cost": 0.0
            })
            for r in records:
                if r.agent:
                    by_agent[r.agent]["requests"] += 1
                    by_agent[r.agent]["tokens"] += r.total_tokens
                    by_agent[r.agent]["cost"] += r.total_cost

            return UsageStats(
                total_requests=total_requests,
                total_input_tokens=total_input_tokens,
                total_output_tokens=total_output_tokens,
                total_tokens=total_tokens,
                total_cost=total_cost,
                average_tokens_per_request=total_tokens / total_requests,
                average_cost_per_request=total_cost / total_requests,
                by_model=dict(by_model),
                by_user=dict(by_user),
                by_agent=dict(by_agent),
            )

    def get_budget_status(self) -> Dict[str, Any]:
        """Get budget status."""
        with self._lock:
            if not self.budget_limit:
                return {
                    "budget_enabled": False,
                    "total_cost": self.total_cost,
                }

            remaining = self.budget_limit - self.total_cost
            percentage_used = (self.total_cost / self.budget_limit) * 100

            return {
                "budget_enabled": True,
                "budget_limit": self.budget_limit,
                "total_cost": self.total_cost,
                "remaining": remaining,
                "percentage_used": percentage_used,
                "is_exceeded": self.total_cost >= self.budget_limit,
            }

    def reset(self):
        """Reset all tracking data."""
        with self._lock:
            self.usage_records.clear()
            self.total_cost = 0.0
            self.total_tokens = 0
            self._save_data()
            logger.info("Token tracker reset")

    def _load_data(self):
        """Load usage data from storage."""
        if not self.storage_file.exists():
            logger.info("No existing token usage data found")
            return

        try:
            with open(self.storage_file, "r") as f:
                data = json.load(f)

            self.usage_records = [
                TokenUsage(
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    **{k: v for k, v in r.items() if k != "timestamp"}
                )
                for r in data.get("records", [])
            ]
            self.total_cost = data.get("total_cost", 0.0)
            self.total_tokens = data.get("total_tokens", 0)

            logger.info(
                f"Loaded {len(self.usage_records)} usage records. "
                f"Total cost: ${self.total_cost:.4f}"
            )
        except Exception as e:
            logger.error(f"Failed to load token usage data: {e}")

    def _save_data(self):
        """Save usage data to storage."""
        try:
            data = {
                "total_cost": self.total_cost,
                "total_tokens": self.total_tokens,
                "last_updated": datetime.utcnow().isoformat(),
                "records": [
                    {
                        **asdict(r),
                        "timestamp": r.timestamp.isoformat(),
                    }
                    for r in self.usage_records
                ],
            }

            with open(self.storage_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save token usage data: {e}")


# Global token tracker instance
_global_tracker: Optional[TokenTracker] = None


def get_token_tracker() -> TokenTracker:
    """Get global token tracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = TokenTracker()
    return _global_tracker


def set_token_tracker(tracker: TokenTracker):
    """Set global token tracker instance."""
    global _global_tracker
    _global_tracker = tracker
