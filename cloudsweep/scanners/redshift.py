"""
Redshift Scanner - Detects unused and over-provisioned Redshift clusters
"""

import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError


def scan_redshift_clusters(session, region):
    """
    Scan for unused and over-provisioned Redshift clusters that are incurring costs
    
    Returns list of waste items with cost calculations
    """
    try:
        redshift_client = session.client('redshift', region_name=region)
        cloudwatch = session.client('cloudwatch', region_name=region)
        
        waste_items = []
        
        # Get all Redshift clusters
        paginator = redshift_client.get_paginator('describe_clusters')
        
        for page in paginator.paginate():
            for cluster in page['Clusters']:
                cluster_identifier = cluster['ClusterIdentifier']
                cluster_status = cluster['ClusterStatus']
                created_time = cluster['ClusterCreateTime']
                node_type = cluster['NodeType']
                number_of_nodes = cluster['NumberOfNodes']
                
                # Calculate age in days
                age_days = (datetime.now(created_time.tzinfo) - created_time).days
                
                # Skip recently created clusters (safety check)
                if age_days < 30:
                    continue
                
                # Check for paused clusters (still incurring storage costs)
                if cluster_status == 'paused':
                    monthly_cost = calculate_redshift_storage_cost(cluster, region)
                    
                    if monthly_cost > 10.0:  # Only flag if cost > £10/month
                        waste_items.append({
                            'resource_id': cluster_identifier,
                            'resource_type': 'Redshift Cluster (Paused)',
                            'region': region,
                            'monthly_cost': monthly_cost,
                            'annual_cost': monthly_cost * 12,
                            'age_days': age_days,
                            'details': {
                                'cluster_identifier': cluster_identifier,
                                'status': cluster_status,
                                'node_type': node_type,
                                'number_of_nodes': number_of_nodes,
                                'created_time': created_time.isoformat(),
                                'db_name': cluster.get('DBName', 'Unknown'),
                                'master_username': cluster.get('MasterUsername', 'Unknown')
                            },
                            'confidence': 'High',
                            'risk_level': 'Medium',
                            'reason': f'Paused cluster still incurring storage costs (£{monthly_cost:.2f}/month)'
                        })
                
                elif cluster_status == 'available':
                    # Check if cluster is unused (no queries)
                    query_count = check_redshift_usage(cloudwatch, cluster_identifier, days=30)
                    
                    if query_count == 0:
                        # Unused cluster
                        monthly_cost = calculate_redshift_cost(cluster, region)
                        
                        if monthly_cost > 50.0:  # Only flag if cost > £50/month
                            waste_items.append({
                                'resource_id': cluster_identifier,
                                'resource_type': 'Redshift Cluster (Unused)',
                                'region': region,
                                'monthly_cost': monthly_cost,
                                'annual_cost': monthly_cost * 12,
                                'age_days': age_days,
                                'details': {
                                    'cluster_identifier': cluster_identifier,
                                    'status': cluster_status,
                                    'node_type': node_type,
                                    'number_of_nodes': number_of_nodes,
                                    'created_time': created_time.isoformat(),
                                    'db_name': cluster.get('DBName', 'Unknown'),
                                    'master_username': cluster.get('MasterUsername', 'Unknown'),
                                    'queries_30d': query_count
                                },
                                'confidence': 'High',
                                'risk_level': 'High',
                                'reason': f'No queries in 30 days (£{monthly_cost:.2f}/month)'
                            })
                    
                    elif query_count > 0:
                        # Check for underutilization
                        avg_cpu_utilization = check_redshift_utilization(cloudwatch, cluster_identifier, days=30)
                        
                        if avg_cpu_utilization is not None and avg_cpu_utilization < 10:  # Less than 10% CPU
                            monthly_cost = calculate_redshift_cost(cluster, region)
                            
                            if monthly_cost > 100.0:  # Only flag expensive underutilized clusters
                                waste_items.append({
                                    'resource_id': cluster_identifier,
                                    'resource_type': 'Redshift Cluster (Underutilized)',
                                    'region': region,
                                    'monthly_cost': monthly_cost * 0.5,  # Potential savings from downsizing
                                    'annual_cost': monthly_cost * 0.5 * 12,
                                    'age_days': age_days,
                                    'details': {
                                        'cluster_identifier': cluster_identifier,
                                        'status': cluster_status,
                                        'node_type': node_type,
                                        'number_of_nodes': number_of_nodes,
                                        'avg_cpu_utilization': avg_cpu_utilization,
                                        'created_time': created_time.isoformat(),
                                        'queries_30d': query_count,
                                        'current_monthly_cost': monthly_cost
                                    },
                                    'confidence': 'Medium',
                                    'risk_level': 'Medium',
                                    'reason': f'Low CPU utilization ({avg_cpu_utilization:.1f}%) - consider downsizing (£{monthly_cost * 0.5:.2f}/month potential savings)'
                                })
        
        return waste_items
        
    except ClientError as e:
        print(f"Error scanning Redshift clusters in {region}: {e}")
        return []


