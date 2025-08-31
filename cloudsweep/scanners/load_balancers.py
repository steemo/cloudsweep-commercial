"""
Load Balancer Scanner - Find unused Application Load Balancers
"""

from datetime import datetime, timezone

class LoadBalancerScanner:
    def __init__(self, region):
        self.region = region
        
    def scan_unused_load_balancers(self, ec2_client):
        """Find unused Application Load Balancers"""
        try:
            import boto3
            # ELBv2 client for Application Load Balancers
            elbv2_client = boto3.client('elbv2', region_name=self.region)
            
            # Get all Application Load Balancers
            response = elbv2_client.describe_load_balancers()
            
            unused_albs = []
            for lb in response['LoadBalancers']:
                # Skip if not Application Load Balancer
                if lb['Type'] != 'application':
                    continue
                
                # Check if load balancer is older than 7 days
                age_days = (datetime.now(timezone.utc) - lb['CreatedTime']).days
                if age_days < 7:
                    continue
                
                # Check for target groups
                try:
                    target_groups = elbv2_client.describe_target_groups(
                        LoadBalancerArn=lb['LoadBalancerArn']
                    )
                    
                    # Check if any target group has healthy targets
                    has_healthy_targets = False
                    for tg in target_groups['TargetGroups']:
                        targets = elbv2_client.describe_target_health(
                            TargetGroupArn=tg['TargetGroupArn']
                        )
                        if any(t['TargetHealth']['State'] == 'healthy' for t in targets['TargetHealthDescriptions']):
                            has_healthy_targets = True
                            break
                    
                    # Skip if has healthy targets
                    if has_healthy_targets:
                        continue
                        
                except Exception:
                    # If we can't check targets, be conservative and skip
                    continue
                
                # Check for protection tags
                try:
                    tags_response = elbv2_client.describe_tags(
                        ResourceArns=[lb['LoadBalancerArn']]
                    )
                    tags = {}
                    if tags_response['TagDescriptions']:
                        tags = {tag['Key']: tag['Value'] for tag in tags_response['TagDescriptions'][0]['Tags']}
                    
                    if any(key.lower() in ['donotdelete', 'keep', 'production'] for key in tags.keys()):
                        continue
                except Exception:
                    tags = {}
                
                unused_albs.append({
                    'resource_id': lb['LoadBalancerName'],
                    'resource_type': 'load_balancer',
                    'load_balancer_arn': lb['LoadBalancerArn'],
                    'scheme': lb['Scheme'],
                    'age_days': age_days,
                    'tags': tags,
                    'created_time': lb['CreatedTime'].isoformat()
                })
            
            return unused_albs
            
        except Exception as e:
            raise Exception(f"Failed to scan Load Balancers: {e}")