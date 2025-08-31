"""
CloudFront Distributions Scanner - Detects unused CloudFront CDN distributions
"""

import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError


def scan_cloudfront_distributions(session, region):
    """
    Scan for unused CloudFront distributions that are incurring costs
    
    Returns list of waste items with cost calculations
    """
    try:
        # CloudFront is global service, always use us-east-1
        cloudfront_client = session.client('cloudfront', region_name='us-east-1')
        cloudwatch = session.client('cloudwatch', region_name='us-east-1')
        
        waste_items = []
        
        # Get all CloudFront distributions
        paginator = cloudfront_client.get_paginator('list_distributions')
        
        for page in paginator.paginate():
            if 'Items' not in page['DistributionList']:
                continue
                
            for distribution in page['DistributionList']['Items']:
                distribution_id = distribution['Id']
                domain_name = distribution['DomainName']
                status = distribution['Status']
                enabled = distribution['Enabled']
                last_modified = distribution['LastModifiedTime']
                
                # Calculate age in days
                age_days = (datetime.now(last_modified.tzinfo) - last_modified).days
                
                # Skip recently created distributions (safety check)
                if age_days < 30:
                    continue
                
                # Only check enabled distributions (disabled ones don't incur significant costs)
                if not enabled:
                    continue
                
                # Check if distribution is unused (no requests)
                is_unused = check_cloudfront_usage(cloudwatch, distribution_id, days=30)
                
                if is_unused:
                    # Calculate monthly cost
                    monthly_cost = calculate_cloudfront_cost(distribution, region)
                    
                    # Get additional distribution details
                    try:
                        dist_config = cloudfront_client.get_distribution_config(Id=distribution_id)
                        origins_count = len(dist_config['DistributionConfig'].get('Origins', {}).get('Items', []))
                        price_class = dist_config['DistributionConfig'].get('PriceClass', 'PriceClass_All')
                    except ClientError:
                        origins_count = 1
                        price_class = 'PriceClass_All'
                    
                    waste_items.append({
                        'resource_id': distribution_id,
                        'resource_type': 'CloudFront Distribution',
                        'region': 'Global',
                        'monthly_cost': monthly_cost,
                        'annual_cost': monthly_cost * 12,
                        'age_days': age_days,
                        'details': {
                            'domain_name': domain_name,
                            'status': status,
                            'enabled': enabled,
                            'origins_count': origins_count,
                            'price_class': price_class,
                            'last_modified': last_modified.isoformat()
                        },
                        'confidence': 'High',
                        'risk_level': 'Low',
                        'reason': f'No requests detected in 30 days (£{monthly_cost:.2f}/month)'
                    })
        
        return waste_items
        
    except ClientError as e:
        print(f"Error scanning CloudFront distributions: {e}")
        return []


def check_cloudfront_usage(cloudwatch, distribution_id, days=30):
    """
    Check if CloudFront distribution has had any requests in the specified period
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Check Requests metric
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/CloudFront',
            MetricName='Requests',
            Dimensions=[
                {
                    'Name': 'DistributionId',
                    'Value': distribution_id
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # Daily
            Statistics=['Sum']
        )
        
        # If no data points or all zeros, consider unused
        if not response['Datapoints']:
            return True
            
        total_requests = sum([point['Sum'] for point in response['Datapoints']])
        return total_requests == 0
        
    except ClientError:
        # If we can't get metrics, be conservative and don't flag as unused
        return False


def calculate_cloudfront_cost(distribution, region):
    """
    Calculate monthly CloudFront distribution cost (simplified pricing)
    """
    # Base monthly cost for CloudFront distribution
    base_monthly_cost = 0.60  # £0.60 per month minimum
    
    # Additional costs based on price class
    price_class = distribution.get('PriceClass', 'PriceClass_All')
    
    price_class_multipliers = {
        'PriceClass_100': 1.0,      # US, Canada, Europe
        'PriceClass_200': 1.2,      # + Asia Pacific
        'PriceClass_All': 1.5       # All edge locations
    }
    
    multiplier = price_class_multipliers.get(price_class, 1.5)
    
    # Estimate based on typical unused distribution costs
    # Most unused distributions have minimal data transfer but still incur base costs
    estimated_monthly_cost = base_monthly_cost * multiplier
    
    # Add estimated data transfer costs for unused distributions (very minimal)
    estimated_monthly_cost += 2.0  # Small amount for any residual traffic
    
    # Typical range for unused CloudFront distributions: £3-15/month
    # But can be much higher if they were previously active
    return max(estimated_monthly_cost, 3.0)


def get_cloudfront_origins_info(cloudfront_client, distribution_id):
    """
    Get information about CloudFront distribution origins
    """
    try:
        response = cloudfront_client.get_distribution_config(Id=distribution_id)
        origins = response['DistributionConfig'].get('Origins', {}).get('Items', [])
        
        origin_info = []
        for origin in origins:
            origin_info.append({
                'id': origin['Id'],
                'domain_name': origin['DomainName'],
                'origin_path': origin.get('OriginPath', ''),
            })
        
        return origin_info
        
    except ClientError:
        return []