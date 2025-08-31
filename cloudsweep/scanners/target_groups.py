"""
Target Group Scanner - Find orphaned target groups
"""

from datetime import datetime, timezone

class TargetGroupScanner:
    def __init__(self, region):
        self.region = region
        
    def scan_orphaned_target_groups(self, ec2_client):
        """Find target groups that are orphaned or linked to unused load balancers"""
        try:
            import boto3
            # ELBv2 client for Target Groups
            elbv2_client = boto3.client('elbv2', region_name=self.region)
            
            # Get all target groups
            target_groups_response = elbv2_client.describe_target_groups()
            
            # Get all load balancers to check which are unused
            load_balancers_response = elbv2_client.describe_load_balancers()
            
            # Identify unused load balancers (same logic as load_balancers.py)
            unused_lb_arns = set()
            for lb in load_balancers_response['LoadBalancers']:
                if lb['Type'] != 'application':
                    continue
                    
                age_days = (datetime.now(timezone.utc) - lb['CreatedTime']).days
                if age_days < 7:
                    continue
                
                # Check for healthy targets
                try:
                    lb_target_groups = elbv2_client.describe_target_groups(
                        LoadBalancerArn=lb['LoadBalancerArn']
                    )
                    
                    has_healthy_targets = False
                    for tg in lb_target_groups['TargetGroups']:
                        targets = elbv2_client.describe_target_health(
                            TargetGroupArn=tg['TargetGroupArn']
                        )
                        if any(t['TargetHealth']['State'] == 'healthy' for t in targets['TargetHealthDescriptions']):
                            has_healthy_targets = True
                            break
                    
                    if not has_healthy_targets:
                        unused_lb_arns.add(lb['LoadBalancerArn'])
                        
                except Exception:
                    continue
            
            orphaned_target_groups = []
            for tg in target_groups_response['TargetGroups']:
                # Target groups don't have CreatedTime, so we'll be conservative
                # and only check for orphaned status without age filtering
                # This is safer for operational cleanup
                
                # Check if target group is orphaned or linked to unused load balancer
                is_orphaned = False
                
                # Case 1: No load balancers attached (completely orphaned)
                if not tg.get('LoadBalancerArns'):
                    is_orphaned = True
                
                # Case 2: Attached to unused load balancers only
                elif all(lb_arn in unused_lb_arns for lb_arn in tg.get('LoadBalancerArns', [])):
                    is_orphaned = True
                
                if not is_orphaned:
                    continue
                
                # Check for protection tags
                try:
                    tags_response = elbv2_client.describe_tags(
                        ResourceArns=[tg['TargetGroupArn']]
                    )
                    tags = {}
                    if tags_response['TagDescriptions']:
                        tags = {tag['Key']: tag['Value'] for tag in tags_response['TagDescriptions'][0]['Tags']}
                    
                    if any(key.lower() in ['donotdelete', 'keep', 'production'] for key in tags.keys()):
                        continue
                except Exception:
                    tags = {}
                
                orphaned_target_groups.append({
                    'resource_id': tg['TargetGroupName'],
                    'resource_type': 'target_group',
                    'target_group_arn': tg['TargetGroupArn'],
                    'target_type': tg['TargetType'],
                    'protocol': tg['Protocol'],
                    'port': tg['Port'],
                    'age_days': 'unknown',
                    'orphan_type': 'completely_orphaned' if not tg.get('LoadBalancerArns') else 'linked_to_unused_lb',
                    'tags': tags
                })
            
            return orphaned_target_groups
            
        except Exception as e:
            raise Exception(f"Failed to scan Target Groups: {e}")