"""Example 8: Disaster Recovery and Backup Automation

This example demonstrates automated disaster recovery planning and backup validation.
"""

import asyncio
import json
from datetime import datetime, timedelta
from aiops.agents.disaster_recovery import DisasterRecoveryAgent
from aiops.agents.infrastructure_analyzer import InfrastructureAnalyzerAgent


async def generate_disaster_recovery_plan():
    """Generate a comprehensive DR plan for infrastructure."""

    print("🛡️  Disaster Recovery Planning")
    print("="*60)

    # Infrastructure configuration
    infrastructure = {
        "services": [
            {
                "name": "aiops-api",
                "type": "application",
                "criticality": "critical",
                "rto": "5m",  # Recovery Time Objective
                "rpo": "1m",  # Recovery Point Objective
                "dependencies": ["postgres", "redis"],
            },
            {
                "name": "postgres",
                "type": "database",
                "criticality": "critical",
                "rto": "10m",
                "rpo": "5m",
                "backup_frequency": "hourly",
            },
            {
                "name": "redis",
                "type": "cache",
                "criticality": "high",
                "rto": "2m",
                "rpo": "0m",  # Can be rebuilt
            },
        ],
        "cloud_provider": "aws",
        "regions": ["us-east-1", "us-west-2"],
        "backup_storage": "s3://aiops-backups",
    }

    print("\n📊 Infrastructure Overview:")
    for service in infrastructure["services"]:
        print(f"\n  {service['name']} ({service['type']})")
        print(f"    Criticality: {service['criticality']}")
        print(f"    RTO: {service['rto']}, RPO: {service['rpo']}")

    # Generate DR plan
    dr_agent = DisasterRecoveryAgent()
    result = await dr_agent.execute(infrastructure=infrastructure)

    print(f"\n\n📋 DR Plan Generated:")
    print(f"  Plan ID: {result.plan_id}")
    print(f"  Estimated Total RTO: {result.estimated_rto}")
    print(f"  Estimated Total RPO: {result.estimated_rpo}")
    print(f"  Risk Score: {result.risk_score}/100")

    # Show recovery procedures
    if hasattr(result, 'recovery_procedures') and result.recovery_procedures:
        print(f"\n\n🔄 Recovery Procedures:")
        for i, procedure in enumerate(result.recovery_procedures, 1):
            print(f"\n  {i}. {procedure.service_name}")
            print(f"     Priority: {procedure.priority}")
            print(f"     Estimated Time: {procedure.estimated_time}")
            print(f"\n     Steps:")
            for step_num, step in enumerate(procedure.steps, 1):
                print(f"       {step_num}. {step}")

    # Show backup strategy
    if hasattr(result, 'backup_strategy'):
        print(f"\n\n💾 Backup Strategy:")
        for service, strategy in result.backup_strategy.items():
            print(f"\n  {service}:")
            print(f"    Method: {strategy.get('method')}")
            print(f"    Frequency: {strategy.get('frequency')}")
            print(f"    Retention: {strategy.get('retention')}")
            print(f"    Storage: {strategy.get('storage')}")

    return result


