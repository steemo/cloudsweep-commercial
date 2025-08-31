"""
Elasticsearch/OpenSearch Scanner - Detects unused and over-provisioned search clusters
"""

import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError


def scan_elasticsearch_clusters(session, region):
    """
    Scan for unused and over-provisioned Elasticsearch/OpenSearch clusters that are incurring costs
    
    Returns list of waste items with cost calculations
    """
    try:
        es_client = session.client('es', region_name=region)
        opensearch_client = session.client('opensearch', region_name=region)
        cloudwatch = session.client('cloudwatch', region_name=region)
        
        waste_items = []
        
        # Scan Elasticsearch domains
        waste_items.extend(scan_elasticsearch_domains(es_client, cloudwatch, region))
        
        # Scan OpenSearch domains
        waste_items.extend(scan_opensearch_domains(opensearch_client, cloudwatch, region))
        
        return waste_items
        
    except ClientError as e:
        print(f"Error scanning Elasticsearch/OpenSearch in {region}: {e}")
        return []


def scan_elasticsearch_domains(es_client, cloudwatch, region):
    """
    Scan Elasticsearch domains for unused instances
    """
    waste_items = []
    
    try:
        # Get all Elasticsearch domains
        response = es_client.list_domain_names()
        
        for domain_info in response['DomainNames']:
            domain_name = domain_info['DomainName']
            
            # Get domain details
            domain_details = es_client.describe_elasticsearch_domain(DomainName=domain_name)
            domain = domain_details['DomainStatus']
            
            created_time = domain['Created']
            processing = domain['Processing']
            
            # Skip domains that are being processed/modified
            if processing:
                continue
            
            # Calculate age in days
            age_days = (datetime.now(created_time.tzinfo) - created_time).days
            
            # Skip recently created domains (safety check)
            if age_days < 30:
                continue
            
            # Check if domain is unused (no search requests)
            search_count = check_elasticsearch_usage(cloudwatch, domain_name, 'Elasticsearch', days=30)
            
            if search_count == 0:
                # Calculate monthly cost
                monthly_cost = calculate_elasticsearch_cost(domain, region)
                
                if monthly_cost > 10.0:  # Only flag if cost > £10/month
                    waste_items.append({
                        'resource_id': domain_name,
                        'resource_type': 'Elasticsearch Domain (Unused)',
                        'region': region,
                        'monthly_cost': monthly_cost,
                        'annual_cost': monthly_cost * 12,
                        'age_days': age_days,
                        'details': {
                            'domain_name': domain_name,
                            'elasticsearch_version': domain.get('ElasticsearchVersion', 'Unknown'),
                            'instance_type': domain.get('ElasticsearchClusterConfig', {}).get('InstanceType', 'Unknown'),
                            'instance_count': domain.get('ElasticsearchClusterConfig', {}).get('InstanceCount', 1),
                            'storage_type': domain.get('EBSOptions', {}).get('VolumeType', 'gp2'),
                            'storage_size': domain.get('EBSOptions', {}).get('VolumeSize', 10),
                            'created_time': created_time.isoformat(),
                            'search_requests_30d': search_count
                        },
                        'confidence': 'High',
                        'risk_level': 'Medium',
                        'reason': f'No search requests in 30 days (£{monthly_cost:.2f}/month)'
                    })
        
    except ClientError as e:
        print(f"Error scanning Elasticsearch domains: {e}")
    
    return waste_items


def scan_opensearch_domains(opensearch_client, cloudwatch, region):
    """
    Scan OpenSearch domains for unused instances
    """
    waste_items = []
    
    try:
        # Get all OpenSearch domains
        response = opensearch_client.list_domain_names()
        
        for domain_info in response['DomainNames']:
            domain_name = domain_info['DomainName']
            
            # Get domain details
            domain_details = opensearch_client.describe_domain(DomainName=domain_name)
            domain = domain_details['DomainStatus']
            
            created_time = domain['Created']
            processing = domain['Processing']
            
            # Skip domains that are being processed/modified
            if processing:
                continue
            
            # Calculate age in days
            age_days = (datetime.now(created_time.tzinfo) - created_time).days
            
            # Skip recently created domains (safety check)
            if age_days < 30:
                continue
            
            # Check if domain is unused (no search requests)
            search_count = check_elasticsearch_usage(cloudwatch, domain_name, 'OpenSearch', days=30)
            
            if search_count == 0:
                # Calculate monthly cost
                monthly_cost = calculate_opensearch_cost(domain, region)
                
                if monthly_cost > 10.0:  # Only flag if cost > £10/month
                    waste_items.append({
                        'resource_id': domain_name,
                        'resource_type': 'OpenSearch Domain (Unused)',
                        'region': region,
                        'monthly_cost': monthly_cost,
                        'annual_cost': monthly_cost * 12,
                        'age_days': age_days,
                        'details': {
                            'domain_name': domain_name,
                            'engine_version': domain.get('EngineVersion', 'Unknown'),
                            'instance_type': domain.get('ClusterConfig', {}).get('InstanceType', 'Unknown'),
                            'instance_count': domain.get('ClusterConfig', {}).get('InstanceCount', 1),
                            'storage_type': domain.get('EBSOptions', {}).get('VolumeType', 'gp3'),
                            'storage_size': domain.get('EBSOptions', {}).get('VolumeSize', 10),
                            'created_time': created_time.isoformat(),
                            'search_requests_30d': search_count
                        },
                        'confidence': 'High',
                        'risk_level': 'Medium',
                        'reason': f'No search requests in 30 days (£{monthly_cost:.2f}/month)'
                    })
        
    except ClientError as e:
        print(f"Error scanning OpenSearch domains: {e}")
    
    return waste_items


