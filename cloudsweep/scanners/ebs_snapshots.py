"""
EBS Snapshots Scanner - Find orphaned snapshots
"""

from datetime import datetime, timezone

class EBSSnapshotScanner:
    def __init__(self, ec2_client):
        self.ec2_client = ec2_client
    
    def scan_orphaned_snapshots(self):
        """Find snapshots not used by any AMI"""
        try:
            # Get all snapshots owned by this account
            snapshots_response = self.ec2_client.describe_snapshots(OwnerIds=['self'])
            
            # Get all AMIs to check which snapshots are in use
            amis_response = self.ec2_client.describe_images(Owners=['self'])
            
            # Collect snapshot IDs used by AMIs
            used_snapshots = set()
            for ami in amis_response['Images']:
                for block_device in ami.get('BlockDeviceMappings', []):
                    if 'Ebs' in block_device and 'SnapshotId' in block_device['Ebs']:
                        used_snapshots.add(block_device['Ebs']['SnapshotId'])
            
            orphaned_snapshots = []
            for snapshot in snapshots_response['Snapshots']:
                # Skip if snapshot is used by an AMI
                if snapshot['SnapshotId'] in used_snapshots:
                    continue
                
                # Check age (older than 7 days)
                age_days = (datetime.now(timezone.utc) - snapshot['StartTime']).days
                if age_days < 7:
                    continue
                
                # Check for protection tags
                tags = {tag['Key']: tag['Value'] for tag in snapshot.get('Tags', [])}
                if any(key.lower() in ['donotdelete', 'keep', 'production'] for key in tags.keys()):
                    continue
                
                orphaned_snapshots.append({
                    'resource_id': snapshot['SnapshotId'],
                    'resource_type': 'ebs_snapshot',
                    'size_gb': snapshot['VolumeSize'],
                    'age_days': age_days,
                    'tags': tags,
                    'created_time': snapshot['StartTime'].isoformat()
                })
            
            return orphaned_snapshots
            
        except Exception as e:
            raise Exception(f"Failed to scan EBS snapshots: {e}")