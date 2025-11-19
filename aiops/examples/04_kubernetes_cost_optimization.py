"""Example 4: Kubernetes Resource and Cost Optimization

This example shows how to optimize Kubernetes resources and reduce cloud costs.
"""

import asyncio
import yaml
from pathlib import Path
from aiops.agents.k8s_optimizer import KubernetesOptimizerAgent
from aiops.agents.cost_optimizer import CloudCostOptimizerAgent


async def optimize_k8s_deployment(manifest_file: str):
    """Optimize a Kubernetes deployment."""

    print(f"☸️  Optimizing Kubernetes Deployment: {manifest_file}")
    print("="*60)

    # Read manifest
    with open(manifest_file, 'r') as f:
        manifest = f.read()

    # Mock metrics (in production, get from Prometheus)
    metrics = {
        "cpu_usage_avg": 25.5,  # 25.5% average CPU
        "memory_usage_avg": 45.2,  # 45.2% average memory
        "cpu_usage_p95": 58.3,
        "memory_usage_p95": 72.1,
        "request_count": 15000,
        "pod_count": 3,
    }

    # Initialize optimizer
    optimizer = KubernetesOptimizerAgent()

    # Analyze and optimize
    result = await optimizer.execute(
        manifest=manifest,
        metrics=metrics
    )

    print("\n📊 Optimization Results")
    print("-" * 60)

    # Resource optimizations
    if result.resource_optimizations:
        print("\n💡 Resource Optimization Recommendations:")
        for opt in result.resource_optimizations:
            print(f"\n  Resource: {opt.resource_type}/{opt.resource_name}")
            print(f"  CPU:")
            print(f"    Current request: {opt.current_cpu_request}")
            print(f"    Recommended: {opt.recommended_cpu_request}")
            print(f"  Memory:")
            print(f"    Current request: {opt.current_memory_request}")
            print(f"    Recommended: {opt.recommended_memory_request}")
            print(f"  Potential savings: {opt.potential_savings_percent:.1f}%")
            print(f"  Justification: {opt.justification}")

    # HPA recommendations
    if result.hpa_recommendations:
        print("\n📈 Horizontal Pod Autoscaler Recommendations:")
        for hpa in result.hpa_recommendations:
            print(f"\n  Resource: {hpa.resource_name}")
            print(f"  Min replicas: {hpa.min_replicas}")
            print(f"  Max replicas: {hpa.max_replicas}")
            print(f"  Target CPU: {hpa.target_cpu_percent}%")
            if hpa.target_memory_percent:
                print(f"  Target Memory: {hpa.target_memory_percent}%")
            print(f"  Justification: {hpa.justification}")

    # Cost savings
    print(f"\n💰 Estimated Monthly Savings: ${result.cost_savings_monthly:.2f}")
    print(f"📊 Overall Optimization Score: {result.overall_score}/100")

    # Generate optimized manifest
    if result.resource_optimizations:
        print("\n📝 Generating Optimized Manifest...")

        # Parse original manifest
        docs = list(yaml.safe_load_all(manifest))

        # Apply optimizations (simplified example)
        for doc in docs:
            if doc.get('kind') == 'Deployment':
                for opt in result.resource_optimizations:
                    if 'containers' in doc['spec']['template']['spec']:
                        for container in doc['spec']['template']['spec']['containers']:
                            if 'resources' not in container:
                                container['resources'] = {}
                            if 'requests' not in container['resources']:
                                container['resources']['requests'] = {}

                            # Update resource requests
                            container['resources']['requests']['cpu'] = opt.recommended_cpu_request
                            container['resources']['requests']['memory'] = opt.recommended_memory_request

        # Save optimized manifest
        output_file = manifest_file.replace('.yaml', '_optimized.yaml')
        with open(output_file, 'w') as f:
            yaml.dump_all(docs, f, default_flow_style=False)

        print(f"   Saved to: {output_file}")

    print("\n✅ Optimization Complete!\n")

    return result


