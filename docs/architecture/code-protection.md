# CloudSweep - Code Protection & IP Security

## 🔐 Overview

This document outlines strategies to protect CloudSweep's intellectual property and source code when sharing with colleagues, partners, or potential collaborators.

## 🛡️ Protection Strategies

### 1. Legal Protection Framework

#### Required Legal Documents
```
cloudsweep/
├── legal/
│   ├── NDA-template.md          # Non-disclosure agreement
│   ├── LICENSE.md               # Proprietary license
│   ├── CONTRIBUTOR-AGREEMENT.md # IP ownership for contributors
│   └── PARTNERSHIP-AGREEMENT.md # Technical partner terms
```

#### Key Legal Protections
- **NDA (Non-Disclosure Agreement)**: Must be signed before any code sharing
- **Proprietary License**: "All rights reserved" - no open source components
- **Contributor Agreement**: Any contributed code becomes company property
- **Code Escrow**: Third-party holds source code for enterprise customers

### 2. Technical Code Protection

#### A) Code Obfuscation
```python
# Install obfuscation tool
pip install pyarmor

# Obfuscate sensitive modules
pyarmor obfuscate --recursive cloudsweep/core/
pyarmor obfuscate --recursive cloudsweep/algorithms/

# Creates unreadable but executable code
# Original: def calculate_waste_score(resources):
# Obfuscated: exec(marshal.loads(zlib.decompress(base64.b64decode(...))))
```

#### B) Core Logic Separation
```python
# Repository Structure for IP Protection
cloudsweep/
├── public/                    # Shareable code
│   ├── cli/                  # Command line interface
│   ├── utils/                # General utilities
│   ├── aws_client/           # AWS API wrappers
│   └── tests/                # Public tests
├── private/                  # Protected code (add to .gitignore)
│   ├── algorithms/           # Core business logic
│   │   ├── waste_detection.py
│   │   ├── cost_calculation.py
│   │   └── risk_assessment.py
│   ├── pricing/              # Proprietary pricing models
│   └── ml_models/            # Machine learning algorithms
└── .gitignore               # Exclude private/ folder

# Example separation
# public/scanner.py (shareable)
from private.algorithms import calculate_waste_score

def scan_resources():
    resources = get_aws_resources()
    return calculate_waste_score(resources)  # Black box call

# private/algorithms/waste_detection.py (protected)
def calculate_waste_score(resources):
    # Your secret sauce algorithm
    # Complex proprietary logic here
    pass
```

#### C) Environment-Based Licensing
```python
import os
import hashlib
import platform
from datetime import datetime, timedelta

class LicenseManager:
    def __init__(self):
        self.license_key = os.getenv('CLOUDSWEEP_LICENSE')
        self.machine_id = self._get_machine_fingerprint()
        
    def validate_license(self):
        """Validate license before allowing execution"""
        if not self.license_key:
            raise Exception("CLOUDSWEEP_LICENSE environment variable required")
            
        if not self._is_valid_license(self.license_key):
            raise Exception("Invalid license key")
            
        if self._is_expired(self.license_key):
            raise Exception("License expired - contact support")
    
    def _get_machine_fingerprint(self):
        """Generate unique machine identifier"""
        machine_info = f"{platform.node()}-{platform.processor()}-{platform.system()}"
        return hashlib.md5(machine_info.encode()).hexdigest()
    
    def _is_valid_license(self, key):
        """Validate license key format and authenticity"""
        try:
            # Decode license (base64 + encryption)
            decoded = base64.b64decode(key)
            decrypted = self._decrypt_license(decoded)
            
            # Check machine binding
            if self.machine_id not in decrypted:
                return False
                
            return True
        except:
            return False
    
    def _is_expired(self, key):
        """Check if license is expired"""
        # Extract expiration date from license
        # Return True if expired
        pass

# Usage in main application
def main():
    license_manager = LicenseManager()
    license_manager.validate_license()
    
    # Continue with application logic
    run_cloudsweep()
```

### 3. Repository Security

#### A) Git Submodules for Sensitive Code
```bash
# Keep sensitive code in separate private repository
git submodule add git@github.com:yourcompany/cloudsweep-core.git private/core

# Main repository structure
cloudsweep-public/           # Public repository
├── cli/
├── utils/
├── tests/
└── private/core/           # Git submodule (private repo)
    ├── algorithms/
    └── models/

# Colleagues get main repo but not the submodule
git clone https://github.com/yourcompany/cloudsweep-public.git
# They can't access private/core/ without separate access
```

