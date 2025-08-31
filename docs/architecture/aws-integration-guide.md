# CloudSweep - AWS Integration Guide

## 🔐 AWS Security Model

CloudSweep uses cross-account IAM roles for secure, temporary access to customer AWS accounts. No long-term credentials are stored.

## 🏗️ Cross-Account Role Setup

### Step 1: Create CloudSweep IAM Role

Customer creates this role in their AWS account:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::CLOUDSWEEP-ACCOUNT:role/CloudSweepAssumeRole"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "customer-unique-external-id"
        },
        "IpAddress": {
          "aws:SourceIp": ["52.1.2.3/32", "52.1.2.4/32"]
        }
      }
    }
  ]
}
```

### Step 2: Attach Minimal Permissions Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadOnlyAccess",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVolumes",
        "ec2:DescribeSnapshots",
        "ec2:DescribeAddresses",
        "ec2:DescribeImages",
        "ec2:DescribeInstances",
        "ec2:DescribeTags",
        "pricing:GetProducts",
        "pricing:GetAttributeValues"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CleanupActions",
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteVolume",
        "ec2:DeleteSnapshot",
        "ec2:ReleaseAddress"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2", "eu-west-1"]
        },
        "ForAllValues:StringLike": {
          "ec2:ResourceTag/CloudSweep": "*"
        }
      }
    }
  ]
}
```

## 🔧 CLI Configuration

### AWS Profile Setup

```bash
# Configure AWS CLI profile
aws configure --profile cloudsweep-customer
# AWS Access Key ID: [Customer's access key]
# AWS Secret Access Key: [Customer's secret key]
# Default region name: us-east-1
# Default output format: json
```

### CloudSweep Configuration File

Create `~/.cloudsweep/config.yaml`:

```yaml
aws:
  default_profile: cloudsweep-customer
  regions:
    - us-east-1
    - us-west-2
    - eu-west-1
  
accounts:
  production:
    role_arn: "arn:aws:iam::123456789012:role/CloudSweepRole"
    external_id: "prod-unique-external-id-2025"
    regions: ["us-east-1", "us-west-2"]
  
  staging:
    role_arn: "arn:aws:iam::987654321098:role/CloudSweepRole"
    external_id: "staging-unique-external-id-2025"
    regions: ["us-east-1"]

scanning:
  min_age_days: 7
  confidence_threshold: 70
  exclude_tags:
    - "DoNotDelete"
    - "Production"
    - "Critical"

cleanup:
  dry_run: true
  require_confirmation: true
  backup_before_delete: true
```

## 🔍 Resource Scanning Logic

### EBS Volume Detection

```python
def scan_ebs_volumes(ec2_client, region):
    """Scan for unattached EBS volumes"""
    volumes = ec2_client.describe_volumes(
        Filters=[
            {'Name': 'state', 'Values': ['available']},
            {'Name': 'attachment.status', 'Values': ['detached']}
        ]
    )
    
    waste_volumes = []
    for volume in volumes['Volumes']:
        # Skip if too new
        if is_too_recent(volume['CreateTime'], min_days=7):
            continue
            
        # Skip if protected by tags
        if has_protection_tags(volume.get('Tags', [])):
            continue
            
        # Calculate cost
        monthly_cost = calculate_ebs_cost(
            volume['Size'], 
            volume['VolumeType'], 
            region
        )
        
        waste_volumes.append({
            'resource_id': volume['VolumeId'],
            'resource_type': 'ebs_volume',
            'region': region,
            'size_gb': volume['Size'],
            'volume_type': volume['VolumeType'],
            'monthly_cost': monthly_cost,
            'annual_cost': monthly_cost * 12,
            'confidence_score': calculate_confidence_score(volume),
            'risk_level': assess_risk_level(volume)
        })
    
    return waste_volumes
```

### EBS Snapshot Detection