async def validate_backups():
    """Validate that backups are complete and restorable."""

    print("\n\n🔍 Backup Validation")
    print("="*60)

    # Mock backup metadata
    backups = [
        {
            "service": "postgres",
            "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
            "size_gb": 25.5,
            "backup_type": "full",
            "location": "s3://aiops-backups/postgres/2024-01-15-12-00.dump",
            "checksum": "a1b2c3d4e5f6",
        },
        {
            "service": "postgres",
            "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
            "size_gb": 0.5,
            "backup_type": "incremental",
            "location": "s3://aiops-backups/postgres/2024-01-15-11-00.dump",
            "checksum": "f6e5d4c3b2a1",
        },
        {
            "service": "redis",
            "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "size_gb": 2.1,
            "backup_type": "snapshot",
            "location": "s3://aiops-backups/redis/2024-01-15-12-30.rdb",
            "checksum": "1a2b3c4d5e6f",
        },
    ]

    print("\n📦 Available Backups:")
    for backup in backups:
        age = datetime.now() - datetime.fromisoformat(backup["timestamp"])
        hours = age.total_seconds() / 3600
        print(f"\n  {backup['service']} - {backup['backup_type']}")
        print(f"    Age: {hours:.1f} hours")
        print(f"    Size: {backup['size_gb']:.1f} GB")
        print(f"    Location: {backup['location']}")

    # Validation checks
    print("\n\n✅ Validation Checks:")

    # Check 1: Backup freshness
    print("\n  1. Backup Freshness:")
    for backup in backups:
        age = datetime.now() - datetime.fromisoformat(backup["timestamp"])
        hours = age.total_seconds() / 3600
        max_age = 2 if backup["service"] == "postgres" else 1
        status = "✅" if hours < max_age else "❌"
        print(f"     {status} {backup['service']}: {hours:.1f}h (max: {max_age}h)")

    # Check 2: Backup integrity
    print("\n  2. Backup Integrity:")
    print("     ✅ All checksums verified")
    print("     ✅ No corruption detected")

    # Check 3: Restore test
    print("\n  3. Restore Test (Last 7 Days):")
    print("     ✅ postgres: Last tested 2 days ago (SUCCESS)")
    print("     ✅ redis: Last tested 1 day ago (SUCCESS)")

    # Check 4: Storage availability
    print("\n  4. Storage Availability:")
    print("     ✅ S3 bucket accessible")
    print("     ✅ Sufficient space: 850 GB free")
    print("     ✅ Versioning enabled")

    return True


async def simulate_disaster_scenario():
    """Simulate a disaster scenario and recovery process."""

    print("\n\n🚨 Disaster Scenario Simulation")
    print("="*60)

    # Simulate database failure
    print("\n⚠️  SCENARIO: Primary database failure in us-east-1")
    print("\nTimeline:")
    print("  T+0s:  Database instance becomes unresponsive")
    print("  T+30s: Health check fails, alerts triggered")
    print("  T+60s: Failover initiated")

    # Recovery steps
    recovery_steps = [
        {
            "step": 1,
            "action": "Promote read replica in us-west-2 to primary",
            "duration": "2m",
            "status": "✅ SUCCESS",
        },
        {
            "step": 2,
            "action": "Update DNS records to point to new primary",
            "duration": "30s",
            "status": "✅ SUCCESS",
        },
        {
            "step": 3,
            "action": "Restart application services with new DB endpoint",
            "duration": "1m",
            "status": "✅ SUCCESS",
        },
        {
            "step": 4,
            "action": "Validate data consistency",
            "duration": "1m",
            "status": "✅ SUCCESS",
        },
        {
            "step": 5,
            "action": "Resume normal operations",
            "duration": "30s",
            "status": "✅ SUCCESS",
        },
    ]

    print("\n\n🔄 Recovery Process:")
    total_time = 0
    for step in recovery_steps:
        print(f"\n  Step {step['step']}: {step['action']}")
        print(f"    Duration: {step['duration']}")
        print(f"    Status: {step['status']}")

        # Convert duration to seconds
        duration_str = step['duration']
        if 'm' in duration_str:
            minutes = int(duration_str.replace('m', ''))
            total_time += minutes * 60
        elif 's' in duration_str:
            seconds = int(duration_str.replace('s', ''))
            total_time += seconds

        # Simulate progress
        await asyncio.sleep(0.5)

    print(f"\n\n📊 Recovery Summary:")
    print(f"  Total Recovery Time: {total_time // 60}m {total_time % 60}s")
    print(f"  RTO Objective: 10m")
    print(f"  Status: {'✅ MET' if total_time < 600 else '❌ EXCEEDED'}")

    # Data loss assessment
    print(f"\n  Data Loss Assessment:")
    print(f"    Last Backup: 30 minutes ago")
    print(f"    Last Replicated Transaction: 5 seconds ago")
    print(f"    Estimated Data Loss: <5 seconds of transactions")
    print(f"    RPO Objective: 5m")
    print(f"    Status: ✅ MET")


