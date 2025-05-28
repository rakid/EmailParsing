# 🔌 Integration Patterns & Examples

This guide provides comprehensive examples and patterns for integrating with the Inbox Zen Email Parsing MCP Server across different environments and use cases.

---

## 🎯 Common Integration Patterns

### Pattern 1: Real-time Email Processing Pipeline

**Use Case:** Automatically process incoming emails and trigger actions based on analysis  
**Components:** Postmark Webhook → Inbox Zen → Action Triggers

```python
# integration_pipeline.py
import asyncio
import requests
from mcp import Client

class EmailProcessingPipeline:
    def __init__(self, mcp_server_path: str, action_handlers: dict):
        self.mcp_server_path = mcp_server_path
        self.action_handlers = action_handlers
        self.client = None
    
    async def initialize(self):
        """Initialize MCP client connection"""
        self.client = Client()
        await self.client.connect("stdio", ["python", "-m", self.mcp_server_path])
    
    async def process_new_emails(self):
        """Check for new high-urgency emails and trigger actions"""
        # Get high urgency emails from last hour
        result = await self.client.call_tool(
            "get_processed_emails",
            {
                "urgency_filter": "high",
                "limit": 10,
                "date_from": datetime.now(timezone.utc) - timedelta(hours=1)
            }
        )
        
        emails = result.content.get("emails", [])
        
        for email in emails:
            await self.handle_urgent_email(email)
    
    async def handle_urgent_email(self, email: dict):
        """Process urgent email and trigger appropriate actions"""
        analysis = email["analysis"]
        
        # Extract action items
        if analysis["extracted_tasks"]:
            await self.create_task_items(email, analysis["extracted_tasks"])
        
        # Send notifications for high urgency
        if analysis["urgency_score"] > 0.8:
            await self.send_urgent_notification(email)
        
        # Route to appropriate team based on keywords
        await self.route_email(email, analysis["keywords"])
    
    async def create_task_items(self, email: dict, tasks: list):
        """Create task items in project management system"""
        for task in tasks:
            task_data = {
                "title": task["task"],
                "description": f"From email: {email['data']['subject']}",
                "priority": "high" if email["analysis"]["urgency_level"] == "high" else "medium",
                "source_email_id": email["id"],
                "confidence": task["confidence"]
            }
            
            # Call task creation handler
            if "create_task" in self.action_handlers:
                await self.action_handlers["create_task"](task_data)
    
    async def send_urgent_notification(self, email: dict):
        """Send notifications for urgent emails"""
        notification_data = {
            "type": "urgent_email",
            "subject": email["data"]["subject"],
            "sender": email["data"]["from"],
            "urgency_score": email["analysis"]["urgency_score"],
            "tasks_count": len(email["analysis"]["extracted_tasks"])
        }
        
        if "send_notification" in self.action_handlers:
            await self.action_handlers["send_notification"](notification_data)
    
    async def route_email(self, email: dict, keywords: list):
        """Route email to appropriate team based on keywords"""
        routing_rules = {
            ["bug", "error", "issue", "problem"]: "engineering",
            ["billing", "payment", "invoice"]: "finance", 
            ["customer", "support", "help"]: "customer_success",
            ["marketing", "campaign", "promotion"]: "marketing"
        }
        
        for rule_keywords, team in routing_rules.items():
            if any(kw in keywords for kw in rule_keywords):
                route_data = {
                    "email_id": email["id"],
                    "team": team,
                    "reason": f"Keywords: {', '.join(set(keywords) & set(rule_keywords))}"
                }
                
                if "route_email" in self.action_handlers:
                    await self.action_handlers["route_email"](route_data)
                break

# Usage example
async def main():
    # Define action handlers
    action_handlers = {
        "create_task": create_jira_ticket,
        "send_notification": send_slack_notification,
        "route_email": route_to_team_channel
    }
    
    # Initialize pipeline
    pipeline = EmailProcessingPipeline("src.server", action_handlers)
    await pipeline.initialize()
    
    # Process emails every 5 minutes
    while True:
        await pipeline.process_new_emails()
        await asyncio.sleep(300)  # 5 minutes

# Action handler implementations
async def create_jira_ticket(task_data: dict):
    """Create JIRA ticket from task data"""
    jira_payload = {
        "fields": {
            "project": {"key": "INBOX"},
            "summary": task_data["title"],
            "description": task_data["description"],
            "priority": {"name": task_data["priority"].title()},
            "labels": ["email-generated", f"confidence-{int(task_data['confidence']*100)}"]
        }
    }
    
    # Make JIRA API call
    response = requests.post(
        "https://yourcompany.atlassian.net/rest/api/2/issue",
        json=jira_payload,
        auth=("username", "api_token")
    )
    
    if response.status_code == 201:
        print(f"✅ Created JIRA ticket: {response.json()['key']}")
    else:
        print(f"❌ Failed to create JIRA ticket: {response.status_code}")

async def send_slack_notification(notification_data: dict):
    """Send Slack notification for urgent emails"""
    slack_payload = {
        "text": f"🚨 Urgent Email Alert",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚨 Urgent Email Alert"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Subject:* {notification_data['subject']}"},
                    {"type": "mrkdwn", "text": f"*From:* {notification_data['sender']}"},
                    {"type": "mrkdwn", "text": f"*Urgency Score:* {notification_data['urgency_score']:.2f}"},
                    {"type": "mrkdwn", "text": f"*Tasks Found:* {notification_data['tasks_count']}"}
                ]
            }
        ]
    }
    
    response = requests.post(
        "https://hooks.slack.com/your/webhook/url",
        json=slack_payload
    )
    
    if response.status_code == 200:
        print("✅ Sent Slack notification")
    else:
        print(f"❌ Failed to send Slack notification: {response.status_code}")

async def route_to_team_channel(route_data: dict):
    """Route email to appropriate team channel"""
    team_channels = {
        "engineering": "#engineering-alerts",
        "finance": "#finance-inbox",
        "customer_success": "#customer-support",
        "marketing": "#marketing-inbox"
    }
    
    channel = team_channels.get(route_data["team"], "#general")
    
    slack_payload = {
        "channel": channel,
        "text": f"📧 Email routed to {route_data['team']}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Email `{route_data['email_id']}` has been routed to *{route_data['team']}*\n*Reason:* {route_data['reason']}"
                }
            }
        ]
    }
    
    # Send to Slack
    print(f"📧 Routed email {route_data['email_id']} to {route_data['team']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Pattern 2: Email Analytics Dashboard

**Use Case:** Create real-time dashboard showing email processing metrics  
**Components:** Inbox Zen MCP → Analytics API → Dashboard

```python
# email_analytics_api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mcp import Client
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import uvicorn

