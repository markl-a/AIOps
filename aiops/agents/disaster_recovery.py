"""
Disaster Recovery Planner Agent

Creates and validates disaster recovery plans, calculates RTO/RPO,
tests backup strategies, and ensures business continuity.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from aiops.core.logger import get_logger

logger = get_logger(__name__)


class RecoveryProcedure(BaseModel):
    """Disaster recovery procedure"""
    step_number: int
    description: str = Field(description="What to do")
    estimated_time_minutes: int = Field(description="Time to complete")
    responsible_team: str = Field(description="Who executes this")
    automation_available: bool = Field(description="Can be automated")
    dependencies: List[int] = Field(default_factory=list, description="Depends on steps")
    verification: str = Field(description="How to verify success")


class DisasterScenario(BaseModel):
    """Disaster scenario"""
    scenario_name: str = Field(description="Type of disaster")
    probability: str = Field(description="low, medium, high")
    impact_severity: str = Field(description="low, medium, high, critical")
    affected_systems: List[str] = Field(description="Systems affected")
    rto_minutes: int = Field(description="Recovery Time Objective")
    rpo_minutes: int = Field(description="Recovery Point Objective")
    recovery_procedures: List[RecoveryProcedure] = Field(description="Recovery steps")
    estimated_total_recovery_time: int = Field(description="Total time in minutes")


class BackupValidation(BaseModel):
    """Backup validation result"""
    system_name: str
    backup_frequency: str = Field(description="hourly, daily, weekly")
    last_backup: str = Field(description="Timestamp of last backup")
    backup_size_gb: float
    retention_days: int
    tested_recently: bool = Field(description="Backup tested in last 30 days")
    issues: List[str] = Field(description="Issues found")
    status: str = Field(description="healthy, warning, critical")


class DRPlanResult(BaseModel):
    """Disaster recovery plan result"""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    organization: str = Field(description="Organization name")
    scenarios: List[DisasterScenario] = Field(description="Disaster scenarios")
    backup_validations: List[BackupValidation] = Field(description="Backup status")
    overall_readiness: str = Field(description="excellent, good, fair, poor")
    max_rto_minutes: int = Field(description="Maximum RTO across scenarios")
    max_rpo_minutes: int = Field(description="Maximum RPO across scenarios")
    summary: str = Field(description="Summary")
    recommendations: List[str] = Field(description="Recommendations")


class DisasterRecoveryPlanner:
    """Disaster recovery planner agent"""

    def __init__(self, llm_factory=None):
        self.llm_factory = llm_factory
        logger.info("Disaster Recovery Planner initialized")

    async def create_dr_plan(
        self,
        systems: List[Dict[str, Any]],
        organization: str = "MyOrg"
    ) -> DRPlanResult:
        """Create comprehensive disaster recovery plan"""

        scenarios = []
        backup_validations = []

        # Scenario 1: Database Failure
        db_systems = [s['name'] for s in systems if s.get('type') == 'database']
        if db_systems:
            scenarios.append(DisasterScenario(
                scenario_name="Database Server Failure",
                probability="medium",
                impact_severity="critical",
                affected_systems=db_systems,
                rto_minutes=30,
                rpo_minutes=15,
                recovery_procedures=[
                    RecoveryProcedure(
                        step_number=1,
                        description="Detect database failure via monitoring alerts",
                        estimated_time_minutes=2,
                        responsible_team="SRE/DevOps",
                        automation_available=True,
                        verification="Check monitoring dashboard shows failure"
                    ),
                    RecoveryProcedure(
                        step_number=2,
                        description="Failover to standby replica",
                        estimated_time_minutes=5,
                        responsible_team="SRE/DevOps",
                        automation_available=True,
                        dependencies=[1],
                        verification="Verify replica promoted to primary, accepting writes"
                    ),
                    RecoveryProcedure(
                        step_number=3,
                        description="Update DNS/load balancer to point to new primary",
                        estimated_time_minutes=3,
                        responsible_team="SRE/DevOps",
                        automation_available=True,
                        dependencies=[2],
                        verification="nslookup shows updated IP, traffic flowing"
                    ),
                    RecoveryProcedure(
                        step_number=4,
                        description="Verify application connectivity and data integrity",
                        estimated_time_minutes=10,
                        responsible_team="Engineering",
                        automation_available=False,
                        dependencies=[3],
                        verification="Run smoke tests, check recent transactions"
                    ),
                    RecoveryProcedure(
                        step_number=5,
                        description="Rebuild failed database instance",
                        estimated_time_minutes=60,
                        responsible_team="SRE/DevOps",
                        automation_available=True,
                        dependencies=[4],
                        verification="New instance syncing, replication lag < 1s"
                    )
                ],
                estimated_total_recovery_time=30
            ))

        # Scenario 2: Region Outage
        scenarios.append(DisasterScenario(
            scenario_name="Complete Region/Datacenter Outage",
            probability="low",
            impact_severity="critical",
            affected_systems=[s['name'] for s in systems],
            rto_minutes=120,
            rpo_minutes=60,
            recovery_procedures=[
                RecoveryProcedure(
                    step_number=1,
                    description="Declare regional disaster, activate DR team",
                    estimated_time_minutes=10,
                    responsible_team="Incident Commander",
                    automation_available=False,
                    verification="DR team assembled, communication channels active"
                ),
                RecoveryProcedure(
                    step_number=2,
                    description="Failover DNS to secondary region",
                    estimated_time_minutes=15,
                    responsible_team="SRE/DevOps",
                    automation_available=True,
                    dependencies=[1],
                    verification="DNS propagation started, traffic shifting"
                ),
                RecoveryProcedure(
                    step_number=3,
                    description="Restore databases from latest backups in DR region",
                    estimated_time_minutes=45,
                    responsible_team="DBA/SRE",
                    automation_available=True,
                    dependencies=[2],
                    verification="Database restored, point-in-time recovery complete"
                ),
                RecoveryProcedure(
                    step_number=4,
                    description="Scale up application instances in DR region",
                    estimated_time_minutes=20,
                    responsible_team="SRE/DevOps",
                    automation_available=True,
                    dependencies=[3],
                    verification="Auto-scaling group scaled, health checks passing"
                ),
                RecoveryProcedure(
                    step_number=5,
                    description="Verify all services operational, run integration tests",
                    estimated_time_minutes=30,
                    responsible_team="Engineering/QA",
                    automation_available=True,
                    dependencies=[4],
                    verification="All critical paths tested, monitoring green"
                )
            ],
            estimated_total_recovery_time=120
        ))

        # Scenario 3: Ransomware Attack
        scenarios.append(DisasterScenario(
            scenario_name="Ransomware/Cyber Attack",
            probability="medium",
            impact_severity="critical",
            affected_systems=[s['name'] for s in systems if s.get('type') in ['application', 'database']],
            rto_minutes=240,
            rpo_minutes=120,
            recovery_procedures=[
                RecoveryProcedure(
                    step_number=1,
                    description="Isolate affected systems, disconnect from network",
                    estimated_time_minutes=10,
                    responsible_team="Security/SRE",
                    automation_available=False,
                    verification="Network segments isolated, spread contained"
                ),
                RecoveryProcedure(
                    step_number=2,
                    description="Assess scope of compromise, identify last clean backup",
                    estimated_time_minutes=60,
                    responsible_team="Security/Forensics",
                    automation_available=False,
                    dependencies=[1],
                    verification="Forensics report generated, clean backup identified"
                ),
                RecoveryProcedure(
                    step_number=3,
                    description="Build new clean infrastructure from IaC",
                    estimated_time_minutes=90,
                    responsible_team="SRE/DevOps",
                    automation_available=True,
                    dependencies=[2],
                    verification="New infrastructure deployed, hardened, patched"
                ),
                RecoveryProcedure(
                    step_number=4,
                    description="Restore data from pre-compromise backup",
                    estimated_time_minutes=60,
                    responsible_team="DBA/SRE",
                    automation_available=True,
                    dependencies=[3],
                    verification="Data restored, integrity verified"
                ),
                RecoveryProcedure(
                    step_number=5,
                    description="Reset all credentials, deploy with new secrets",
                    estimated_time_minutes=20,
                    responsible_team="Security/SRE",
                    automation_available=False,
                    dependencies=[4],
                    verification="All passwords rotated, keys regenerated"
                )
            ],
            estimated_total_recovery_time=240
        ))

        # Validate backups for each system
        for system in systems:
            last_backup_time = datetime.now() - timedelta(hours=system.get('hours_since_backup', 24))
            backup_age_hours = system.get('hours_since_backup', 24)

            issues = []
            if backup_age_hours > 48:
                issues.append("Backup too old (>48 hours)")
            if not system.get('backup_tested', False):
                issues.append("Backup not tested recently")
            if system.get('backup_size_gb', 0) == 0:
                issues.append("Backup size is 0 (may be failing)")

            if len(issues) >= 2:
                status = "critical"
            elif len(issues) == 1:
                status = "warning"
            else:
                status = "healthy"

            backup_validations.append(BackupValidation(
                system_name=system['name'],
                backup_frequency=system.get('backup_frequency', 'daily'),
                last_backup=last_backup_time.isoformat(),
                backup_size_gb=system.get('backup_size_gb', 0),
                retention_days=system.get('retention_days', 30),
                tested_recently=system.get('backup_tested', False),
                issues=issues,
                status=status
            ))

        # Calculate overall readiness
        critical_backups = sum(1 for b in backup_validations if b.status == "critical")
        untested_backups = sum(1 for b in backup_validations if not b.tested_recently)

        if critical_backups > 0 or untested_backups > len(backup_validations) / 2:
            readiness = "poor"
        elif untested_backups > 0:
            readiness = "fair"
        elif any(s.rto_minutes > 60 for s in scenarios):
            readiness = "good"
        else:
            readiness = "excellent"

        max_rto = max((s.rto_minutes for s in scenarios), default=0)
        max_rpo = max((s.rpo_minutes for s in scenarios), default=0)

        # Generate recommendations
        recommendations = self._generate_recommendations(scenarios, backup_validations, readiness)

        # Generate summary
        summary = self._generate_summary(organization, scenarios, readiness, max_rto, max_rpo)

        return DRPlanResult(
            organization=organization,
            scenarios=scenarios,
            backup_validations=backup_validations,
            overall_readiness=readiness,
            max_rto_minutes=max_rto,
            max_rpo_minutes=max_rpo,
            summary=summary,
            recommendations=recommendations
        )

    def _generate_recommendations(
        self,
        scenarios: List[DisasterScenario],
        backups: List[BackupValidation],
        readiness: str
    ) -> List[str]:
        """Generate DR recommendations"""
        recommendations = []

        if readiness in ['poor', 'fair']:
            recommendations.append("🚨 URGENT: Improve disaster recovery readiness")

        # Backup recommendations
        untested = [b for b in backups if not b.tested_recently]
        if untested:
            recommendations.append(
                f"Test {len(untested)} untested backups - schedule quarterly DR drills"
            )

        critical_backups = [b for b in backups if b.status == "critical"]
        if critical_backups:
            recommendations.append(
                f"Fix {len(critical_backups)} critical backup issues immediately"
            )

        # RTO/RPO recommendations
        high_rto = [s for s in scenarios if s.rto_minutes > 60]
        if high_rto:
            recommendations.extend([
                "Implement automated failover to reduce RTO",
                "Consider multi-region active-active architecture",
                "Set up continuous replication for databases"
            ])

        # General recommendations
        recommendations.extend([
            "Document and practice DR procedures quarterly",
            "Implement Infrastructure as Code for rapid rebuilding",
            "Use immutable infrastructure for security scenarios",
            "Set up monitoring and automated alerts for DR triggers",
            "Maintain up-to-date runbooks with screenshots",
            "Conduct chaos engineering exercises"
        ])

        return recommendations[:8]

    def _generate_summary(
        self,
        org: str,
        scenarios: List[DisasterScenario],
        readiness: str,
        max_rto: int,
        max_rpo: int
    ) -> str:
        """Generate summary"""
        summary = f"Disaster Recovery Plan: {org}\n\n"
        summary += f"Scenarios covered: {len(scenarios)}\n"
        summary += f"Overall readiness: {readiness.upper()}\n"
        summary += f"Maximum RTO: {max_rto} minutes ({max_rto/60:.1f} hours)\n"
        summary += f"Maximum RPO: {max_rpo} minutes ({max_rpo/60:.1f} hours)\n\n"

        if readiness == "excellent":
            summary += "✓ Organization is well-prepared for disasters"
        elif readiness == "good":
            summary += "✓ Good DR posture, some improvements recommended"
        elif readiness == "fair":
            summary += "⚠ DR capabilities need improvement"
        else:
            summary += "✗ CRITICAL: DR readiness is inadequate"

        return summary
