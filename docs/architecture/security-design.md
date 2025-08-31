# CloudSweep - Security Architecture & Design

## 🔐 Security Overview

CloudSweep handles sensitive AWS credentials and financial data, requiring enterprise-grade security across all system components. Our security model follows defense-in-depth principles with multiple layers of protection.

## 🏛️ Security Architecture Layers

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

## 🔑 Authentication & Authorization

### JWT Token Strategy
```python
# Token Configuration
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30
ALGORITHM = "HS256"
SECRET_KEY = os.getenv("JWT_SECRET_KEY")  # 256-bit random key

# Token Payload Structure
{
  "sub": "user_id",           # Subject (user ID)
  "org": "organization_id",   # Organization context
  "role": "admin",           # User role
  "iat": 1642694400,         # Issued at
  "exp": 1642698000,         # Expires at
  "jti": "unique_token_id"   # JWT ID for revocation
}
```

### Role-Based Access Control (RBAC)
```python
class UserRole(Enum):
    VIEWER = "viewer"      # Read-only access
    MEMBER = "member"      # Standard user operations
    ADMIN = "admin"        # Full organization access
    OWNER = "owner"        # Billing and user management

# Permission Matrix
PERMISSIONS = {
    "viewer": [
        "scans:read",
        "waste_items:read",
        "reports:read"
    ],
    "member": [
        "scans:read", "scans:create",
        "waste_items:read", "waste_items:approve",
        "reports:read",
        "aws_accounts:read"
    ],
    "admin": [
        "*:*",  # All permissions except billing
        "!billing:*"  # Explicit deny
    ],
    "owner": [
        "*:*"  # All permissions including billing
    ]
}
```

### Multi-Factor Authentication (MFA)
```python
# TOTP Implementation
class MFAManager:
    def generate_secret(self) -> str:
        """Generate TOTP secret for user"""
        return pyotp.random_base32()
    
    def verify_token(self, secret: str, token: str) -> bool:
        """Verify TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)
    
    def generate_backup_codes(self) -> List[str]:
        """Generate one-time backup codes"""
        return [secrets.token_hex(4) for _ in range(10)]
```

## 🛡️ AWS Security Model

### Cross-Account Role Strategy
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

### Minimal IAM Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadOnlyAccess",
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "rds:Describe*",
        "elasticloadbalancing:Describe*",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics",
        "pricing:GetProducts",
        "pricing:GetAttributeValues",
        "support:DescribeTrustedAdvisorChecks",
        "support:DescribeTrustedAdvisorCheckResult"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CleanupActions",
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteVolume",
        "ec2:DeleteSnapshot",
        "ec2:ReleaseAddress",
        "ec2:DeleteLoadBalancer",
        "rds:DeleteDBInstance",
        "rds:StopDBInstance"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2", "eu-west-1"]
        },
        "ForAllValues:StringLike": {
          "aws:TagKeys": ["CloudSweep:*"]
        }
      }
    }
  ]
}
```

### AWS Credential Management
```python
class AWSCredentialManager:
    def __init__(self):
        self.sts_client = boto3.client('sts')
        self.session_cache = {}  # Redis-backed cache
    
    def assume_role(self, role_arn: str, external_id: str) -> boto3.Session:
        """Assume cross-account role with temporary credentials"""
        cache_key = f"{role_arn}:{external_id}"
        
        # Check cache for valid session
        if cache_key in self.session_cache:
            session = self.session_cache[cache_key]
            if not self._is_session_expired(session):
                return session
        
        # Assume role with external ID
        response = self.sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=f"CloudSweep-{int(time.time())}",
            ExternalId=external_id,
            DurationSeconds=3600  # 1 hour
        )
        
        # Create session with temporary credentials
        session = boto3.Session(
            aws_access_key_id=response['Credentials']['AccessKeyId'],
            aws_secret_access_key=response['Credentials']['SecretAccessKey'],
            aws_session_token=response['Credentials']['SessionToken']
        )
        
        # Cache session
        self.session_cache[cache_key] = session
        return session
    
    def _is_session_expired(self, session: boto3.Session) -> bool:
        """Check if AWS session is expired"""
        try:
            sts = session.client('sts')
            sts.get_caller_identity()
            return False
        except ClientError:
            return True
