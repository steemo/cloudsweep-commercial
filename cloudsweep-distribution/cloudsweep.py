#!/usr/bin/env python3
"""
CloudSweep - Automated AWS Cost Optimization Tool
Standalone version for distribution
"""

import boto3
import click
import json
from colorama import init, Fore, Style
import sys
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
            
        except ProfileNotFound:
            # Fallback to default credentials (CloudShell, EC2 roles, etc.)
            try:
                self.session = boto3.Session(region_name=self.region)
                self.ec2 = self.session.client('ec2')
                self.elbv2 = self.session.client('elbv2')
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
            response = self.ec2.describe_volumes(Filters=[{'Name': 'state', 'Values': ['available']}])
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
        
        # Scan all resource types
        click.echo(f"{Fore.YELLOW}Scanning AWS resources...{Style.RESET_ALL}")
        
        waste_items = []
        waste_items.extend(scanner.scan_unattached_volumes())
        waste_items.extend(scanner.scan_orphaned_snapshots())
        waste_items.extend(scanner.scan_unassociated_ips())
        waste_items.extend(scanner.scan_unused_load_balancers())
        waste_items.extend(scanner.scan_unused_nat_gateways())
        waste_items.extend(scanner.scan_stopped_instances())
        waste_items.extend(scanner.scan_orphaned_target_groups())
        waste_items.extend(scanner.scan_unattached_enis())
        waste_items.extend(scanner.scan_old_unused_amis())
        
        if waste_items:
            savings = cost_calc.calculate_total_savings(waste_items)
            
            click.echo(f"{Fore.GREEN}✓ Found {len(waste_items)} waste items{Style.RESET_ALL}")
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