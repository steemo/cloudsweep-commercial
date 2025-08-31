# CloudSweep - Development Phases & Timeline

## 🎯 Development Overview

**Total Timeline**: 4 weeks to MVP launch
**Team Size**: 1-2 developers
**Methodology**: Agile with weekly sprints
**Success Criteria**: 5 paying customers by Week 6

## 📅 Phase Breakdown

### Phase 1: Core Foundation (Week 1)
**Goal**: Build the essential scanning and cost calculation engine

#### Sprint 1.1: AWS Integration (Days 1-3)
- [ ] **AWS Credential Management**
  - Support for AWS profiles and IAM roles
  - Cross-account role assumption
  - Credential validation and error handling
  - Region selection and validation

- [ ] **Core Scanner Architecture**
  - Base scanner class with plugin architecture
  - Error handling and retry logic
  - Logging and debugging infrastructure
  - Configuration management system

- [ ] **EBS Volume Scanner**
  - Scan for unattached EBS volumes
  - Filter by age (>7 days) and tags
  - Extract volume metadata (size, type, creation date)
  - Basic safety validation

#### Sprint 1.2: Cost Calculation (Days 4-7)
- [ ] **AWS Pricing API Integration**
  - Connect to AWS Pricing API
  - Cache pricing data for performance
  - Handle API rate limits and errors
  - Support for multiple regions

- [ ] **Cost Calculation Engine**
  - Calculate monthly costs for EBS volumes
  - Project annual costs
  - Handle different volume types (gp2, gp3, io1, etc.)
  - Currency conversion (USD to GBP)

- [ ] **JSON Output Format**
  - Standardised JSON schema for scan results
  - Include all metadata and cost information
  - Validate output format
  - Error handling for malformed data

#### Week 1 Deliverables:
- [ ] Working EBS volume scanner
- [ ] Accurate cost calculations
- [ ] JSON output format
- [ ] Basic CLI interface
- [ ] Unit tests for core functions

### Phase 2: Safety & Additional Resources (Week 2)
**Goal**: Add safety mechanisms and scan additional resource types

#### Sprint 2.1: Safety Mechanisms (Days 8-10)
- [ ] **Confidence Scoring Algorithm**
  - Age-based scoring (older = safer)
  - Tag-based scoring (meaningful tags = riskier)
  - Size-based scoring (larger = riskier)
  - Usage history scoring

- [ ] **Risk Assessment**
  - Categorise resources as safe/low/medium/high risk
  - Safety validation rules
  - Tag-based exclusions (DoNotDelete, Production, etc.)
  - Manual override capabilities

- [ ] **Cleanup Validation**
  - Pre-cleanup safety checks
  - Dry-run mode implementation
  - Rollback capability planning
  - User confirmation prompts

#### Sprint 2.2: Additional Resource Types (Days 11-14)
- [ ] **EBS Snapshot Scanner**
  - Identify orphaned snapshots (not used by AMIs)
  - Calculate snapshot storage costs
  - Age and safety validation
  - Integration with existing safety mechanisms

- [ ] **Elastic IP Scanner**
  - Identify unassociated Elastic IPs
  - Calculate hourly costs
  - High confidence scoring (EIPs are usually safe to release)
  - Integration with cleanup engine

- [ ] **Enhanced Reporting**
  - Summary statistics (total waste, savings potential)
  - Resource type breakdown
  - Risk level distribution
  - Regional analysis

#### Week 2 Deliverables:
- [ ] Confidence scoring system
- [ ] EBS snapshot scanning
- [ ] Elastic IP scanning
- [ ] Enhanced safety mechanisms
- [ ] Comprehensive test suite

### Phase 3: CLI Interface & Cleanup (Week 3)
**Goal**: Build user-friendly CLI and implement cleanup functionality

#### Sprint 3.1: CLI Development (Days 15-17)
- [ ] **Click-based CLI Framework**
  - Main command structure
  - Subcommands for scan, cleanup, report
  - Option parsing and validation
  - Help text and documentation

- [ ] **Scan Command**
  ```bash
  cloudsweep scan --profile prod --region us-east-1 --output results.json
  ```
  - Profile and region selection
  - Output file specification
  - Progress indicators
  - Error handling and user feedback

- [ ] **Configuration System**
  - YAML configuration file support
  - Default settings and overrides
  - Profile-based configurations
  - Environment variable support

#### Sprint 3.2: Cleanup Implementation (Days 18-21)
- [ ] **Cleanup Command**
  ```bash
  cloudsweep cleanup --input results.json --dry-run --confirm
  ```
  - Read scan results from JSON
  - Filter by risk level and user preferences
  - Dry-run mode for testing
  - Interactive confirmation prompts

- [ ] **AWS Resource Cleanup**
  - Delete unattached EBS volumes
  - Delete orphaned snapshots
  - Release unassociated Elastic IPs
  - Error handling and retry logic

- [ ] **Cleanup Reporting**
  - Success/failure tracking
  - Cost savings calculation
  - Detailed action logs
  - Rollback information

#### Week 3 Deliverables:
- [ ] Complete CLI interface
- [ ] Working cleanup functionality
- [ ] Configuration system
- [ ] Comprehensive error handling
- [ ] Integration tests

### Phase 4: Polish & Launch Preparation (Week 4)
**Goal**: Package, test, and prepare for launch

#### Sprint 4.1: Packaging & Distribution (Days 22-24)
- [ ] **PyInstaller Packaging**
  - Create standalone executables
  - Support for Windows, macOS, Linux
  - Include all dependencies
  - Optimise file size

- [ ] **Installation & Setup**
  - pip package creation
  - Installation documentation
  - Quick start guide
  - Configuration examples

- [ ] **Documentation**
  - README with clear examples
  - API documentation
  - Troubleshooting guide
  - FAQ section

