# CloudSweep - MVP Definition & Scope

## 🎯 MVP Vision Statement

**CloudSweep MVP** is a command-line tool that identifies and safely removes AWS waste, helping SMEs save £200-500/month on cloud bills within their first week of usage.

## 📋 MVP Feature Scope

### ✅ Core Features (Must Have)

#### 1. AWS Resource Scanning
- **EBS Volumes**: Unattached volumes (available state)
- **EBS Snapshots**: Orphaned snapshots (no associated AMI)
- **Elastic IPs**: Unassociated IP addresses
- **Regions**: US East 1, US West 2, EU West 1 only
- **Output**: JSON format for programmatic use

#### 2. Cost Calculation
- **AWS Pricing API**: Real-time pricing data
- **Monthly Cost**: Calculate current monthly waste
- **Annual Projection**: 12-month cost projection
- **Currency**: USD only (GBP conversion in UI)

#### 3. Safety Validation
- **Age Checks**: Resources older than 7 days only
- **Tag Validation**: Skip resources with "DoNotDelete" tags
- **Confidence Scoring**: 1-100 scale based on safety checks
- **Risk Levels**: Safe (90-100), Low (70-89), Medium (50-69)

#### 4. CLI Interface
```bash
cloudsweep scan --profile production --region us-east-1
cloudsweep cleanup --input scan-results.json --dry-run
cloudsweep report --format csv --output monthly-waste.csv
```

#### 5. Basic Cleanup Actions
- **Delete EBS Volumes**: Unattached volumes only
- **Delete Snapshots**: Orphaned snapshots only
- **Release Elastic IPs**: Unassociated IPs only
- **Dry Run Mode**: Preview actions without execution

### 🚫 MVP Exclusions (Future Versions)

#### Not in MVP:
- Web dashboard (CLI only)
- Multi-cloud support (AWS only)
- RDS instances (too risky for MVP)
- Load balancers (complex dependencies)
- Automated scheduling (manual execution only)
- User management (single user tool)
- Advanced reporting (basic CSV only)
- Slack/email notifications (CLI output only)

## 🏗️ Technical Architecture (MVP)

### Simple Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Commands  │───►│   Core Scanner   │───►│  AWS API Calls  │
│   (Click)       │    │   (Python)       │    │   (boto3)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  JSON/CSV Output │
                       │  (Local Files)   │
                       └──────────────────┘
```

### Technology Stack
- **Language**: Python 3.11+
- **CLI Framework**: Click
- **AWS SDK**: boto3
- **Configuration**: YAML files
- **Output**: JSON/CSV
- **Packaging**: PyInstaller (executable)

## 📊 Success Metrics (MVP)

### Week 1-2 (Development)
- [ ] CLI scans 3 resource types successfully
- [ ] Cost calculations accurate within 5%
- [ ] Safety checks prevent risky deletions
- [ ] JSON output format validated

### Week 3-4 (Testing)
- [ ] 10+ test AWS accounts scanned
- [ ] Zero false positives on "safe" resources
- [ ] Cleanup actions reversible/documented
- [ ] Performance: <2 minutes per region scan

### Month 1 (Launch)
- [ ] 50+ CLI downloads
- [ ] 10+ successful customer scans
- [ ] £5,000+ in identified waste
- [ ] 90%+ customer satisfaction

### Month 2 (Validation)
- [ ] 5+ paying customers (£49-99/month)
- [ ] £500+ actual savings generated
- [ ] 3+ feature requests for automation
- [ ] Zero security incidents

## 🎯 Target Customer (MVP)

### Primary Persona: "DevOps Dave"
- **Role**: DevOps Engineer or Cloud Architect
- **Company**: 10-200 employees
- **AWS Spend**: £1,000-10,000/month
- **Pain**: Manual cost optimisation takes 4+ hours/month
- **Goal**: Automate waste identification and cleanup

### Use Case Scenarios
1. **Monthly Cost Review**: Dave runs scan before monthly AWS bill
2. **Quarterly Cleanup**: Bulk removal of accumulated waste
3. **New Account Audit**: Scan inherited or acquired AWS accounts
4. **Budget Planning**: Identify potential savings for next quarter

## 🔧 MVP Development Plan

### Week 1: Core Scanner
- [ ] AWS credential handling (profiles, roles)
- [ ] EBS volume scanning (unattached only)
- [ ] Basic cost calculation (Pricing API)
- [ ] JSON output format
- [ ] Unit tests for core functions

### Week 2: Safety & Cleanup
- [ ] Safety validation rules
- [ ] Confidence scoring algorithm
- [ ] EBS snapshot scanning
- [ ] Elastic IP scanning
- [ ] Dry-run cleanup mode

### Week 3: CLI & Polish
- [ ] Click-based CLI interface
- [ ] CSV report generation
- [ ] Error handling and logging
- [ ] Configuration file support
- [ ] Integration tests

### Week 4: Packaging & Launch
- [ ] PyInstaller executable build
- [ ] Documentation and examples
- [ ] Beta testing with 5 users
- [ ] Launch preparation

## 💰 MVP Monetisation

### Pricing Strategy
- **Free Tier**: Scan only, no cleanup (lead generation)
- **Basic**: £49/month - Single AWS account, basic cleanup
- **Pro**: £99/month - Multiple accounts, advanced features

### Revenue Targets
- Month 1: £500 MRR (10 Basic customers)
- Month 2: £1,500 MRR (15 Basic, 5 Pro)
- Month 3: £3,000 MRR (20 Basic, 10 Pro)

## 🚀 Post-MVP Roadmap

### Version 1.1 (Month 2)
- Web dashboard for results visualisation
- Scheduled scanning (cron integration)
- Email notifications for high-value waste

### Version 1.2 (Month 3)
- RDS instance scanning (stopped instances)
- Load balancer analysis
- Multi-region batch scanning

### Version 2.0 (Month 4-6)
- n8n workflow integration
- Advanced reporting and trends
- Team collaboration features

## ⚠️ MVP Risks & Mitigations

### Technical Risks
- **AWS API Rate Limits**: Implement exponential backoff
- **False Positives**: Conservative safety checks, manual approval
- **Credential Security**: Use IAM roles, never store keys

### Business Risks
- **Low Adoption**: Focus on clear value demonstration
- **Competition**: Emphasise SME focus and simplicity
- **Pricing**: Start low, increase based on value delivered

### Operational Risks
- **Support Overhead**: Comprehensive documentation and examples
- **Quality Issues**: Extensive testing before launch
- **Security Concerns**: Regular security reviews and audits

---

*Last Updated: January 2025*
*Next Review: Weekly during development*
*Success Criteria: 5 paying customers by Month 2*