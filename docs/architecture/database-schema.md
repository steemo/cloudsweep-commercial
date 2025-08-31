# CloudSweep - Database Schema Design

## 🗂️ Database Architecture

### Technology Choice: PostgreSQL
- **ACID Compliance**: Critical for financial data integrity
- **JSON Support**: Flexible storage for AWS resource metadata
- **Performance**: Excellent for complex queries and reporting
- **Scalability**: Supports read replicas and partitioning

## 📋 Core Tables

### Organizations (Multi-Tenant Architecture)
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan_type VARCHAR(20) NOT NULL DEFAULT 'free', -- free, starter, pro, enterprise
    billing_email VARCHAR(255),
    monthly_scan_limit INTEGER DEFAULT 5,
    auto_cleanup_enabled BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_plan_type ON organizations(plan_type);
```

### Users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(20) NOT NULL DEFAULT 'member', -- admin, member, viewer
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_organization_id ON users(organization_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

### AWS Accounts
```sql
CREATE TABLE aws_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    account_id VARCHAR(12) NOT NULL, -- AWS account number
    account_name VARCHAR(255),
    role_arn VARCHAR(512) NOT NULL, -- Cross-account role ARN
    external_id VARCHAR(255), -- For additional security
    regions TEXT[] DEFAULT ARRAY['us-east-1', 'us-west-2'], -- Enabled regions
    scan_enabled BOOLEAN DEFAULT true,
    auto_cleanup_enabled BOOLEAN DEFAULT false,
    last_scan_at TIMESTAMP WITH TIME ZONE,
    connection_status VARCHAR(20) DEFAULT 'pending', -- pending, connected, failed
    connection_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_aws_accounts_org_account ON aws_accounts(organization_id, account_id);
