# CloudSweep - Complete Architecture Documentation

## 🎯 System Overview

**CloudSweep** is an automated cloud cost optimisation platform that identifies and eliminates AWS waste, helping SMEs save 20-40% on their cloud bills through intelligent automation.

### High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │   API Gateway    │    │  Background     │
│   (React SPA)   │◄──►│   (FastAPI)      │◄──►│  Workers        │
└─────────────────┘    └──────────────────┘    │  (Celery)       │
                                │               └─────────────────┘
                                │                        │
                       ┌────────▼────────┐              │
                       │   Core Engine   │              │
                       │   (Python)      │              │
                       └────────┬────────┘              │
                                │                        │
        ┌───────────────────────┼────────────────────────┼──────────┐
        │                       │                        │          │
┌───────▼──────┐    ┌──────────▼─────────┐    ┌─────────▼────┐   ┌─▼──────┐
│ AWS Scanner  │    │   Cost Calculator  │    │  Cleanup     │   │ Notif. │
│ (boto3)      │    │   (Pricing API)    │    │  Engine      │   │ System │
└──────────────┘    └────────────────────┘    └──────────────┘   └────────┘
        │                       │                        │
┌───────▼──────┐    ┌──────────▼─────────┐    ┌─────────▼────┐
│ PostgreSQL   │    │     Redis Cache    │    │   S3 Logs    │
│ (Main DB)    │    │   (Temp Results)   │    │  (Audit)     │
└──────────────┘    └────────────────────┘    └──────────────┘
```

### Core Components

1. **Web Frontend (React SPA)**: Dashboard, scan management, waste items, settings
2. **API Gateway (FastAPI)**: JWT auth, REST API, WebSocket, rate limiting
3. **Core Engine (Python)**: Orchestration, business logic, integration hub
4. **Background Workers (Celery)**: Async scanning, cleanup, notifications, scheduled tasks

---

## 🔐 Security Architecture

### Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Security                      │
│  • Input validation  • Output encoding  • Business logic   │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   Authentication & Authorization             │
│  • JWT tokens  • RBAC  • MFA  • Session management         │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      Network Security                        │
│  • TLS 1.3  • WAF  • DDoS protection  • VPC isolation      │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      Data Security                           │
│  • Encryption at rest  • Encryption in transit  • Key mgmt │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Security                    │
│  • Container security  • OS hardening  • Patch management  │
└─────────────────────────────────────────────────────────────┘
```

### JWT Token Strategy
- **Access Token**: 60 minutes expiry
- **Refresh Token**: 30 days expiry
- **Algorithm**: HS256
- **Payload**: user_id, organization_id, role, issued_at, expires_at, JWT_ID

### Role-Based Access Control
- **Viewer**: Read-only access (scans, waste items, reports)
- **Member**: Standard operations (create scans, approve cleanup)
- **Admin**: Full organisation access (except billing)
- **Owner**: All permissions including billing

### AWS Security Model
- **Cross-Account Roles**: No long-term credentials stored
- **Least Privilege**: Minimal required permissions
- **External ID**: Additional security layer
- **IP Restrictions**: Source IP validation

---

## 🗂️ Database Schema

### Technology: PostgreSQL
- **ACID Compliance**: Critical for financial data integrity
- **JSON Support**: Flexible storage for AWS resource metadata
- **Performance**: Excellent for complex queries and reporting
- **Scalability**: Supports read replicas and partitioning

### Core Tables

#### Organizations (Multi-Tenant)
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan_type VARCHAR(20) NOT NULL DEFAULT 'free',
    billing_email VARCHAR(255),
    monthly_scan_limit INTEGER DEFAULT 5,
    auto_cleanup_enabled BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(20) NOT NULL DEFAULT 'member',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### AWS Accounts
```sql
CREATE TABLE aws_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    account_id VARCHAR(12) NOT NULL,
    account_name VARCHAR(255),
    role_arn VARCHAR(512) NOT NULL,
    external_id VARCHAR(255),
    regions TEXT[] DEFAULT ARRAY['us-east-1', 'us-west-2'],
    scan_enabled BOOLEAN DEFAULT true,
    auto_cleanup_enabled BOOLEAN DEFAULT false,
    connection_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Waste Items (Core Entity)
```sql
CREATE TABLE waste_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_result_id UUID NOT NULL REFERENCES scan_results(id),
    aws_account_id UUID NOT NULL REFERENCES aws_accounts(id),
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    resource_arn VARCHAR(512),
    region VARCHAR(20) NOT NULL,
    monthly_cost DECIMAL(10,2) NOT NULL,
    annual_cost DECIMAL(12,2) NOT NULL,
    confidence_score INTEGER NOT NULL CHECK (confidence_score >= 1 AND confidence_score <= 100),
    risk_level VARCHAR(10) NOT NULL,
    cleanup_status VARCHAR(20) DEFAULT 'pending',
    resource_details JSONB NOT NULL,
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 🌐 API Design

### Technology Stack
- **Framework**: FastAPI (Python)
- **Authentication**: JWT with refresh tokens
- **Documentation**: Auto-generated OpenAPI/Swagger
- **Validation**: Pydantic models
- **Rate Limiting**: Redis-based sliding window

### Base URLs
```
Production:  https://api.cloudsweep.io/v1
Staging:     https://api-staging.cloudsweep.io/v1
Development: http://localhost:8000/v1
```

### Key Endpoints

#### Authentication
```
POST /auth/login          # User login
POST /auth/refresh        # Refresh access token
DELETE /auth/logout       # User logout
```