#### B) Selective File Sharing
```bash
# .gitignore for protecting sensitive files
# CloudSweep .gitignore

# Sensitive algorithms
private/
algorithms/
models/
pricing_data/

# Configuration files with secrets
config/production.yaml
config/pricing.json
.env.production

# License keys and certificates
licenses/
certificates/
keys/

# Compiled proprietary modules
*.pyc
__pycache__/
build/
dist/
```

### 4. Runtime Protection

#### A) Hardware Fingerprinting
```python
import platform
import hashlib
import psutil

class MachineFingerprint:
    def __init__(self):
        self.fingerprint = self._generate_fingerprint()
    
    def _generate_fingerprint(self):
        """Generate unique machine identifier"""
        components = [
            platform.node(),           # Computer name
            platform.processor(),      # Processor info
            platform.system(),         # OS
            str(psutil.virtual_memory().total),  # RAM size
            self._get_mac_address()     # Network MAC
        ]
        
        machine_string = "-".join(components)
        return hashlib.sha256(machine_string.encode()).hexdigest()
    
    def _get_mac_address(self):
        """Get primary network interface MAC address"""
        import uuid
        return ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                        for elements in range(0,2*6,2)][::-1])
    
    def is_authorized(self, authorized_fingerprints):
        """Check if current machine is authorized"""
        return self.fingerprint in authorized_fingerprints

# Usage
def check_machine_authorization():
    machine = MachineFingerprint()
    authorized_machines = [
        "a1b2c3d4e5f6...",  # Your development machine
        "f6e5d4c3b2a1...",  # Authorized colleague machine
        "1234567890ab..."   # Demo machine
    ]
    
    if not machine.is_authorized(authorized_machines):
        print("Unauthorized machine detected")
        print(f"Machine fingerprint: {machine.fingerprint}")
        print("Contact support for authorization")
        exit(1)
```

#### B) Time-Limited Demo Licenses
```python
from datetime import datetime, timedelta
import json
import base64

class DemoLicense:
    def __init__(self, demo_days=14):
        self.demo_period = timedelta(days=demo_days)
        self.start_date = datetime.now()
        self.expiry_date = self.start_date + self.demo_period
        
    def check_demo_validity(self):
        """Check if demo period is still valid"""
        current_time = datetime.now()
        
        if current_time > self.expiry_date:
            days_expired = (current_time - self.expiry_date).days
            print(f"Demo expired {days_expired} days ago")
            print("Contact sales for full license: sales@cloudsweep.io")
            exit(1)
        
        remaining_days = (self.expiry_date - current_time).days
        if remaining_days <= 3:
            print(f"Demo expires in {remaining_days} days")
            print("Contact sales for full license: sales@cloudsweep.io")
    
    def generate_demo_license(self, machine_fingerprint):
        """Generate time-limited demo license"""
        license_data = {
            "type": "demo",
            "machine": machine_fingerprint,
            "start": self.start_date.isoformat(),
            "expiry": self.expiry_date.isoformat(),
            "features": ["scan", "report"],  # Limited features
            "max_accounts": 1  # Limit AWS accounts
        }
        
        # Encode license
        license_json = json.dumps(license_data)
        license_b64 = base64.b64encode(license_json.encode()).decode()
        return license_b64

# Usage in application
def main():
    demo = DemoLicense(days=14)
    demo.check_demo_validity()
    
    # Continue with limited functionality
    run_demo_mode()
```

### 5. Distribution Security

#### A) Compiled Distribution
```python
# PyInstaller configuration for secure distribution
# build_secure.py

import PyInstaller.__main__
import os

def build_secure_executable():
    """Build obfuscated executable"""
    
    # First obfuscate the code
    os.system("pyarmor obfuscate --recursive cloudsweep/")
    
    # Then compile to executable
    PyInstaller.__main__.run([
        '--onefile',                    # Single executable
        '--noconsole',                  # No console window
        '--hidden-import=boto3',        # Include AWS SDK
        '--hidden-import=click',        # Include CLI framework
        '--add-data=config:config',     # Include config files
        '--name=cloudsweep-demo',       # Output name
        'cloudsweep/main.py'           # Entry point
    ])

# Usage
# python build_secure.py
# Generates: dist/cloudsweep-demo.exe
```

