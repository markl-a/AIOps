"""Agent Registry for lazy loading of AI agents.

This module provides a centralized registry for all AI agents, enabling:
- Lazy loading of agent classes (only load when first used)
- Reduced startup time (no upfront imports of all agents)
- Runtime agent discovery and management
- Memory efficiency (only loaded agents consume memory)

Usage:
    from aiops.agents.registry import agent_registry

    # Get an agent instance (lazy loaded)
    code_reviewer = await agent_registry.get("code_reviewer")
    result = await code_reviewer.execute(code="...")

    # List available agents
    agents = agent_registry.list_agents()
"""

import importlib
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field
from aiops.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentInfo:
    """Information about a registered agent."""
    name: str
    module_path: str
    class_name: str
    description: str = ""
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    is_loaded: bool = False


class AgentRegistry:
    """
    Centralized registry for AI agents with lazy loading support.

    Agents are registered with their module path and class name,
    but are only imported and instantiated when first requested.
    """

    def __init__(self):
        """Initialize the agent registry."""
        self._registry: Dict[str, AgentInfo] = {}
        self._instances: Dict[str, Any] = {}
        self._classes: Dict[str, Type] = {}

        # Auto-register built-in agents
        self._register_builtin_agents()

    def _register_builtin_agents(self):
        """Register all built-in agents."""
        # Code Quality & Review
        self.register(
            name="code_reviewer",
            module_path="aiops.agents.code_reviewer",
            class_name="CodeReviewAgent",
            description="Reviews code for quality, security, and best practices",
            category="code_quality",
            tags=["code", "review", "quality"],
        )
        self.register(
            name="test_generator",
            module_path="aiops.agents.test_generator",
            class_name="TestGeneratorAgent",
            description="Generates unit and integration tests for code",
            category="code_quality",
            tags=["code", "testing", "automation"],
        )
        self.register(
            name="doc_generator",
            module_path="aiops.agents.doc_generator",
            class_name="DocGeneratorAgent",
            description="Generates documentation for code",
            category="code_quality",
            tags=["code", "documentation"],
        )
        self.register(
            name="performance_analyzer",
            module_path="aiops.agents.performance_analyzer",
            class_name="PerformanceAnalyzerAgent",
            description="Analyzes code for performance issues",
            category="code_quality",
            tags=["code", "performance", "optimization"],
        )

        # Monitoring & Analysis
        self.register(
            name="log_analyzer",
            module_path="aiops.agents.log_analyzer",
            class_name="LogAnalyzerAgent",
            description="Analyzes logs for errors and patterns",
            category="monitoring",
            tags=["logs", "analysis", "debugging"],
        )
        self.register(
            name="anomaly_detector",
            module_path="aiops.agents.anomaly_detector",
            class_name="AnomalyDetectorAgent",
            description="Detects anomalies in metrics and data",
            category="monitoring",
            tags=["metrics", "anomaly", "monitoring"],
        )
        self.register(
            name="intelligent_monitor",
            module_path="aiops.agents.intelligent_monitor",
            class_name="IntelligentMonitorAgent",
            description="Provides intelligent monitoring insights",
            category="monitoring",
            tags=["monitoring", "insights", "alerts"],
        )

        # Infrastructure & Operations
        self.register(
            name="k8s_optimizer",
            module_path="aiops.agents.k8s_optimizer",
            class_name="KubernetesOptimizerAgent",
            description="Optimizes Kubernetes resource configurations",
            category="infrastructure",
            tags=["kubernetes", "optimization", "resources"],
        )
        self.register(
            name="cicd_optimizer",
            module_path="aiops.agents.cicd_optimizer",
            class_name="CICDOptimizerAgent",
            description="Optimizes CI/CD pipelines",
            category="infrastructure",
            tags=["cicd", "pipeline", "optimization"],
        )
        self.register(
            name="cost_optimizer",
            module_path="aiops.agents.cost_optimizer",
            class_name="CostOptimizerAgent",
            description="Analyzes and optimizes cloud costs",
            category="infrastructure",
            tags=["cost", "cloud", "optimization"],
        )
        self.register(
            name="disaster_recovery",
            module_path="aiops.agents.disaster_recovery",
            class_name="DisasterRecoveryAgent",
            description="Plans and validates disaster recovery",
            category="infrastructure",
            tags=["disaster", "recovery", "backup"],
        )

        # Security
        self.register(
            name="security_scanner",
            module_path="aiops.agents.security_scanner",
            class_name="SecurityScannerAgent",
            description="Scans code and configs for security vulnerabilities",
            category="security",
            tags=["security", "vulnerabilities", "scanning"],
        )
        self.register(
            name="secret_scanner",
            module_path="aiops.agents.secret_scanner",
            class_name="SecretScannerAgent",
            description="Detects hardcoded secrets and credentials",
            category="security",
            tags=["security", "secrets", "credentials"],
        )
        self.register(
            name="container_security",
            module_path="aiops.agents.container_security",
            class_name="ContainerSecurityAgent",
            description="Analyzes container security configurations",
            category="security",
            tags=["security", "containers", "docker"],
        )
        self.register(
            name="compliance_checker",
            module_path="aiops.agents.compliance_checker",
            class_name="ComplianceCheckerAgent",
            description="Checks compliance with security standards",
            category="security",
            tags=["security", "compliance", "audit"],
        )

        # Automation
        self.register(
            name="auto_fixer",
            module_path="aiops.agents.auto_fixer",
            class_name="AutoFixerAgent",
            description="Automatically generates fixes for issues",
            category="automation",
            tags=["automation", "fixes", "remediation"],
        )
        self.register(
            name="incident_response",
            module_path="aiops.agents.incident_response",
            class_name="IncidentResponseAgent",
            description="Analyzes and responds to incidents",
            category="automation",
            tags=["incidents", "response", "automation"],
        )

        logger.info(f"Registered {len(self._registry)} built-in agents")

    def register(
        self,
        name: str,
        module_path: str,
        class_name: str,
        description: str = "",
        category: str = "general",
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        Register an agent for lazy loading.

        Args:
            name: Unique agent identifier
            module_path: Full module path (e.g., "aiops.agents.code_reviewer")
            class_name: Class name within the module
            description: Human-readable description
            category: Agent category for grouping
            tags: Tags for filtering and search
        """
        if name in self._registry:
            logger.warning(f"Agent '{name}' already registered, overwriting")

        self._registry[name] = AgentInfo(
            name=name,
            module_path=module_path,
            class_name=class_name,
            description=description,
            category=category,
            tags=tags or [],
        )
        logger.debug(f"Registered agent: {name} ({module_path}.{class_name})")

    def _load_class(self, name: str) -> Type:
        """
        Load agent class from module (lazy loading).

        Args:
            name: Agent name

        Returns:
            Agent class

        Raises:
            KeyError: If agent not registered
            ImportError: If module cannot be imported
        """
        if name not in self._registry:
            raise KeyError(f"Agent '{name}' not registered")

        if name in self._classes:
            return self._classes[name]

        info = self._registry[name]

        try:
            logger.debug(f"Loading agent class: {info.module_path}.{info.class_name}")
            module = importlib.import_module(info.module_path)
            agent_class = getattr(module, info.class_name)
            self._classes[name] = agent_class
            info.is_loaded = True
            logger.info(f"Loaded agent: {name}")
            return agent_class
        except ImportError as e:
            logger.error(f"Failed to import agent module: {info.module_path}: {e}")
            raise
        except AttributeError as e:
            logger.error(f"Agent class not found: {info.class_name} in {info.module_path}: {e}")
            raise

    def get_class(self, name: str) -> Type:
        """
        Get agent class (lazy loads if needed).

        Args:
            name: Agent name

        Returns:
            Agent class
        """
        return self._load_class(name)

    async def get(
        self,
        name: str,
        use_cache: bool = True,
        **kwargs,
    ) -> Any:
        """
        Get agent instance (lazy loads and caches).

        Args:
            name: Agent name
            use_cache: Whether to return cached instance
            **kwargs: Arguments to pass to agent constructor

        Returns:
            Agent instance
        """
        if use_cache and name in self._instances:
            return self._instances[name]

        agent_class = self._load_class(name)
        instance = agent_class(**kwargs)

        if use_cache:
            self._instances[name] = instance

        return instance

    def get_sync(
        self,
        name: str,
        use_cache: bool = True,
        **kwargs,
    ) -> Any:
        """
        Synchronous version of get().

        Args:
            name: Agent name
            use_cache: Whether to return cached instance
            **kwargs: Arguments to pass to agent constructor

        Returns:
            Agent instance
        """
        if use_cache and name in self._instances:
            return self._instances[name]

        agent_class = self._load_class(name)
        instance = agent_class(**kwargs)

        if use_cache:
            self._instances[name] = instance

        return instance

    def list_agents(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        loaded_only: bool = False,
    ) -> List[AgentInfo]:
        """
        List registered agents.

        Args:
            category: Filter by category
            tags: Filter by tags (any match)
            loaded_only: Only return loaded agents

        Returns:
            List of agent info objects
        """
        agents = list(self._registry.values())

        if category:
            agents = [a for a in agents if a.category == category]

        if tags:
            agents = [a for a in agents if any(t in a.tags for t in tags)]

        if loaded_only:
            agents = [a for a in agents if a.is_loaded]

        return agents

    def list_categories(self) -> List[str]:
        """Get list of all agent categories."""
        return list(set(a.category for a in self._registry.values()))

    def is_registered(self, name: str) -> bool:
        """Check if agent is registered."""
        return name in self._registry

    def is_loaded(self, name: str) -> bool:
        """Check if agent is loaded."""
        return name in self._classes

    def unload(self, name: str) -> bool:
        """
        Unload an agent to free memory.

        Args:
            name: Agent name

        Returns:
            True if agent was unloaded
        """
        if name in self._instances:
            del self._instances[name]

        if name in self._classes:
            del self._classes[name]
            if name in self._registry:
                self._registry[name].is_loaded = False
            logger.info(f"Unloaded agent: {name}")
            return True

        return False

    def clear_cache(self) -> None:
        """Clear all cached instances."""
        self._instances.clear()
        logger.info("Cleared agent instance cache")

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "registered": len(self._registry),
            "loaded": len(self._classes),
            "cached_instances": len(self._instances),
            "categories": self.list_categories(),
        }


# Global registry instance
agent_registry = AgentRegistry()


# Convenience functions
def get_agent(name: str, **kwargs) -> Any:
    """Get agent instance (sync)."""
    return agent_registry.get_sync(name, **kwargs)


async def get_agent_async(name: str, **kwargs) -> Any:
    """Get agent instance (async)."""
    return await agent_registry.get(name, **kwargs)


def list_agents(**kwargs) -> List[AgentInfo]:
    """List registered agents."""
    return agent_registry.list_agents(**kwargs)
