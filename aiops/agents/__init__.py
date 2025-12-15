"""AI Agents for DevOps automation."""

from aiops.agents.base_agent import BaseAgent
from aiops.agents.code_reviewer import CodeReviewAgent
from aiops.agents.test_generator import TestGeneratorAgent
from aiops.agents.log_analyzer import LogAnalyzerAgent
from aiops.agents.cicd_optimizer import CICDOptimizerAgent
from aiops.agents.doc_generator import DocGeneratorAgent
from aiops.agents.performance_analyzer import PerformanceAnalyzerAgent
from aiops.agents.anomaly_detector import AnomalyDetectorAgent
from aiops.agents.auto_fixer import AutoFixerAgent
from aiops.agents.intelligent_monitor import IntelligentMonitorAgent
from aiops.agents.security_scanner import SecurityScannerAgent
from aiops.agents.dependency_analyzer import DependencyAnalyzerAgent
from aiops.agents.code_quality import CodeQualityAgent
from aiops.agents.k8s_optimizer import KubernetesOptimizerAgent
from aiops.agents.cost_optimizer import CloudCostOptimizer as CostOptimizerAgent
from aiops.agents.disaster_recovery import DisasterRecoveryPlanner as DisasterRecoveryAgent
from aiops.agents.chaos_engineer import ChaosEngineer as ChaosEngineerAgent
from aiops.agents.db_query_analyzer import DatabaseQueryAnalyzer as DatabaseQueryAnalyzerAgent
from aiops.agents.config_drift_detector import ConfigurationDriftDetector as ConfigDriftDetectorAgent
from aiops.agents.container_security import ContainerSecurityScanner as ContainerSecurityAgent
from aiops.agents.iac_validator import IaCValidator as IaCValidatorAgent
from aiops.agents.secret_scanner import SecretScanner as SecretScannerAgent
from aiops.agents.service_mesh_analyzer import ServiceMeshAnalyzer as ServiceMeshAnalyzerAgent
from aiops.agents.sla_monitor import SLAComplianceMonitor as SLAMonitorAgent
from aiops.agents.api_performance_analyzer import APIPerformanceAnalyzer as APIPerformanceAnalyzerAgent
# New agents
from aiops.agents.incident_response import IncidentResponseAgent
from aiops.agents.compliance_checker import ComplianceCheckerAgent
from aiops.agents.migration_planner import MigrationPlannerAgent
from aiops.agents.release_manager import ReleaseManagerAgent

__all__ = [
    "BaseAgent",
    "CodeReviewAgent",
    "TestGeneratorAgent",
    "LogAnalyzerAgent",
    "CICDOptimizerAgent",
    "DocGeneratorAgent",
    "PerformanceAnalyzerAgent",
    "AnomalyDetectorAgent",
    "AutoFixerAgent",
    "IntelligentMonitorAgent",
    "SecurityScannerAgent",
    "DependencyAnalyzerAgent",
    "CodeQualityAgent",
    "KubernetesOptimizerAgent",
    "CostOptimizerAgent",
    "DisasterRecoveryAgent",
    "ChaosEngineerAgent",
    "DatabaseQueryAnalyzerAgent",
    "ConfigDriftDetectorAgent",
    "ContainerSecurityAgent",
    "IaCValidatorAgent",
    "SecretScannerAgent",
    "ServiceMeshAnalyzerAgent",
    "SLAMonitorAgent",
    "APIPerformanceAnalyzerAgent",
    # New agents
    "IncidentResponseAgent",
    "ComplianceCheckerAgent",
    "MigrationPlannerAgent",
    "ReleaseManagerAgent",
]
