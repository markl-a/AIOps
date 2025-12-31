"""AI Agents for DevOps automation.

This module uses lazy loading via the agent registry.
Import agents directly only when needed, or use the registry:

    from aiops.agents.registry import agent_registry
    agent = await agent_registry.get("code_reviewer")

For direct imports (only when explicitly needed):
    from aiops.agents.code_reviewer import CodeReviewAgent
"""

# Only export the base classes and registry - no eager loading of agents
from aiops.agents.base_agent import BaseAgent
from aiops.agents.prompt_generator import AgentPromptGenerator
from aiops.agents.registry import agent_registry, get_agent, get_agent_async, list_agents

__all__ = [
    "BaseAgent",
    "AgentPromptGenerator",
    "agent_registry",
    "get_agent",
    "get_agent_async",
    "list_agents",
]

# Legacy support: Define __getattr__ for backward compatibility
# This allows: from aiops.agents import CodeReviewAgent
# but only loads when actually accessed
def __getattr__(name: str):
    """Lazy load agents on attribute access for backward compatibility."""
    # Map of legacy names to registry names
    _AGENT_MAP = {
        "CodeReviewAgent": "code_reviewer",
        "TestGeneratorAgent": "test_generator",
        "LogAnalyzerAgent": "log_analyzer",
        "CICDOptimizerAgent": "cicd_optimizer",
        "DocGeneratorAgent": "doc_generator",
        "PerformanceAnalyzerAgent": "performance_analyzer",
        "AnomalyDetectorAgent": "anomaly_detector",
        "AutoFixerAgent": "auto_fixer",
        "IntelligentMonitorAgent": "intelligent_monitor",
        "SecurityScannerAgent": "security_scanner",
        "DependencyAnalyzerAgent": "dependency_analyzer",
        "CodeQualityAgent": "code_quality",
        "KubernetesOptimizerAgent": "k8s_optimizer",
        "CostOptimizerAgent": "cost_optimizer",
        "DisasterRecoveryAgent": "disaster_recovery",
        "ChaosEngineerAgent": "chaos_engineer",
        "DatabaseQueryAnalyzerAgent": "db_query_analyzer",
        "ConfigDriftDetectorAgent": "config_drift_detector",
        "ContainerSecurityAgent": "container_security",
        "IaCValidatorAgent": "iac_validator",
        "SecretScannerAgent": "secret_scanner",
        "ServiceMeshAnalyzerAgent": "service_mesh_analyzer",
        "SLAMonitorAgent": "sla_monitor",
        "APIPerformanceAnalyzerAgent": "api_performance_analyzer",
        "IncidentResponseAgent": "incident_response",
        "ComplianceCheckerAgent": "compliance_checker",
        "MigrationPlannerAgent": "migration_planner",
        "ReleaseManagerAgent": "release_manager",
    }

    if name in _AGENT_MAP:
        # Get the agent class from registry (lazy loads)
        registry_name = _AGENT_MAP[name]
        return agent_registry.get_class(registry_name)

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
