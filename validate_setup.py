#!/usr/bin/env python3
"""
GitHub Repository CI/CD Setup Validation Script
For repository: https://github.com/rakid/EmailParsing
"""

import json
import sys
from pathlib import Path

import requests


def check_deployment_health():
    """Check if the Vercel deployment is healthy"""
    try:
        response = requests.get(
            "https://email-parsing-three.vercel.app/health", timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print("✅ Deployment Health: OK")
            print(f"   Timestamp: {data.get('timestamp')}")
            return True
        else:
            print(f"❌ Deployment Health: Failed (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Deployment Health: Error - {str(e)}")
        return False


def check_webhook_endpoint():
    """Check if the webhook endpoint is accessible"""
    try:
        # Test with invalid payload to check if endpoint is active
        response = requests.post(
            "https://email-parsing-three.vercel.app/webhook",
            json={"test": "validation"},
            timeout=10,
        )
        # We expect 403 or 400 (signature validation failure), not 404
        if response.status_code in [400, 403]:
            print("✅ Webhook Endpoint: Active (signature validation working)")
            return True
        elif response.status_code == 404:
            print("❌ Webhook Endpoint: Not found")
            return False
        else:
            print(f"✅ Webhook Endpoint: Active (Status: {response.status_code})")
            return True
    except Exception as e:
        print(f"❌ Webhook Endpoint: Error - {str(e)}")
        return False


def check_github_workflows():
    """Check if GitHub Actions workflow files exist"""
    workflows_dir = Path(".github/workflows")
    required_workflows = [
        "deploy-vercel.yml",
        "code-quality.yml",
        "dependency-management.yml",
        "performance.yml",
        "release.yml",
    ]

    if not workflows_dir.exists():
        print("❌ GitHub Workflows: .github/workflows directory not found")
        return False

    missing_workflows = []
    for workflow in required_workflows:
        if not (workflows_dir / workflow).exists():
            missing_workflows.append(workflow)

    if missing_workflows:
        print(f"❌ GitHub Workflows: Missing files - {', '.join(missing_workflows)}")
        return False
    else:
        print("✅ GitHub Workflows: All required workflow files present")
        return True


def check_configuration_files():
    """Check if configuration files exist"""
    config_files = [
        ".github/dependabot.yml",
        "sonar-project.properties",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        "GITHUB_SETUP.md",
        "SETUP_CHECKLIST.md",
    ]

    missing_files = []
    for config_file in config_files:
        if not Path(config_file).exists():
            missing_files.append(config_file)

    if missing_files:
        print(f"❌ Configuration Files: Missing - {', '.join(missing_files)}")
        return False
    else:
        print("✅ Configuration Files: All present")
        return True


def check_documentation():
    """Check if documentation is updated"""
    readme_path = Path("README.md")
    if not readme_path.exists():
        print("❌ Documentation: README.md not found")
        return False

    readme_content = readme_path.read_text()

    # Check for updated repository links
    if "github.com/rakid/EmailParsing" in readme_content:
        print("✅ Documentation: Repository links updated")
        return True
    else:
        print("❌ Documentation: Repository links not updated in README.md")
        return False


def main():
    """Run all validation checks"""
    print("🔍 Validating CI/CD Setup for EmailParsing Repository")
    print("=" * 60)

    checks = [
        ("Deployment Health", check_deployment_health),
        ("Webhook Endpoint", check_webhook_endpoint),
        ("GitHub Workflows", check_github_workflows),
        ("Configuration Files", check_configuration_files),
        ("Documentation", check_documentation),
    ]

    passed = 0
    total = len(checks)

    for check_name, check_func in checks:
        print(f"\n🔍 Checking {check_name}...")
        if check_func():
            passed += 1

    print("\n" + "=" * 60)
    print(f"📊 Validation Results: {passed}/{total} checks passed")

    if passed == total:
        print("🎉 All checks passed! Your CI/CD setup is ready.")
        print("\n📋 Next steps:")
        print("1. Configure GitHub repository secrets (see SETUP_CHECKLIST.md)")
        print(
            "2. Update Postmark webhook URL to: https://email-parsing-three.vercel.app/webhook"
        )
        print("3. Test the pipeline by making a commit")
        print(
            "4. Monitor the first workflow runs at: https://github.com/rakid/EmailParsing/actions"
        )
        return 0
    else:
        print("⚠️  Some checks failed. Please review the issues above.")
        print("📖 See SETUP_CHECKLIST.md for detailed setup instructions.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
