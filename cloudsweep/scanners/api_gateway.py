"""
API Gateway Scanner - Detects unused and over-provisioned API Gateway instances
"""

import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError


def scan_api_gateway(session, region):
    """
    Scan for unused and over-provisioned API Gateway instances that are incurring costs
    
    Returns list of waste items with cost calculations
    """
    try:
        apigateway_client = session.client('apigateway', region_name=region)
        apigatewayv2_client = session.client('apigatewayv2', region_name=region)
        cloudwatch = session.client('cloudwatch', region_name=region)
        
        waste_items = []
        
        # Scan REST APIs (API Gateway v1)
        waste_items.extend(scan_rest_apis(apigateway_client, cloudwatch, region))
        
        # Scan HTTP APIs (API Gateway v2)
        waste_items.extend(scan_http_apis(apigatewayv2_client, cloudwatch, region))
        
        return waste_items
        
    except ClientError as e:
        print(f"Error scanning API Gateway in {region}: {e}")
        return []


def scan_rest_apis(apigateway_client, cloudwatch, region):
    """
    Scan REST APIs for unused instances
    """
    waste_items = []
    
    try:
        # Get all REST APIs
        paginator = apigateway_client.get_paginator('get_rest_apis')
        
        for page in paginator.paginate():
            for api in page['items']:
                api_id = api['id']
                api_name = api['name']
                created_date = api['createdDate']
                
                # Calculate age in days
                age_days = (datetime.now(created_date.tzinfo) - created_date).days
                
                # Skip recently created APIs (safety check)
                if age_days < 30:
                    continue
                
                # Check if API is unused (no requests)
                request_count = check_api_usage(cloudwatch, api_id, 'REST', days=30)
                
                if request_count == 0:
                    # Get stages to calculate cost
                    stages = get_api_stages(apigateway_client, api_id)
                    monthly_cost = calculate_api_gateway_cost(api, stages, 'REST', region)
                    
                    if monthly_cost > 1.0:  # Only flag if cost > £1/month
                        waste_items.append({
                            'resource_id': api_id,
                            'resource_type': 'API Gateway REST API (Unused)',
                            'region': region,
                            'monthly_cost': monthly_cost,
                            'annual_cost': monthly_cost * 12,
                            'age_days': age_days,
                            'details': {
                                'api_name': api_name,
                                'api_type': 'REST',
                                'stages': len(stages),
                                'created_date': created_date.isoformat(),
                                'requests_30d': request_count
                            },
                            'confidence': 'High',
                            'risk_level': 'Low',
                            'reason': f'No requests in 30 days (£{monthly_cost:.2f}/month)'
                        })
        
    except ClientError as e:
        print(f"Error scanning REST APIs: {e}")
    
    return waste_items


def scan_http_apis(apigatewayv2_client, cloudwatch, region):
    """
    Scan HTTP APIs (API Gateway v2) for unused instances
    """
    waste_items = []
    
    try:
        # Get all HTTP APIs
        paginator = apigatewayv2_client.get_paginator('get_apis')
        
        for page in paginator.paginate():
            for api in page['Items']:
                api_id = api['ApiId']
                api_name = api['Name']
                created_date = api['CreatedDate']
                protocol_type = api['ProtocolType']
                
                # Calculate age in days
                age_days = (datetime.now(created_date.tzinfo) - created_date).days
                
                # Skip recently created APIs (safety check)
                if age_days < 30:
                    continue
                
                # Check if API is unused (no requests)
                request_count = check_api_usage(cloudwatch, api_id, 'HTTP', days=30)
                
                if request_count == 0:
                    # Get stages to calculate cost
                    stages = get_http_api_stages(apigatewayv2_client, api_id)
                    monthly_cost = calculate_api_gateway_cost(api, stages, 'HTTP', region)
                    
                    if monthly_cost > 1.0:  # Only flag if cost > £1/month
                        waste_items.append({
                            'resource_id': api_id,
                            'resource_type': 'API Gateway HTTP API (Unused)',
                            'region': region,
                            'monthly_cost': monthly_cost,
                            'annual_cost': monthly_cost * 12,
                            'age_days': age_days,
                            'details': {
                                'api_name': api_name,
                                'api_type': protocol_type,
                                'stages': len(stages),
                                'created_date': created_date.isoformat(),
                                'requests_30d': request_count
                            },
                            'confidence': 'High',
                            'risk_level': 'Low',
                            'reason': f'No requests in 30 days (£{monthly_cost:.2f}/month)'
                        })
        
    except ClientError as e:
        print(f"Error scanning HTTP APIs: {e}")
    
    return waste_items


def check_api_usage(cloudwatch, api_id, api_type, days=30):
    """
    Check API Gateway request count in the specified period
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Check Count metric (total requests)
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/ApiGateway',
            MetricName='Count',
            Dimensions=[
                {
                    'Name': 'ApiName' if api_type == 'REST' else 'ApiId',
                    'Value': api_id
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


def get_api_stages(apigateway_client, api_id):
    """
    Get REST API stages
    """
    try:
        response = apigateway_client.get_stages(restApiId=api_id)
        return response['item']
    except ClientError:
        return []


def get_http_api_stages(apigatewayv2_client, api_id):
    """
    Get HTTP API stages
    """
    try:
        response = apigatewayv2_client.get_stages(ApiId=api_id)
        return response['Items']
    except ClientError:
        return []


def calculate_api_gateway_cost(api, stages, api_type, region):
    """
    Calculate monthly API Gateway cost based on type and stages
    """
    # Simplified API Gateway pricing (approximate)
    # REST API: £3.50 per million requests + £0.09 per caching hour
    # HTTP API: £1.00 per million requests (cheaper)
    
    base_monthly_cost = 2.00  # Base cost for API management
    
    # Cost per stage (approximate)
    stage_cost = 1.00  # £1 per stage per month
    
    # Calculate based on API type
    if api_type == 'REST':
        # REST APIs typically cost more due to additional features
        api_cost = base_monthly_cost + (len(stages) * stage_cost * 1.5)
    else:
        # HTTP APIs are cheaper
        api_cost = base_monthly_cost + (len(stages) * stage_cost)
    
    # Minimum cost for tracking
    return max(api_cost, 1.00)


def get_api_gateway_integrations(apigateway_client, api_id):
    """
    Get API Gateway integrations for more detailed analysis
    """
    try:
        # Get resources
        resources = apigateway_client.get_resources(restApiId=api_id)
        
        integration_count = 0
        for resource in resources['items']:
            resource_id = resource['id']
            
            # Check each HTTP method
            for method in resource.get('resourceMethods', {}):
                try:
                    integration = apigateway_client.get_integration(
                        restApiId=api_id,
                        resourceId=resource_id,
                        httpMethod=method
                    )
                    integration_count += 1
                except ClientError:
                    continue
        
        return integration_count
        
    except ClientError:
        return 0