#### Sprint 4.2: Testing & Launch (Days 25-28)
- [ ] **Comprehensive Testing**
  - End-to-end testing with real AWS accounts
  - Edge case testing
  - Performance testing
  - Security testing

- [ ] **Beta Testing Programme**
  - Recruit 5-10 beta testers
  - Gather feedback and iterate
  - Fix critical bugs
  - Validate pricing and positioning

- [ ] **Launch Preparation**
  - Website and landing page
  - Payment processing setup
  - Customer support documentation
  - Launch announcement materials

#### Week 4 Deliverables:
- [ ] Production-ready CLI tool
- [ ] Complete documentation
- [ ] Beta testing feedback incorporated
- [ ] Launch materials prepared
- [ ] First paying customers onboarded

## 🛠️ Technical Implementation Details

### Technology Stack
```
Language: Python 3.11+
CLI Framework: Click
AWS SDK: boto3
Configuration: PyYAML
Testing: pytest
Packaging: PyInstaller
Code Quality: black, flake8, mypy
```

### Project Structure
```
cloudsweep/
├── cloudsweep/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py          # Main CLI entry point
│   │   ├── scan.py          # Scan command
│   │   ├── cleanup.py       # Cleanup command
│   │   └── report.py        # Report command
│   ├── core/
│   │   ├── __init__.py
│   │   ├── scanner.py       # Base scanner class
│   │   ├── cost_calc.py     # Cost calculation engine
│   │   ├── safety.py        # Safety mechanisms
│   │   └── cleanup.py       # Cleanup engine
│   ├── scanners/
│   │   ├── __init__.py
│   │   ├── ebs_volumes.py   # EBS volume scanner
│   │   ├── ebs_snapshots.py # EBS snapshot scanner
│   │   └── elastic_ips.py   # Elastic IP scanner
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── aws_client.py    # AWS client wrapper
│   │   ├── config.py        # Configuration management
│   │   └── logger.py        # Logging utilities
│   └── models/
│       ├── __init__.py
│       ├── scan_result.py   # Scan result data models
│       └── waste_item.py    # Waste item data models
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
├── requirements.txt
├── setup.py
└── README.md
```

### Development Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Install in development mode
pip install -e .

# Run tests
pytest

# Run linting
black cloudsweep/
flake8 cloudsweep/
mypy cloudsweep/
```

## 📊 Quality Assurance

### Testing Strategy
- **Unit Tests**: 90%+ code coverage
- **Integration Tests**: Real AWS API testing
- **End-to-End Tests**: Complete workflow testing
- **Performance Tests**: Large account scanning
- **Security Tests**: Credential handling validation

### Code Quality Standards
- **Black**: Code formatting
- **Flake8**: Linting and style checking
- **MyPy**: Type checking
- **Pre-commit hooks**: Automated quality checks
- **Code reviews**: All changes reviewed

### Security Considerations
- **Credential Security**: Never log or store AWS credentials
- **Least Privilege**: Minimal required AWS permissions
- **Input Validation**: Validate all user inputs
- **Error Handling**: Don't expose sensitive information
- **Audit Logging**: Log all cleanup actions

## 🎯 Success Metrics by Phase

### Week 1 Success Criteria
- [ ] EBS volume scanner works with 3+ AWS accounts
- [ ] Cost calculations accurate within 5%
- [ ] JSON output format validated
- [ ] 50+ unit tests passing
- [ ] No critical security vulnerabilities

### Week 2 Success Criteria
- [ ] Safety mechanisms prevent false positives
- [ ] 3 resource types scanning successfully
- [ ] Confidence scoring algorithm validated
- [ ] 100+ unit tests passing
- [ ] Integration tests with real AWS accounts

### Week 3 Success Criteria
- [ ] CLI interface intuitive and user-friendly
- [ ] Cleanup functionality works safely
- [ ] Configuration system flexible
- [ ] End-to-end tests passing
- [ ] Performance acceptable (<2 min per region)

### Week 4 Success Criteria
- [ ] Packaged executables work on all platforms
- [ ] Beta testers successfully using tool
- [ ] Documentation complete and clear
- [ ] First paying customer onboarded
- [ ] Launch materials ready

## ⚠️ Risk Mitigation

### Technical Risks
- **AWS API Changes**: Use stable API versions, monitor AWS announcements
- **Rate Limiting**: Implement exponential backoff, respect API limits
- **False Positives**: Conservative safety checks, extensive testing
- **Performance Issues**: Optimise API calls, implement caching

### Schedule Risks
- **Feature Creep**: Stick to MVP scope, defer nice-to-have features
- **Testing Delays**: Start testing early, automate where possible
- **Integration Issues**: Test with real AWS accounts frequently
- **Documentation Lag**: Write docs alongside code development

### Business Risks
- **Low Customer Interest**: Validate with beta testers early
- **Pricing Issues**: Test pricing with real customers
- **Competition**: Focus on unique value proposition
- **Support Overhead**: Create comprehensive documentation

## 🚀 Post-Launch Roadmap

### Week 5-6: Customer Onboarding
- [ ] Onboard first 10 paying customers
- [ ] Gather feedback and prioritise improvements
- [ ] Fix critical bugs and usability issues
- [ ] Implement most requested features

### Month 2: Feature Expansion
- [ ] Add RDS instance scanning
- [ ] Implement scheduled scanning
- [ ] Build web dashboard
- [ ] Add email notifications

### Month 3: Platform Integration
- [ ] n8n workflow integration
- [ ] Slack integration
- [ ] API for third-party integrations
- [ ] Advanced reporting features

---

*Last Updated: January 2025*
*Review Schedule: Weekly during development*
*Success Target: MVP launch by Week 4*