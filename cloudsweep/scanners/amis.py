"""
AMI Scanner - Find old/unused AMIs incurring storage costs
"""

from datetime import datetime, timezone

class AMIScanner:
    def __init__(self, ec2_client):
        self.ec2_client = ec2_client
    
    def scan_old_unused_amis(self):
        """Find old AMIs not used by any instances (incurring storage costs)"""
        try:
            # Get all AMIs owned by this account
            amis_response = self.ec2_client.describe_images(Owners=['self'])
            
            # Get all instances to check AMI usage
            instances_response = self.ec2_client.describe_instances()
            
            # Collect AMIs currently in use
            used_ami_ids = set()
            for reservation in instances_response['Reservations']:
                for instance in reservation['Instances']:
                    # Skip terminated instances
                    if instance['State']['Name'] != 'terminated':
                        used_ami_ids.add(instance['ImageId'])
            
            old_unused_amis = []
            for ami in amis_response['Images']:
                # Check if AMI is older than 6 months (conservative threshold)
                creation_date = datetime.fromisoformat(ami['CreationDate'].replace('Z', '+00:00'))
                age_days = (datetime.now(timezone.utc) - creation_date).days
                
                if age_days < 180:  # 6 months
                    continue
                
                # Skip if AMI is currently in use
                if ami['ImageId'] in used_ami_ids:
                    continue
                
                # Check for protection tags
                tags = {tag['Key']: tag['Value'] for tag in ami.get('Tags', [])}
                if any(key.lower() in ['donotdelete', 'keep', 'production', 'backup'] for key in tags.keys()):
                    continue
                
                # Calculate storage cost (AMI + associated snapshots)
                total_storage_gb = 0
                snapshot_count = 0
                
                for block_device in ami.get('BlockDeviceMappings', []):
                    if 'Ebs' in block_device and 'SnapshotId' in block_device['Ebs']:
                        snapshot_id = block_device['Ebs']['SnapshotId']
                        try:
                            snapshot_info = self.ec2_client.describe_snapshots(
                                SnapshotIds=[snapshot_id],
                                OwnerIds=['self']
                            )
                            if snapshot_info['Snapshots']:
                                snapshot = snapshot_info['Snapshots'][0]
                                total_storage_gb += snapshot['VolumeSize']
                                snapshot_count += 1
                        except Exception:
                            # Snapshot might be shared or deleted
                            pass
                
                old_unused_amis.append({
                    'resource_id': ami['ImageId'],
                    'resource_type': 'ami',
                    'name': ami.get('Name', 'Unnamed'),
                    'description': ami.get('Description', ''),
                    'storage_gb': total_storage_gb,
                    'snapshot_count': snapshot_count,
                    'age_days': age_days,
                    'architecture': ami.get('Architecture', 'unknown'),
                    'platform': ami.get('Platform', 'linux'),
                    'tags': tags,
                    'creation_date': ami['CreationDate']
                })
            
            return old_unused_amis
            
        except Exception as e:
            raise Exception(f"Failed to scan AMIs: {e}")