# Example Integration Implementation
"""
This module demonstrates how to use the integration interfaces
for extending the Email Parsing MCP Server functionality.
"""

import asyncio
import os
import sys
from typing import List, Dict, Any
from datetime import datetime

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.integrations import (
    integration_registry,
    SQLiteInterface,
    OpenAIInterface,
    PluginInterface,
    DataExporter,
    ExportFormat,
    AIAnalysisFormat
)
from src.models import ProcessedEmail, EmailData, EmailAnalysis, UrgencyLevel
from src.storage import email_storage


# ============================================================================
# Example Custom Plugin
# ============================================================================

class EmailCategoryPlugin:
    """Example plugin that adds email categorization"""

    def get_name(self) -> str:
        return "email-category-plugin"

    def get_version(self) -> str:
        return "1.0.0"

    def get_dependencies(self) -> List[str]:
        return []

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the categorization plugin"""
        self.categories = config.get("categories", [
            "work", "personal", "marketing", "notifications", "support"
        ])
        print(f"EmailCategoryPlugin initialized with categories: {self.categories}")

    async def process_email(self, email: ProcessedEmail) -> ProcessedEmail:
        """Add category to email based on content analysis"""
        if not email.analysis:
            return email

        subject = email.email_data.subject.lower()
        from_email = email.email_data.from_email.lower()

        # Simple categorization logic
        if any(word in subject for word in ["invoice", "payment", "order"]):
            category = "work"
        elif any(word in subject for word in ["newsletter", "unsubscribe", "offer"]):
            category = "marketing"
        elif "noreply" in from_email or "no-reply" in from_email:
            category = "notifications"
        elif any(word in subject for word in ["support", "help", "ticket"]):
            category = "support"
        else:
            category = "personal"

        # Add category to analysis
        if hasattr(email.analysis, 'category'):
            email.analysis.category = category
        else:
            # For demonstration, add to tags
            email.analysis.tags.append(f"category:{category}")

        return email

    async def cleanup(self) -> None:
        """Cleanup plugin resources"""
        print("EmailCategoryPlugin cleaned up")


class SpamDetectionPlugin:
    """Example plugin that adds spam detection"""

    def get_name(self) -> str:
        return "spam-detection-plugin"

    def get_version(self) -> str:
        return "1.0.0"

    def get_dependencies(self) -> List[str]:
        return ["scikit-learn>=1.0.0"]  # Example dependency

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize spam detection"""
        self.spam_threshold = config.get("spam_threshold", 0.8)
        self.spam_keywords = config.get("spam_keywords", [
            "free", "win", "lottery", "click here", "act now", "limited time"
        ])
        print(f"SpamDetectionPlugin initialized with threshold: {self.spam_threshold}")

    async def process_email(self, email: ProcessedEmail) -> ProcessedEmail:
        """Detect spam in email"""
        if not email.email_data.text_body and not email.email_data.subject:
            return email

        text_content = (email.email_data.subject + " " + 
                       (email.email_data.text_body or "")).lower()

        # Simple spam detection
        spam_score = 0
        for keyword in self.spam_keywords:
            if keyword in text_content:
                spam_score += 0.2

        # Check for suspicious patterns
        if text_content.count("!") > 3:
            spam_score += 0.1
        if "FREE" in email.email_data.subject:
            spam_score += 0.3

        is_spam = spam_score >= self.spam_threshold

        # Add spam detection results
        if email.analysis:
            email.analysis.tags.append(f"spam_score:{spam_score:.2f}")
            if is_spam:
                email.analysis.tags.append("spam:detected")
                email.analysis.urgency_level = UrgencyLevel.LOW  # Lower priority for spam

        return email

    async def cleanup(self) -> None:
        """Cleanup plugin resources"""
        print("SpamDetectionPlugin cleaned up")


# ============================================================================
# Example Integration Setup
# ============================================================================

async def setup_example_integrations():
    """Set up example integrations to demonstrate capabilities"""
    
    print("🚀 Setting up example integrations...")

    # 1. Register plugins
    print("📦 Registering plugins...")
    
    category_plugin = EmailCategoryPlugin()
    await category_plugin.initialize({
        "categories": ["work", "personal", "marketing", "notifications", "support"]
    })
    integration_registry.plugin_manager.register_plugin(category_plugin, priority=10)

    spam_plugin = SpamDetectionPlugin()
    await spam_plugin.initialize({
        "spam_threshold": 0.7,
        "spam_keywords": ["free", "win", "lottery", "urgent", "act now"]
    })
    integration_registry.plugin_manager.register_plugin(spam_plugin, priority=5)

    # 2. Set up database interface (if enabled)
    if os.getenv("ENABLE_SQLITE", "false").lower() == "true":
        print("🗄️ Setting up SQLite database...")
        sqlite_interface = SQLiteInterface()
        await sqlite_interface.connect("emails.db")
        integration_registry.register_database("sqlite", sqlite_interface)

    # 3. Set up AI interface (if API key available)
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        print("🤖 Setting up OpenAI interface...")
        openai_interface = OpenAIInterface(
            api_key=openai_api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        )
        integration_registry.register_ai_interface("openai", openai_interface)

    print("✅ Example integrations setup complete!")
    print(f"Available integrations: {integration_registry.list_integrations()}")


