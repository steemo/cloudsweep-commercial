"""
Elastic IP Scanner - Find unassociated Elastic IPs
"""

class ElasticIPScanner:
    def __init__(self, ec2_client):
        self.ec2_client = ec2_client
    
    def scan_unassociated_ips(self):
        """Find Elastic IPs not associated with any instance"""
        try:
            response = self.ec2_client.describe_addresses()
            
            unassociated_ips = []
            for address in response['Addresses']:
                # Skip if IP is associated with an instance
                if 'InstanceId' in address or 'NetworkInterfaceId' in address:
                    continue
                
                # Check for protection tags
                tags = {tag['Key']: tag['Value'] for tag in address.get('Tags', [])}
                if any(key.lower() in ['donotdelete', 'keep', 'production'] for key in tags.keys()):
                    continue
                
                unassociated_ips.append({
                    'resource_id': address['AllocationId'],
                    'resource_type': 'elastic_ip',
                    'public_ip': address['PublicIp'],
                    'domain': address.get('Domain', 'standard'),
                    'tags': tags
                })
            
            return unassociated_ips
            
        except Exception as e:
            raise Exception(f"Failed to scan Elastic IPs: {e}")