```

## 🔒 Data Encryption

### Encryption at Rest
```python
# Database Encryption
DATABASE_URL = "postgresql://user:pass@host:5432/db?sslmode=require"
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "connect_args": {
        "sslmode": "require",
        "sslcert": "/path/to/client-cert.pem",
        "sslkey": "/path/to/client-key.pem",
        "sslrootcert": "/path/to/ca-cert.pem"
    }
}

# Field-Level Encryption for Sensitive Data
class EncryptedField:
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)
    
    def encrypt(self, value: str) -> str:
        """Encrypt sensitive field value"""
        return self.fernet.encrypt(value.encode()).decode()
    
    def decrypt(self, encrypted_value: str) -> str:
        """Decrypt sensitive field value"""
        return self.fernet.decrypt(encrypted_value.encode()).decode()

# Usage for sensitive fields
class AWSAccount(Base):
    __tablename__ = "aws_accounts"
    
    id = Column(UUID, primary_key=True)
    role_arn = Column(String)  # Not encrypted (not sensitive)
    external_id = Column(String)  # Encrypted in application layer
```

### Encryption in Transit
```python
# TLS Configuration
TLS_CONFIG = {
    "ssl_version": ssl.PROTOCOL_TLSv1_3,
    "ssl_ciphers": "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS",
    "ssl_options": ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
}

# Certificate Pinning for AWS API calls
AWS_CERT_PINS = [
    "sha256/9acfab7e43c8d880d06b262a94deeee4b4659989c3d0caf19baf6405e41ab7df",
    "sha256/a031c46782e6e6334c69a85954267b5b1d5dc0c6d5b3a1b6b6b6b6b6b6b6b6b6"
]
```

### Key Management
```python
class KeyManager:
    def __init__(self):
        self.kms_client = boto3.client('kms')
        self.key_id = os.getenv('AWS_KMS_KEY_ID')
    
    def encrypt_data_key(self, plaintext_key: bytes) -> dict:
        """Encrypt data encryption key with KMS"""
        response = self.kms_client.encrypt(
            KeyId=self.key_id,
            Plaintext=plaintext_key
        )
        return {
            'encrypted_key': response['CiphertextBlob'],
            'key_id': response['KeyId']
        }
    
    def decrypt_data_key(self, encrypted_key: bytes) -> bytes:
        """Decrypt data encryption key with KMS"""
        response = self.kms_client.decrypt(
            CiphertextBlob=encrypted_key
        )
        return response['Plaintext']
    
    def rotate_keys(self):
        """Rotate encryption keys"""
        # Generate new data encryption key
        new_key = Fernet.generate_key()
        
        # Encrypt with KMS
        encrypted_new_key = self.encrypt_data_key(new_key)
        
        # Update key in secure storage
        self._store_encrypted_key(encrypted_new_key)
```

## 🛡️ Input Validation & Sanitization

### Request Validation
```python
from pydantic import BaseModel, validator, Field
import re

class AWSAccountCreate(BaseModel):
    account_id: str = Field(..., regex=r'^\d{12}$')
    account_name: str = Field(..., min_length=1, max_length=255)
    role_arn: str = Field(..., regex=r'^arn:aws:iam::\d{12}:role/[\w+=,.@-]+$')
    external_id: str = Field(..., min_length=8, max_length=64)
    regions: List[str] = Field(default_factory=list)
    
    @validator('regions')
    def validate_regions(cls, v):
        valid_regions = [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-west-2', 'eu-central-1',
            'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1'
        ]
        for region in v:
            if region not in valid_regions:
                raise ValueError(f'Invalid AWS region: {region}')
        return v
    
    @validator('account_name')
    def validate_account_name(cls, v):
        # Prevent XSS and injection attacks
        if re.search(r'[<>"\']', v):
            raise ValueError('Account name contains invalid characters')
        return v.strip()