async def demonstrate_plugin_processing():
    """Demonstrate email processing through plugins"""
    
    if not email_storage:
        print("⚠️ No emails in storage to demonstrate plugin processing")
        return

    print("🔄 Demonstrating plugin processing...")

    # Get first email from storage
    email_id = list(email_storage.keys())[0]
    email = email_storage[email_id]

    print(f"Original email: {email.email_data.subject}")
    print(f"Original tags: {email.analysis.tags if email.analysis else 'None'}")

    # Process through plugins
    processed_email = await integration_registry.plugin_manager.process_email_through_plugins(email)

    print(f"After plugin processing:")
    print(f"Updated tags: {processed_email.analysis.tags if processed_email.analysis else 'None'}")

    # Update storage
    email_storage[email_id] = processed_email


async def demonstrate_data_export():
    """Demonstrate data export capabilities"""
    
    if not email_storage:
        print("⚠️ No emails in storage to export")
        return

    print("📤 Demonstrating data export...")

    emails = list(email_storage.values())[:5]  # Export first 5 emails
    
    # Export to different formats
    formats_to_test = [ExportFormat.JSON, ExportFormat.JSONL]
    
    for format_type in formats_to_test:
        filename = f"example_export.{format_type.value}"
        try:
            DataExporter.export_emails(emails, format_type, filename)
            print(f"✅ Exported {len(emails)} emails to {filename}")
        except Exception as e:
            print(f"❌ Failed to export to {format_type.value}: {e}")


async def demonstrate_ai_format():
    """Demonstrate AI analysis format conversion"""
    
    if not email_storage:
        print("⚠️ No emails in storage to convert")
        return

    print("🤖 Demonstrating AI format conversion...")

    # Get first email
    email = list(email_storage.values())[0]
    
    # Convert to AI format
    ai_format = AIAnalysisFormat.from_processed_email(email)
    
    print(f"AI Format for email '{email.email_data.subject}':")
    print(f"  Email ID: {ai_format.email_id}")
    print(f"  Features: {list(ai_format.features.keys())}")
    print(f"  Content keys: {list(ai_format.content.keys())}")
    print(f"  Metadata keys: {list(ai_format.metadata.keys())}")


async def run_integration_examples():
    """Run all integration examples"""
    
    print("🎯 Running Email Parsing MCP Server Integration Examples")
    print("=" * 60)

    try:
        # Setup integrations
        await setup_example_integrations()
        print()

        # Demonstrate plugin processing
        await demonstrate_plugin_processing()
        print()

        # Demonstrate data export
        await demonstrate_data_export()
        print()

        # Demonstrate AI format
        await demonstrate_ai_format()
        print()

        print("🎉 All integration examples completed successfully!")

    except Exception as e:
        print(f"❌ Error running integration examples: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# Example Configuration
# ============================================================================

def create_example_config():
    """Create example configuration file for integrations"""
    
    config_content = """
# Example configuration for Email Parsing MCP Server integrations

# Plugin Configuration
plugins:
  email_category:
    enabled: true
    categories:
      - work
      - personal
      - marketing
      - notifications
      - support
      
  spam_detection:
    enabled: true
    threshold: 0.7
    keywords:
      - free
      - win
      - lottery
      - urgent
      - act now

# Database Configuration
database:
  type: sqlite  # or postgresql
  url: emails.db
  auto_migrate: true

# AI Analysis Configuration
ai:
  openai:
    enabled: true
    model: gpt-3.5-turbo
    api_key: ${OPENAI_API_KEY}
    features:
      - sentiment_analysis
      - urgency_detection
      - action_items
      - categorization

# Export Configuration
export:
  default_format: json
  batch_size: 100
  compression: false
"""

    with open("integration-config.yaml", "w") as f:
        f.write(config_content)
    
    print("📝 Created example configuration file: integration-config.yaml")


if __name__ == "__main__":
    """Run integration examples if called directly"""
    asyncio.run(run_integration_examples())
