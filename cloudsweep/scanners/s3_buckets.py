"""
S3 Buckets Scanner - Detects empty and unused S3 buckets
"""

import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError


def scan_s3_buckets(session, region):
    """
    Scan for empty and unused S3 buckets that are incurring costs
    
    Returns list of waste items with cost calculations
    """
    try:
        s3_client = session.client('s3', region_name=region)
        cloudwatch = session.client('cloudwatch', region_name=region)
        
        waste_items = []
        
        # Get all S3 buckets
        response = s3_client.list_buckets()
        
        for bucket in response['Buckets']:
            bucket_name = bucket['Name']
            creation_date = bucket['CreationDate']
            
            # Calculate age in days
            age_days = (datetime.now(creation_date.tzinfo) - creation_date).days
            
            # Skip recently created buckets (safety check)
            if age_days < 30:
                continue
            
            # Get bucket region (S3 buckets have specific regions)
            try:
                bucket_region = s3_client.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
                if bucket_region is None:
                    bucket_region = 'us-east-1'  # Default region
                
                # Only scan buckets in the current region
                if bucket_region != region and region != 'us-east-1':
                    continue
                    
            except ClientError:
                continue  # Skip if we can't determine region
            
            # Check if bucket is empty
            is_empty = check_bucket_empty(s3_client, bucket_name)
            
            if is_empty:
                # Empty bucket
                monthly_cost = calculate_s3_bucket_cost(bucket_name, 0, 0, region)
                
                waste_items.append({
                    'resource_id': bucket_name,
                    'resource_type': 'S3 Bucket (Empty)',
                    'region': bucket_region,
                    'monthly_cost': monthly_cost,
                    'annual_cost': monthly_cost * 12,
                    'age_days': age_days,
                    'details': {
                        'bucket_region': bucket_region,
                        'creation_date': creation_date.isoformat(),
                        'object_count': 0,
                        'storage_gb': 0
                    },
                    'confidence': 'High',
                    'risk_level': 'Low',
                    'reason': f'Empty bucket incurring base costs (£{monthly_cost:.2f}/month)'
                })
            
            else:
                # Check if bucket is unused (no requests)
                request_count = check_bucket_usage(cloudwatch, bucket_name, days=90)  # 90 days for S3
                
                if request_count == 0:
                    # Get bucket size for cost calculation
                    storage_gb, object_count = get_bucket_size(s3_client, bucket_name)
                    
                    if storage_gb > 0:  # Only flag if there's actual storage cost
                        monthly_cost = calculate_s3_bucket_cost(bucket_name, storage_gb, object_count, region)
                        
                        if monthly_cost > 1.0:  # Only flag if cost > £1/month
                            waste_items.append({
                                'resource_id': bucket_name,
                                'resource_type': 'S3 Bucket (Unused)',
                                'region': bucket_region,
                                'monthly_cost': monthly_cost,
                                'annual_cost': monthly_cost * 12,
                                'age_days': age_days,
                                'details': {
                                    'bucket_region': bucket_region,
                                    'creation_date': creation_date.isoformat(),
                                    'object_count': object_count,
                                    'storage_gb': storage_gb,
                                    'requests_90d': request_count
                                },
                                'confidence': 'Medium',
                                'risk_level': 'Medium',
                                'reason': f'No requests in 90 days, {storage_gb:.1f}GB storage (£{monthly_cost:.2f}/month)'
                            })
        
        return waste_items
        
    except ClientError as e:
        print(f"Error scanning S3 buckets: {e}")
        return []


def check_bucket_empty(s3_client, bucket_name):
    """
    Check if S3 bucket is empty
    """
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
        return 'Contents' not in response
        
    except ClientError:
        # If we can't access the bucket, assume it's not empty (conservative)
        return False


def check_bucket_usage(cloudwatch, bucket_name, days=90):
    """
    Check S3 bucket request count in the specified period
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Check AllRequests metric
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/S3',
            MetricName='AllRequests',
            Dimensions=[
                {
                    'Name': 'BucketName',
                    'Value': bucket_name
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # Daily
            Statistics=['Sum']
        )
        
        # Sum all requests
        if not response['Datapoints']:
            return 0
            
        total_requests = sum([point['Sum'] for point in response['Datapoints']])
        return int(total_requests)
        
    except ClientError:
        # If we can't get metrics, assume it's used (conservative)
        return 1


def get_bucket_size(s3_client, bucket_name):
    """
    Get S3 bucket size and object count (simplified estimation)
    """
    try:
        # Use CloudWatch metrics for bucket size (more efficient than listing all objects)
        cloudwatch = boto3.client('cloudwatch')
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        
        # Get BucketSizeBytes metric
        size_response = cloudwatch.get_metric_statistics(
            Namespace='AWS/S3',
            MetricName='BucketSizeBytes',
            Dimensions=[
                {'Name': 'BucketName', 'Value': bucket_name},
                {'Name': 'StorageType', 'Value': 'StandardStorage'}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,
            Statistics=['Average']
        )
        
        # Get NumberOfObjects metric
        count_response = cloudwatch.get_metric_statistics(
            Namespace='AWS/S3',
            MetricName='NumberOfObjects',
            Dimensions=[
                {'Name': 'BucketName', 'Value': bucket_name},
                {'Name': 'StorageType', 'Value': 'AllStorageTypes'}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,
            Statistics=['Average']
        )
        
        storage_bytes = 0
        if size_response['Datapoints']:
            storage_bytes = size_response['Datapoints'][-1]['Average']
        
        object_count = 0
        if count_response['Datapoints']:
            object_count = int(count_response['Datapoints'][-1]['Average'])
        
        storage_gb = storage_bytes / (1024 ** 3)  # Convert to GB
        
        return storage_gb, object_count
        
    except ClientError:
        # Fallback: try to estimate by listing objects (limited sample)
        try:
            response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1000)
            
            if 'Contents' not in response:
                return 0, 0
            
            # Estimate based on sample
            sample_size = sum([obj['Size'] for obj in response['Contents']])
            sample_count = len(response['Contents'])
            
            # If we got the max keys, estimate total
            if sample_count == 1000 and response.get('IsTruncated', False):
                # Rough estimation - multiply by estimated total objects
                estimated_total_objects = sample_count * 10  # Conservative estimate
                estimated_total_size = sample_size * 10
            else:
                estimated_total_objects = sample_count
                estimated_total_size = sample_size
            
            storage_gb = estimated_total_size / (1024 ** 3)
            return storage_gb, estimated_total_objects
            
        except ClientError:
            return 0, 0


def calculate_s3_bucket_cost(bucket_name, storage_gb, object_count, region):
    """
    Calculate monthly S3 bucket cost based on storage and requests
    """
    # Simplified S3 pricing (approximate for major regions)
    # Standard storage: £0.023 per GB/month
    # Requests: £0.0004 per 1,000 PUT requests, £0.0004 per 10,000 GET requests
    
    storage_cost_per_gb = 0.023
    
    # Calculate storage cost
    storage_cost = storage_gb * storage_cost_per_gb
    
    # Base cost for bucket management (minimal)
    base_cost = 0.10
    
    # Total monthly cost
    total_cost = storage_cost + base_cost
    
    # Minimum cost for tracking
    return max(total_cost, 0.10)