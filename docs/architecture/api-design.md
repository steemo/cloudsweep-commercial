# CloudSweep - API Design Specification

## 🌐 API Architecture

### Technology Stack
- **Framework**: FastAPI (Python)
- **Authentication**: JWT with refresh tokens
- **Documentation**: Auto-generated OpenAPI/Swagger
- **Validation**: Pydantic models
- **Rate Limiting**: Redis-based sliding window

### Base URL Structure
```
Production:  https://api.cloudsweep.io/v1
Staging:     https://api-staging.cloudsweep.io/v1
Development: http://localhost:8000/v1
```

## 🔐 Authentication Endpoints

### POST /auth/login
```json
Request:
{
  "email": "user@example.com",
  "password": "secure_password"
}

Response (200):
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "admin",
    "organization": {
      "id": "uuid",
      "name": "Acme Corp",
      "plan_type": "pro"
    }
  }
}

Error (401):
{
  "detail": "Invalid credentials"
}
```

### POST /auth/refresh
```json
Request:
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}

Response (200):
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### DELETE /auth/logout
```json
Headers: Authorization: Bearer <access_token>

Response (204): No content
```

## 🏢 Organization Management

### GET /organizations/me
```json
Headers: Authorization: Bearer <access_token>

Response (200):
{
  "id": "uuid",
  "name": "Acme Corp",
  "slug": "acme-corp",
  "plan_type": "pro",
  "billing_email": "billing@acme.com",
  "monthly_scan_limit": 100,
  "auto_cleanup_enabled": true,
  "usage": {
    "scans_this_month": 15,
    "total_savings_this_month": 2450.75,
    "aws_accounts_connected": 3
  },
  "created_at": "2025-01-01T00:00:00Z"
}
```

### PUT /organizations/me
```json
Request:
{
  "name": "Acme Corporation",
  "billing_email": "finance@acme.com",
  "auto_cleanup_enabled": false
}

Response (200): Updated organization object
```

## ☁️ AWS Account Management

### GET /aws-accounts
```json
Headers: Authorization: Bearer <access_token>

Query Parameters:
- page: integer (default: 1)
- limit: integer (default: 20, max: 100)
- status: string (connected, failed, pending)

