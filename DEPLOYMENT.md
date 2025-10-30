# EME Dish Calculator - Deployment Guide

This guide covers deploying the EME Dish Calculator to AWS using serverless architecture.

## Prerequisites

- AWS CLI configured with appropriate permissions
- AWS SAM CLI installed
- Python 3.9+
- Git

## Quick Deployment

### 1. Clone and Setup
```bash
git clone https://github.com/yourusername/eme-dish-calculator.git
cd eme-dish-calculator

# Install dependencies
pip install -r requirements.txt
```

### 2. Build Lambda Layer
```bash
cd layer
./build.sh
cd ..
```

### 3. Deploy with SAM
```bash
# Build the application
sam build

# Deploy (first time - guided)
sam deploy --guided

# Subsequent deployments
sam deploy
```

### 4. Access Your Application
After deployment, SAM will output:
- **API Endpoint**: Use for API calls
- **Website URL**: CloudFront distribution URL for web interface

## Detailed Deployment Steps

### AWS Permissions Required

Your AWS user/role needs these permissions:
- CloudFormation (full access)
- Lambda (full access)
- API Gateway (full access)
- S3 (full access)
- CloudFront (full access)
- IAM (create/attach roles)

### Environment Configuration

The template supports multiple environments:

```bash
# Deploy to development
sam deploy --parameter-overrides Environment=dev

# Deploy to production
sam deploy --parameter-overrides Environment=prod
```

### Custom Domain (Optional)

To use a custom domain:

1. Register domain in Route 53
2. Create SSL certificate in ACM
3. Deploy with domain parameter:

```bash
sam deploy --parameter-overrides DomainName=eme-calculator.yourdomain.com
```

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CloudFront    │────│   S3 Website     │    │   API Gateway   │
│   Distribution  │    │   Bucket         │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────┐
                                               │  Lambda Function│
                                               │  (EME Calc)     │
                                               └─────────────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────┐
                                               │  Lambda Layer   │
                                               │  (Dependencies) │
                                               └─────────────────┘
```

## Cost Estimation

### Monthly Costs (Typical Usage)
- **Lambda**: $0.20 (1000 calculations/month)
- **API Gateway**: $3.50 (1000 requests/month)
- **S3**: $0.50 (website hosting)
- **CloudFront**: $1.00 (1GB transfer)
- **Total**: ~$5.20/month

### Free Tier Eligible
- Lambda: 1M requests/month free
- API Gateway: 1M requests/month free
- S3: 5GB storage free
- CloudFront: 1TB transfer free

## Monitoring and Logging

### CloudWatch Logs
```bash
# View Lambda logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/eme-calculator

# Tail logs in real-time
sam logs -n EMECalculatorFunction --stack-name eme-dish-calculator --tail
```

### API Gateway Metrics
- Request count
- Error rates
- Latency percentiles

### Custom Metrics
The application logs:
- Calculation requests by frequency band
- Error types and frequencies
- Performance metrics

## Troubleshooting

### Common Issues

#### 1. Lambda Layer Build Fails
```bash
# Ensure Python 3.9 is used
cd layer
python3.9 -m pip install -r requirements.txt -t python/
```

#### 2. CORS Errors
- Check API Gateway CORS configuration
- Verify Lambda function returns proper headers
- Test with browser dev tools

#### 3. S3 Website Not Loading
```bash
# Check bucket policy
aws s3api get-bucket-policy --bucket your-bucket-name

# Verify CloudFront distribution
aws cloudfront list-distributions
```

#### 4. High Lambda Costs
- Monitor execution duration
- Optimize calculation algorithms
- Consider caching results

### Debug Mode

Enable debug logging:
```bash
sam deploy --parameter-overrides Environment=dev LogLevel=DEBUG
```

## Security Considerations

### API Security
- Rate limiting via API Gateway
- Input validation in Lambda
- CORS properly configured

### S3 Security
- Public read-only access for website
- No sensitive data in web files
- CloudFront for HTTPS termination

### Lambda Security
- Minimal IAM permissions
- No secrets in environment variables
- VPC isolation (if needed)

## Performance Optimization

### Lambda Optimization
- Use provisioned concurrency for consistent performance
- Optimize calculation algorithms
- Consider result caching

### API Gateway Optimization
- Enable caching for repeated requests
- Use compression
- Monitor throttling limits

### CloudFront Optimization
- Configure appropriate cache behaviors
- Use gzip compression
- Set proper TTL values

## Backup and Recovery

### Code Backup
- Source code in Git repository
- Infrastructure as Code (SAM template)
- Automated deployments

### Data Backup
- No persistent data stored
- Calculations are stateless
- Configuration in version control

## Scaling Considerations

### Automatic Scaling
- Lambda scales automatically
- API Gateway handles traffic spikes
- CloudFront provides global distribution

### Manual Scaling
- Increase Lambda memory for faster execution
- Use provisioned concurrency for predictable load
- Consider multiple regions for global users

## Maintenance

### Regular Updates
```bash
# Update dependencies
pip install -r requirements.txt --upgrade

# Rebuild and deploy
sam build && sam deploy
```

### Security Updates
- Monitor AWS security bulletins
- Update Lambda runtime versions
- Review IAM permissions regularly

### Performance Monitoring
- Set up CloudWatch alarms
- Monitor error rates
- Track user feedback

## Development Workflow

### Local Development
```bash
# Start local API
sam local start-api

# Test specific function
sam local invoke EMECalculatorFunction -e events/test-event.json
```

### Testing
```bash
# Run unit tests
python -m pytest tests/

# Integration tests
python tests/integration_test.py
```

### CI/CD Pipeline
Example GitHub Actions workflow:

```yaml
name: Deploy EME Calculator
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: aws-actions/setup-sam@v1
      - run: sam build
      - run: sam deploy --no-confirm-changeset
```

## Support and Maintenance

### Monitoring Checklist
- [ ] CloudWatch alarms configured
- [ ] Error rate monitoring
- [ ] Cost monitoring
- [ ] Performance baselines established

### Regular Tasks
- [ ] Review CloudWatch logs weekly
- [ ] Update dependencies monthly
- [ ] Review costs monthly
- [ ] Test disaster recovery quarterly

### Emergency Procedures
1. **API Down**: Check Lambda function logs
2. **High Costs**: Review CloudWatch metrics
3. **Security Issue**: Disable API Gateway stage
4. **Data Loss**: Redeploy from Git repository

## Getting Help

- **AWS Documentation**: [AWS SAM Guide](https://docs.aws.amazon.com/serverless-application-model/)
- **GitHub Issues**: Report bugs and feature requests
- **Amateur Radio Forums**: EME-specific questions
- **AWS Support**: For infrastructure issues

---

**73 de K2UA**  
*Happy EME operations!*
