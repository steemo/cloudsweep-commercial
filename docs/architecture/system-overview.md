# CloudSweep - System Architecture Overview

## 🎯 Product Vision
**CloudSweep** is an automated cloud cost optimization platform that identifies and eliminates AWS waste, helping SMEs save 20-40% on their cloud bills through intelligent automation.

## 🏗️ High-Level Architecture

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

## 🎯 Core Components

### 1. Web Frontend (React SPA)
- **Dashboard**: Savings overview, waste breakdown, recent activity
- **Scan Management**: Start scans, view progress, results
- **Waste Items**: List, filter, approve/reject cleanup actions
- **Settings**: AWS accounts, cleanup policies, notifications

### 2. API Gateway (FastAPI)
- **Authentication**: JWT-based auth with refresh tokens
- **REST API**: CRUD operations for all resources
- **WebSocket**: Real-time updates for scans and cleanups
- **Rate Limiting**: Prevent abuse and ensure fair usage

### 3. Core Engine (Python)
- **Orchestration**: Coordinate scanning and cleanup workflows
- **Business Logic**: Cost calculations, risk assessment
- **Integration Hub**: Connect all system components

### 4. Background Workers (Celery)
- **Scan Jobs**: Asynchronous AWS resource scanning
- **Cleanup Jobs**: Execute approved cleanup actions
- **Notification Jobs**: Send alerts and reports
- **Scheduled Tasks**: Regular scans, report generation

## 🔧 Key Modules

### AWS Scanner Module
- **Multi-Region Support**: Scan across all enabled AWS regions
- **Resource Discovery**: EC2, EBS, RDS, ELB, ElasticIP, Snapshots
- **Metrics Collection**: CloudWatch data for utilization analysis
- **Cost Attribution**: Link resources to cost and usage data

### Cost Calculator Module
- **AWS Pricing API**: Real-time pricing data
- **Cost Modeling**: Calculate monthly/annual waste costs
- **Savings Projection**: Estimate potential savings
- **ROI Analysis**: Track actual vs projected savings

### Cleanup Engine Module
- **Safety Validation**: Multi-layer safety checks
- **Rollback Capability**: Undo actions when possible
- **Approval Workflows**: Human approval for high-risk actions
- **Audit Logging**: Complete action history

### Notification System
- **Multi-Channel**: Slack, email, webhooks, in-app
- **Smart Alerts**: Contextual notifications based on user preferences
- **Report Generation**: Weekly/monthly savings reports
- **Escalation**: Alert on failed cleanups or security issues

## 📊 Data Flow

### 1. Account Onboarding
```
User adds AWS account → Cross-account role setup → Connection test → Initial scan
```

### 2. Regular Scanning
```
Scheduled trigger → Multi-region scan → Cost calculation → Risk assessment → Results storage
```

### 3. Cleanup Workflow
```
User approval → Safety validation → Backup creation → Action execution → Result logging
```

### 4. Reporting
```
Data aggregation → Trend analysis → Report generation → Multi-channel delivery
```

## 🔐 Security Architecture

### Authentication & Authorization
- **JWT Tokens**: Short-lived access tokens with refresh mechanism
- **Role-Based Access**: Organization admin, member, viewer roles
- **API Keys**: For programmatic access and integrations

### AWS Security
- **Cross-Account Roles**: No long-term credentials stored
- **Least Privilege**: Minimal required permissions
- **Read-Only Default**: Write permissions only when needed
- **Audit Trail**: All AWS actions logged

### Data Security
- **Encryption at Rest**: Database and file storage encrypted
- **Encryption in Transit**: TLS 1.3 for all communications
- **PII Protection**: No sensitive AWS data stored permanently
- **Compliance**: SOC2, GDPR-ready architecture

## 📈 Scalability Considerations

### Horizontal Scaling
- **Stateless Services**: API and workers can scale independently
- **Load Balancing**: Distribute traffic across multiple instances
- **Database Sharding**: Partition data by organization
- **Caching Strategy**: Redis for frequently accessed data

### Performance Optimization
- **Async Processing**: Non-blocking operations for better UX
- **Batch Operations**: Group similar AWS API calls
- **Connection Pooling**: Efficient database connections
- **CDN Integration**: Fast static asset delivery

## 🔄 Deployment Strategy

### Infrastructure as Code
- **Terraform**: All infrastructure defined as code
- **Multi-Environment**: Dev, staging, production environments
- **Blue-Green Deployment**: Zero-downtime deployments
- **Auto-Scaling**: Dynamic resource allocation

### Container Strategy
- **Docker**: Containerized applications
- **ECS/Fargate**: Managed container orchestration
- **Multi-Stage Builds**: Optimized container images
- **Health Checks**: Automated service monitoring

## 📊 Monitoring & Observability

### Application Metrics
- **Business KPIs**: Savings generated, cleanup success rate
- **Technical Metrics**: Response times, error rates, throughput
- **User Analytics**: Feature usage, conversion funnels

### Infrastructure Monitoring
- **System Health**: CPU, memory, disk, network usage
- **Database Performance**: Query performance, connection pools
- **AWS API Limits**: Rate limiting and quota monitoring

### Alerting Strategy
- **Critical Alerts**: System outages, security incidents
- **Warning Alerts**: Performance degradation, approaching limits
- **Info Alerts**: Deployment notifications, usage milestones

---

*Last Updated: January 2025*
*Next Review: As architecture evolves*