"""
Email Routing Module for Postmark Inbound Email Addresses

This module provides functionality to route emails based on the inbound_email_address
(MailboxHash) field from Postmark webhooks, enabling different processing logic
for different email addresses.
"""

import re
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from .models import EmailData, ProcessedEmail
from .logging_system import logger


class RoutingAction(str, Enum):
    """Available routing actions"""
    PROCESS_NORMAL = "process_normal"
    PROCESS_PRIORITY = "process_priority"
    FORWARD_TO_TEAM = "forward_to_team"
    AUTO_REPLY = "auto_reply"
    ARCHIVE = "archive"
    SPAM_CHECK = "spam_check"
    CUSTOM_HANDLER = "custom_handler"


@dataclass
class RoutingRule:
    """Email routing rule configuration"""
    name: str
    description: str
    inbound_addresses: List[str]  # List of MailboxHash values or patterns
    action: RoutingAction
    priority: int = 0  # Higher priority rules are checked first
    enabled: bool = True
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class EmailRouter:
    """Email routing engine based on inbound email addresses"""
    
    def __init__(self):
        self.rules: List[RoutingRule] = []
        self.custom_handlers: Dict[str, Callable] = {}
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default routing rules"""
        default_rules = [
            RoutingRule(
                name="support_emails",
                description="Route support emails to priority processing",
                inbound_addresses=["support", "help", "contact"],
                action=RoutingAction.PROCESS_PRIORITY,
                priority=100,
                metadata={"team": "support", "sla_hours": 4}
            ),
            RoutingRule(
                name="sales_emails", 
                description="Route sales inquiries to sales team",
                inbound_addresses=["sales", "info", "hello"],
                action=RoutingAction.FORWARD_TO_TEAM,
                priority=90,
                metadata={"team": "sales", "auto_reply": True}
            ),
            RoutingRule(
                name="billing_emails",
                description="Route billing emails to finance team",
                inbound_addresses=["billing", "invoices", "payments"],
                action=RoutingAction.FORWARD_TO_TEAM,
                priority=80,
                metadata={"team": "finance", "urgent": True}
            ),
            RoutingRule(
                name="noreply_emails",
                description="Archive no-reply emails",
                inbound_addresses=["noreply", "no-reply", "donotreply"],
                action=RoutingAction.ARCHIVE,
                priority=70,
                metadata={"auto_archive": True}
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: RoutingRule):
        """Add a routing rule"""
        self.rules.append(rule)
        # Sort by priority (highest first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Added routing rule: {rule.name} (priority: {rule.priority})")
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a routing rule by name"""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                del self.rules[i]
                logger.info(f"Removed routing rule: {rule_name}")
                return True
        return False
    
    def add_custom_handler(self, name: str, handler: Callable):
        """Add a custom routing handler"""
        self.custom_handlers[name] = handler
        logger.info(f"Added custom routing handler: {name}")
    
    def match_inbound_address(self, inbound_address: str, patterns: List[str]) -> bool:
        """Check if inbound address matches any of the patterns"""
        if not inbound_address:
            return False
        
        inbound_lower = inbound_address.lower()
        
        for pattern in patterns:
            pattern_lower = pattern.lower()
            
            # Exact match
            if inbound_lower == pattern_lower:
                return True
            
            # Contains match (for partial matches)
            if pattern_lower in inbound_lower:
                return True
            
            # Regex match (if pattern starts with 'regex:')
            if pattern.startswith('regex:'):
                regex_pattern = pattern[6:]  # Remove 'regex:' prefix
                try:
                    if re.search(regex_pattern, inbound_address, re.IGNORECASE):
                        return True
                except re.error:
                    logger.warning(f"Invalid regex pattern: {regex_pattern}")
        
        return False
    
    def find_matching_rule(self, email_data: EmailData) -> Optional[RoutingRule]:
        """Find the first matching routing rule for an email"""
        if not email_data.inbound_email_address:
            logger.debug("No inbound email address found, using default processing")
            return None
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            if self.match_inbound_address(email_data.inbound_email_address, rule.inbound_addresses):
                logger.info(f"Email matched routing rule: {rule.name}")
                return rule
        
        logger.debug(f"No routing rule matched for inbound address: {email_data.inbound_email_address}")
        return None
    
    async def route_email(self, email_data: EmailData) -> Dict[str, Any]:
        """Route an email based on its inbound address"""
        routing_result = {
            "inbound_address": email_data.inbound_email_address,
            "matched_rule": None,
            "action": RoutingAction.PROCESS_NORMAL,
            "metadata": {},
            "routed": False
        }
        
        # Find matching rule
        matching_rule = self.find_matching_rule(email_data)
        
        if matching_rule:
            routing_result.update({
                "matched_rule": matching_rule.name,
                "action": matching_rule.action,
                "metadata": matching_rule.metadata.copy(),
                "routed": True
            })
            
            logger.info(
                f"Email routed: {email_data.subject} -> {matching_rule.name} "
                f"(action: {matching_rule.action})"
            )
        
        return routing_result
    
    async def apply_routing_action(self, email_data: EmailData, routing_result: Dict[str, Any]) -> EmailData:
        """Apply the routing action to the email data"""
        action = routing_result["action"]
        metadata = routing_result.get("metadata", {})
        
        # Add routing information to email headers
        if not email_data.headers:
            email_data.headers = {}
        
        email_data.headers["X-Routing-Rule"] = routing_result.get("matched_rule", "default")
        email_data.headers["X-Routing-Action"] = action
        
        # Apply action-specific logic
        if action == RoutingAction.PROCESS_PRIORITY:
            email_data.headers["X-Priority"] = "high"
            email_data.headers["X-SLA-Hours"] = str(metadata.get("sla_hours", 24))
        
        elif action == RoutingAction.FORWARD_TO_TEAM:
            team = metadata.get("team", "general")
            email_data.headers["X-Forward-To-Team"] = team
            email_data.headers["X-Team-Urgent"] = str(metadata.get("urgent", False))
        
        elif action == RoutingAction.ARCHIVE:
            email_data.headers["X-Auto-Archive"] = "true"
        
        elif action == RoutingAction.CUSTOM_HANDLER:
            handler_name = metadata.get("handler")
            if handler_name and handler_name in self.custom_handlers:
                try:
                    email_data = await self.custom_handlers[handler_name](email_data, metadata)
                except Exception as e:
                    logger.error(f"Custom handler {handler_name} failed: {e}")
        
        return email_data
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules if r.enabled]),
            "custom_handlers": len(self.custom_handlers),
            "rules": [
                {
                    "name": rule.name,
                    "priority": rule.priority,
                    "enabled": rule.enabled,
                    "action": rule.action,
                    "addresses": rule.inbound_addresses
                }
                for rule in self.rules
            ]
        }


# Global router instance
email_router = EmailRouter()


async def route_email_by_inbound_address(email_data: EmailData) -> EmailData:
    """
    Main function to route an email based on its inbound address.
    
    This function:
    1. Analyzes the inbound_email_address field
    2. Finds matching routing rules
    3. Applies appropriate routing actions
    4. Returns the modified email data
    """
    try:
        # Get routing decision
        routing_result = await email_router.route_email(email_data)
        
        # Apply routing action
        routed_email = await email_router.apply_routing_action(email_data, routing_result)
        
        logger.info(
            f"Email routing completed: {email_data.subject} "
            f"(inbound: {email_data.inbound_email_address}, "
            f"action: {routing_result['action']})"
        )
        
        return routed_email
        
    except Exception as e:
        logger.error(f"Email routing failed: {e}", exc_info=True)
        return email_data  # Return original email if routing fails