async def analyze_namespace_costs(namespace: str = "production"):
    """Analyze costs for an entire namespace."""

    print(f"💰 Analyzing Costs for Namespace: {namespace}")
    print("="*60)

    # Mock namespace resources
    namespace_config = {
        "deployments": 8,
        "total_cpu_requested": "12000m",
        "total_memory_requested": "24Gi",
        "total_pods": 24,
        "storage_pvc": "500Gi",
    }

    # Mock current cloud costs
    cloud_resources = {
        "ec2_instances": [
            {"id": "i-worker-1", "type": "m5.2xlarge", "utilization": 35.2, "monthly_cost": 280},
            {"id": "i-worker-2", "type": "m5.2xlarge", "utilization": 42.1, "monthly_cost": 280},
            {"id": "i-worker-3", "type": "m5.xlarge", "utilization": 65.8, "monthly_cost": 140},
        ],
        "ebs_volumes": [
            {"id": "vol-1", "size_gb": 500, "iops": 3000, "attached": True, "monthly_cost": 50},
            {"id": "vol-2", "size_gb": 100, "iops": 3000, "attached": False, "monthly_cost": 10},
        ],
    }

    # Optimize K8s resources
    k8s_optimizer = KubernetesOptimizerAgent()
    k8s_result = await k8s_optimizer.optimize_namespace(
        namespace=namespace,
        config=namespace_config
    )

    # Optimize cloud costs
    cost_optimizer = CloudCostOptimizerAgent()
    cost_result = await cost_optimizer.execute(
        resources=cloud_resources,
        cloud_provider="aws"
    )

    print("\n📊 Cost Analysis Summary")
    print("-" * 60)

    # Current costs
    total_current = sum(i["monthly_cost"] for i in cloud_resources["ec2_instances"])
    total_current += sum(v["monthly_cost"] for v in cloud_resources["ebs_volumes"])

    print(f"\nCurrent Monthly Costs:")
    print(f"  EC2 Instances: ${sum(i['monthly_cost'] for i in cloud_resources['ec2_instances']):.2f}")
    print(f"  EBS Volumes: ${sum(v['monthly_cost'] for v in cloud_resources['ebs_volumes']):.2f}")
    print(f"  Total: ${total_current:.2f}")

    # Potential savings
    print(f"\nPotential Savings:")
    print(f"  Kubernetes optimization: ${k8s_result.cost_savings_monthly:.2f}")
    print(f"  Cloud resource optimization: ${cost_result.total_potential_savings:.2f}")
    print(f"  Total Monthly Savings: ${k8s_result.cost_savings_monthly + cost_result.total_potential_savings:.2f}")

    # Recommendations
    print(f"\n💡 Top Recommendations:")
    all_recommendations = []

    if cost_result.recommendations:
        all_recommendations.extend([
            f"{rec.category}: {rec.action} (Save ${rec.estimated_savings:.2f})"
            for rec in cost_result.recommendations[:3]
        ])

    for i, rec in enumerate(all_recommendations, 1):
        print(f"  {i}. {rec}")

    # Cost breakdown by resource type
    print(f"\n📊 Cost Breakdown:")
    instance_utilization = [i["utilization"] for i in cloud_resources["ec2_instances"]]
    avg_utilization = sum(instance_utilization) / len(instance_utilization)

    print(f"  Average EC2 Utilization: {avg_utilization:.1f}%")
    print(f"  Underutilized Instances: {sum(1 for u in instance_utilization if u < 50)}")
    print(f"  Unattached Volumes: {sum(1 for v in cloud_resources['ebs_volumes'] if not v['attached'])}")

    print("\n✅ Analysis Complete!\n")


async def continuous_cost_monitoring():
    """Example of continuous cost monitoring."""

    print("📊 Continuous Cost Monitoring Example")
    print("="*60)

    print("\nThis would run periodically (e.g., daily) to:")
    print("  1. Collect resource usage metrics from Prometheus")
    print("  2. Analyze K8s resource allocation")
    print("  3. Identify cost optimization opportunities")
    print("  4. Generate reports and alerts")
    print("  5. Automatically apply safe optimizations")

    print("\nExample Celery task:")
    print("""
    from celery import Celery
    from celery.schedules import crontab

    @app.task
    def daily_cost_optimization():
        # Collect metrics
        metrics = get_prometheus_metrics()

        # Run optimization
        result = await optimize_all_deployments(metrics)

        # Send report
        send_cost_report(result)

        # Auto-apply if savings > $100 and confidence > 90%
        if result.monthly_savings > 100 and result.confidence > 0.9:
            apply_optimizations(result)

    # Schedule
    app.conf.beat_schedule = {
        'daily-cost-optimization': {
            'task': 'tasks.daily_cost_optimization',
            'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        },
    }
    """)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        manifest_file = sys.argv[1]
        asyncio.run(optimize_k8s_deployment(manifest_file))
    else:
        # Run demos
        print("Demo: Namespace Cost Analysis\n")
        asyncio.run(analyze_namespace_costs())

        print("\n" + "="*60 + "\n")
        asyncio.run(continuous_cost_monitoring())