```python
def scan_ebs_snapshots(ec2_client, region):
    """Scan for orphaned EBS snapshots"""
    snapshots = ec2_client.describe_snapshots(
        OwnerIds=['self'],
        Filters=[
            {'Name': 'status', 'Values': ['completed']}
        ]
    )
    
    # Get all AMIs to check for orphaned snapshots
    images = ec2_client.describe_images(Owners=['self'])
    ami_snapshot_ids = set()
    for image in images['Images']:
        for bdm in image.get('BlockDeviceMappings', []):
            if 'Ebs' in bdm and 'SnapshotId' in bdm['Ebs']:
                ami_snapshot_ids.add(bdm['Ebs']['SnapshotId'])
    
    waste_snapshots = []
    for snapshot in snapshots['Snapshots']:
        # Skip if used by AMI
        if snapshot['SnapshotId'] in ami_snapshot_ids:
            continue
            
        # Skip if too new
        if is_too_recent(snapshot['StartTime'], min_days=7):
            continue
            
        # Skip if protected
        if has_protection_tags(snapshot.get('Tags', [])):
            continue
            
        monthly_cost = calculate_snapshot_cost(
            snapshot['VolumeSize'], 
            region
        )
        
        waste_snapshots.append({
            'resource_id': snapshot['SnapshotId'],
            'resource_type': 'ebs_snapshot',
            'region': region,
            'size_gb': snapshot['VolumeSize'],
            'monthly_cost': monthly_cost,
            'annual_cost': monthly_cost * 12,
            'confidence_score': calculate_confidence_score(snapshot),
            'risk_level': assess_risk_level(snapshot)
        })
    
    return waste_snapshots
```

### Elastic IP Detection

```python
def scan_elastic_ips(ec2_client, region):
    """Scan for unassociated Elastic IPs"""
    addresses = ec2_client.describe_addresses()
    
    waste_ips = []
    for address in addresses['Addresses']:
        # Skip if associated with instance or network interface
        if 'InstanceId' in address or 'NetworkInterfaceId' in address:
            continue
            
        # Skip if protected
        if has_protection_tags(address.get('Tags', [])):
            continue
            
        monthly_cost = calculate_eip_cost(region)
        
        waste_ips.append({
            'resource_id': address['AllocationId'],
            'resource_type': 'elastic_ip',
            'region': region,
            'public_ip': address['PublicIp'],
            'monthly_cost': monthly_cost,
            'annual_cost': monthly_cost * 12,
            'confidence_score': 95,  # High confidence for unassociated EIPs
            'risk_level': 'safe'
        })
    
    return waste_ips
```

## 💰 Cost Calculation

### AWS Pricing API Integration

```python
import boto3
from decimal import Decimal

class AWSPricingCalculator:
    def __init__(self):
        self.pricing_client = boto3.client('pricing', region_name='us-east-1')
        self.price_cache = {}
    
    def get_ebs_price(self, volume_type, region):
        """Get EBS pricing per GB per month"""
        cache_key = f"ebs_{volume_type}_{region}"
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]
        
        response = self.pricing_client.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'},
                {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': volume_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._region_to_location(region)}
            ]
        )
        
        # Parse pricing data
        for price_item in response['PriceList']:
            price_data = json.loads(price_item)
            terms = price_data['terms']['OnDemand']
            for term_key, term_data in terms.items():
                for price_key, price_info in term_data['priceDimensions'].items():
                    price_per_gb = Decimal(price_info['pricePerUnit']['USD'])
                    self.price_cache[cache_key] = price_per_gb
                    return price_per_gb
        
        # Fallback pricing if API fails
        fallback_prices = {
            'gp3': Decimal('0.08'),
            'gp2': Decimal('0.10'),
            'io1': Decimal('0.125'),
            'io2': Decimal('0.125'),
            'st1': Decimal('0.045'),
            'sc1': Decimal('0.025')
        }
        return fallback_prices.get(volume_type, Decimal('0.10'))
    
    def get_snapshot_price(self, region):
        """Get EBS snapshot pricing per GB per month"""
        # Simplified - snapshots are typically $0.05 per GB per month
        return Decimal('0.05')
    
    def get_eip_price(self, region):
        """Get Elastic IP pricing per month"""
        # Unassociated EIPs cost $0.005 per hour = ~$3.60 per month
        return Decimal('3.60')
```

## 🛡️ Safety Mechanisms

### Confidence Scoring Algorithm

```python
def calculate_confidence_score(resource):
    """Calculate confidence score (1-100) for safe cleanup"""
    score = 100
    
    # Age factor (older = safer)
    age_days = (datetime.now() - resource['created_time']).days
    if age_days < 7:
        score -= 50
    elif age_days < 30:
        score -= 20
    elif age_days < 90:
        score -= 10
    
    # Tag factor
    tags = resource.get('tags', [])
    for tag in tags:
        if tag['Key'].lower() in ['environment', 'project', 'owner']:
            score -= 10  # Has meaningful tags, might be in use
    
    # Size factor (for EBS volumes)
    if resource['resource_type'] == 'ebs_volume':
        if resource['size_gb'] > 100:
            score -= 15  # Large volumes are riskier
    
    # Usage history (if available)
    if 'last_attached' in resource and resource['last_attached']:
        days_since_detached = (datetime.now() - resource['last_attached']).days
        if days_since_detached < 7:
            score -= 30
    
    return max(1, min(100, score))
```