CREATE INDEX idx_aws_accounts_scan_enabled ON aws_accounts(scan_enabled);
```

### Scan Results
```sql
CREATE TABLE scan_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aws_account_id UUID NOT NULL REFERENCES aws_accounts(id) ON DELETE CASCADE,
    scan_type VARCHAR(20) NOT NULL DEFAULT 'full', -- full, incremental, manual
    status VARCHAR(20) NOT NULL DEFAULT 'running', -- running, completed, failed, cancelled
    regions_scanned TEXT[],
    total_resources_scanned INTEGER DEFAULT 0,
    total_waste_items_found INTEGER DEFAULT 0,
    total_monthly_waste_cost DECIMAL(12,2) DEFAULT 0.00,
    total_annual_waste_cost DECIMAL(12,2) DEFAULT 0.00,
    scan_duration_seconds INTEGER,
    error_message TEXT,
    metadata JSONB, -- Additional scan metadata
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_scan_results_aws_account ON scan_results(aws_account_id);
CREATE INDEX idx_scan_results_status ON scan_results(status);
CREATE INDEX idx_scan_results_started_at ON scan_results(started_at);
```

### Waste Items (Core Entity)
```sql
CREATE TABLE waste_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_result_id UUID NOT NULL REFERENCES scan_results(id) ON DELETE CASCADE,
    aws_account_id UUID NOT NULL REFERENCES aws_accounts(id) ON DELETE CASCADE,
    
    -- Resource Identification
    resource_type VARCHAR(50) NOT NULL, -- ebs_volume, snapshot, elastic_ip, load_balancer, rds_instance
    resource_id VARCHAR(255) NOT NULL, -- AWS resource identifier
    resource_arn VARCHAR(512),
    region VARCHAR(20) NOT NULL,
    availability_zone VARCHAR(30),
    
    -- Cost Information
    monthly_cost DECIMAL(10,2) NOT NULL,
    annual_cost DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Risk Assessment
    confidence_score INTEGER NOT NULL CHECK (confidence_score >= 1 AND confidence_score <= 100),
    risk_level VARCHAR(10) NOT NULL, -- safe, low, medium, high
    safety_checks_passed BOOLEAN DEFAULT false,
    
    -- Cleanup Status
    cleanup_status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected, cleaning, cleaned, failed
    cleanup_approved_by UUID REFERENCES users(id),
    cleanup_approved_at TIMESTAMP WITH TIME ZONE,
    cleanup_executed_at TIMESTAMP WITH TIME ZONE,
    cleanup_error TEXT,
    
    -- Resource Details (JSON for flexibility)
    resource_details JSONB NOT NULL,
    cleanup_metadata JSONB, -- Rollback information, etc.
    
    -- Timestamps
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_waste_items_scan_result ON waste_items(scan_result_id);
CREATE INDEX idx_waste_items_aws_account ON waste_items(aws_account_id);
CREATE INDEX idx_waste_items_resource_type ON waste_items(resource_type);
CREATE INDEX idx_waste_items_cleanup_status ON waste_items(cleanup_status);
CREATE INDEX idx_waste_items_risk_level ON waste_items(risk_level);
CREATE INDEX idx_waste_items_monthly_cost ON waste_items(monthly_cost DESC);
CREATE UNIQUE INDEX idx_waste_items_resource ON waste_items(aws_account_id, resource_id, resource_type);
```

### Cleanup Actions (Audit Trail)
```sql
CREATE TABLE cleanup_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    waste_item_id UUID NOT NULL REFERENCES waste_items(id) ON DELETE CASCADE,
    
    -- Action Details
    action_type VARCHAR(30) NOT NULL, -- delete, stop, resize, detach
    action_description TEXT,
    dry_run BOOLEAN DEFAULT false,
    
    -- Execution Info
    executed_by UUID REFERENCES users(id), -- NULL for automated actions
    execution_method VARCHAR(20) DEFAULT 'manual', -- manual, automated, scheduled
    
    -- Results
    success BOOLEAN NOT NULL,
    error_message TEXT,
    aws_response JSONB, -- Raw AWS API response
    
    -- Rollback Information
    rollback_possible BOOLEAN DEFAULT false,
    rollback_data JSONB, -- Data needed to undo the action
    rollback_executed BOOLEAN DEFAULT false,
    rollback_executed_at TIMESTAMP WITH TIME ZONE,
    
    -- Cost Impact
    estimated_monthly_savings DECIMAL(10,2),
    actual_monthly_savings DECIMAL(10,2), -- Calculated after action
    
    -- Timestamps
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_cleanup_actions_waste_item ON cleanup_actions(waste_item_id);
CREATE INDEX idx_cleanup_actions_executed_by ON cleanup_actions(executed_by);
CREATE INDEX idx_cleanup_actions_success ON cleanup_actions(success);
CREATE INDEX idx_cleanup_actions_executed_at ON cleanup_actions(executed_at);
```

## 📊 Reporting & Analytics Tables

### Savings Summary (Materialized View)
```sql
CREATE MATERIALIZED VIEW savings_summary AS
SELECT 
    o.id as organization_id,
    o.name as organization_name,
    aa.id as aws_account_id,
    aa.account_name,
    DATE_TRUNC('month', ca.executed_at) as month,
    COUNT(ca.id) as total_cleanups,
    SUM(ca.estimated_monthly_savings) as estimated_monthly_savings,
    SUM(ca.actual_monthly_savings) as actual_monthly_savings,
    COUNT(CASE WHEN ca.success THEN 1 END) as successful_cleanups,
    COUNT(CASE WHEN NOT ca.success THEN 1 END) as failed_cleanups
FROM organizations o
JOIN aws_accounts aa ON o.id = aa.organization_id
JOIN waste_items wi ON aa.id = wi.aws_account_id
JOIN cleanup_actions ca ON wi.id = ca.waste_item_id
WHERE ca.executed_at >= NOW() - INTERVAL '12 months'
GROUP BY o.id, o.name, aa.id, aa.account_name, DATE_TRUNC('month', ca.executed_at);