app = FastAPI(title="Email Analytics API", version="1.0.0")

# Enable CORS for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EmailAnalyticsService:
    def __init__(self):
        self.mcp_client = None
    
    async def initialize(self):
        """Initialize MCP client connection"""
        self.mcp_client = Client()
        await self.mcp_client.connect("stdio", ["python", "-m", "src.server"])
    
    async def get_email_stats(self, period: str = "day"):
        """Get email statistics from MCP server"""
        result = await self.mcp_client.call_tool(
            "get_email_stats",
            {"period": period, "include_detailed": True}
        )
        return result.content
    
    async def get_recent_emails(self, limit: int = 50, urgency_filter: Optional[str] = None):
        """Get recent processed emails"""
        params = {"limit": limit}
        if urgency_filter:
            params["urgency_filter"] = urgency_filter
        
        result = await self.mcp_client.call_tool("get_processed_emails", params)
        return result.content
    
    async def search_emails(self, query: str, limit: int = 20):
        """Search through emails"""
        result = await self.mcp_client.call_tool(
            "search_emails",
            {"query": query, "limit": limit}
        )
        return result.content

# Global service instance
analytics_service = EmailAnalyticsService()

@app.on_event("startup")
async def startup_event():
    await analytics_service.initialize()

@app.get("/api/stats")
async def get_stats(period: str = "day"):
    """Get email processing statistics"""
    try:
        stats = await analytics_service.get_email_stats(period)
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/emails/recent")
async def get_recent_emails(limit: int = 50, urgency: Optional[str] = None):
    """Get recent emails with optional urgency filtering"""
    try:
        emails = await analytics_service.get_recent_emails(limit, urgency)
        return {"success": True, "data": emails}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/emails/search")
