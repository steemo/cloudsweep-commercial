"""
RDS Instances Scanner - Detects stopped and unused RDS database instances
"""

import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError


def scan_rds_instances(session, region):
    """
    Scan for stopped and unused RDS instances that are incurring costs
    
    Returns list of waste items with cost calculations
    """
    try:
        rds_client = session.client('rds', region_name=region)
        cloudwatch = session.client('cloudwatch', region_name=region)
        
        waste_items = []
        
        # Get all RDS instances
        paginator = rds_client.get_paginator('describe_db_instances')
        
        for page in paginator.paginate():
            for instance in page['DBInstances']:
                db_instance_id = instance['DBInstanceIdentifier']
                instance_class = instance['DBInstanceClass']
                engine = instance['Engine']
                status = instance['DBInstanceStatus']
                created_time = instance['InstanceCreateTime']
                
                # Calculate age in days
                age_days = (datetime.now(created_time.tzinfo) - created_time).days
                
                # Skip recently created instances (safety check)
                if age_days < 30:
                    continue
                
                # Check for stopped instances (still incurring storage costs)
                if status == 'stopped':
                    storage_gb = instance.get('AllocatedStorage', 0)
                    storage_type = instance.get('StorageType', 'gp2')
                    
                    # Calculate monthly storage cost
                    monthly_cost = calculate_rds_storage_cost(storage_gb, storage_type, region)
                    
                    waste_items.append({
                        'resource_id': db_instance_id,
                        'resource_type': 'RDS Instance (Stopped)',
                        'region': region,
                        'monthly_cost': monthly_cost,
                        'annual_cost': monthly_cost * 12,
                        'age_days': age_days,
                        'details': {
                            'instance_class': instance_class,
                            'engine': engine,
                            'status': status,
                            'storage_gb': storage_gb,
                            'storage_type': storage_type
                        },
                        'confidence': 'High',
                        'risk_level': 'Low',
                        'reason': f'Stopped RDS instance still incurring storage costs (£{monthly_cost:.2f}/month)'
                    })
                
                # Check for unused running instances (no connections)
                elif status == 'available':
                    # Check CloudWatch metrics for database connections
                    is_unused = check_rds_usage(cloudwatch, db_instance_id, days=30)
                    
                    if is_unused:
                        # Calculate full instance cost
                        monthly_cost = calculate_rds_instance_cost(instance_class, engine, region)
                        
                        waste_items.append({
                            'resource_id': db_instance_id,
                            'resource_type': 'RDS Instance (Unused)',
                            'region': region,
                            'monthly_cost': monthly_cost,
                            'annual_cost': monthly_cost * 12,
                            'age_days': age_days,
                            'details': {
                                'instance_class': instance_class,
                                'engine': engine,
                                'status': status,
                                'allocated_storage': instance.get('AllocatedStorage', 0)
                            },
                            'confidence': 'High',
                            'risk_level': 'Medium',
                            'reason': f'No database connections detected in 30 days (£{monthly_cost:.2f}/month)'
                        })
        
        return waste_items
        
    except ClientError as e:
        print(f"Error scanning RDS instances in {region}: {e}")
        return []


def check_rds_usage(cloudwatch, db_instance_id, days=30):
    """
    Check if RDS instance has had any connections in the specified period
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Check DatabaseConnections metric
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='DatabaseConnections',
            Dimensions=[
                {
                    'Name': 'DBInstanceIdentifier',
                    'Value': db_instance_id
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # Daily
            Statistics=['Maximum']
        )
        
        # If no data points or all zeros, consider unused
        if not response['Datapoints']:
            return True
            
        max_connections = max([point['Maximum'] for point in response['Datapoints']])
        return max_connections == 0
        
    except ClientError:
        # If we can't get metrics, be conservative and don't flag as unused
        return False


def calculate_rds_storage_cost(storage_gb, storage_type, region):
    """
    Calculate monthly RDS storage cost based on storage type and size
    """
    # Simplified pricing for major regions (approximate)
    storage_prices = {
        'gp2': 0.115,      # £0.115 per GB/month
        'gp3': 0.092,      # £0.092 per GB/month  
        'io1': 0.138,      # £0.138 per GB/month
        'io2': 0.138,      # £0.138 per GB/month
        'magnetic': 0.115   # £0.115 per GB/month
    }
    
    price_per_gb = storage_prices.get(storage_type, 0.115)
    return storage_gb * price_per_gb


def calculate_rds_instance_cost(instance_class, engine, region):
    """
    Calculate monthly RDS instance cost (simplified pricing)
    """
    # Simplified pricing for common instance types (approximate)
    instance_prices = {
        'db.t3.micro': 18.50,
        'db.t3.small': 37.00,
        'db.t3.medium': 74.00,
        'db.t3.large': 148.00,
        'db.t3.xlarge': 296.00,
        'db.t3.2xlarge': 592.00,
        'db.m5.large': 185.00,
        'db.m5.xlarge': 370.00,
        'db.m5.2xlarge': 740.00,
        'db.m5.4xlarge': 1480.00,
        'db.r5.large': 230.00,
        'db.r5.xlarge': 460.00,
        'db.r5.2xlarge': 920.00,
    }
    
    # Default cost if instance type not found
    base_cost = instance_prices.get(instance_class, 100.00)
    
    # Engine multipliers (some engines cost more)
    engine_multipliers = {
        'mysql': 1.0,
        'postgres': 1.0,
        'mariadb': 1.0,
        'oracle-ee': 2.5,
        'oracle-se2': 1.8,
        'sqlserver-ee': 3.0,
        'sqlserver-se': 2.0,
        'sqlserver-ex': 1.0,
        'sqlserver-web': 1.2
    }
    
    multiplier = engine_multipliers.get(engine, 1.0)
    return base_cost * multiplier