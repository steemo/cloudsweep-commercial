#!/usr/bin/env python3
"""
CloudSweep - Automated AWS Cost Optimization Tool
Standalone version for distribution
"""

import sys
import subprocess

def install_missing_dependencies():
    """Auto-install missing Python dependencies"""
    required_packages = ['boto3', 'click', 'colorama']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"📦 Installing missing dependencies: {', '.join(missing_packages)}")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing_packages, 
                         check=True, capture_output=True)
            print("✅ Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            print("Please run: pip3 install boto3 click colorama")
            sys.exit(1)

# Auto-install dependencies before importing
install_missing_dependencies()

import boto3
import click
import json
from colorama import init, Fore, Style
from datetime import datetime, timezone
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

# Initialize colorama
init()

class AWSScanner:
    def __init__(self, profile='default', region='us-east-1'):
        self.profile = profile
        self.region = region
        self.session = None
        self.ec2 = None
        self.elbv2 = None
        self.rds = None
        self.cloudwatch = None
        self.cloudfront = None
        self.lambda_client = None
        self.s3 = None
        self.ecs = None
        
    def connect(self):
        try:
            # If no profile specified or profile is None, use default credential chain
            if self.profile is None or self.profile == 'None':
                self.session = boto3.Session(region_name=self.region)
            else:
                # Try with specified profile
                self.session = boto3.Session(profile_name=self.profile, region_name=self.region)
            
            self.ec2 = self.session.client('ec2')
            self.elbv2 = self.session.client('elbv2')
            self.rds = self.session.client('rds')
            self.cloudwatch = self.session.client('cloudwatch')
            self.cloudfront = self.session.client('cloudfront', region_name='us-east-1')
            self.lambda_client = self.session.client('lambda')
            self.s3 = self.session.client('s3')
            self.ecs = self.session.client('ecs')
            
        except ProfileNotFound:
            # Fallback to default credentials (CloudShell, EC2 roles, etc.)
            try:
                self.session = boto3.Session(region_name=self.region)
                self.ec2 = self.session.client('ec2')
                self.elbv2 = self.session.client('elbv2')
                self.rds = self.session.client('rds')
                self.cloudwatch = self.session.client('cloudwatch')
                self.cloudfront = self.session.client('cloudfront', region_name='us-east-1')
                self.lambda_client = self.session.client('lambda')
                self.s3 = self.session.client('s3')
                self.ecs = self.session.client('ecs')
            except (NoCredentialsError, ClientError) as e:
                raise Exception(f"AWS credentials not found. In CloudShell they should be automatic. Try: aws sts get-caller-identity")
        except (NoCredentialsError, ClientError) as e:
            raise Exception(f"AWS credentials not found. In CloudShell they should be automatic. Try: aws sts get-caller-identity")
    
    def get_account_info(self):
        try:
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            return {
                'account_id': identity['Account'],
                'user_arn': identity['Arn']
            }
        except Exception as e:
            raise Exception(f"Failed to get account info: {e}")
    
    def scan_unattached_volumes(self):
        volumes = []
        try:
            response = self.ec2.describe_volumes(Filters=[{'Name': 'status', 'Values': ['available']}])
            for volume in response['Volumes']:
                age_days = (datetime.now(timezone.utc) - volume['CreateTime']).days
                volumes.append({
                    'type': 'ebs_volume',
                    'id': volume['VolumeId'],
                    'size_gb': volume['Size'],
                    'volume_type': volume['VolumeType'],
                    'age_days': age_days,
                    'created': volume['CreateTime'].isoformat()
                })
        except Exception as e:
            print(f"Error scanning volumes: {e}")
        return volumes
    
    def scan_orphaned_snapshots(self):
        snapshots = []
        try:
            response = self.ec2.describe_snapshots(OwnerIds=['self'])
            for snapshot in response['Snapshots']:
                age_days = (datetime.now(timezone.utc) - snapshot['StartTime']).days
                if age_days > 30:  # Only old snapshots
                    snapshots.append({
                        'type': 'ebs_snapshot',
                        'id': snapshot['SnapshotId'],
                        'size_gb': snapshot['VolumeSize'],
                        'age_days': age_days,
                        'created': snapshot['StartTime'].isoformat()
                    })
        except Exception as e:
            print(f"Error scanning snapshots: {e}")
        return snapshots
    
    def scan_unassociated_ips(self):
        ips = []
        try:
            response = self.ec2.describe_addresses()
            for address in response['Addresses']:
                if 'AssociationId' not in address:
                    ips.append({
                        'type': 'elastic_ip',
                        'id': address['AllocationId'],
                        'ip': address['PublicIp'],
                        'domain': address['Domain']
                    })
        except Exception as e:
            print(f"Error scanning Elastic IPs: {e}")
        return ips
    
    def scan_unused_load_balancers(self):
        load_balancers = []
        try:
            response = self.elbv2.describe_load_balancers()
            for lb in response['LoadBalancers']:
                age_days = (datetime.now(timezone.utc) - lb['CreatedTime']).days
                if age_days > 30:
                    # Check if has healthy targets
                    try:
                        tg_response = self.elbv2.describe_target_groups(LoadBalancerArn=lb['LoadBalancerArn'])
                        has_healthy_targets = False
                        for tg in tg_response['TargetGroups']:
                            health = self.elbv2.describe_target_health(TargetGroupArn=tg['TargetGroupArn'])
                            if any(t['TargetHealth']['State'] == 'healthy' for t in health['TargetHealthDescriptions']):
                                has_healthy_targets = True
                                break
                        
                        if not has_healthy_targets:
                            load_balancers.append({
                                'type': 'load_balancer',
                                'id': lb['LoadBalancerArn'].split('/')[-1],
                                'name': lb['LoadBalancerName'],
                                'type_detail': lb['Type'],
                                'age_days': age_days,
                                'created': lb['CreatedTime'].isoformat()
                            })
                    except Exception:
                        pass
        except Exception as e:
            print(f"Error scanning Load Balancers: {e}")
        return load_balancers
    
    def scan_unused_nat_gateways(self):
        nat_gateways = []
        try:
            response = self.ec2.describe_nat_gateways(Filters=[{'Name': 'state', 'Values': ['available']}])
            for nat in response['NatGateways']:
                age_days = (datetime.now(timezone.utc) - nat['CreateTime']).days
                if age_days > 30:
                    nat_gateways.append({
                        'type': 'nat_gateway',
                        'id': nat['NatGatewayId'],
                        'subnet_id': nat['SubnetId'],
                        'age_days': age_days,
                        'created': nat['CreateTime'].isoformat()
                    })
        except Exception as e:
            print(f"Error scanning NAT Gateways: {e}")
        return nat_gateways
    
    def scan_stopped_instances(self):
        instances = []
        try:
            response = self.ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['stopped']}])
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    # Calculate stopped duration
                    state_transition = instance.get('StateTransitionReason', '')
                    if 'stopped' in state_transition.lower():
                        launch_time = instance['LaunchTime']
                        age_days = (datetime.now(timezone.utc) - launch_time).days
                        if age_days > 30:
                            instances.append({
                                'type': 'stopped_instance',
                                'id': instance['InstanceId'],
                                'instance_type': instance['InstanceType'],
                                'age_days': age_days,
                                'launched': launch_time.isoformat()
                            })
        except Exception as e:
            print(f"Error scanning stopped instances: {e}")
        return instances
    
    def scan_orphaned_target_groups(self):
        target_groups = []
        try:
            response = self.elbv2.describe_target_groups()
            for tg in response['TargetGroups']:
                if not tg.get('LoadBalancerArns'):
                    target_groups.append({
                        'type': 'target_group',
                        'id': tg['TargetGroupArn'].split('/')[-1],
                        'name': tg['TargetGroupName'],
                        'protocol': tg['Protocol'],
                        'port': tg['Port']
                    })
        except Exception as e:
            print(f"Error scanning Target Groups: {e}")
        return target_groups
    
    def scan_unattached_enis(self):
        enis = []
        try:
            response = self.ec2.describe_network_interfaces(Filters=[{'Name': 'status', 'Values': ['available']}])
            for eni in response['NetworkInterfaces']:
                if eni.get('RequesterId') != 'amazon-aws':  # Skip AWS-managed
                    enis.append({
                        'type': 'network_interface',
                        'id': eni['NetworkInterfaceId'],
                        'subnet_id': eni['SubnetId'],
                        'interface_type': eni.get('InterfaceType', 'interface')
                    })
        except Exception as e:
            print(f"Error scanning Network Interfaces: {e}")
        return enis
    
    def scan_old_unused_amis(self):
        amis = []
        try:
            response = self.ec2.describe_images(Owners=['self'])
            for ami in response['Images']:
                creation_date = datetime.strptime(ami['CreationDate'], '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
                age_days = (datetime.now(timezone.utc) - creation_date).days
                if age_days > 180:  # 6+ months old
                    amis.append({
                        'type': 'ami',
                        'id': ami['ImageId'],
                        'name': ami.get('Name', 'N/A'),
                        'age_days': age_days,
                        'created': ami['CreationDate']
                    })
        except Exception as e:
            print(f"Error scanning AMIs: {e}")
        return amis
    
    def scan_rds_instances(self):
        rds_instances = []
        try:
            response = self.rds.describe_db_instances()
            for instance in response['DBInstances']:
                db_id = instance['DBInstanceIdentifier']
                status = instance['DBInstanceStatus']
                created_time = instance['InstanceCreateTime']
                age_days = (datetime.now(timezone.utc) - created_time).days
                
                if age_days > 30:  # Only check instances older than 30 days
                    if status == 'stopped':
                        # Stopped instance still incurring storage costs
                        storage_gb = instance.get('AllocatedStorage', 0)
                        rds_instances.append({
                            'type': 'rds_stopped',
                            'id': db_id,
                            'instance_class': instance['DBInstanceClass'],
                            'engine': instance['Engine'],
                            'storage_gb': storage_gb,
                            'age_days': age_days,
                            'created': created_time.isoformat()
                        })
                    elif status == 'available':
                        # Check if unused (no connections)
                        if self._check_rds_unused(db_id):
                            rds_instances.append({
                                'type': 'rds_unused',
                                'id': db_id,
                                'instance_class': instance['DBInstanceClass'],
                                'engine': instance['Engine'],
                                'storage_gb': instance.get('AllocatedStorage', 0),
                                'age_days': age_days,
                                'created': created_time.isoformat()
                            })
        except Exception as e:
            print(f"Error scanning RDS instances: {e}")
        return rds_instances
    
    def _check_rds_unused(self, db_instance_id):
        try:
            from datetime import timedelta
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=30)
            
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='DatabaseConnections',
                Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=['Maximum']
            )
            
            if not response['Datapoints']:
                return True
            
            max_connections = max([point['Maximum'] for point in response['Datapoints']])
            return max_connections == 0
        except Exception:
            return False  # Conservative approach
    
    def scan_cloudfront_distributions(self):
        distributions = []
        try:
            response = self.cloudfront.list_distributions()
            if 'Items' not in response['DistributionList']:
                return distributions
                
            for dist in response['DistributionList']['Items']:
                dist_id = dist['Id']
                domain_name = dist['DomainName']
                enabled = dist['Enabled']
                last_modified = dist['LastModifiedTime']
                age_days = (datetime.now(timezone.utc) - last_modified).days
                
                if age_days > 30 and enabled:  # Only check old, enabled distributions
                    if self._check_cloudfront_unused(dist_id):
                        distributions.append({
                            'type': 'cloudfront_distribution',
                            'id': dist_id,
                            'domain_name': domain_name,
                            'status': dist['Status'],
                            'age_days': age_days,
                            'last_modified': last_modified.isoformat()
                        })
        except Exception as e:
            print(f"Error scanning CloudFront distributions: {e}")
        return distributions
    
    def _check_cloudfront_unused(self, distribution_id):
        try:
            from datetime import timedelta
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=30)
            
            # CloudWatch metrics for CloudFront are in us-east-1
            cloudwatch_us = self.session.client('cloudwatch', region_name='us-east-1')
            
            response = cloudwatch_us.get_metric_statistics(
                Namespace='AWS/CloudFront',
                MetricName='Requests',
                Dimensions=[{'Name': 'DistributionId', 'Value': distribution_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=['Sum']
            )
            
            if not response['Datapoints']:
                return True
            
            total_requests = sum([point['Sum'] for point in response['Datapoints']])
            return total_requests == 0
        except Exception:
            return False  # Conservative approach
    
    def scan_lambda_functions(self):
        functions = []
        try:
            response = self.lambda_client.list_functions()
            for func in response['Functions']:
                func_name = func['FunctionName']
                memory_size = func['MemorySize']
                last_modified = func['LastModified']
                
                # Parse date and check age
                last_modified_date = datetime.strptime(last_modified, '%Y-%m-%dT%H:%M:%S.%f%z')
                age_days = (datetime.now(timezone.utc) - last_modified_date.replace(tzinfo=timezone.utc)).days
                
                if age_days > 30:  # Only check old functions
                    if self._check_lambda_unused(func_name):
                        functions.append({
                            'type': 'lambda_unused',
                            'id': func_name,
                            'memory_size': memory_size,
                            'runtime': func['Runtime'],
                            'age_days': age_days,
                            'last_modified': last_modified
                        })
        except Exception as e:
            print(f"Error scanning Lambda functions: {e}")
        return functions
    
    def _check_lambda_unused(self, function_name):
        try:
            from datetime import timedelta
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=30)
            
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Invocations',
                Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=['Sum']
            )
            
            if not response['Datapoints']:
                return True
            
            total_invocations = sum([point['Sum'] for point in response['Datapoints']])
            return total_invocations == 0
        except Exception:
            return False
    
    def scan_s3_buckets(self):
        buckets = []
        try:
            response = self.s3.list_buckets()
            for bucket in response['Buckets']:
                bucket_name = bucket['Name']
                creation_date = bucket['CreationDate']
                age_days = (datetime.now(timezone.utc) - creation_date.replace(tzinfo=timezone.utc)).days
                
                if age_days > 30:  # Only check old buckets
                    if self._check_bucket_empty(bucket_name):
                        buckets.append({
                            'type': 's3_empty',
                            'id': bucket_name,
                            'age_days': age_days,
                            'created': creation_date.isoformat()
                        })
                    elif self._check_bucket_unused(bucket_name):
                        storage_gb = self._get_bucket_size(bucket_name)
                        if storage_gb > 0.1:  # Only flag if significant storage
                            buckets.append({
                                'type': 's3_unused',
                                'id': bucket_name,
                                'storage_gb': storage_gb,
                                'age_days': age_days,
                                'created': creation_date.isoformat()
                            })
        except Exception as e:
            print(f"Error scanning S3 buckets: {e}")
        return buckets
    
    def _check_bucket_empty(self, bucket_name):
        try:
            response = self.s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
            return 'Contents' not in response
        except Exception:
            return False
    
    def _check_bucket_unused(self, bucket_name):
        try:
            from datetime import timedelta
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=90)
            
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/S3',
                MetricName='AllRequests',
                Dimensions=[{'Name': 'BucketName', 'Value': bucket_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=['Sum']
            )
            
            if not response['Datapoints']:
                return True
            
            total_requests = sum([point['Sum'] for point in response['Datapoints']])
            return total_requests == 0
        except Exception:
            return False
    
    def _get_bucket_size(self, bucket_name):
        try:
            response = self.s3.list_objects_v2(Bucket=bucket_name, MaxKeys=100)
            if 'Contents' not in response:
                return 0
            
            sample_size = sum([obj['Size'] for obj in response['Contents']])
            return sample_size / (1024 ** 3)  # Convert to GB
        except Exception:
            return 0
    
    def scan_ecs_services(self):
        services = []
        try:
            clusters = self.ecs.list_clusters()
            for cluster_arn in clusters['clusterArns']:
                cluster_name = cluster_arn.split('/')[-1]
                
                cluster_services = self.ecs.list_services(cluster=cluster_arn)
                for service_arn in cluster_services['serviceArns']:
                    service_name = service_arn.split('/')[-1]
                    
                    service_details = self.ecs.describe_services(
                        cluster=cluster_arn,
                        services=[service_arn]
                    )
                    
                    if service_details['services']:
                        service = service_details['services'][0]
                        created_at = service['createdAt']
                        age_days = (datetime.now(timezone.utc) - created_at.replace(tzinfo=timezone.utc)).days
                        
                        if age_days > 30:  # Only check old services
                            desired_count = service['desiredCount']
                            running_count = service['runningCount']
                            
                            if desired_count == 0 and running_count == 0:
                                services.append({
                                    'type': 'ecs_unused',
                                    'id': f"{cluster_name}/{service_name}",
                                    'cluster_name': cluster_name,
                                    'service_name': service_name,
                                    'launch_type': service.get('launchType', 'EC2'),
                                    'age_days': age_days,
                                    'created': created_at.isoformat()
                                })
        except Exception as e:
            print(f"Error scanning ECS services: {e}")
        return services

class CostCalculator:
    def __init__(self, region='us-east-1'):
        self.region = region
        self.pricing = {
            'ebs_gp2': 0.10,  # per GB/month
            'ebs_gp3': 0.08,
            'ebs_io1': 0.125,
            'ebs_io2': 0.125,
            'ebs_st1': 0.045,
            'ebs_sc1': 0.025,
            'ebs_snapshot': 0.05,  # per GB/month
            'elastic_ip': 3.65,  # per month
            'alb': 16.20,  # per month
            'nlb': 16.20,
            'nat_gateway': 32.85,  # per month
            'ami_storage': 0.05  # per GB/month
        }
    
    def calculate_total_savings(self, waste_items):
        total_monthly = 0
        breakdown = {}
        
        for item in waste_items:
            monthly_cost = self._calculate_item_cost(item)
            total_monthly += monthly_cost
            
            item_type = item['type']
            if item_type not in breakdown:
                breakdown[item_type] = {'count': 0, 'monthly_cost': 0}
            breakdown[item_type]['count'] += 1
            breakdown[item_type]['monthly_cost'] += monthly_cost
        
        return {
            'total_monthly_savings': round(total_monthly, 2),
            'total_annual_savings': round(total_monthly * 12, 2),
            'breakdown': breakdown
        }
    
    def _calculate_item_cost(self, item):
        item_type = item['type']
        
        if item_type == 'ebs_volume':
            volume_type = item.get('volume_type', 'gp2')
            price_key = f"ebs_{volume_type}"
            return item['size_gb'] * self.pricing.get(price_key, self.pricing['ebs_gp2'])
        
        elif item_type == 'ebs_snapshot':
            return item['size_gb'] * self.pricing['ebs_snapshot']
        
        elif item_type == 'elastic_ip':
            return self.pricing['elastic_ip']
        
        elif item_type == 'load_balancer':
            lb_type = item.get('type_detail', 'application')
            return self.pricing['alb'] if lb_type == 'application' else self.pricing['nlb']
        
        elif item_type == 'nat_gateway':
            return self.pricing['nat_gateway']
        
        elif item_type == 'ami':
            return item.get('size_gb', 8) * self.pricing['ami_storage']
        
        elif item_type == 'rds_stopped':
            return item.get('storage_gb', 20) * 0.115  # Storage cost only
        
        elif item_type == 'rds_unused':
            # Simplified RDS instance pricing
            instance_class = item.get('instance_class', 'db.t3.micro')
            base_costs = {
                'db.t3.micro': 18.50,
                'db.t3.small': 37.00,
                'db.t3.medium': 74.00,
                'db.t3.large': 148.00,
                'db.m5.large': 185.00,
                'db.m5.xlarge': 370.00,
                'db.r5.large': 230.00,
                'db.r5.xlarge': 460.00
            }
            return base_costs.get(instance_class, 100.00)
        
        elif item_type == 'cloudfront_distribution':
            return 15.00  # Estimated monthly cost for unused CloudFront distribution
        
        elif item_type == 'lambda_unused':
            return 5.00  # Estimated monthly cost for unused Lambda function
        
        elif item_type == 's3_empty':
            return 1.00  # Base cost for empty S3 bucket
        
        elif item_type == 's3_unused':
            storage_gb = item.get('storage_gb', 1)
            return storage_gb * 0.023  # S3 Standard storage cost
        
        elif item_type == 'ecs_unused':
            launch_type = item.get('launch_type', 'EC2')
            if launch_type == 'FARGATE':
                return 25.00  # Estimated monthly cost for unused Fargate service
            else:
                return 5.00  # Base cost for unused EC2-based ECS service
        
        return 0

@click.group()
@click.version_option(version="1.0.0")
def cli():
    """CloudSweep - Automated AWS cost optimization for SMEs"""
    pass

@cli.command()
@click.option('--profile', default=None, help='AWS profile to use (optional in CloudShell)')
@click.option('--region', default='us-east-1', help='AWS region to scan')
@click.option('--output', default='scan-results.json', help='Output file for results')
def scan(profile, region, output):
    """Scan AWS account for cost optimization opportunities"""
    click.echo(f"{Fore.GREEN}🔍 CloudSweep Scanner v1.0.0{Style.RESET_ALL}")
    click.echo(f"Profile: {profile}")
    click.echo(f"Region: {region}")
    
    try:
        scanner = AWSScanner(profile=profile, region=region)
        cost_calc = CostCalculator(region=region)
        
        click.echo(f"{Fore.YELLOW}Connecting to AWS...{Style.RESET_ALL}")
        scanner.connect()
        
        account_info = scanner.get_account_info()
        click.echo(f"Account: {account_info['account_id']}")
        
        # Scan all resource types with detailed progress
        waste_items = []
        
        click.echo(f"{Fore.YELLOW}🔍 Scanning EBS volumes...{Style.RESET_ALL}")
        waste_items.extend(scanner.scan_unattached_volumes())
        
        click.echo(f"{Fore.YELLOW}🔍 Scanning EBS snapshots...{Style.RESET_ALL}")
        waste_items.extend(scanner.scan_orphaned_snapshots())
        
        click.echo(f"{Fore.YELLOW}🔍 Scanning Elastic IPs...{Style.RESET_ALL}")
        waste_items.extend(scanner.scan_unassociated_ips())
        
        click.echo(f"{Fore.YELLOW}🔍 Scanning Load Balancers...{Style.RESET_ALL}")
        waste_items.extend(scanner.scan_unused_load_balancers())
        
        click.echo(f"{Fore.YELLOW}🔍 Scanning NAT Gateways...{Style.RESET_ALL}")
        waste_items.extend(scanner.scan_unused_nat_gateways())
        
        click.echo(f"{Fore.YELLOW}🔍 Scanning stopped EC2 instances...{Style.RESET_ALL}")
        waste_items.extend(scanner.scan_stopped_instances())
        
        click.echo(f"{Fore.YELLOW}🔍 Scanning Target Groups...{Style.RESET_ALL}")
        waste_items.extend(scanner.scan_orphaned_target_groups())
        
        click.echo(f"{Fore.YELLOW}🔍 Scanning Network Interfaces...{Style.RESET_ALL}")
        waste_items.extend(scanner.scan_unattached_enis())
        
        click.echo(f"{Fore.YELLOW}🔍 Scanning AMIs...{Style.RESET_ALL}")
        waste_items.extend(scanner.scan_old_unused_amis())
        
        click.echo(f"{Fore.YELLOW}🔍 Scanning RDS instances...{Style.RESET_ALL}")
        waste_items.extend(scanner.scan_rds_instances())
        
        click.echo(f"{Fore.YELLOW}🔍 Scanning CloudFront distributions...{Style.RESET_ALL}")
        waste_items.extend(scanner.scan_cloudfront_distributions())
        
        click.echo(f"{Fore.YELLOW}🔍 Scanning Lambda functions...{Style.RESET_ALL}")
        waste_items.extend(scanner.scan_lambda_functions())
        
        click.echo(f"{Fore.YELLOW}🔍 Scanning S3 buckets...{Style.RESET_ALL}")
        waste_items.extend(scanner.scan_s3_buckets())
        
        click.echo(f"{Fore.YELLOW}🔍 Scanning ECS services...{Style.RESET_ALL}")
        waste_items.extend(scanner.scan_ecs_services())
        
        click.echo(f"{Fore.GREEN}✅ Scan complete!{Style.RESET_ALL}")
        
        if waste_items:
            savings = cost_calc.calculate_total_savings(waste_items)
            
            click.echo(f"{Fore.GREEN}🎯 Found {len(waste_items)} waste items across 14 AWS services{Style.RESET_ALL}")
            click.echo(f"{Fore.CYAN}💰 Monthly savings: £{savings['total_monthly_savings']}{Style.RESET_ALL}")
            click.echo(f"{Fore.CYAN}💰 Annual savings: £{savings['total_annual_savings']}{Style.RESET_ALL}")
            
            results = {
                'account_info': account_info,
                'region': region,
                'savings_summary': savings,
                'waste_items': waste_items,
                'scan_timestamp': datetime.now().isoformat()
            }
            
            with open(output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            click.echo(f"{Fore.GREEN}Results saved to: {output}{Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.GREEN}✓ No waste found - your AWS account is optimized!{Style.RESET_ALL}")
            
    except Exception as e:
        click.echo(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
        return 1

if __name__ == '__main__':
    cli()