def check_elasticsearch_usage(cloudwatch, domain_name, service_type, days=30):
    """
    Check Elasticsearch/OpenSearch domain search request count in the specified period
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Determine namespace based on service type
        namespace = f'AWS/{service_type}'
        
        # Check SearchRate metric (searches per second)
        response = cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName='SearchRate',
            Dimensions=[
                {
                    'Name': 'DomainName',
                    'Value': domain_name
                },
                {
                    'Name': 'ClientId',
                    'Value': cloudwatch._client_config.__dict__.get('_user_provided_options', {}).get('region_name', 'us-east-1')
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # Daily
            Statistics=['Sum']
        )
        
        # Sum all search requests
        if not response['Datapoints']:
            return 0
            
        total_searches = sum([point['Sum'] for point in response['Datapoints']])
        return int(total_searches)
        
    except ClientError:
        # If we can't get metrics, assume it's used (conservative)
        return 1


def calculate_elasticsearch_cost(domain, region):
    """
    Calculate monthly Elasticsearch domain cost based on instance type and storage
    """
    cluster_config = domain.get('ElasticsearchClusterConfig', {})
    ebs_options = domain.get('EBSOptions', {})
    
    # Instance configuration
    instance_type = cluster_config.get('InstanceType', 't3.small.elasticsearch')
    instance_count = cluster_config.get('InstanceCount', 1)
    
    # Storage configuration
    storage_size = ebs_options.get('VolumeSize', 10)
    storage_type = ebs_options.get('VolumeType', 'gp2')
    
    # Simplified Elasticsearch pricing (approximate)
    instance_prices = {
        't3.small.elasticsearch': 25.00,
        't3.medium.elasticsearch': 50.00,
        'm5.large.elasticsearch': 120.00,
        'm5.xlarge.elasticsearch': 240.00,
        'm5.2xlarge.elasticsearch': 480.00,
        'r5.large.elasticsearch': 150.00,
        'r5.xlarge.elasticsearch': 300.00,
        'r5.2xlarge.elasticsearch': 600.00,
        'c5.large.elasticsearch': 100.00,
        'c5.xlarge.elasticsearch': 200.00
    }
    
    # Calculate instance cost
    instance_cost = instance_prices.get(instance_type, 50.00) * instance_count
    
    # Calculate storage cost
    storage_cost_per_gb = 0.115 if storage_type == 'gp2' else 0.092  # gp3 is cheaper
    storage_cost = storage_size * storage_cost_per_gb
    
    # Total monthly cost
    total_cost = instance_cost + storage_cost
    
    return max(total_cost, 10.00)


def calculate_opensearch_cost(domain, region):
    """
    Calculate monthly OpenSearch domain cost based on instance type and storage
    """
    cluster_config = domain.get('ClusterConfig', {})
    ebs_options = domain.get('EBSOptions', {})
    
    # Instance configuration
    instance_type = cluster_config.get('InstanceType', 't3.small.search')
    instance_count = cluster_config.get('InstanceCount', 1)
    
    # Storage configuration
    storage_size = ebs_options.get('VolumeSize', 10)
    storage_type = ebs_options.get('VolumeType', 'gp3')
    
    # Simplified OpenSearch pricing (approximate)
    instance_prices = {
        't3.small.search': 25.00,
        't3.medium.search': 50.00,
        'm5.large.search': 120.00,
        'm5.xlarge.search': 240.00,
        'm5.2xlarge.search': 480.00,
        'r5.large.search': 150.00,
        'r5.xlarge.search': 300.00,
        'r5.2xlarge.search': 600.00,
        'c5.large.search': 100.00,
        'c5.xlarge.search': 200.00
    }
    
    # Calculate instance cost
    instance_cost = instance_prices.get(instance_type, 50.00) * instance_count
    
    # Calculate storage cost
    storage_cost_per_gb = 0.092 if storage_type == 'gp3' else 0.115  # gp3 default for OpenSearch
    storage_cost = storage_size * storage_cost_per_gb
    
    # Total monthly cost
    total_cost = instance_cost + storage_cost
    
    return max(total_cost, 10.00)