"""
Network Interface Scanner - Find unattached ENIs incurring costs
"""

from datetime import datetime, timezone

class NetworkInterfaceScanner:
    def __init__(self, ec2_client):
        self.ec2_client = ec2_client
    
    def scan_unattached_enis(self):
        """Find unattached Elastic Network Interfaces (ENIs) incurring hourly costs"""
        try:
            # Get all network interfaces
            response = self.ec2_client.describe_network_interfaces()
            
            unattached_enis = []
            for eni in response['NetworkInterfaces']:
                # Skip if ENI is attached to an instance
                if eni.get('Attachment') and eni['Attachment'].get('InstanceId'):
                    continue
                
                # Skip if ENI is attached to other AWS services (load balancers, etc.)
                if eni.get('Attachment') and eni['Attachment'].get('AttachmentId'):
                    continue
                
                # Skip default VPC ENIs (they're usually system-managed)
                if eni.get('Description', '').startswith('Primary network interface'):
                    continue
                
                # Skip ENIs managed by AWS services
                if eni.get('RequesterId') and eni['RequesterId'] != 'self':
                    continue
                
                # Check for protection tags
                tags = {tag['Key']: tag['Value'] for tag in eni.get('TagSet', [])}
                if any(key.lower() in ['donotdelete', 'keep', 'production'] for key in tags.keys()):
                    continue
                
                # Calculate age (conservative - only flag if we can determine creation)
                age_days = 'unknown'
                if 'Attachment' in eni and 'AttachTime' in eni['Attachment']:
                    # Use detach time as proxy for age
                    age_days = 'recently_detached'
                
                unattached_enis.append({
                    'resource_id': eni['NetworkInterfaceId'],
                    'resource_type': 'network_interface',
                    'interface_type': eni.get('InterfaceType', 'interface'),
                    'subnet_id': eni.get('SubnetId'),
                    'vpc_id': eni.get('VpcId'),
                    'private_ip': eni.get('PrivateIpAddress'),
                    'age_days': age_days,
                    'tags': tags,
                    'description': eni.get('Description', '')
                })
            
            return unattached_enis
            
        except Exception as e:
            raise Exception(f"Failed to scan Network Interfaces: {e}")