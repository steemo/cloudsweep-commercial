"""
AWS Scanner - Core scanning functionality
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import json
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scanners.ebs_snapshots import EBSSnapshotScanner
from scanners.elastic_ips import ElasticIPScanner
from scanners.load_balancers import LoadBalancerScanner
from scanners.nat_gateways import NATGatewayScanner
from scanners.ec2_instances import EC2InstanceScanner
from scanners.target_groups import TargetGroupScanner
from scanners.network_interfaces import NetworkInterfaceScanner
from scanners.amis import AMIScanner
from scanners.rds_instances import scan_rds_instances
from scanners.cloudfront_distributions import scan_cloudfront_distributions
from scanners.lambda_functions import scan_lambda_functions
from scanners.s3_buckets import scan_s3_buckets

class AWSScanner:
    def __init__(self, profile='default', region='us-east-1'):
        self.profile = profile
        self.region = region
        self.session = None
        self.ec2_client = None
        
    def connect(self):
        """Establish AWS connection - works everywhere"""
        try:
            if self.profile == 'default' or self.profile == '':
                # Try default credentials first (CloudShell, EC2, env vars)
                self.ec2_client = boto3.client('ec2', region_name=self.region)
                self.session = boto3.Session()
            else:
                # Use specific profile (local development)
                self.session = boto3.Session(profile_name=self.profile)
                self.ec2_client = self.session.client('ec2', region_name=self.region)
            
            # Test connection
            self.ec2_client.describe_regions(RegionNames=[self.region])
            return True
            
        except NoCredentialsError:
            raise Exception(f"AWS credentials not found for profile '{self.profile}'")
        except ClientError as e:
            raise Exception(f"AWS connection failed: {e}")
    
    def scan_unattached_volumes(self):
        """Find unattached EBS volumes"""
        try:
            # Get all volumes first, then filter in Python
            response = self.ec2_client.describe_volumes()
            
            waste_volumes = []
            for volume in response['Volumes']:
                # Check if volume is available (unattached)
                if volume['State'] != 'available':
                    continue
                    
                # Check if volume is older than 7 days
                age_days = (datetime.now(timezone.utc) - volume['CreateTime']).days
                if age_days < 7:
                    continue
                
                # Check for protection tags
                tags = {tag['Key']: tag['Value'] for tag in volume.get('Tags', [])}
                if any(key.lower() in ['donotdelete', 'keep', 'production'] for key in tags.keys()):
                    continue
                
                waste_volumes.append({
                    'resource_id': volume['VolumeId'],
                    'resource_type': 'ebs_volume',
                    'size_gb': volume['Size'],
                    'volume_type': volume['VolumeType'],
                    'region': self.region,
                    'age_days': age_days,
                    'tags': tags,
                    'created_time': volume['CreateTime'].isoformat()
                })
            
            return waste_volumes
            
        except ClientError as e:
            raise Exception(f"Failed to scan EBS volumes: {e}")
    
    def scan_orphaned_snapshots(self):
        """Find orphaned EBS snapshots"""
        snapshot_scanner = EBSSnapshotScanner(self.ec2_client)
        return snapshot_scanner.scan_orphaned_snapshots()
    
    def scan_unassociated_ips(self):
        """Find unassociated Elastic IPs"""
        ip_scanner = ElasticIPScanner(self.ec2_client)
        return ip_scanner.scan_unassociated_ips()
    
    def scan_unused_load_balancers(self):
        """Find unused Application Load Balancers"""
        lb_scanner = LoadBalancerScanner(self.region)
        return lb_scanner.scan_unused_load_balancers(self.ec2_client)
    
    def scan_unused_nat_gateways(self):
        """Find unused NAT Gateways"""
        nat_scanner = NATGatewayScanner(self.ec2_client)
        return nat_scanner.scan_unused_nat_gateways()
    
    def scan_stopped_instances(self):
        """Find long-stopped EC2 instances still incurring storage costs"""
        instance_scanner = EC2InstanceScanner(self.ec2_client)
        return instance_scanner.scan_stopped_instances()
    
    def scan_orphaned_target_groups(self):
        """Find orphaned target groups (completely orphaned or linked to unused load balancers)"""
        tg_scanner = TargetGroupScanner(self.region)
        return tg_scanner.scan_orphaned_target_groups(self.ec2_client)
    
    def scan_unattached_enis(self):
        """Find unattached Elastic Network Interfaces (ENIs) incurring costs"""
        eni_scanner = NetworkInterfaceScanner(self.ec2_client)
        return eni_scanner.scan_unattached_enis()
    
    def scan_old_unused_amis(self):
        """Find old/unused AMIs incurring storage costs"""
        ami_scanner = AMIScanner(self.ec2_client)
        return ami_scanner.scan_old_unused_amis()
    
    def scan_rds_instances(self):
        """Find stopped and unused RDS instances incurring costs"""
        return scan_rds_instances(self.session, self.region)
    
    def scan_cloudfront_distributions(self):
        """Find unused CloudFront distributions incurring costs"""
        return scan_cloudfront_distributions(self.session, self.region)
    
    def scan_lambda_functions(self):
        """Find unused and over-provisioned Lambda functions incurring costs"""
        return scan_lambda_functions(self.session, self.region)
    
    def scan_s3_buckets(self):
        """Find empty and unused S3 buckets incurring costs"""
        return scan_s3_buckets(self.session, self.region)
    
    def get_account_info(self):
        """Get AWS account information"""
        try:
            if self.session:
                sts_client = self.session.client('sts')
            else:
                sts_client = boto3.client('sts')
            identity = sts_client.get_caller_identity()
            return {
                'account_id': identity['Account'],
                'user_arn': identity['Arn']
            }
        except ClientError as e:
            raise Exception(f"Failed to get account info: {e}")