#### B) Docker Container Distribution
```dockerfile
# Dockerfile for secure distribution
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 cloudsweep

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy obfuscated code only
COPY dist/obfuscated/ /app/
WORKDIR /app

# Remove source files and build tools
RUN apt-get remove -y gcc python3-dev && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    find /app -name "*.py" -type f -delete && \
    find /app -name "__pycache__" -type d -exec rm -rf {} +

# Switch to non-root user
USER cloudsweep

# Set entrypoint
ENTRYPOINT ["python", "-m", "cloudsweep"]

# Build and distribute
# docker build -t cloudsweep:demo .
# docker save cloudsweep:demo > cloudsweep-demo.tar
```

### 6. Monitoring & Tracking

#### A) Usage Analytics
```python
import uuid
import requests
import threading
from datetime import datetime

class UsageTracker:
    def __init__(self, user_id, license_type="demo"):
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        self.license_type = license_type
        self.analytics_endpoint = "https://analytics.cloudsweep.io/track"
        
    def track_usage(self, action, metadata=None):
        """Track feature usage asynchronously"""
        def send_analytics():
            try:
                payload = {
                    "user_id": self.user_id,
                    "session_id": self.session_id,
                    "license_type": self.license_type,
                    "action": action,
                    "metadata": metadata or {},
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "1.0.0"
                }
                
                requests.post(
                    self.analytics_endpoint,
                    json=payload,
                    timeout=5
                )
            except:
                pass  # Fail silently
        
        # Send in background thread
        thread = threading.Thread(target=send_analytics)
        thread.daemon = True
        thread.start()
    
    def track_scan(self, aws_account_count, resources_found):
        """Track scan operations"""
        self.track_usage("scan", {
            "aws_accounts": aws_account_count,
            "resources_found": resources_found
        })
    
    def track_cleanup(self, resources_cleaned, estimated_savings):
        """Track cleanup operations"""
        self.track_usage("cleanup", {
            "resources_cleaned": resources_cleaned,
            "estimated_savings": estimated_savings
        })

# Usage in application
tracker = UsageTracker("demo-user-123", "demo")
tracker.track_scan(aws_account_count=1, resources_found=25)
```

#### B) Code Watermarking
```python
import hashlib
import time

class CodeWatermark:
    def __init__(self, user_id, distribution_id):
        self.user_id = user_id
        self.distribution_id = distribution_id
        self.watermark = self._generate_watermark()
    
    def _generate_watermark(self):
        """Generate unique watermark for this distribution"""
        data = f"{self.user_id}-{self.distribution_id}-{int(time.time())}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def embed_watermark(self, code_content):
        """Embed watermark in code comments"""
        watermark_comment = f"# Distribution ID: {self.watermark}\n"
        return watermark_comment + code_content
    
    def verify_watermark(self, code_content):
        """Verify watermark in distributed code"""
        lines = code_content.split('\n')
        for line in lines:
            if "Distribution ID:" in line:
                found_watermark = line.split(":")[1].strip()
                return found_watermark == self.watermark
        return False

# Usage
watermark = CodeWatermark("colleague-001", "demo-2025-01")
watermarked_code = watermark.embed_watermark(original_code)
```

## 🎯 Recommended Protection Levels

### For Early Colleagues/Testers
1. **Legal**: Simple NDA
2. **Technical**: Core algorithm separation + demo license
3. **Distribution**: Compiled executable with time limit
4. **Monitoring**: Basic usage tracking

### For Potential Partners
1. **Legal**: Comprehensive partnership agreement
2. **Technical**: Code escrow + limited source access
3. **Distribution**: Gradual code disclosure
4. **Monitoring**: Detailed analytics + watermarking

### For Customer Demos
1. **Legal**: Standard terms of service
2. **Technical**: SaaS demo (no code sharing)
3. **Distribution**: Web-based demo or compiled tool
4. **Monitoring**: Feature usage analytics

### For Investors
1. **Legal**: NDA + due diligence agreement
2. **Technical**: Code review in controlled environment
3. **Distribution**: Screen sharing or escrow access
4. **Monitoring**: Access logging

## 🔧 Implementation Checklist

- [ ] Set up legal document templates
- [ ] Implement license validation system
- [ ] Create code obfuscation pipeline
- [ ] Set up private repository structure
- [ ] Implement machine fingerprinting
- [ ] Create demo license generator
- [ ] Set up usage analytics
- [ ] Implement code watermarking
- [ ] Create secure build pipeline
- [ ] Test protection mechanisms

---

*Last Updated: January 2025*
*Security Review: Before each distribution*
*Legal Review: Quarterly*