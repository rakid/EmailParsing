#!/usr/bin/env python3
"""
Test script for Vercel deployment
Run this to test your deployed Inbox Zen MCP server
"""

import sys
import time
from typing import Optional

import requests


class VercelDeploymentTester:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def test_health_check(self):
        """Test basic health check"""
        print("🏥 Testing health check...")
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed: {data.get('status', 'unknown')}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

    def test_mcp_health(self):
        """Test MCP server health"""
        print("🔌 Testing MCP health...")
        try:
            response = requests.get(f"{self.base_url}/mcp/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                mcp_available = data.get("mcp_available", False)
                status = data.get("status", "unknown")
                print(f"✅ MCP health check: {status} (available: {mcp_available})")
                return True
            else:
                print(f"❌ MCP health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ MCP health check error: {e}")
            return False

    def test_mcp_resources(self):
        """Test MCP resources listing"""
        print("📚 Testing MCP resources...")
        try:
            response = requests.get(f"{self.base_url}/mcp/resources", timeout=15)
            if response.status_code == 200:
                data = response.json()
                resources = data.get("resources", [])
                print(f"✅ MCP resources available: {len(resources)}")
                for resource in resources:
                    print(
                        f"   - {resource.get('name', 'Unknown')}: {resource.get('uri', 'No URI')}"
                    )
                return True
            else:
                print(f"❌ MCP resources failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ MCP resources error: {e}")
            return False

    def test_mcp_tools(self):
        """Test MCP tools listing"""
        print("🛠️ Testing MCP tools...")
        try:
            response = requests.get(f"{self.base_url}/mcp/tools", timeout=15)
            if response.status_code == 200:
                data = response.json()
                tools = data.get("tools", [])
                print(f"✅ MCP tools available: {len(tools)}")
                for tool in tools:
                    print(
                        f"   - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}"
                    )
                return True
            else:
                print(f"❌ MCP tools failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ MCP tools error: {e}")
            return False

    def test_webhook_endpoint(self):
        """Test webhook endpoint with sample payload"""
        print("📬 Testing webhook endpoint...")

        # Sample Postmark webhook payload
        test_payload = {
            "From": "test@example.com",
            "To": "inbox@yourapp.com",
            "ToFull": [{"Email": "inbox@yourapp.com", "Name": "Your App"}],
            "Subject": "Test Email for Vercel Deployment",
            "TextBody": "This is a test email to verify the webhook endpoint is working correctly in Vercel.",
            "HtmlBody": "<p>This is a <strong>test email</strong> to verify the webhook endpoint is working correctly in Vercel.</p>",
            "MessageID": f"test-{int(time.time())}@example.com",
            "Date": "2025-01-28T10:30:00.000Z",
            "Headers": [{"Name": "X-Test", "Value": "VercelDeployment"}],
            "Attachments": [],
        }

        try:
            response = requests.post(
                f"{self.base_url}/webhook",
                json=test_payload,
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Webhook test successful!")
                print(f"   Email ID: {data.get('email_id', 'Unknown')}")
                print(f"   Processing time: {data.get('processing_time', 'Unknown')}s")
                if "analysis" in data:
                    analysis = data["analysis"]
                    print(f"   Urgency: {analysis.get('urgency_level', 'Unknown')}")
                    print(f"   Sentiment: {analysis.get('sentiment', 'Unknown')}")
                return True
            else:
                print(f"❌ Webhook test failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('detail', 'Unknown error')}")
                except BaseException:
                    print(f"   Raw response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Webhook test error: {e}")
            return False

    def test_email_stats(self):
        """Test email statistics endpoint"""
        print("📊 Testing email statistics...")
        try:
            response = requests.get(f"{self.base_url}/mcp/emails/stats", timeout=15)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Email stats retrieved:")
                print(f"   Total processed: {data.get('total_processed', 0)}")
                print(f"   Total errors: {data.get('total_errors', 0)}")
                print(f"   Avg urgency: {data.get('avg_urgency_score', 0)}")
                return True
            else:
                print(f"❌ Email stats failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Email stats error: {e}")
            return False

    def run_all_tests(self):
        """Run all tests"""
        print(f"🧪 Testing Vercel deployment at: {self.base_url}")
        print("=" * 60)

        tests = [
            ("Health Check", self.test_health_check),
            ("MCP Health", self.test_mcp_health),
            ("MCP Resources", self.test_mcp_resources),
            ("MCP Tools", self.test_mcp_tools),
            ("Webhook Endpoint", self.test_webhook_endpoint),
            ("Email Statistics", self.test_email_stats),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            print(f"\n{test_name}:")
            try:
                if test_func():
                    passed += 1
                time.sleep(1)  # Brief pause between tests
            except Exception as e:
                print(f"❌ {test_name} crashed: {e}")

        print("\n" + "=" * 60)
        print(f"🏁 Test Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All tests passed! Your Vercel deployment is working correctly.")
            return True
        else:
            print("⚠️ Some tests failed. Check the output above for details.")
            return False


def main():
    """Main test runner"""
    if len(sys.argv) < 2:
        print("Usage: python test_vercel_deployment.py <base_url> [api_key]")
        print("Example: python test_vercel_deployment.py https://your-app.vercel.app")
        sys.exit(1)

    base_url = sys.argv[1]
    api_key = sys.argv[2] if len(sys.argv) > 2 else None

    tester = VercelDeploymentTester(base_url, api_key)
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
