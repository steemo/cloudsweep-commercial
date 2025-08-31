# CloudSweep Distribution

**Automated AWS Cost Optimization Tool**

CloudSweep scans your AWS account and identifies unused resources that are costing you money. Simple, safe, and effective.

## 🚀 Quick Installation

### Linux
```bash
chmod +x install-linux.sh
./install-linux.sh
```

### macOS
```bash
chmod +x install-macos.sh
./install-macos.sh
```

### Windows
```cmd
install-windows.bat
```

## 💡 Usage

After installation, CloudSweep is available system-wide:

```bash
# Scan your AWS account
cloudsweep scan --region us-east-1

# Use specific AWS profile
cloudsweep scan --profile production --region eu-west-1

# Save results to custom file
cloudsweep scan --region us-east-1 --output my-results.json
```

## 🔧 Manual Build

If you prefer to build the executable yourself:

```bash
# Install dependencies
pip3 install -r requirements.txt

# Build for current OS
python3 build.py

# Run the executable
./executables/[platform]/cloudsweep-[platform] scan --region us-east-1
```

## 📋 Requirements

- **AWS CLI configured** with valid credentials
- **Python 3.7+** (for building only)
- **Internet connection** for AWS API calls

## 🎯 What CloudSweep Finds

- **EBS Volumes**: Unattached volumes costing £0.10/GB/month
- **EBS Snapshots**: Orphaned snapshots costing £0.05/GB/month  
- **Elastic IPs**: Unassociated IPs costing £3.65/month each
- **Load Balancers**: Unused ALBs/NLBs costing £16.20/month each
- **NAT Gateways**: Unused gateways costing £32.85/month each
- **EC2 Instances**: Long-stopped instances with EBS costs
- **Target Groups**: Orphaned target groups (operational cleanup)
- **Network Interfaces**: Unattached ENIs with hourly costs
- **AMIs**: Old unused AMIs with storage costs

## 🛡️ Safety Features

- **Read-only scanning** - never modifies your AWS resources
- **Conservative detection** - only flags resources 30+ days old
- **Detailed reporting** - full JSON output with all findings
- **Multi-region support** - scan any AWS region
- **Profile support** - works with AWS CLI profiles

## 📊 Example Output

```
🔍 CloudSweep Scanner v1.0.0
Profile: default
Region: eu-west-2
Connecting to AWS...
Account: 123456789012
Scanning AWS resources...
✓ Found 3 waste items
💰 Monthly savings: £47.70
💰 Annual savings: £572.40
Results saved to: scan-results.json
```

## 🆘 Support

- **Documentation**: Check the generated JSON output for detailed findings
- **AWS Credentials**: Ensure `aws configure` is set up correctly
- **Permissions**: CloudSweep needs read-only EC2 and ELB permissions
- **Regions**: Use valid AWS region codes (us-east-1, eu-west-1, etc.)

## 📄 License

Copyright © 2025 CloudSweep. All rights reserved.