# SQL Injection Prevention
class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
    
    def execute_query(self, query: str, params: dict):
        """Execute parameterized query to prevent SQL injection"""
        with self.engine.connect() as conn:
            # Use parameterized queries only
            result = conn.execute(text(query), params)
            return result.fetchall()
```

### Output Encoding
```python
class ResponseEncoder:
    @staticmethod
    def encode_json_response(data: dict) -> dict:
        """Encode response data to prevent XSS"""
        if isinstance(data, dict):
            return {k: ResponseEncoder.encode_value(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [ResponseEncoder.encode_value(item) for item in data]
        return data
    
    @staticmethod
    def encode_value(value):
        """Encode individual values"""
        if isinstance(value, str):
            # HTML encode special characters
            return html.escape(value, quote=True)
        return value
```

## 🔍 Security Monitoring & Logging

### Audit Logging
```python
class AuditLogger:
    def __init__(self):
        self.logger = structlog.get_logger("audit")
    
    def log_action(self, user_id: str, action: str, resource: str, 
                   details: dict, ip_address: str):
        """Log security-relevant actions"""
        self.logger.info(
            "security_event",
            user_id=user_id,
            action=action,
            resource=resource,
            details=details,
            ip_address=ip_address,
            timestamp=datetime.utcnow().isoformat(),
            severity="info"
        )
    
    def log_security_event(self, event_type: str, severity: str, 
                          details: dict, ip_address: str = None):
        """Log security incidents"""
        self.logger.warning(
            "security_incident",
            event_type=event_type,
            severity=severity,
            details=details,
            ip_address=ip_address,
            timestamp=datetime.utcnow().isoformat()
        )

# Usage Examples
audit = AuditLogger()

# Log successful login
audit.log_action(
    user_id="uuid",
    action="login",
    resource="auth",
    details={"method": "password", "mfa": True},
    ip_address="192.168.1.100"
)

# Log failed login attempt
audit.log_security_event(
    event_type="failed_login",
    severity="medium",
    details={"email": "user@example.com", "attempts": 3},
    ip_address="192.168.1.100"
)
```

### Intrusion Detection
```python
class SecurityMonitor:
    def __init__(self):
        self.redis = redis.Redis()
        self.alert_manager = AlertManager()
    
    def check_rate_limiting(self, user_id: str, action: str) -> bool:
        """Check for suspicious activity patterns"""
        key = f"rate_limit:{user_id}:{action}"
        current_count = self.redis.incr(key)
        
        if current_count == 1:
            self.redis.expire(key, 3600)  # 1 hour window
        
        # Alert on suspicious activity
        if current_count > 100:  # Threshold
            self.alert_manager.send_alert(
                "suspicious_activity",
                f"User {user_id} exceeded rate limit for {action}",
                severity="high"
            )
            return False
        
        return True
    
    def detect_anomalies(self, user_id: str, ip_address: str, 
                        user_agent: str):
        """Detect anomalous login patterns"""
        # Check for new IP address
        known_ips = self.redis.smembers(f"known_ips:{user_id}")
        if ip_address not in known_ips:
            self.alert_manager.send_alert(
                "new_ip_login",
                f"User {user_id} logged in from new IP: {ip_address}",
                severity="medium"
            )
        
        # Check for suspicious user agent
        if self._is_suspicious_user_agent(user_agent):
            self.alert_manager.send_alert(
                "suspicious_user_agent",
                f"Suspicious user agent detected: {user_agent}",
                severity="medium"
            )
```

## 🔐 Secrets Management

### Application Secrets
```python
class SecretsManager:
    def __init__(self):
        self.ssm_client = boto3.client('ssm')
        self.secrets_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def get_secret(self, secret_name: str) -> str:
        """Retrieve secret from AWS Systems Manager Parameter Store"""
        cache_key = f"secret:{secret_name}"
        
        # Check cache
        if cache_key in self.secrets_cache:
            cached_secret, timestamp = self.secrets_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_secret
        
        # Retrieve from SSM
        try:
            response = self.ssm_client.get_parameter(
                Name=secret_name,
                WithDecryption=True
            )
            secret_value = response['Parameter']['Value']
            
            # Cache the secret
            self.secrets_cache[cache_key] = (secret_value, time.time())
            return secret_value
            
        except ClientError as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise
    
    def rotate_secret(self, secret_name: str, new_value: str):
        """Rotate application secret"""
        try:
            self.ssm_client.put_parameter(
                Name=secret_name,
                Value=new_value,
                Type='SecureString',
                Overwrite=True
            )
            
            # Clear cache
            cache_key = f"secret:{secret_name}"
            if cache_key in self.secrets_cache:
                del self.secrets_cache[cache_key]
                
        except ClientError as e:
            logger.error(f"Failed to rotate secret {secret_name}: {e}")
            raise
```

## 🛡️ Container Security

### Dockerfile Security Best Practices
```dockerfile
# Use minimal base image
FROM python:3.11-slim-bullseye

# Create non-root user
RUN groupadd -r cloudsweep && useradd -r -g cloudsweep cloudsweep

# Install security updates
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=cloudsweep:cloudsweep . .

# Remove unnecessary files
RUN rm -rf tests/ docs/ .git/

# Switch to non-root user
USER cloudsweep

# Set security headers
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Runtime Security
```python
# Security middleware
class SecurityMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add security headers
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    
                    # Security headers
                    security_headers = {
                        b"x-content-type-options": b"nosniff",
                        b"x-frame-options": b"DENY",
                        b"x-xss-protection": b"1; mode=block",
                        b"strict-transport-security": b"max-age=31536000; includeSubDomains",
                        b"content-security-policy": b"default-src 'self'",
                        b"referrer-policy": b"strict-origin-when-cross-origin"
                    }
                    
                    headers.update(security_headers)
                    message["headers"] = list(headers.items())
                
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)
```

## 📋 Security Compliance

### SOC 2 Type II Controls
```python
class ComplianceControls:
    def __init__(self):
        self.audit_logger = AuditLogger()
    
    def access_control_review(self):
        """CC6.1 - Logical and physical access controls"""
        # Review user access permissions
        # Log access control changes
        # Monitor privileged access
        pass
    
    def data_classification(self):
        """CC6.7 - Data classification and handling"""
        # Classify sensitive data
        # Apply appropriate controls
        # Monitor data access
        pass
    
    def vulnerability_management(self):
        """CC7.1 - Vulnerability identification and remediation"""
        # Scan for vulnerabilities
        # Track remediation efforts
        # Report on security posture
        pass
```

### GDPR Compliance
```python
class GDPRCompliance:
    def __init__(self):
        self.data_processor = DataProcessor()
    
    def data_subject_request(self, user_id: str, request_type: str):
        """Handle GDPR data subject requests"""
        if request_type == "access":
            return self._export_user_data(user_id)
        elif request_type == "deletion":
            return self._delete_user_data(user_id)
        elif request_type == "portability":
            return self._export_portable_data(user_id)
    
    def _export_user_data(self, user_id: str) -> dict:
        """Export all user data for GDPR access request"""
        # Collect all user data from all systems
        # Return in structured format
        pass
    
    def _delete_user_data(self, user_id: str):
        """Delete user data for GDPR deletion request"""
        # Anonymize or delete user data
        # Maintain audit trail
        # Notify data processors
        pass
```

---

*Last Updated: January 2025*
*Security Review: Quarterly*
*Compliance Audit: Annual*