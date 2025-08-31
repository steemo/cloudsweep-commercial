"""
Lambda Functions Scanner - Detects unused and over-provisioned Lambda functions
"""

import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError


def scan_lambda_functions(session, region):
    """
    Scan for unused and over-provisioned Lambda functions that are incurring costs
    
    Returns list of waste items with cost calculations
    """
    try:
        lambda_client = session.client('lambda', region_name=region)
        cloudwatch = session.client('cloudwatch', region_name=region)
        
        waste_items = []
        
        # Get all Lambda functions
        paginator = lambda_client.get_paginator('list_functions')
        
        for page in paginator.paginate():
            for function in page['Functions']:
                function_name = function['FunctionName']
                memory_size = function['MemorySize']
                runtime = function['Runtime']
                last_modified = function['LastModified']
                
                # Parse last modified date
                last_modified_date = datetime.strptime(last_modified, '%Y-%m-%dT%H:%M:%S.%f%z')
                age_days = (datetime.now(last_modified_date.tzinfo) - last_modified_date).days
                
                # Skip recently created functions (safety check)
                if age_days < 30:
                    continue
                
                # Check if function is unused (no invocations)
                invocation_count = check_lambda_usage(cloudwatch, function_name, days=30)
                
                if invocation_count == 0:
                    # Unused function
                    monthly_cost = calculate_lambda_cost(memory_size, 0, region)
                    
                    waste_items.append({
                        'resource_id': function_name,
                        'resource_type': 'Lambda Function (Unused)',
                        'region': region,
                        'monthly_cost': monthly_cost,
                        'annual_cost': monthly_cost * 12,
                        'age_days': age_days,
                        'details': {
                            'memory_size': memory_size,
                            'runtime': runtime,
                            'last_modified': last_modified,
                            'invocations_30d': invocation_count
                        },
                        'confidence': 'High',
                        'risk_level': 'Low',
                        'reason': f'No invocations in 30 days (£{monthly_cost:.2f}/month potential)'
                    })
                
                elif invocation_count > 0:
                    # Check for over-provisioning
                    avg_duration, avg_memory_used = check_lambda_performance(cloudwatch, function_name, days=30)
                    
                    if avg_memory_used > 0 and memory_size > avg_memory_used * 2:
                        # Over-provisioned (using less than 50% of allocated memory)
                        optimized_memory = max(128, int(avg_memory_used * 1.2))  # 20% buffer
                        current_cost = calculate_lambda_cost(memory_size, invocation_count, region)
                        optimized_cost = calculate_lambda_cost(optimized_memory, invocation_count, region)
                        monthly_savings = current_cost - optimized_cost
                        
                        if monthly_savings > 1.0:  # Only flag if savings > £1/month
                            waste_items.append({
                                'resource_id': function_name,
                                'resource_type': 'Lambda Function (Over-provisioned)',
                                'region': region,
                                'monthly_cost': monthly_savings,
                                'annual_cost': monthly_savings * 12,
                                'age_days': age_days,
                                'details': {
                                    'current_memory': memory_size,
                                    'recommended_memory': optimized_memory,
                                    'avg_memory_used': avg_memory_used,
                                    'invocations_30d': invocation_count,
                                    'current_monthly_cost': current_cost,
                                    'optimized_monthly_cost': optimized_cost
                                },
                                'confidence': 'Medium',
                                'risk_level': 'Low',
                                'reason': f'Over-provisioned memory: {memory_size}MB → {optimized_memory}MB (£{monthly_savings:.2f}/month savings)'
                            })
        
        return waste_items
        
    except ClientError as e:
        print(f"Error scanning Lambda functions in {region}: {e}")
        return []


def check_lambda_usage(cloudwatch, function_name, days=30):
    """
    Check Lambda function invocation count in the specified period
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Check Invocations metric
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='Invocations',
            Dimensions=[
                {
                    'Name': 'FunctionName',
                    'Value': function_name
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # Daily
            Statistics=['Sum']
        )
        
        # Sum all invocations
        if not response['Datapoints']:
            return 0
            
        total_invocations = sum([point['Sum'] for point in response['Datapoints']])
        return int(total_invocations)
        
    except ClientError:
        # If we can't get metrics, assume it's used (conservative)
        return 1


def check_lambda_performance(cloudwatch, function_name, days=30):
    """
    Check Lambda function performance metrics to detect over-provisioning
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Get Duration metrics
        duration_response = cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='Duration',
            Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,
            Statistics=['Average']
        )
        
        avg_duration = 0
        if duration_response['Datapoints']:
            avg_duration = sum([point['Average'] for point in duration_response['Datapoints']]) / len(duration_response['Datapoints'])
        
        # Estimate memory usage (simplified calculation)
        # This is an approximation - actual memory usage requires custom metrics
        avg_memory_used = 0
        if avg_duration > 0:
            # Rough estimation: shorter duration often means less memory needed
            # This is a simplified heuristic
            if avg_duration < 1000:  # < 1 second
                avg_memory_used = 128
            elif avg_duration < 5000:  # < 5 seconds
                avg_memory_used = 256
            elif avg_duration < 15000:  # < 15 seconds
                avg_memory_used = 512
            else:
                avg_memory_used = 1024
        
        return avg_duration, avg_memory_used
        
    except ClientError:
        return 0, 0


def calculate_lambda_cost(memory_size, invocations_per_month, region):
    """
    Calculate monthly Lambda cost based on memory size and invocations
    """
    # Simplified Lambda pricing (approximate for major regions)
    # Price per GB-second: £0.0000166667
    # Price per request: £0.0000002
    
    gb_memory = memory_size / 1024.0
    
    # Estimate average duration (simplified)
    if invocations_per_month == 0:
        # For unused functions, estimate minimal cost
        return 0.50  # Small base cost for unused function
    
    # Estimate average execution time based on memory (heuristic)
    if memory_size <= 128:
        avg_duration_seconds = 2.0
    elif memory_size <= 512:
        avg_duration_seconds = 5.0
    elif memory_size <= 1024:
        avg_duration_seconds = 10.0
    else:
        avg_duration_seconds = 15.0
    
    # Calculate costs
    gb_seconds_per_month = gb_memory * avg_duration_seconds * invocations_per_month
    compute_cost = gb_seconds_per_month * 0.0000166667
    request_cost = invocations_per_month * 0.0000002
    
    total_monthly_cost = compute_cost + request_cost
    
    # Minimum cost for tracking purposes
    return max(total_monthly_cost, 0.10)