### Risk Assessment

```python
def assess_risk_level(resource):
    """Assess risk level based on confidence score"""
    confidence = resource.get('confidence_score', 0)
    
    if confidence >= 90:
        return 'safe'
    elif confidence >= 70:
        return 'low'
    elif confidence >= 50:
        return 'medium'
    else:
        return 'high'
```

## 🔧 CLI Implementation

### Main CLI Structure

```python
import click
import boto3
from pathlib import Path

@click.group()
@click.option('--config', default='~/.cloudsweep/config.yaml', help='Configuration file path')
@click.pass_context
def cli(ctx, config):
    """CloudSweep - AWS Cost Optimisation Tool"""
    ctx.ensure_object(dict)
    ctx.obj['config'] = load_config(Path(config).expanduser())

@cli.command()
@click.option('--profile', help='AWS profile to use')
@click.option('--region', help='AWS region to scan')
@click.option('--account', help='Account name from config')
@click.option('--output', default='scan-results.json', help='Output file')
@click.pass_context
def scan(ctx, profile, region, account, output):
    """Scan AWS account for waste"""
    config = ctx.obj['config']
    
    # Initialize scanner
    scanner = CloudSweepScanner(config)
    
    # Perform scan
    results = scanner.scan_account(
        profile=profile,
        region=region,
        account=account
    )
    
    # Save results
    with open(output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Display summary
    total_cost = sum(item['monthly_cost'] for item in results['waste_items'])
    click.echo(f"Found {len(results['waste_items'])} waste items")
    click.echo(f"Potential monthly savings: ${total_cost:.2f}")

@cli.command()
@click.option('--input', required=True, help='Scan results JSON file')
@click.option('--dry-run', is_flag=True, help='Preview actions without executing')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompts')
@click.pass_context
def cleanup(ctx, input, dry_run, confirm):
    """Execute cleanup actions"""
    with open(input, 'r') as f:
        results = json.load(f)
    
    cleaner = CloudSweepCleaner(ctx.obj['config'])
    
    # Filter safe items only
    safe_items = [
        item for item in results['waste_items']
        if item['risk_level'] == 'safe'
    ]
    
    if not confirm:
        click.echo(f"About to clean up {len(safe_items)} items")
        if not click.confirm('Continue?'):
            return
    
    # Execute cleanup
    cleanup_results = cleaner.cleanup_items(safe_items, dry_run=dry_run)
    
    # Display results
    successful = sum(1 for r in cleanup_results if r['success'])
    click.echo(f"Successfully cleaned up {successful}/{len(safe_items)} items")

if __name__ == '__main__':
    cli()
```

## 🧪 Testing Strategy

### Integration Tests

```python
import pytest
import boto3
from moto import mock_ec2

@mock_ec2
def test_ebs_volume_scanning():
    """Test EBS volume scanning with mocked AWS"""
    # Create mock EC2 client
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    # Create test volume
    volume = ec2.create_volume(Size=10, AvailabilityZone='us-east-1a')
    volume_id = volume['VolumeId']
    
    # Scan for volumes
    scanner = CloudSweepScanner({})
    results = scanner.scan_ebs_volumes(ec2, 'us-east-1')
    
    # Verify results
    assert len(results) == 1
    assert results[0]['resource_id'] == volume_id
    assert results[0]['resource_type'] == 'ebs_volume'
    assert results[0]['monthly_cost'] > 0

@mock_ec2
def test_safety_mechanisms():
    """Test safety mechanisms prevent risky deletions"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    # Create volume with protection tag
    volume = ec2.create_volume(
        Size=10, 
        AvailabilityZone='us-east-1a',
        TagSpecifications=[{
            'ResourceType': 'volume',
            'Tags': [{'Key': 'DoNotDelete', 'Value': 'true'}]
        }]
    )
    
    scanner = CloudSweepScanner({})
    results = scanner.scan_ebs_volumes(ec2, 'us-east-1')
    
    # Should be filtered out by safety checks
    assert len(results) == 0
```

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] AWS IAM roles configured correctly
- [ ] Cross-account trust relationships tested
- [ ] Pricing API access verified
- [ ] Safety mechanisms tested thoroughly
- [ ] CLI packaging completed

### Post-Deployment
- [ ] Customer onboarding documentation ready
- [ ] Support procedures documented
- [ ] Monitoring and alerting configured
- [ ] Backup and recovery procedures tested

---

*Last Updated: January 2025*
*Security Review: Before each release*
*Integration Tests: Run before deployment*