async def search_emails(q: str, limit: int = 20):
    """Search through emails"""
    try:
        results = await analytics_service.search_emails(q, limit)
        return {"success": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/overview")
async def get_dashboard_overview():
    """Get comprehensive dashboard data"""
    try:
        # Get multiple data points in parallel
        stats_task = analytics_service.get_email_stats("day")
        recent_urgent_task = analytics_service.get_recent_emails(10, "high")
        recent_all_task = analytics_service.get_recent_emails(20)
        
        stats, urgent_emails, recent_emails = await asyncio.gather(
            stats_task, recent_urgent_task, recent_all_task
        )
        
        # Calculate additional metrics
        total_emails = len(recent_emails.get("emails", []))
        urgent_count = len(urgent_emails.get("emails", []))
        urgent_percentage = (urgent_count / total_emails * 100) if total_emails > 0 else 0
        
        # Get sentiment distribution
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        for email in recent_emails.get("emails", []):
            sentiment = email.get("analysis", {}).get("sentiment", "neutral")
            sentiment_counts[sentiment] += 1
        
        return {
            "success": True,
            "data": {
                "stats": stats,
                "urgent_emails": urgent_emails,
                "recent_emails": recent_emails,
                "metrics": {
                    "total_emails_today": total_emails,
                    "urgent_emails_today": urgent_count,
                    "urgent_percentage": urgent_percentage,
                    "sentiment_distribution": sentiment_counts
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

### Pattern 3: Email-to-CRM Integration

**Use Case:** Automatically create CRM records from email interactions  
**Components:** Inbox Zen → CRM API → Customer Records

```python
# crm_integration.py
import asyncio
from mcp import Client
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CRMContact:
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    source: str = "email"

@dataclass
class CRMActivity:
    contact_email: str
    activity_type: str
    subject: str
    content: str
    timestamp: datetime
    urgency_level: str
    sentiment: str
    tags: List[str]

class EmailToCRMIntegration:
    def __init__(self, crm_api_url: str, crm_api_key: str):
        self.crm_api_url = crm_api_url
        self.crm_api_key = crm_api_key
        self.mcp_client = None
        self.headers = {
            "Authorization": f"Bearer {crm_api_key}",
            "Content-Type": "application/json"
        }
    
    async def initialize(self):
        """Initialize MCP client connection"""
        self.mcp_client = Client()
        await self.mcp_client.connect("stdio", ["python", "-m", "src.server"])
    
    async def sync_recent_emails(self, hours_back: int = 24):
        """Sync recent emails to CRM"""
        # Get emails from the last N hours
        from_time = datetime.now() - timedelta(hours=hours_back)
        
        result = await self.mcp_client.call_tool(
            "get_processed_emails",
            {
                "limit": 100,
                "date_from": from_time.isoformat()
            }
        )
        
        emails = result.content.get("emails", [])
        
        for email in emails:
            await self.process_email_for_crm(email)
    
    async def process_email_for_crm(self, email: dict):
        """Process a single email for CRM integration"""
        email_data = email["data"]
        analysis = email["analysis"]
        
        # Extract sender information
        sender_email = email_data["from"]
        sender_name = self.extract_name_from_email(sender_email)
        
        # Create or update contact
        contact = CRMContact(
            email=sender_email,
            name=sender_name,
            source="inbox_zen_email"
        )
        
        contact_id = await self.create_or_update_contact(contact)
        
        # Create activity record
        activity = CRMActivity(
            contact_email=sender_email,
            activity_type="email_inbound",
            subject=email_data["subject"],
            content=email_data["text_body"][:1000],  # Truncate for CRM
            timestamp=datetime.fromisoformat(email["timestamp"].replace('Z', '+00:00')),
            urgency_level=analysis["urgency_level"],
            sentiment=analysis["sentiment"],
            tags=analysis["keywords"][:5]  # Limit tags
        )
        
        await self.create_activity(contact_id, activity)
        
        # Handle urgent emails specially
        if analysis["urgency_level"] == "high":
            await self.create_urgent_follow_up(contact_id, email)
    
    def extract_name_from_email(self, email: str) -> Optional[str]:
        """Extract name from email address"""
        # Simple extraction - in practice, you might use more sophisticated methods
        local_part = email.split('@')[0]
        
        # Convert common patterns to names
        if '.' in local_part:
            parts = local_part.split('.')
            return ' '.join(part.capitalize() for part in parts)
        elif '_' in local_part:
            parts = local_part.split('_')
            return ' '.join(part.capitalize() for part in parts)
        else:
            return local_part.capitalize()
    
    async def create_or_update_contact(self, contact: CRMContact) -> str:
        """Create or update contact in CRM"""
        # Check if contact exists
        search_response = requests.get(
            f"{self.crm_api_url}/contacts/search",
            params={"email": contact.email},
            headers=self.headers
        )
        
        if search_response.status_code == 200:
            existing_contacts = search_response.json().get("contacts", [])
            if existing_contacts:
                # Update existing contact
                contact_id = existing_contacts[0]["id"]
                update_data = {
                    "last_email_activity": datetime.now().isoformat(),
                    "source": contact.source
                }
                
                if contact.name and not existing_contacts[0].get("name"):
                    update_data["name"] = contact.name
                
                update_response = requests.patch(
                    f"{self.crm_api_url}/contacts/{contact_id}",
                    json=update_data,
                    headers=self.headers
                )
                
                print(f"✅ Updated contact: {contact.email}")
                return contact_id
        
        # Create new contact
        create_data = {
            "email": contact.email,
            "name": contact.name,
            "company": contact.company,
            "phone": contact.phone,
            "source": contact.source,
            "created_via": "inbox_zen_integration",
            "first_email_activity": datetime.now().isoformat()
        }
        
        create_response = requests.post(
            f"{self.crm_api_url}/contacts",
            json=create_data,
            headers=self.headers
        )
        
        if create_response.status_code == 201:
            contact_id = create_response.json()["id"]
            print(f"✅ Created new contact: {contact.email}")
            return contact_id
        else:
            print(f"❌ Failed to create contact: {contact.email}")
            return None
    
    async def create_activity(self, contact_id: str, activity: CRMActivity):
        """Create activity record in CRM"""
        activity_data = {
            "contact_id": contact_id,
            "type": activity.activity_type,
            "subject": activity.subject,
            "content": activity.content,
            "timestamp": activity.timestamp.isoformat(),
            "metadata": {
                "urgency_level": activity.urgency_level,
                "sentiment": activity.sentiment,
                "tags": activity.tags,
                "source": "inbox_zen"
            }
        }
        
        response = requests.post(
            f"{self.crm_api_url}/activities",
            json=activity_data,
            headers=self.headers
        )
        
        if response.status_code == 201:
            print(f"✅ Created activity for {activity.contact_email}")
        else:
            print(f"❌ Failed to create activity for {activity.contact_email}")
    
    async def create_urgent_follow_up(self, contact_id: str, email: dict):
        """Create urgent follow-up task for high-priority emails"""
        follow_up_data = {
            "contact_id": contact_id,
            "type": "urgent_follow_up",
            "subject": f"URGENT: Follow up on email - {email['data']['subject']}",
            "due_date": (datetime.now() + timedelta(hours=4)).isoformat(),
            "priority": "high",
            "description": f"Urgent email received with urgency score: {email['analysis']['urgency_score']:.2f}",
            "metadata": {
                "email_id": email["id"],
                "urgency_score": email["analysis"]["urgency_score"],
                "extracted_tasks": email["analysis"]["extracted_tasks"]
            }
        }
        
        response = requests.post(
            f"{self.crm_api_url}/tasks",
            json=follow_up_data,
            headers=self.headers
        )
        
        if response.status_code == 201:
            print(f"✅ Created urgent follow-up task for contact {contact_id}")
        else:
            print(f"❌ Failed to create urgent follow-up task for contact {contact_id}")

# Usage example
async def main():
    # Initialize CRM integration
    crm_integration = EmailToCRMIntegration(
        crm_api_url="https://your-crm.com/api/v1",
        crm_api_key="your_crm_api_key"
    )
    
    await crm_integration.initialize()
    
    # Sync emails from last 24 hours
    await crm_integration.sync_recent_emails(hours_back=24)
    
    print("✅ CRM sync completed")

if __name__ == "__main__":
    asyncio.run(main())
```

### Pattern 4: AI-Enhanced Email Processing

**Use Case:** Send processed emails to external AI services for enhanced analysis  
**Components:** Inbox Zen → OpenAI/Claude API → Enhanced Analysis

```python
# ai_enhanced_processing.py
import asyncio
import openai
from mcp import Client
import json
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class AIAnalysisResult:
    summary: str
    action_items: List[str]
    sentiment_details: str
    priority_assessment: str
    recommended_response: str
    categories: List[str]

class AIEnhancedEmailProcessor:
    def __init__(self, openai_api_key: str):
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.mcp_client = None
    
    async def initialize(self):
        """Initialize MCP client connection"""
        self.mcp_client = Client()
        await self.mcp_client.connect("stdio", ["python", "-m", "src.server"])
    
    async def process_recent_emails_with_ai(self, limit: int = 10):
        """Process recent emails with AI enhancement"""
        # Get recent high-urgency emails
        result = await self.mcp_client.call_tool(
            "get_processed_emails",
            {"urgency_filter": "high", "limit": limit}
        )
        
        emails = result.content.get("emails", [])
        
        for email in emails:
            ai_analysis = await self.enhance_email_with_ai(email)
            await self.store_ai_analysis(email["id"], ai_analysis)
    
    async def enhance_email_with_ai(self, email: dict) -> AIAnalysisResult:
        """Send email to AI for enhanced analysis"""
        email_data = email["data"]
        existing_analysis = email["analysis"]
        
        # Prepare prompt for AI
        prompt = self.create_analysis_prompt(email_data, existing_analysis)
        
        # Call OpenAI API
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert email analyst. Provide detailed analysis of business emails including summaries, action items, and recommendations."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.3
        )
        
        # Parse AI response
        ai_response = response.choices[0].message.content
        return self.parse_ai_response(ai_response)
    
    def create_analysis_prompt(self, email_data: dict, existing_analysis: dict) -> str:
        """Create analysis prompt for AI"""
        return f"""
Analyze this business email and provide detailed insights:

**Email Details:**
From: {email_data['from']}
To: {', '.join(email_data['to'])}
Subject: {email_data['subject']}

**Content:**
{email_data['text_body']}

**Existing Analysis:**
- Urgency Level: {existing_analysis['urgency_level']}
- Sentiment: {existing_analysis['sentiment']}
- Keywords: {', '.join(existing_analysis['keywords'])}
- Extracted Tasks: {json.dumps(existing_analysis['extracted_tasks'], indent=2)}

**Please provide:**
1. **Summary** (2-3 sentences): Brief overview of the email content and purpose
2. **Action Items** (list): Specific actionable tasks mentioned or implied
3. **Sentiment Details**: Detailed explanation of the emotional tone and context
4. **Priority Assessment**: Business priority level with reasoning
5. **Recommended Response**: Suggested response approach and key points to address
6. **Categories** (list): Business categories this email falls into (e.g., customer-support, sales, technical, etc.)

Format your response as JSON with these exact keys: summary, action_items, sentiment_details, priority_assessment, recommended_response, categories
"""
    
    def parse_ai_response(self, ai_response: str) -> AIAnalysisResult:
        """Parse AI response into structured result"""
        try:
            # Try to parse as JSON first
            data = json.loads(ai_response)
            return AIAnalysisResult(
                summary=data.get("summary", ""),
                action_items=data.get("action_items", []),
                sentiment_details=data.get("sentiment_details", ""),
                priority_assessment=data.get("priority_assessment", ""),
                recommended_response=data.get("recommended_response", ""),
                categories=data.get("categories", [])
            )
        except json.JSONDecodeError:
            # Fallback: parse as text
            lines = ai_response.split('\n')
            return AIAnalysisResult(
                summary=self.extract_section(lines, "Summary"),
                action_items=self.extract_list_section(lines, "Action Items"),
                sentiment_details=self.extract_section(lines, "Sentiment Details"),
                priority_assessment=self.extract_section(lines, "Priority Assessment"),
                recommended_response=self.extract_section(lines, "Recommended Response"),
                categories=self.extract_list_section(lines, "Categories")
            )
    
    def extract_section(self, lines: List[str], section_name: str) -> str:
        """Extract text from a specific section"""
        in_section = False
        content = []
        
        for line in lines:
            if section_name.lower() in line.lower():
                in_section = True
                continue
            elif in_section and line.strip().startswith(('**', '##', '###')):
                break
            elif in_section and line.strip():
                content.append(line.strip())
        
        return ' '.join(content)
    
    def extract_list_section(self, lines: List[str], section_name: str) -> List[str]:
        """Extract list items from a specific section"""
        in_section = False
        items = []
        
        for line in lines:
            if section_name.lower() in line.lower():
                in_section = True
                continue
            elif in_section and line.strip().startswith(('**', '##', '###')):
                break
            elif in_section and line.strip().startswith(('-', '*', '•')):
                item = line.strip().lstrip('-*•').strip()
                if item:
                    items.append(item)
        
        return items
    
    async def store_ai_analysis(self, email_id: str, ai_analysis: AIAnalysisResult):
        """Store AI analysis results (in practice, this would go to a database)"""
        analysis_data = {
            "email_id": email_id,
            "ai_analysis": {
                "summary": ai_analysis.summary,
                "action_items": ai_analysis.action_items,
                "sentiment_details": ai_analysis.sentiment_details,
                "priority_assessment": ai_analysis.priority_assessment,
                "recommended_response": ai_analysis.recommended_response,
                "categories": ai_analysis.categories
            },
            "processed_at": datetime.now().isoformat()
        }
        
        # In practice, store to database
        print(f"✅ AI analysis stored for email {email_id}")
        print(f"   Summary: {ai_analysis.summary[:100]}...")
        print(f"   Action items: {len(ai_analysis.action_items)}")
        print(f"   Categories: {', '.join(ai_analysis.categories)}")

# Usage example
async def main():
    processor = AIEnhancedEmailProcessor(openai_api_key="your_openai_api_key")
    await processor.initialize()
    
    # Process recent urgent emails with AI
    await processor.process_recent_emails_with_ai(limit=5)
    
    print("✅ AI-enhanced processing completed")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🚀 Quick Start Templates

### Claude Desktop Integration

```json
{
  "mcpServers": {
    "inbox-zen-email-parser": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/EmailParsing",
      "env": {
        "PYTHONPATH": "/path/to/EmailParsing",
        "POSTMARK_WEBHOOK_SECRET": "your_secret_here"
      }
    }
  }
}
```

### Custom MCP Client

```python
# simple_mcp_client.py
import asyncio
from mcp import Client

async def main():
    client = Client()
    await client.connect("stdio", ["python", "-m", "src.server"])
    
    # Get recent urgent emails
    urgent_emails = await client.call_tool(
        "get_processed_emails",
        {"urgency_filter": "high", "limit": 5}
    )
    
    print("Urgent Emails:")
    for email in urgent_emails.content["emails"]:
        print(f"- {email['data']['subject']} (Score: {email['analysis']['urgency_score']:.2f})")
    
    # Get statistics
    stats = await client.call_tool("get_email_stats", {"period": "day"})
    print(f"\nDaily Stats: {stats.content['stats']['total_processed']} emails processed")

if __name__ == "__main__":
    asyncio.run(main())
```

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  inbox-zen-mcp:
    build: .
    ports:
      - "8000:8000"
    environment:
      - POSTMARK_WEBHOOK_SECRET=${POSTMARK_WEBHOOK_SECRET}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
  
  inbox-zen-webhook:
    build: .
    command: python -m src.webhook
    ports:
      - "8001:8001"
    environment:
      - POSTMARK_WEBHOOK_SECRET=${POSTMARK_WEBHOOK_SECRET}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    depends_on:
      - inbox-zen-mcp
```

---

## 🔗 Advanced Integration Examples

### Multi-tenant Email Processing

```python
# multi_tenant_processor.py
class MultiTenantEmailProcessor:
    def __init__(self):
        self.tenant_configs = {}
        self.mcp_clients = {}
    
    async def add_tenant(self, tenant_id: str, config: dict):
        """Add a new tenant with specific configuration"""
        self.tenant_configs[tenant_id] = config
        
        # Create dedicated MCP client for tenant
        client = Client()
        await client.connect("stdio", ["python", "-m", "src.server"])
        self.mcp_clients[tenant_id] = client
    
    async def process_tenant_emails(self, tenant_id: str):
        """Process emails for specific tenant"""
        client = self.mcp_clients[tenant_id]
        config = self.tenant_configs[tenant_id]
        
        # Get emails with tenant-specific filters
        emails = await client.call_tool(
            "get_processed_emails",
            config.get("email_filters", {"limit": 50})
        )
        
        # Apply tenant-specific processing
        for email in emails.content["emails"]:
            await self.apply_tenant_rules(tenant_id, email)
```

### Real-time Webhook Processing

```python
# webhook_processor.py
from fastapi import FastAPI, BackgroundTasks
import asyncio

app = FastAPI()

@app.post("/process-webhook")
async def process_webhook(webhook_data: dict, background_tasks: BackgroundTasks):
    """Process webhook and trigger background analysis"""
    
    # Immediate response to Postmark
    background_tasks.add_task(analyze_email_async, webhook_data)
    
    return {"status": "accepted", "message": "Email processing started"}

async def analyze_email_async(webhook_data: dict):
    """Background email analysis"""
    # Connect to MCP server
    client = Client()
    await client.connect("stdio", ["python", "-m", "src.server"])
    
    # Wait for email to be processed
    await asyncio.sleep(1)
    
    # Get analysis results
    emails = await client.call_tool(
        "search_emails",
        {"query": webhook_data.get("MessageID", "")}
    )
    
    if emails.content["emails"]:
        email = emails.content["emails"][0]
        await trigger_post_processing(email)

async def trigger_post_processing(email: dict):
    """Trigger additional processing based on analysis"""
    analysis = email["analysis"]
    
    if analysis["urgency_level"] == "high":
        await send_urgent_alert(email)
    
    if analysis["extracted_tasks"]:
        await create_task_tickets(email, analysis["extracted_tasks"])
```

This integration patterns guide provides comprehensive examples for connecting the Inbox Zen MCP Server with various external systems and workflows. Choose the patterns that best fit your use case and customize them according to your specific requirements.
