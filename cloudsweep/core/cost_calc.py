"""
Cost Calculator - Calculate AWS resource costs
"""

import boto3
from botocore.exceptions import ClientError

class CostCalculator:
    def __init__(self, region='us-east-1'):
        self.region = region
        self.pricing_client = boto3.client('pricing', region_name='us-east-1')  # Pricing API only in us-east-1
        
        # EBS pricing per GB per month (approximate)
        self.ebs_pricing = {
            'gp2': 0.10,
            'gp3': 0.08,
            'io1': 0.125,
            'io2': 0.125,
            'st1': 0.045,
            'sc1': 0.025
        }
        
        # EBS snapshot pricing per GB per month
        self.snapshot_pricing = 0.05  # $0.05 per GB per month
        
        # Elastic IP pricing per hour (when unassociated)
        self.elastic_ip_hourly = 0.005  # $0.005 per hour
        
        # Application Load Balancer pricing per hour
        self.alb_hourly = 0.0225  # $0.0225 per hour
        
        # NAT Gateway pricing per hour (base cost, excluding data transfer)
        self.nat_gateway_hourly = 0.045  # $0.045 per hour
        
        # Stopped instance EBS storage costs (same as EBS volume pricing)
        # Instances still pay for attached EBS volumes when stopped
        
        # Network Interface (ENI) pricing per hour when unattached
        self.eni_hourly = 0.005  # $0.005 per hour for unattached ENIs
        
        # AMI storage costs (same as EBS snapshot pricing for associated snapshots)
        # AMIs incur costs through their underlying EBS snapshots
    
    def calculate_ebs_cost(self, volume_type, size_gb):
        """Calculate monthly cost for EBS volume"""
        price_per_gb = self.ebs_pricing.get(volume_type, 0.10)  # Default to gp2 pricing
        monthly_cost = size_gb * price_per_gb
        annual_cost = monthly_cost * 12
        
        return {
            'monthly_cost': round(monthly_cost, 2),
            'annual_cost': round(annual_cost, 2),
            'price_per_gb': price_per_gb
        }
    
    def calculate_snapshot_cost(self, size_gb):
        """Calculate monthly cost for EBS snapshot"""
        monthly_cost = size_gb * self.snapshot_pricing
        annual_cost = monthly_cost * 12
        
        return {
            'monthly_cost': round(monthly_cost, 2),
            'annual_cost': round(annual_cost, 2),
            'price_per_gb': self.snapshot_pricing
        }
    
    def calculate_elastic_ip_cost(self):
        """Calculate monthly cost for unassociated Elastic IP"""
        # 24 hours * 30 days * hourly rate
        monthly_cost = 24 * 30 * self.elastic_ip_hourly
        annual_cost = monthly_cost * 12
        
        return {
            'monthly_cost': round(monthly_cost, 2),
            'annual_cost': round(annual_cost, 2),
            'hourly_rate': self.elastic_ip_hourly
        }
    
    def calculate_load_balancer_cost(self):
        """Calculate monthly cost for unused Application Load Balancer"""
        # 24 hours * 30 days * hourly rate
        monthly_cost = 24 * 30 * self.alb_hourly
        annual_cost = monthly_cost * 12
        
        return {
            'monthly_cost': round(monthly_cost, 2),
            'annual_cost': round(annual_cost, 2),
            'hourly_rate': self.alb_hourly
        }
    
    def calculate_nat_gateway_cost(self):
        """Calculate monthly cost for unused NAT Gateway"""
        # 24 hours * 30 days * hourly rate (base cost only)
        monthly_cost = 24 * 30 * self.nat_gateway_hourly
        annual_cost = monthly_cost * 12
        
        return {
            'monthly_cost': round(monthly_cost, 2),
            'annual_cost': round(annual_cost, 2),
            'hourly_rate': self.nat_gateway_hourly,
            'note': 'Base cost only - excludes data transfer charges'
        }
    
    def calculate_stopped_instance_cost(self, storage_gb):
        """Calculate monthly cost for stopped instance EBS storage"""
        # Stopped instances still pay for attached EBS volumes (use gp3 pricing as default)
        monthly_cost = storage_gb * self.ebs_pricing['gp3']
        annual_cost = monthly_cost * 12
        
        return {
            'monthly_cost': round(monthly_cost, 2),
            'annual_cost': round(annual_cost, 2),
            'storage_cost_per_gb': self.ebs_pricing['gp3'],
            'note': 'EBS storage cost while instance is stopped'
        }
    
    def calculate_target_group_cost(self):
        """Calculate cost for orphaned target group (operational cleanup only)"""
        return {
            'monthly_cost': 0.0,
            'annual_cost': 0.0,
            'note': 'No direct cost - operational cleanup for account hygiene'
        }
    
    def calculate_eni_cost(self):
        """Calculate monthly cost for unattached ENI"""
        # 24 hours * 30 days * hourly rate
        monthly_cost = 24 * 30 * self.eni_hourly
        annual_cost = monthly_cost * 12
        
        return {
            'monthly_cost': round(monthly_cost, 2),
            'annual_cost': round(annual_cost, 2),
            'hourly_rate': self.eni_hourly
        }
    
    def calculate_ami_cost(self, storage_gb):
        """Calculate monthly cost for old AMI storage (via associated snapshots)"""
        # AMIs cost money through their underlying EBS snapshots
        monthly_cost = storage_gb * self.snapshot_pricing
        annual_cost = monthly_cost * 12
        
        return {
            'monthly_cost': round(monthly_cost, 2),
            'annual_cost': round(annual_cost, 2),
            'storage_cost_per_gb': self.snapshot_pricing,
            'note': 'Cost from underlying EBS snapshots'
        }
    
    def calculate_total_savings(self, waste_items):
        """Calculate total potential savings"""
        total_monthly = 0
        total_annual = 0
        
        for item in waste_items:
            if item['resource_type'] == 'ebs_volume':
                costs = self.calculate_ebs_cost(item['volume_type'], item['size_gb'])
                item.update(costs)
                total_monthly += costs['monthly_cost']
                total_annual += costs['annual_cost']
            elif item['resource_type'] == 'ebs_snapshot':
                costs = self.calculate_snapshot_cost(item['size_gb'])
                item.update(costs)
                total_monthly += costs['monthly_cost']
                total_annual += costs['annual_cost']
            elif item['resource_type'] == 'elastic_ip':
                costs = self.calculate_elastic_ip_cost()
                item.update(costs)
                total_monthly += costs['monthly_cost']
                total_annual += costs['annual_cost']
            elif item['resource_type'] == 'load_balancer':
                costs = self.calculate_load_balancer_cost()
                item.update(costs)
                total_monthly += costs['monthly_cost']
                total_annual += costs['annual_cost']
            elif item['resource_type'] == 'nat_gateway':
                costs = self.calculate_nat_gateway_cost()
                item.update(costs)
                total_monthly += costs['monthly_cost']
                total_annual += costs['annual_cost']
            elif item['resource_type'] == 'stopped_instance':
                costs = self.calculate_stopped_instance_cost(item['storage_gb'])
                item.update(costs)
                total_monthly += costs['monthly_cost']
                total_annual += costs['annual_cost']
            elif item['resource_type'] == 'target_group':
                costs = self.calculate_target_group_cost()
                item.update(costs)
                # No cost added to total (operational cleanup only)
            elif item['resource_type'] == 'network_interface':
                costs = self.calculate_eni_cost()
                item.update(costs)
                total_monthly += costs['monthly_cost']
                total_annual += costs['annual_cost']
            elif item['resource_type'] == 'ami':
                costs = self.calculate_ami_cost(item['storage_gb'])
                item.update(costs)
                total_monthly += costs['monthly_cost']
                total_annual += costs['annual_cost']
        
        return {
            'total_monthly_savings': round(total_monthly, 2),
            'total_annual_savings': round(total_annual, 2),
            'waste_items_count': len(waste_items)
        }