def check_redshift_usage(cloudwatch, cluster_identifier, days=30):
    """
    Check Redshift cluster query count in the specified period
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Check DatabaseConnections metric as a proxy for usage
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/Redshift',
            MetricName='DatabaseConnections',
            Dimensions=[
                {
                    'Name': 'ClusterIdentifier',
                    'Value': cluster_identifier
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # Daily
            Statistics=['Maximum']
        )
        
        # Check if there were any connections
        if not response['Datapoints']:
            return 0
            
        max_connections = max([point['Maximum'] for point in response['Datapoints']])
        return int(max_connections)
        
    except ClientError:
        # If we can't get metrics, assume it's used (conservative)
        return 1


def check_redshift_utilization(cloudwatch, cluster_identifier, days=30):
    """
    Check Redshift cluster CPU utilization in the specified period
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Check CPUUtilization metric
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/Redshift',
            MetricName='CPUUtilization',
            Dimensions=[
                {
                    'Name': 'ClusterIdentifier',
                    'Value': cluster_identifier
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


def calculate_redshift_cost(cluster, region):
    """
    Calculate monthly Redshift cluster cost based on node type and count
    """
    node_type = cluster['NodeType']
    number_of_nodes = cluster['NumberOfNodes']
    
    # Simplified Redshift pricing (approximate for major regions)
    # Prices per node per month
    node_prices = {
        'dc2.large': 180.00,
        'dc2.8xlarge': 4800.00,
        'ds2.xlarge': 850.00,
        'ds2.8xlarge': 6800.00,
        'ra3.xlplus': 3250.00,
        'ra3.4xlarge': 13000.00,
        'ra3.16xlarge': 52000.00
    }
    
    # Get price per node
    price_per_node = node_prices.get(node_type, 500.00)  # Default fallback
    
    # Calculate total monthly cost
    total_monthly_cost = price_per_node * number_of_nodes
    
    return max(total_monthly_cost, 50.00)


def calculate_redshift_storage_cost(cluster, region):
    """
    Calculate monthly Redshift storage cost for paused clusters
    """
    # For paused clusters, only storage costs apply
    # Simplified calculation based on typical storage usage
    
    node_type = cluster['NodeType']
    number_of_nodes = cluster['NumberOfNodes']
    
    # Estimate storage based on node type and count
    if 'dc2' in node_type:
        # DC2 nodes have SSD storage
        storage_per_node_gb = 160 if 'large' in node_type else 2560
    elif 'ds2' in node_type:
        # DS2 nodes have HDD storage
        storage_per_node_gb = 2000 if 'xlarge' in node_type else 16000
    elif 'ra3' in node_type:
        # RA3 nodes use managed storage (separate billing)
        storage_per_node_gb = 1000  # Estimated average
    else:
        storage_per_node_gb = 1000  # Default estimate
    
    total_storage_gb = storage_per_node_gb * number_of_nodes
    
    # Storage cost per GB per month (approximate)
    storage_cost_per_gb = 0.024  # £0.024 per GB/month
    
    monthly_storage_cost = total_storage_gb * storage_cost_per_gb
    
    return max(monthly_storage_cost, 10.00)