Response (200):
{
  "items": [
    {
      "id": "uuid",
      "account_id": "123456789012",
      "account_name": "Production Account",
      "role_arn": "arn:aws:iam::123456789012:role/CloudSweepRole",
      "regions": ["us-east-1", "us-west-2"],
      "scan_enabled": true,
      "auto_cleanup_enabled": false,
      "connection_status": "connected",
      "last_scan_at": "2025-01-15T10:30:00Z",
      "total_monthly_waste": 1250.50,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 3,
  "page": 1,
  "limit": 20,
  "pages": 1
}
```

### POST /aws-accounts
```json
Request:
{
  "account_id": "123456789012",
  "account_name": "Production Account",
  "role_arn": "arn:aws:iam::123456789012:role/CloudSweepRole",
  "external_id": "unique-external-id",
  "regions": ["us-east-1", "us-west-2", "eu-west-1"],
  "scan_enabled": true,
  "auto_cleanup_enabled": false
}

Response (201): Created AWS account object

Error (400):
{
  "detail": "Invalid role ARN format"
}

Error (409):
{
  "detail": "AWS account already exists"
}
```

### PUT /aws-accounts/{account_id}
```json
Request:
{
  "account_name": "Updated Production Account",
  "regions": ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
  "scan_enabled": true,
  "auto_cleanup_enabled": true
}

Response (200): Updated AWS account object
```

### DELETE /aws-accounts/{account_id}
```json
Response (204): No content

Error (409):
{
  "detail": "Cannot delete account with pending scans"
}
```

### POST /aws-accounts/{account_id}/test-connection
```json
Response (200):
{
  "status": "success",
  "message": "Successfully connected to AWS account",
  "permissions_verified": [
    "ec2:DescribeVolumes",
    "ec2:DescribeSnapshots",
    "ec2:DescribeAddresses"
  ],
  "regions_accessible": ["us-east-1", "us-west-2"],
  "test_duration_ms": 1250
}

Error (400):
{
  "status": "failed",
  "message": "Access denied: Missing required permissions",
  "missing_permissions": ["ec2:DescribeVolumes"],
  "error_code": "AccessDenied"
}
```

## 🔍 Scan Management

### GET /scans
```json
Query Parameters:
- aws_account_id: uuid (optional)
- status: string (running, completed, failed)
- page: integer (default: 1)
- limit: integer (default: 20)
- sort: string (started_at, completed_at)
- order: string (asc, desc)

Response (200):
{
  "items": [
    {
      "id": "uuid",
      "aws_account": {
        "id": "uuid",
        "account_id": "123456789012",
        "account_name": "Production"
      },
      "scan_type": "full",
      "status": "completed",
      "regions_scanned": ["us-east-1", "us-west-2"],
      "total_resources_scanned": 1250,
      "total_waste_items_found": 45,
      "total_monthly_waste_cost": 890.25,
      "scan_duration_seconds": 180,
      "started_at": "2025-01-15T10:00:00Z",
      "completed_at": "2025-01-15T10:03:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "limit": 20
}
```

### POST /scans/start
```json
Request:
{
  "aws_account_id": "uuid",
  "scan_type": "full", // full, incremental
  "regions": ["us-east-1", "us-west-2"], // optional, defaults to account regions
  "resource_types": ["ebs_volume", "snapshot", "elastic_ip"] // optional, defaults to all
}

Response (202):
{
  "id": "uuid",
  "status": "running",
  "message": "Scan started successfully",
  "estimated_duration_minutes": 5
}

Error (429):
{
  "detail": "Monthly scan limit exceeded"
}
```

### GET /scans/{scan_id}
```json
Response (200):
{
  "id": "uuid",
  "aws_account": {
    "id": "uuid",
    "account_id": "123456789012",
    "account_name": "Production"
  },
  "scan_type": "full",
  "status": "completed",
  "regions_scanned": ["us-east-1", "us-west-2"],
  "total_resources_scanned": 1250,
  "total_waste_items_found": 45,
  "total_monthly_waste_cost": 890.25,
  "total_annual_waste_cost": 10683.00,
  "scan_duration_seconds": 180,
  "progress": {
    "current_region": "us-west-2",
    "regions_completed": 1,
    "total_regions": 2,
    "current_resource_type": "ebs_volume",
    "percentage_complete": 75
  },
  "started_at": "2025-01-15T10:00:00Z",
  "completed_at": "2025-01-15T10:03:00Z",
  "created_by": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John"
  }
}
```

### DELETE /scans/{scan_id}
```json
Response (204): No content (cancels running scan)

Error (400):
{
  "detail": "Cannot cancel completed scan"
}
```

## 🗑️ Waste Item Management

### GET /waste-items
```json
Query Parameters:
- aws_account_id: uuid (optional)
- scan_result_id: uuid (optional)
- resource_type: string (ebs_volume, snapshot, elastic_ip, etc.)
- cleanup_status: string (pending, approved, rejected, cleaned)
- risk_level: string (safe, low, medium, high)
- min_monthly_cost: float
- max_monthly_cost: float
- page: integer (default: 1)
- limit: integer (default: 50)
- sort: string (monthly_cost, discovered_at, confidence_score)
- order: string (asc, desc)

Response (200):
{
  "items": [
    {
      "id": "uuid",
      "resource_type": "ebs_volume",
      "resource_id": "vol-1234567890abcdef0",
      "resource_arn": "arn:aws:ec2:us-east-1:123456789012:volume/vol-1234567890abcdef0",
      "region": "us-east-1",
      "monthly_cost": 25.60,
      "annual_cost": 307.20,
      "confidence_score": 95,
      "risk_level": "safe",
      "cleanup_status": "pending",
      "resource_details": {
        "size_gb": 100,
        "volume_type": "gp3",
        "state": "available",
        "created_date": "2024-12-01T00:00:00Z",
        "last_attached": null,
        "tags": {}
      },
      "discovered_at": "2025-01-15T10:01:30Z",
      "aws_account": {
        "id": "uuid",
        "account_id": "123456789012",
        "account_name": "Production"
      }
    }
  ],
  "total": 45,
  "page": 1,
  "limit": 50,
  "summary": {
    "total_monthly_cost": 890.25,
    "total_annual_cost": 10683.00,
    "by_risk_level": {
      "safe": 30,
      "low": 10,
      "medium": 4,
      "high": 1
    },
    "by_resource_type": {
      "ebs_volume": 20,
      "snapshot": 15,
      "elastic_ip": 8,
      "load_balancer": 2
    }
  }
}
```

### GET /waste-items/{waste_item_id}
```json
Response (200):
{
  "id": "uuid",
  "resource_type": "ebs_volume",
  "resource_id": "vol-1234567890abcdef0",
  "resource_arn": "arn:aws:ec2:us-east-1:123456789012:volume/vol-1234567890abcdef0",
  "region": "us-east-1",
  "availability_zone": "us-east-1a",
  "monthly_cost": 25.60,
  "annual_cost": 307.20,
  "currency": "USD",
  "confidence_score": 95,
  "risk_level": "safe",
  "safety_checks_passed": true,
  "cleanup_status": "pending",
  "resource_details": {
    "size_gb": 100,
    "volume_type": "gp3",
    "iops": 3000,
    "throughput": 125,
    "state": "available",
    "created_date": "2024-12-01T00:00:00Z",
    "last_attached": null,
    "last_attachment_instance": null,
    "tags": {},
    "encrypted": false,
    "kms_key_id": null
  },
  "scan_result": {
    "id": "uuid",
    "started_at": "2025-01-15T10:00:00Z"
  },
  "aws_account": {
    "id": "uuid",
    "account_id": "123456789012",
    "account_name": "Production"
  },
  "discovered_at": "2025-01-15T10:01:30Z"
}
```

### POST /waste-items/{waste_item_id}/approve
```json
Request:
{
  "action_type": "delete", // delete, stop, resize
  "notes": "Confirmed unused volume, safe to delete"
}

Response (200):
{
  "id": "uuid",
  "cleanup_status": "approved",
  "cleanup_approved_by": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John"
  },
  "cleanup_approved_at": "2025-01-15T14:30:00Z"
}
```

### POST /waste-items/{waste_item_id}/reject
```json
Request:
{
  "reason": "This volume is actually in use by our backup system"
}

Response (200):
{
  "id": "uuid",
  "cleanup_status": "rejected"
}
```

### POST /waste-items/{waste_item_id}/cleanup
```json
Request:
{
  "dry_run": false,
  "force": false // Override safety checks (admin only)
}

Response (202):
{
  "cleanup_job_id": "uuid",
  "message": "Cleanup job started",
  "estimated_duration_minutes": 2
}

Error (400):
{
  "detail": "Waste item not approved for cleanup"
}
```

### POST /waste-items/bulk-cleanup
```json
Request:
{
  "waste_item_ids": ["uuid1", "uuid2", "uuid3"],
  "action_type": "delete",
  "dry_run": false
}

Response (202):
{
  "bulk_cleanup_job_id": "uuid",
  "items_queued": 3,
  "estimated_duration_minutes": 5
}
```

## 📊 Reports & Analytics

### GET /reports/savings
```json
Query Parameters:
- aws_account_id: uuid (optional)
- period: string (week, month, quarter, year)
- start_date: date (YYYY-MM-DD)
- end_date: date (YYYY-MM-DD)

Response (200):
{
  "period": "month",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "total_estimated_savings": 2450.75,
  "total_actual_savings": 2180.50,
  "savings_by_account": [
    {
      "aws_account_id": "uuid",
      "account_name": "Production",
      "estimated_savings": 1500.25,
      "actual_savings": 1320.75
    }
  ],
  "savings_by_resource_type": [
    {
      "resource_type": "ebs_volume",
      "estimated_savings": 1200.00,
      "actual_savings": 1050.25,
      "items_cleaned": 15
    }
  ],
  "trend_data": [
    {
      "date": "2025-01-01",
      "cumulative_savings": 0
    },
    {
      "date": "2025-01-15",
      "cumulative_savings": 1090.25
    },
    {
      "date": "2025-01-31",
      "cumulative_savings": 2180.50
    }
  ]
}
```

### GET /reports/waste-trends
```json
Response (200):
{
  "period_weeks": 12,
  "trend_data": [
    {
      "week": "2025-W01",
      "waste_items_found": 45,
      "total_monthly_cost": 890.25,
      "avg_confidence_score": 87.5
    }
  ],
  "resource_type_trends": [
    {
      "resource_type": "ebs_volume",
      "trend": "increasing", // increasing, decreasing, stable
      "change_percentage": 15.5,
      "current_week_count": 20,
      "previous_week_count": 17
    }
  ]
}
```

## 🔔 WebSocket Events

### Connection
```javascript
const ws = new WebSocket('wss://api.cloudsweep.io/v1/ws?token=<jwt_token>');
```

### Event Types
```json
// Scan Progress
{
  "type": "scan.progress",
  "data": {
    "scan_id": "uuid",
    "progress": {
      "percentage_complete": 45,
      "current_region": "us-west-2",
      "current_resource_type": "ebs_volume",
      "items_found": 12
    }
  }
}

// Scan Completed
{
  "type": "scan.completed",
  "data": {
    "scan_id": "uuid",
    "total_waste_items_found": 45,
    "total_monthly_waste_cost": 890.25,
    "duration_seconds": 180
  }
}

// Cleanup Progress
{
  "type": "cleanup.progress",
  "data": {
    "cleanup_job_id": "uuid",
    "waste_item_id": "uuid",
    "status": "cleaning",
    "progress": "Deleting EBS volume vol-1234567890abcdef0"
  }
}

// Cleanup Completed
{
  "type": "cleanup.completed",
  "data": {
    "cleanup_job_id": "uuid",
    "waste_item_id": "uuid",
    "success": true,
    "monthly_savings": 25.60
  }
}
```

## 🚫 Error Handling

### Standard Error Response Format
```json
{
  "detail": "Human readable error message",
  "error_code": "SPECIFIC_ERROR_CODE",
  "field_errors": { // For validation errors
    "email": ["This field is required"],
    "password": ["Password must be at least 8 characters"]
  },
  "request_id": "uuid" // For debugging
}
```

### HTTP Status Codes
- **200**: Success
- **201**: Created
- **202**: Accepted (async operation started)
- **204**: No Content
- **400**: Bad Request (validation error)
- **401**: Unauthorized
- **403**: Forbidden
- **404**: Not Found
- **409**: Conflict
- **422**: Unprocessable Entity
- **429**: Too Many Requests
- **500**: Internal Server Error

## 🔒 Rate Limiting

### Limits by Plan
```
Free:      100 requests/hour
Starter:   1000 requests/hour  
Pro:       5000 requests/hour
Enterprise: 20000 requests/hour
```

### Rate Limit Headers
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642694400
```

---

*Last Updated: January 2025*
*API Version: 1.0*