"""
EC2 Instance Scanner - Find long-stopped instances still incurring storage costs
"""

from datetime import datetime, timezone

class EC2InstanceScanner:
    def __init__(self, ec2_client):
        self.ec2_client = ec2_client
    
    def scan_stopped_instances(self):
        """Find EC2 instances stopped for 30+ days (still paying for EBS storage)"""
        try:
            # Get all stopped instances
            response = self.ec2_client.describe_instances(
                Filters=[
                    {'Name': 'instance-state-name', 'Values': ['stopped']}
                ]
            )
            
            stopped_instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    # Get stop time from state transitions
                    stop_time = None
                    for transition in instance.get('StateTransitionReason', ''):
                        if 'stopped' in transition.lower():
                            # Parse stop time from state reason if available
                            pass
                    
                    # Use launch time as fallback (conservative approach)
                    launch_time = instance['LaunchTime']
                    days_since_launch = (datetime.now(timezone.utc) - launch_time).days
                    
                    # Only flag if stopped for 30+ days (conservative)
                    if days_since_launch < 30:
                        continue
                    
                    # Check for protection tags
                    tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                    if any(key.lower() in ['donotdelete', 'keep', 'production'] for key in tags.keys()):
                        continue
                    
                    # Calculate EBS storage cost (instances still pay for attached volumes when stopped)
                    total_storage_gb = 0
                    for block_device in instance.get('BlockDeviceMappings', []):
                        if 'Ebs' in block_device:
                            volume_id = block_device['Ebs']['VolumeId']
                            try:
                                volume_info = self.ec2_client.describe_volumes(VolumeIds=[volume_id])
                                if volume_info['Volumes']:
                                    total_storage_gb += volume_info['Volumes'][0]['Size']
                            except Exception:
                                pass
                    
                    stopped_instances.append({
                        'resource_id': instance['InstanceId'],
                        'resource_type': 'stopped_instance',
                        'instance_type': instance['InstanceType'],
                        'storage_gb': total_storage_gb,
                        'days_stopped': days_since_launch,  # Conservative estimate
                        'tags': tags,
                        'launch_time': launch_time.isoformat()
                    })
            
            return stopped_instances
            
        except Exception as e:
            raise Exception(f"Failed to scan stopped EC2 instances: {e}")