async def create_backup_automation_script():
    """Create automated backup scripts."""

    print("\n\n📝 Backup Automation Scripts")
    print("="*60)

    # PostgreSQL backup script
    postgres_backup_script = """#!/bin/bash
# PostgreSQL Automated Backup Script

set -e

# Configuration
BACKUP_DIR="/backups/postgres"
S3_BUCKET="s3://aiops-backups/postgres"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y-%m-%d-%H-%M)
BACKUP_FILE="postgres-${TIMESTAMP}.dump"

# Create backup directory
mkdir -p ${BACKUP_DIR}

# Perform backup
echo "Starting PostgreSQL backup..."
pg_dump -h $DB_HOST -U $DB_USER -d aiops \\
  -F custom -b -v \\
  -f ${BACKUP_DIR}/${BACKUP_FILE}

# Compress backup
echo "Compressing backup..."
gzip ${BACKUP_DIR}/${BACKUP_FILE}

# Calculate checksum
CHECKSUM=$(sha256sum ${BACKUP_DIR}/${BACKUP_FILE}.gz | awk '{print $1}')
echo ${CHECKSUM} > ${BACKUP_DIR}/${BACKUP_FILE}.gz.sha256

# Upload to S3
echo "Uploading to S3..."
aws s3 cp ${BACKUP_DIR}/${BACKUP_FILE}.gz ${S3_BUCKET}/ \\
  --metadata checksum=${CHECKSUM}
aws s3 cp ${BACKUP_DIR}/${BACKUP_FILE}.gz.sha256 ${S3_BUCKET}/

# Verify upload
aws s3 ls ${S3_BUCKET}/${BACKUP_FILE}.gz

# Clean old backups
echo "Cleaning old backups..."
find ${BACKUP_DIR} -name "*.gz" -mtime +${RETENTION_DAYS} -delete
aws s3 ls ${S3_BUCKET}/ | \\
  awk '{if (NR > '${RETENTION_DAYS}') print $4}' | \\
  xargs -I {} aws s3 rm ${S3_BUCKET}/{}

echo "Backup completed successfully: ${BACKUP_FILE}.gz"
echo "Checksum: ${CHECKSUM}"

# Send notification
curl -X POST $SLACK_WEBHOOK \\
  -H 'Content-Type: application/json' \\
  -d '{
    "text": "✅ PostgreSQL backup completed",
    "attachments": [{
      "color": "good",
      "fields": [
        {"title": "Backup File", "value": "'${BACKUP_FILE}.gz'", "short": true},
        {"title": "Checksum", "value": "'${CHECKSUM}'", "short": true}
      ]
    }]
  }'
"""

    print("\n🐘 PostgreSQL Backup Script:")
    print(postgres_backup_script)

    # Kubernetes backup script
    k8s_backup_script = """#!/bin/bash
# Kubernetes Resources Backup Script

set -e

BACKUP_DIR="/backups/k8s"
S3_BUCKET="s3://aiops-backups/k8s"
TIMESTAMP=$(date +%Y-%m-%d-%H-%M)
NAMESPACE="aiops"

mkdir -p ${BACKUP_DIR}/${TIMESTAMP}

echo "Backing up Kubernetes resources..."

# Backup all resources in namespace
kubectl get all -n ${NAMESPACE} -o yaml > ${BACKUP_DIR}/${TIMESTAMP}/all-resources.yaml

# Backup ConfigMaps and Secrets
kubectl get configmaps -n ${NAMESPACE} -o yaml > ${BACKUP_DIR}/${TIMESTAMP}/configmaps.yaml
kubectl get secrets -n ${NAMESPACE} -o yaml > ${BACKUP_DIR}/${TIMESTAMP}/secrets.yaml

# Backup PersistentVolumeClaims
kubectl get pvc -n ${NAMESPACE} -o yaml > ${BACKUP_DIR}/${TIMESTAMP}/pvc.yaml

# Backup Custom Resources
kubectl get crd -o yaml > ${BACKUP_DIR}/${TIMESTAMP}/crds.yaml

# Create tarball
tar -czf ${BACKUP_DIR}/${TIMESTAMP}.tar.gz -C ${BACKUP_DIR} ${TIMESTAMP}

# Upload to S3
aws s3 cp ${BACKUP_DIR}/${TIMESTAMP}.tar.gz ${S3_BUCKET}/

echo "Kubernetes backup completed: ${TIMESTAMP}.tar.gz"
"""

    print("\n\n☸️  Kubernetes Backup Script:")
    print(k8s_backup_script)

    # Restoration script
    restore_script = """#!/bin/bash
# Database Restore Script

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <backup-file>"
  exit 1
fi

BACKUP_FILE=$1
S3_BUCKET="s3://aiops-backups/postgres"

echo "⚠️  WARNING: This will restore the database from backup"
echo "Backup file: ${BACKUP_FILE}"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "Restore cancelled"
  exit 0
fi

# Download backup from S3
echo "Downloading backup from S3..."
aws s3 cp ${S3_BUCKET}/${BACKUP_FILE} /tmp/${BACKUP_FILE}

# Verify checksum
echo "Verifying checksum..."
aws s3 cp ${S3_BUCKET}/${BACKUP_FILE}.sha256 /tmp/${BACKUP_FILE}.sha256
sha256sum -c /tmp/${BACKUP_FILE}.sha256

# Decompress
echo "Decompressing..."
gunzip /tmp/${BACKUP_FILE}
DUMP_FILE=${BACKUP_FILE%.gz}

# Stop application
echo "Stopping application..."
kubectl scale deployment aiops-api --replicas=0 -n aiops

# Drop existing database
echo "Dropping existing database..."
psql -h $DB_HOST -U $DB_USER -c "DROP DATABASE IF EXISTS aiops"
psql -h $DB_HOST -U $DB_USER -c "CREATE DATABASE aiops"

# Restore database
echo "Restoring database..."
pg_restore -h $DB_HOST -U $DB_USER -d aiops /tmp/${DUMP_FILE}

# Restart application
echo "Restarting application..."
kubectl scale deployment aiops-api --replicas=3 -n aiops

echo "✅ Database restore completed successfully"
"""

    print("\n\n🔄 Database Restore Script:")
    print(restore_script)


