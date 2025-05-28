# 🚀 GitHub Repository Setup Guide

This guide will help you configure the GitHub repository with all the necessary secrets and settings to enable the complete CI/CD pipeline.

## 📋 Required GitHub Secrets

The following secrets need to be configured in your GitHub repository settings (`Settings > Secrets and variables > Actions`):

### 🔑 Core Deployment Secrets

| Secret Name               | Description                     | Required For       |
| ------------------------- | ------------------------------- | ------------------ |
| `VERCEL_TOKEN`            | Vercel personal access token    | Vercel deployment  |
| `VERCEL_ORG_ID`           | Vercel organization ID          | Vercel deployment  |
| `VERCEL_PROJECT_ID`       | Vercel project ID               | Vercel deployment  |
| `POSTMARK_WEBHOOK_SECRET` | Postmark webhook signing secret | Webhook validation |

### 🔍 Code Quality & Security Secrets

| Secret Name     | Description                     | Required For            |
| --------------- | ------------------------------- | ----------------------- |
| `CODECOV_TOKEN` | Codecov upload token            | Test coverage reporting |
| `SONAR_TOKEN`   | SonarCloud authentication token | Code quality analysis   |

### 🐳 Docker Publishing Secrets (Optional)

| Secret Name       | Description               | Required For            |
| ----------------- | ------------------------- | ----------------------- |
| `DOCKER_USERNAME` | Docker Hub username       | Docker image publishing |
| `DOCKER_PASSWORD` | Docker Hub password/token | Docker image publishing |

### 🧪 Performance Testing Secrets

| Secret Name             | Description               | Required For |
| ----------------------- | ------------------------- | ------------ |
| `VERCEL_PRODUCTION_URL` | Production deployment URL | Load testing |

## 🛠️ Setup Instructions

### Step 1: Vercel Integration

1. **Get Vercel Token**:

   ```bash
   # Install Vercel CLI
   npm i -g vercel

   # Login and get token
   vercel login
   vercel --token
   ```

2. **Get Organization and Project IDs**:

   ```bash
   # In your project directory
   vercel env ls

   # Or get from Vercel dashboard:
   # Project Settings > General > Project ID
   # Account Settings > General > Organization ID
   ```

3. **Set up Vercel Environment Variables**:
   - Go to your Vercel project dashboard
   - Navigate to Settings > Environment Variables
   - Add `POSTMARK_WEBHOOK_SECRET` with your Postmark webhook secret

### Step 2: Code Quality Tools

1. **Codecov Setup**:

   - Visit [codecov.io](https://codecov.io)
   - Sign in with GitHub
   - Add your repository
   - Copy the upload token from repository settings

2. **SonarCloud Setup**:
   - Visit [sonarcloud.io](https://sonarcloud.io)
   - Sign in with GitHub
   - Create a new project
   - Copy the project token
   - Update `sonar-project.properties` with your organization key

### Step 3: Docker Hub (Optional)

1. **Docker Hub Token**:
   - Sign in to [hub.docker.com](https://hub.docker.com)
   - Go to Account Settings > Security > New Access Token
   - Create token with read/write/delete permissions

### Step 4: Performance Testing

1. **Set Production URL**:
   ```bash
   # Add as GitHub secret
   VERCEL_PRODUCTION_URL=https://email-parsing-three.vercel.app
   ```

## 🔧 Configuration Files Overview

### GitHub Actions Workflows

| Workflow                    | Trigger              | Purpose                           |
| --------------------------- | -------------------- | --------------------------------- |
| `deploy-vercel.yml`         | Push to main, PRs    | Deployment with testing           |
| `code-quality.yml`          | Push, PRs, scheduled | Code quality analysis             |
| `dependency-management.yml` | Scheduled weekly     | Dependency vulnerability scanning |
| `performance.yml`           | Manual, scheduled    | Performance benchmarking          |
| `release.yml`               | Tag creation         | Automated releases                |

### Dependency Management

| File                       | Purpose                      |
| -------------------------- | ---------------------------- |
| `dependabot.yml`           | Automated dependency updates |
| `sonar-project.properties` | SonarCloud configuration     |

### Issue Templates

| Template         | Purpose                  |
| ---------------- | ------------------------ |
| `bug_report.yml` | Structured bug reporting |

## 🚦 Validation Checklist

After setting up all secrets, verify the following:

- [ ] **Deployment Pipeline**: Push a small change to trigger the deployment workflow
- [ ] **Code Quality**: Check that code quality analysis runs on PRs
- [ ] **Security Scanning**: Verify that security scans complete successfully
- [ ] **Dependency Updates**: Ensure Dependabot is creating PRs for updates
- [ ] **Performance Tests**: Run manual performance workflow
- [ ] **Issue Templates**: Create a test issue using the bug report template

## 🔗 Useful Commands

### Local Development

```bash
# Run code quality checks locally
black --check src/ tests/
isort --check-only src/ tests/
flake8 src/ tests/
mypy src/

# Run security scan
bandit -r src/
safety check

# Run performance test
python simple_performance_test.py
```

### Vercel Management

```bash
# Deploy to preview
vercel

# Deploy to production
vercel --prod

# View deployment logs
vercel logs
```

## 🆘 Troubleshooting

### Common Issues

1. **Vercel Deployment Fails**:

   - Verify `VERCEL_TOKEN`, `VERCEL_ORG_ID`, and `VERCEL_PROJECT_ID` are correct
   - Check if the token has sufficient permissions

2. **Code Quality Workflow Fails**:

   - Ensure all dependencies are listed in `requirements.txt`
   - Check Python version compatibility

3. **SonarCloud Analysis Fails**:

   - Verify `SONAR_TOKEN` is valid
   - Update organization key in `sonar-project.properties`

4. **Performance Tests Fail**:
   - Ensure `VERCEL_PRODUCTION_URL` points to working deployment
   - Check if the deployment is accessible publicly

### Getting Help

- Check the [GitHub Actions logs](https://github.com/your-repo/actions) for detailed error messages
- Review the [Vercel dashboard](https://vercel.com/dashboard) for deployment issues
- Consult the [SonarCloud documentation](https://docs.sonarcloud.io/) for code quality setup

## 🎯 Next Steps

1. **Set up all required secrets** in your GitHub repository
2. **Update configuration files** with your specific organization details
3. **Test the complete pipeline** by making a small commit
4. **Configure Postmark webhook** to point to your Vercel deployment
5. **Monitor the CI/CD pipeline** and adjust as needed

---

_Last updated: May 28, 2025_
