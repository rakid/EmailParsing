# Shared storage for email data between MCP server and webhook
import os
import sys
from typing import Dict

# Add src directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import EmailStats, ProcessedEmail

# Global storage instances
email_storage: Dict[str, ProcessedEmail] = {}
stats = EmailStats()