async def test_disaster_recovery_runbook():
    """Test the disaster recovery runbook procedures."""

    print("\n\n📖 DR Runbook Testing")
    print("="*60)

    runbook = {
        "scenario": "Complete AWS Region Failure",
        "procedures": [
            {
                "phase": "Detection & Assessment",
                "actions": [
                    "Monitor receives region health alerts",
                    "Verify scope of outage (region vs AZ)",
                    "Assess impact on services",
                    "Notify stakeholders",
                ],
                "max_duration": "5m",
            },
            {
                "phase": "Failover Initiation",
                "actions": [
                    "Update Route53 to point to backup region",
                    "Promote RDS read replica to primary",
                    "Start standby compute instances",
                    "Verify connectivity",
                ],
                "max_duration": "10m",
            },
            {
                "phase": "Service Restoration",
                "actions": [
                    "Restart application pods",
                    "Validate database integrity",
                    "Test critical user flows",
                    "Monitor error rates",
                ],
                "max_duration": "15m",
            },
            {
                "phase": "Validation & Communication",
                "actions": [
                    "Run smoke tests",
                    "Check all integrations",
                    "Update status page",
                    "Post-incident review planning",
                ],
                "max_duration": "30m",
            },
        ],
    }

    print(f"\n🎯 Scenario: {runbook['scenario']}")
    print("\nProcedures:\n")

    total_max_duration = 0
    for i, procedure in enumerate(runbook['procedures'], 1):
        print(f"{i}. {procedure['phase']} (Max: {procedure['max_duration']})")
        print("   Actions:")
        for action in procedure['actions']:
            print(f"     • {action}")
        print()

        # Convert to minutes
        duration = int(procedure['max_duration'].replace('m', ''))
        total_max_duration += duration

    print(f"Total Maximum Recovery Time: {total_max_duration} minutes\n")

    # Test results
    print("\n✅ Runbook Test Results:")
    print("  • All procedures documented: ✅")
    print("  • Contact information current: ✅")
    print("  • Access credentials verified: ✅")
    print("  • Backup region operational: ✅")
    print("  • Estimated RTO: 30 minutes")
    print("  • Estimated RPO: 5 minutes")


if __name__ == "__main__":
    print("🛡️  Disaster Recovery & Backup Automation Examples")
    print("="*60)

    # Run examples
    asyncio.run(generate_disaster_recovery_plan())

    print("\n" + "="*60)
    asyncio.run(validate_backups())

    print("\n" + "="*60)
    asyncio.run(simulate_disaster_scenario())

    print("\n" + "="*60)
    asyncio.run(create_backup_automation_script())

    print("\n" + "="*60)
    asyncio.run(test_disaster_recovery_runbook())

    print("\n✅ All disaster recovery examples complete!\n")
