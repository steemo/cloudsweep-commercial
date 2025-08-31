#!/usr/bin/env python3
"""
CloudSweep CLI - Main entry point
"""

import click
import json
from colorama import init, Fore, Style
import sys
import os

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.scanner import AWSScanner
from core.cost_calc import CostCalculator

# Initialize colorama for cross-platform colored output
init()

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """CloudSweep - Automated AWS cost optimization for SMEs"""
    pass

@cli.command()
@click.option('--profile', default='default', help='AWS profile to use')
@click.option('--region', default='us-east-1', help='AWS region to scan')
@click.option('--output', default='scan-results.json', help='Output file for results')
def scan(profile, region, output):
    """Scan AWS account for cost optimization opportunities"""
    click.echo(f"{Fore.GREEN}🔍 CloudSweep Scanner v0.1.0{Style.RESET_ALL}")
    click.echo(f"Profile: {profile}")
    click.echo(f"Region: {region}")
    
    try:
        # Initialize scanner
        scanner = AWSScanner(profile=profile, region=region)
        cost_calc = CostCalculator(region=region)
        
        click.echo(f"{Fore.YELLOW}Connecting to AWS...{Style.RESET_ALL}")
        scanner.connect()
        
        account_info = scanner.get_account_info()
        click.echo(f"Account: {account_info['account_id']}")
        
        click.echo(f"{Fore.YELLOW}Scanning for unattached EBS volumes...{Style.RESET_ALL}")
        waste_volumes = scanner.scan_unattached_volumes()
        
        click.echo(f"{Fore.YELLOW}Scanning for orphaned EBS snapshots...{Style.RESET_ALL}")
        waste_snapshots = scanner.scan_orphaned_snapshots()
        
        click.echo(f"{Fore.YELLOW}Scanning for unassociated Elastic IPs...{Style.RESET_ALL}")
        waste_ips = scanner.scan_unassociated_ips()
        
        click.echo(f"{Fore.YELLOW}Scanning for unused Load Balancers...{Style.RESET_ALL}")
        waste_load_balancers = scanner.scan_unused_load_balancers()
        
        click.echo(f"{Fore.YELLOW}Scanning for unused NAT Gateways...{Style.RESET_ALL}")
        waste_nat_gateways = scanner.scan_unused_nat_gateways()
        
        click.echo(f"{Fore.YELLOW}Scanning for stopped EC2 instances...{Style.RESET_ALL}")
        waste_stopped_instances = scanner.scan_stopped_instances()
        
        click.echo(f"{Fore.YELLOW}Scanning for orphaned target groups...{Style.RESET_ALL}")
        waste_target_groups = scanner.scan_orphaned_target_groups()
        
        click.echo(f"{Fore.YELLOW}Scanning for unattached network interfaces...{Style.RESET_ALL}")
        waste_enis = scanner.scan_unattached_enis()
        
        click.echo(f"{Fore.YELLOW}Scanning for old/unused AMIs...{Style.RESET_ALL}")
        waste_amis = scanner.scan_old_unused_amis()
        
        click.echo(f"{Fore.YELLOW}Scanning for stopped/unused RDS instances...{Style.RESET_ALL}")
        waste_rds = scanner.scan_rds_instances()
        
        click.echo(f"{Fore.YELLOW}Scanning for unused CloudFront distributions...{Style.RESET_ALL}")
        waste_cloudfront = scanner.scan_cloudfront_distributions()
        
        click.echo(f"{Fore.YELLOW}Scanning for unused/over-provisioned Lambda functions...{Style.RESET_ALL}")
        waste_lambda = scanner.scan_lambda_functions()
        
        click.echo(f"{Fore.YELLOW}Scanning for empty/unused S3 buckets...{Style.RESET_ALL}")
        waste_s3 = scanner.scan_s3_buckets()
        
        # Combine all waste items
        all_waste_items = waste_volumes + waste_snapshots + waste_ips + waste_load_balancers + waste_nat_gateways + waste_stopped_instances + waste_target_groups + waste_enis + waste_amis + waste_rds + waste_cloudfront + waste_lambda + waste_s3
        
        if all_waste_items:
            # Calculate costs
            savings = cost_calc.calculate_total_savings(all_waste_items)
            
            click.echo(f"{Fore.GREEN}✓ Found {len(waste_volumes)} unattached EBS volumes{Style.RESET_ALL}")
            click.echo(f"{Fore.GREEN}✓ Found {len(waste_snapshots)} orphaned EBS snapshots{Style.RESET_ALL}")
            click.echo(f"{Fore.GREEN}✓ Found {len(waste_ips)} unassociated Elastic IPs{Style.RESET_ALL}")
            click.echo(f"{Fore.GREEN}✓ Found {len(waste_load_balancers)} unused Load Balancers{Style.RESET_ALL}")
            click.echo(f"{Fore.GREEN}✓ Found {len(waste_nat_gateways)} unused NAT Gateways{Style.RESET_ALL}")
            click.echo(f"{Fore.GREEN}✓ Found {len(waste_stopped_instances)} stopped EC2 instances{Style.RESET_ALL}")
            click.echo(f"{Fore.GREEN}✓ Found {len(waste_target_groups)} orphaned target groups{Style.RESET_ALL}")
            click.echo(f"{Fore.GREEN}✓ Found {len(waste_enis)} unattached network interfaces{Style.RESET_ALL}")
            click.echo(f"{Fore.GREEN}✓ Found {len(waste_amis)} old/unused AMIs{Style.RESET_ALL}")
            click.echo(f"{Fore.GREEN}✓ Found {len(waste_rds)} stopped/unused RDS instances{Style.RESET_ALL}")
            click.echo(f"{Fore.GREEN}✓ Found {len(waste_cloudfront)} unused CloudFront distributions{Style.RESET_ALL}")
            click.echo(f"{Fore.GREEN}✓ Found {len(waste_lambda)} unused/over-provisioned Lambda functions{Style.RESET_ALL}")
            click.echo(f"{Fore.GREEN}✓ Found {len(waste_s3)} empty/unused S3 buckets{Style.RESET_ALL}")
            click.echo(f"{Fore.GREEN}✓ Total waste items: {len(all_waste_items)}{Style.RESET_ALL}")
            click.echo(f"{Fore.CYAN}💰 Potential monthly savings: £{savings['total_monthly_savings']}{Style.RESET_ALL}")
            click.echo(f"{Fore.CYAN}💰 Potential annual savings: £{savings['total_annual_savings']}{Style.RESET_ALL}")
            
            # Save results
            results = {
                'account_info': account_info,
                'region': region,
                'savings_summary': savings,
                'waste_items': all_waste_items
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