CREATE UNIQUE INDEX idx_savings_summary_unique ON savings_summary(organization_id, aws_account_id, month);
```

### Waste Trends (Materialized View)
```sql
CREATE MATERIALIZED VIEW waste_trends AS
SELECT 
    aa.organization_id,
    aa.id as aws_account_id,
    wi.resource_type,
    DATE_TRUNC('week', sr.started_at) as week,
    COUNT(wi.id) as waste_items_found,
    SUM(wi.monthly_cost) as total_monthly_waste_cost,
    AVG(wi.confidence_score) as avg_confidence_score
FROM aws_accounts aa
JOIN scan_results sr ON aa.id = sr.aws_account_id
JOIN waste_items wi ON sr.id = wi.scan_result_id
WHERE sr.status = 'completed' 
  AND sr.started_at >= NOW() - INTERVAL '6 months'
GROUP BY aa.organization_id, aa.id, wi.resource_type, DATE_TRUNC('week', sr.started_at);

CREATE INDEX idx_waste_trends_org_account ON waste_trends(organization_id, aws_account_id);
CREATE INDEX idx_waste_trends_week ON waste_trends(week);
```

## 🔧 Configuration Tables

### Cleanup Policies
```sql
CREATE TABLE cleanup_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    
    -- Policy Rules (JSON for flexibility)
    rules JSONB NOT NULL, -- e.g., {"min_age_days": 30, "max_cost": 100}
    
    -- Auto-execution settings
    auto_execute BOOLEAN DEFAULT false,
    max_monthly_cost DECIMAL(10,2) DEFAULT 0.00, -- Max cost to auto-execute
    require_approval_above DECIMAL(10,2) DEFAULT 50.00,
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_cleanup_policies_org ON cleanup_policies(organization_id);
CREATE INDEX idx_cleanup_policies_resource_type ON cleanup_policies(resource_type);
```

### Notification Settings
```sql
CREATE TABLE notification_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Notification Types
    scan_completed BOOLEAN DEFAULT true,
    cleanup_completed BOOLEAN DEFAULT true,
    high_value_waste_found BOOLEAN DEFAULT true,
    weekly_report BOOLEAN DEFAULT true,
    monthly_report BOOLEAN DEFAULT true,
    
    -- Delivery Channels
    email_enabled BOOLEAN DEFAULT true,
    slack_webhook_url VARCHAR(512),
    slack_enabled BOOLEAN DEFAULT false,
    
    -- Thresholds
    min_waste_amount_notify DECIMAL(10,2) DEFAULT 10.00,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_notification_settings_user ON notification_settings(user_id);
```

## 🔄 Database Maintenance

### Partitioning Strategy
```sql
-- Partition scan_results by month for better performance
CREATE TABLE scan_results_y2025m01 PARTITION OF scan_results
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- Partition cleanup_actions by month
CREATE TABLE cleanup_actions_y2025m01 PARTITION OF cleanup_actions
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

### Data Retention Policies
```sql
-- Delete old scan results (keep 12 months)
DELETE FROM scan_results 
WHERE started_at < NOW() - INTERVAL '12 months';

-- Archive old cleanup actions (keep 24 months)
DELETE FROM cleanup_actions 
WHERE executed_at < NOW() - INTERVAL '24 months';
```

### Performance Optimization
```sql
-- Refresh materialized views daily
SELECT cron.schedule('refresh-savings-summary', '0 2 * * *', 'REFRESH MATERIALIZED VIEW savings_summary;');
SELECT cron.schedule('refresh-waste-trends', '0 3 * * *', 'REFRESH MATERIALIZED VIEW waste_trends;');

-- Analyze tables weekly for query optimization
SELECT cron.schedule('analyze-tables', '0 4 * * 0', 'ANALYZE;');
```

---

*Last Updated: January 2025*
*Schema Version: 1.0*