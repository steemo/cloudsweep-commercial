"""
ECS Services Scanner - Detects unused and over-provisioned ECS/Fargate services
"""

import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError


def scan_ecs_services(session, region):
    """
    Scan for unused and over-provisioned ECS services that are incurring costs
    
    Returns list of waste items with cost calculations
    """
    try:
        ecs_client = session.client('ecs', region_name=region)
        cloudwatch = session.client('cloudwatch', region_name=region)
        
        waste_items = []
        
        # Get all ECS clusters
        clusters_response = ecs_client.list_clusters()
        
        for cluster_arn in clusters_response['clusterArns']:
            cluster_name = cluster_arn.split('/')[-1]
            
            # Get services in this cluster
            services_response = ecs_client.list_services(cluster=cluster_arn)
            
            for service_arn in services_response['serviceArns']:
                service_name = service_arn.split('/')[-1]
                
                # Get service details
                service_details = ecs_client.describe_services(
                    cluster=cluster_arn,
                    services=[service_arn]
                )
                
                if not service_details['services']:
                    continue
                    
                service = service_details['services'][0]
                service_status = service['status']
                created_at = service['createdAt']
                desired_count = service['desiredCount']
                running_count = service['runningCount']
                
                # Calculate age in days
                age_days = (datetime.now(created_at.tzinfo) - created_at).days
                
                # Skip recently created services (safety check)
                if age_days < 30:
                    continue
                
                # Check for unused services (no running tasks)
                if desired_count == 0 and running_count == 0 and service_status == 'ACTIVE':
                    # Service exists but has no tasks - still incurring base costs
                    monthly_cost = calculate_ecs_service_cost(service, 0, region)
                    
                    waste_items.append({
                        'resource_id': f"{cluster_name}/{service_name}",
                        'resource_type': 'ECS Service (Unused)',
                        'region': region,
                        'monthly_cost': monthly_cost,
                        'annual_cost': monthly_cost * 12,
                        'age_days': age_days,
                        'details': {
                            'cluster_name': cluster_name,
                            'service_name': service_name,
                            'status': service_status,
                            'desired_count': desired_count,
                            'running_count': running_count,
                            'launch_type': service.get('launchType', 'EC2'),
                            'created_at': created_at.isoformat()
                        },
                        'confidence': 'High',
                        'risk_level': 'Low',
                        'reason': f'ECS service with no running tasks (£{monthly_cost:.2f}/month base cost)'
                    })
                
                elif running_count > 0:
                    # Check if service is underutilized
                    avg_cpu_utilization = check_ecs_utilization(cloudwatch, cluster_name, service_name, days=30)
                    
                    if avg_cpu_utilization is not None and avg_cpu_utilization < 10:  # Less than 10% CPU
                        monthly_cost = calculate_ecs_service_cost(service, running_count, region)
                        
                        if monthly_cost > 10:  # Only flag if cost > £10/month
                            waste_items.append({
                                'resource_id': f"{cluster_name}/{service_name}",
                                'resource_type': 'ECS Service (Underutilized)',
                                'region': region,
                                'monthly_cost': monthly_cost,
                                'annual_cost': monthly_cost * 12,
                                'age_days': age_days,
                                'details': {
                                    'cluster_name': cluster_name,
                                    'service_name': service_name,
                                    'status': service_status,
                                    'desired_count': desired_count,
                                    'running_count': running_count,
                                    'avg_cpu_utilization': avg_cpu_utilization,
                                    'launch_type': service.get('launchType', 'EC2'),
                                    'created_at': created_at.isoformat()
                                },
                                'confidence': 'Medium',
                                'risk_level': 'Medium',
                                'reason': f'Low CPU utilization ({avg_cpu_utilization:.1f}%) - consider downsizing (£{monthly_cost:.2f}/month)'
                            })
        
        return waste_items
        
    except ClientError as e:
        print(f"Error scanning ECS services in {region}: {e}")
        return []


def check_ecs_utilization(cloudwatch, cluster_name, service_name, days=30):
    """
    Check ECS service CPU utilization in the specified period
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Check CPUUtilization metric
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/ECS',
            MetricName='CPUUtilization',
            Dimensions=[
                {
                    'Name': 'ServiceName',
                    'Value': service_name
                },
                {
                    'Name': 'ClusterName',
                    'Value': cluster_name
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # Daily
            Statistics=['Average']
        )
        
        # Calculate average CPU utilization
        if not response['Datapoints']:
            return None
            
        avg_cpu = sum([point['Average'] for point in response['Datapoints']]) / len(response['Datapoints'])
        return avg_cpu
        
    except ClientError:
        # If we can't get metrics, assume it's utilized (conservative)
        return None


def calculate_ecs_service_cost(service, task_count, region):
    """
    Calculate monthly ECS service cost based on launch type and task configuration
    """
    launch_type = service.get('launchType', 'EC2')
    
    if launch_type == 'FARGATE':
        # Fargate pricing (simplified)
        # Base cost per task per month (approximate)
        base_cost_per_task = 25.00  # £25/month per typical Fargate task
        
        # Get task definition for more accurate pricing
        try:
            task_definition_arn = service.get('taskDefinition', '')
            if task_definition_arn:
                # Simplified cost calculation based on task count
                monthly_cost = task_count * base_cost_per_task
            else:
                monthly_cost = task_count * base_cost_per_task
        except:
            monthly_cost = task_count * base_cost_per_task
            
    else:
        # EC2 launch type - base service cost (instances are counted separately)
        base_service_cost = 5.00  # £5/month base cost for ECS service management
        monthly_cost = base_service_cost
    
    # Minimum cost for tracking
    return max(monthly_cost, 1.00)


def get_task_definition_details(ecs_client, task_definition_arn):
    """
    Get task definition details for more accurate cost calculation
    """
    try:
        response = ecs_client.describe_task_definition(taskDefinition=task_definition_arn)
        task_def = response['taskDefinition']
        
        # Extract CPU and memory requirements
        cpu = task_def.get('cpu', '256')
        memory = task_def.get('memory', '512')
        
        # Convert to numbers for calculation
        cpu_units = int(cpu) if cpu else 256
        memory_mb = int(memory) if memory else 512
        
        return {
            'cpu_units': cpu_units,
            'memory_mb': memory_mb,
            'requires_attributes': task_def.get('requiresAttributes', [])
        }
        
    except ClientError:
        return {
            'cpu_units': 256,
            'memory_mb': 512,
            'requires_attributes': []
        }