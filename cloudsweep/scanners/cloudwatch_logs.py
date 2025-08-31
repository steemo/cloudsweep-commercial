"""
CloudWatch Log Groups Scanner - Detects unused and over-retained log groups
"""

import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError


def scan_cloudwatch_log_groups(session, region, days=60):
    """
    Scan for unused and over-retained CloudWatch Log Groups that are incurring costs
    
    Returns list of waste items with cost calculations
    """
    try:
        logs_client = session.client('logs', region_name=region)
        
        waste_items = []
        
        # Get all log groups with pagination
        paginator = logs_client.get_paginator('describe_log_groups')
        
        for page in paginator.paginate():
            for log_group in page['logGroups']:
                log_group_name = log_group['logGroupName']
                creation_time = log_group['creationTime']
                retention_days = log_group.get('retentionInDays', None)  # None means "never expire"
                stored_bytes = log_group.get('storedBytes', 0)
                
                # Convert creation time from epoch milliseconds
                created_date = datetime.fromtimestamp(creation_time / 1000)
                age_days = (datetime.now() - created_date).days
                
                # Skip recently created log groups (safety check)
                if age_days < 30:
                    continue
                
                # Check for unused log groups (no recent log events)
                if check_log_group_unused(logs_client, log_group_name, days):
                    monthly_cost = calculate_log_group_cost(stored_bytes, retention_days)
                    
                    if monthly_cost > 0.50:  # Only flag if cost > £0.50/month
                        waste_items.append({
                            'resource_id': log_group_name,
                            'resource_type': 'CloudWatch Log Group (Unused)',
                            'region': region,
                            'monthly_cost': monthly_cost,
                            'annual_cost': monthly_cost * 12,
                            'age_days': age_days,
                            'details': {
                                'log_group_name': log_group_name,
                                'stored_bytes': stored_bytes,
                                'stored_gb': stored_bytes / (1024**3) if stored_bytes > 0 else 0,
                                'retention_days': retention_days,
                                'retention_policy': 'Never expire' if retention_days is None else f'{retention_days} days',
                                'creation_time': created_date.isoformat(),
                                'last_activity_days': days
                            },
                            'confidence': 'High',
                            'risk_level': 'Low',
                            'reason': f'No log events in {days} days (£{monthly_cost:.2f}/month storage cost)'
                        })
                
                # Check for over-retained log groups (never expire policy with significant storage)
                elif retention_days is None and stored_bytes > 1024**3:  # > 1GB and never expire
                    monthly_cost = calculate_log_group_cost(stored_bytes, retention_days)
                    
                    if monthly_cost > 5.00:  # Only flag expensive over-retention
                        waste_items.append({
                            'resource_id': log_group_name,
                            'resource_type': 'CloudWatch Log Group (Over-retained)',
                            'region': region,
                            'monthly_cost': monthly_cost * 0.7,  # Potential savings from setting retention
                            'annual_cost': monthly_cost * 0.7 * 12,
                            'age_days': age_days,
                            'details': {
                                'log_group_name': log_group_name,
                                'stored_bytes': stored_bytes,
                                'stored_gb': stored_bytes / (1024**3),
                                'retention_days': retention_days,
                                'retention_policy': 'Never expire',
                                'creation_time': created_date.isoformat(),
                                'current_monthly_cost': monthly_cost,
                                'recommended_retention': '90 days'
                            },
                            'confidence': 'Medium',
                            'risk_level': 'Low',
                            'reason': f'Never expire policy with {stored_bytes/(1024**3):.1f}GB - consider 90-day retention (£{monthly_cost * 0.7:.2f}/month potential savings)'
                        })
        
        return waste_items
        
    except ClientError as e:
        print(f"Error scanning CloudWatch Log Groups in {region}: {e}")
        return []


def check_log_group_unused(logs_client, log_group_name, days):
    """
    Check if log group has had any log events in the specified period
    """
    try:
        # Calculate time range (CloudWatch Logs uses epoch milliseconds)
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        # Get log streams for this log group
        try:
            streams_response = logs_client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=10  # Check only recent streams
            )
            
            # Check if any stream has recent activity
            for stream in streams_response['logStreams']:
                last_event_time = stream.get('lastEventTime', 0)
                if last_event_time > start_time:
                    return False  # Found recent activity
            
            return True  # No recent activity found
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return True  # Log group exists but no streams = unused
            else:
                return False  # Conservative approach on other errors
        
    except Exception:
        return False  # Conservative approach


def calculate_log_group_cost(stored_bytes, retention_days):
    """
    Calculate monthly CloudWatch Logs cost based on storage
    """
    if stored_bytes == 0:
        return 0.0
    
    # Convert bytes to GB
    stored_gb = stored_bytes / (1024**3)
    
    # CloudWatch Logs pricing (approximate)
    # £0.50 per GB per month for log storage
    storage_cost_per_gb = 0.50
    
    monthly_storage_cost = stored_gb * storage_cost_per_gb
    
    # Minimum cost for tracking
    return max(monthly_storage_cost, 0.10)


def get_log_group_size_estimate(logs_client, log_group_name):
    """
    Get estimated size of log group by sampling recent log streams
    """
    try:
        # Get recent log streams
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        total_size = 0
        for stream in streams_response['logStreams']:
            stored_bytes = stream.get('storedBytes', 0)
            total_size += stored_bytes
        
        return total_size
        
    except Exception:
        return 0


def check_log_group_retention_policy(retention_days):
    """
    Analyze retention policy and suggest optimizations
    """
    if retention_days is None:
        return {
            'policy': 'Never expire',
            'recommendation': 'Set 90-day retention',
            'risk': 'High storage costs over time',
            'potential_savings': 0.7  # 70% savings from setting retention
        }
    elif retention_days > 365:
        return {
            'policy': f'{retention_days} days',
            'recommendation': 'Consider 90-180 day retention',
            'risk': 'Excessive long-term storage',
            'potential_savings': 0.3  # 30% savings from shorter retention
        }
    else:
        return {
            'policy': f'{retention_days} days',
            'recommendation': 'Retention policy appropriate',
            'risk': 'Low',
            'potential_savings': 0.0
        }