#### AWS Account Management
```
GET /aws-accounts         # List AWS accounts
POST /aws-accounts        # Add AWS account
PUT /aws-accounts/{id}    # Update AWS account
DELETE /aws-accounts/{id} # Remove AWS account
POST /aws-accounts/{id}/test-connection # Test connection
```

#### Scan Management
```
GET /scans               # List scans
POST /scans/start        # Start new scan
GET /scans/{id}          # Get scan details
DELETE /scans/{id}       # Cancel scan
```

#### Waste Item Management
```
GET /waste-items         # List waste items
GET /waste-items/{id}    # Get waste item details
POST /waste-items/{id}/approve  # Approve cleanup
POST /waste-items/{id}/reject   # Reject cleanup
POST /waste-items/{id}/cleanup  # Execute cleanup
POST /waste-items/bulk-cleanup  # Bulk cleanup
```

### Rate Limiting
- **Free**: 100 requests/hour
- **Starter**: 1000 requests/hour
- **Pro**: 5000 requests/hour
- **Enterprise**: 20000 requests/hour

---

## 🏗️ AWS Integration

### Cross-Account Role Setup

#### Customer IAM Role Trust Policy
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

#### Minimal Permissions Policy
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
        "pricing:GetProducts"
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
        }
      }
    }
  ]
}
```

### Resource Scanning Logic

#### EBS Volume Detection
```python
def scan_ebs_volumes(ec2_client, region):
    volumes = ec2_client.describe_volumes(
        Filters=[
            {'Name': 'state', 'Values': ['available']},
            {'Name': 'attachment.status', 'Values': ['detached']}
        ]
    )
    
    waste_volumes = []
    for volume in volumes['Volumes']:
        if is_too_recent(volume['CreateTime'], min_days=7):
            continue
        if has_protection_tags(volume.get('Tags', [])):
            continue
            
        monthly_cost = calculate_ebs_cost(volume['Size'], volume['VolumeType'], region)
        
        waste_volumes.append({
            'resource_id': volume['VolumeId'],
            'resource_type': 'ebs_volume',
            'region': region,
            'monthly_cost': monthly_cost,
            'confidence_score': calculate_confidence_score(volume),
            'risk_level': assess_risk_level(volume)
        })
    
    return waste_volumes
```

### Safety Mechanisms

#### Confidence Scoring Algorithm
```python
def calculate_confidence_score(resource):
    score = 100
    
    # Age factor (older = safer)
    age_days = (datetime.now() - resource['created_time']).days
    if age_days < 7:
        score -= 50
    elif age_days < 30:
        score -= 20
    
    # Tag factor
    tags = resource.get('tags', [])
    for tag in tags:
        if tag['Key'].lower() in ['environment', 'project', 'owner']:
            score -= 10
    
    # Size factor (for EBS volumes)
    if resource['resource_type'] == 'ebs_volume' and resource['size_gb'] > 100:
        score -= 15
    
    return max(1, min(100, score))
```

---

## 🔐 Code Protection & IP Security

### Protection Strategies

#### 1. Legal Protection
- **NDA**: Required before code sharing
- **Proprietary License**: All rights reserved
- **Contributor Agreement**: IP ownership for contributors
- **Code Escrow**: Third-party holds source for enterprise customers

#### 2. Technical Protection

##### Code Obfuscation
```python
# Install obfuscation tool
pip install pyarmor

# Obfuscate sensitive modules
pyarmor obfuscate --recursive cloudsweep/core/
pyarmor obfuscate --recursive cloudsweep/algorithms/
```

##### Core Logic Separation
```python
# Repository Structure for IP Protection
cloudsweep/
├── public/                    # Shareable code
│   ├── cli/                  # Command line interface
│   ├── utils/                # General utilities
│   └── tests/                # Public tests
├── private/                  # Protected code (gitignored)
│   ├── algorithms/           # Core business logic
│   ├── pricing/              # Proprietary pricing models
│   └── ml_models/            # Machine learning algorithms
```

##### Environment-Based Licensing
```python
class LicenseManager:
    def validate_license(self):
        if not self.license_key:
            raise Exception("CLOUDSWEEP_LICENSE environment variable required")
        if not self._is_valid_license(self.license_key):
            raise Exception("Invalid license key")
        if self._is_expired(self.license_key):
            raise Exception("License expired - contact support")
```

#### 3. Runtime Protection

##### Hardware Fingerprinting
```python
class MachineFingerprint:
    def _generate_fingerprint(self):
        components = [
            platform.node(),
            platform.processor(),
            platform.system(),
            str(psutil.virtual_memory().total),
            self._get_mac_address()
        ]
        machine_string = "-".join(components)
        return hashlib.sha256(machine_string.encode()).hexdigest()
```

##### Time-Limited Demo Licenses
```python
class DemoLicense:
    def check_demo_validity(self):
        if datetime.now() > self.expiry_date:
            print("Demo expired - contact sales for full license")
            exit(1)
```

### Recommended Protection Levels

#### For Early Colleagues/Testers
1. Simple NDA
2. Core algorithm separation + demo license
3. Compiled executable with time limit
4. Basic usage tracking

#### For Potential Partners
1. Comprehensive partnership agreement
2. Code escrow + limited source access
3. Gradual code disclosure
4. Detailed analytics + watermarking

---

*Last Updated: January 2025*
*Architecture Review: Monthly*
*Security Review: Quarterly*