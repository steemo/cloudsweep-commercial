"""
NAT Gateway Scanner - Find unused NAT Gateways
"""

from datetime import datetime, timezone

class NATGatewayScanner:
    def __init__(self, ec2_client):
        self.ec2_client = ec2_client
    
    def scan_unused_nat_gateways(self):
        """Find potentially unused NAT Gateways"""
        try:
            # Get all NAT Gateways
            response = self.ec2_client.describe_nat_gateways()
            
            unused_nat_gateways = []
            for nat_gw in response['NatGateways']:
                # Skip if not available
                if nat_gw['State'] != 'available':
                    continue
                
                # Check if NAT Gateway is older than 7 days
                age_days = (datetime.now(timezone.utc) - nat_gw['CreateTime']).days
                if age_days < 7:
                    continue
                
                # Check for protection tags
                tags = {tag['Key']: tag['Value'] for tag in nat_gw.get('Tags', [])}
                if any(key.lower() in ['donotdelete', 'keep', 'production'] for key in tags.keys()):
                    continue
                
                # Check if NAT Gateway is in a route table
                try:
                    route_tables = self.ec2_client.describe_route_tables()
                    is_in_use = False
                    
                    for rt in route_tables['RouteTables']:
                        for route in rt.get('Routes', []):
                            if route.get('NatGatewayId') == nat_gw['NatGatewayId']:
                                is_in_use = True
                                break
                        if is_in_use:
                            break
                    
                    # If not found in any route table, it's potentially unused
                    # But be conservative - only flag if very old (30+ days)
                    if is_in_use or age_days < 30:
                        continue
                        
                except Exception:
                    # If we can't check route tables, be conservative and skip
                    continue
                
                unused_nat_gateways.append({
                    'resource_id': nat_gw['NatGatewayId'],
                    'resource_type': 'nat_gateway',
                    'subnet_id': nat_gw['SubnetId'],
                    'vpc_id': nat_gw['VpcId'],
                    'age_days': age_days,
                    'tags': tags,
                    'created_time': nat_gw['CreateTime'].isoformat()
                })
            
            return unused_nat_gateways
            
        except Exception as e:
            raise Exception(f"Failed to scan NAT Gateways: {e}")