# Future Integration Interfaces and Data Export Formats
"""
This module provides interfaces and data formats for future integrations
including AI analysis modules, database systems, and plugin architecture.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union

from pydantic import BaseModel, Field

from .models import EmailAnalysis, EmailData, EmailStats, ProcessedEmail


class ExportFormat(str, Enum):
    """Supported data export formats"""

    JSON = "json"
    CSV = "csv"
    JSONL = "jsonl"  # JSON Lines for streaming
    PARQUET = "parquet"  # For analytics
    XML = "xml"
    YAML = "yaml"


class IntegrationType(str, Enum):
    """Types of integrations supported"""

    AI_ANALYSIS = "ai_analysis"
    DATABASE = "database"
    WORKFLOW = "workflow"
    NOTIFICATION = "notification"
    ANALYTICS = "analytics"
    STORAGE = "storage"


# ============================================================================
# Data Export Formats for AI Analysis Modules
# ============================================================================


class AIAnalysisFormat(BaseModel):
    """Standardized format for AI analysis modules"""

    email_id: str
    timestamp: datetime
    content: Dict[str, Any] = Field(description="Email content optimized for AI")
    metadata: Dict[str, Any] = Field(description="Processing metadata")
    features: Dict[str, Union[str, int, float, List]] = Field(
        description="Extracted features"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context"
    )

    @classmethod
    def from_processed_email(cls, email: ProcessedEmail) -> "AIAnalysisFormat":
        """Convert ProcessedEmail to AI analysis format"""
        return cls(
            email_id=email.id,
            timestamp=email.processed_at or datetime.now(timezone.utc),
            content={
                "subject": email.email_data.subject,
                "text_body": email.email_data.text_body,
                "html_body": email.email_data.html_body,
                "from_email": email.email_data.from_email,
                "to_emails": email.email_data.to_emails,
                "received_at": email.email_data.received_at.isoformat(),
            },
            metadata={
                "message_id": email.email_data.message_id,
                "status": email.status.value,
                "processing_time": getattr(email, "processing_time", None),
                "attachments_count": len(email.email_data.attachments),
            },
            features={
                "urgency_score": email.analysis.urgency_score if email.analysis else 0,
                "urgency_level": (
                    email.analysis.urgency_level.value if email.analysis else "low"
                ),
                "sentiment": email.analysis.sentiment if email.analysis else "neutral",
                "confidence": email.analysis.confidence if email.analysis else 0.0,
                "keywords": email.analysis.keywords if email.analysis else [],
                "action_items": email.analysis.action_items if email.analysis else [],
                "temporal_references": (
                    email.analysis.temporal_references if email.analysis else []
                ),
                "tags": email.analysis.tags if email.analysis else [],
            },
        )


class DatabaseFormat(BaseModel):
    """Standardized format for database storage"""

    id: str
    message_id: str
    from_email: str
    to_emails: str  # JSON string for relational DB
    subject: str
    text_body: Optional[str]
    html_body: Optional[str]
    received_at: datetime
    processed_at: Optional[datetime]
    urgency_score: Optional[int]
    urgency_level: Optional[str]
    sentiment: Optional[str]
    confidence: Optional[float]
    keywords: Optional[str]  # JSON string
    action_items: Optional[str]  # JSON string
    tags: Optional[str]  # JSON string
    status: str
    headers: Optional[str]  # JSON string
    attachments: Optional[str]  # JSON string

    @classmethod
    def from_processed_email(cls, email: ProcessedEmail) -> "DatabaseFormat":
        """Convert ProcessedEmail to database format"""
        return cls(
            id=email.id,
            message_id=email.email_data.message_id,
            from_email=email.email_data.from_email,
            to_emails=json.dumps(email.email_data.to_emails),
            subject=email.email_data.subject,
            text_body=email.email_data.text_body,
            html_body=email.email_data.html_body,
            received_at=email.email_data.received_at,
            processed_at=email.processed_at,
            urgency_score=email.analysis.urgency_score if email.analysis else None,
            urgency_level=(
                email.analysis.urgency_level.value if email.analysis else None
            ),
            sentiment=email.analysis.sentiment if email.analysis else None,
            confidence=email.analysis.confidence if email.analysis else None,
            keywords=json.dumps(email.analysis.keywords) if email.analysis else None,
            action_items=(
                json.dumps(email.analysis.action_items) if email.analysis else None
            ),
            tags=json.dumps(email.analysis.tags) if email.analysis else None,
            status=email.status.value,
            headers=json.dumps(email.email_data.headers),
            attachments=json.dumps(
                [att.dict() for att in email.email_data.attachments]
            ),
        )


# ============================================================================
# Database Integration Interfaces
# ============================================================================


class DatabaseInterface(ABC):
    """Abstract interface for database integrations"""

    @abstractmethod
    async def connect(self, connection_string: str) -> None:
        """Establish database connection"""

    @abstractmethod
    async def store_email(self, email: ProcessedEmail) -> str:
        """Store processed email and return ID"""

    @abstractmethod
    async def get_email(self, email_id: str) -> Optional[ProcessedEmail]:
        """Retrieve email by ID"""

    @abstractmethod
    async def search_emails(self, query: Dict[str, Any]) -> List[ProcessedEmail]:
        """Search emails with filters"""

    @abstractmethod
    async def get_stats(self) -> EmailStats:
        """Get processing statistics"""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection"""


class SQLiteInterface(DatabaseInterface):
    """SQLite database interface implementation"""

    def __init__(self):
        self.connection = None
        self.db_path = None

    async def connect(self, connection_string: str) -> None:
        """Connect to SQLite database"""
        # Implementation would use aiosqlite
        self.db_path = connection_string

    async def store_email(self, email: ProcessedEmail) -> str:
        """Store email in SQLite"""
        # Convert to database format and insert
        DatabaseFormat.from_processed_email(email)
        # Implementation would execute SQL INSERT
        # async with aiosqlite.connect(self.db_path) as db:
        #     await db.execute("INSERT INTO emails (...) VALUES (...)", ...)
        #     await db.commit()
        return email.id

    async def get_email(self, email_id: str) -> Optional[ProcessedEmail]:
        """Retrieve email from SQLite"""
        # Implementation would execute SQL SELECT and convert back
        # async with aiosqlite.connect(self.db_path) as db:
        #     cursor = await db.execute(
        #         "SELECT * FROM emails WHERE id = ?", (email_id,)
        #     )
        #     result = await cursor.fetchone()
        #     return convert_to_processed_email(result) if result else None

    async def search_emails(self, query: Dict[str, Any]) -> List[ProcessedEmail]:
        """Search emails in SQLite"""
        # Implementation would build SQL WHERE clause from query
        # async with aiosqlite.connect(self.db_path) as db:
        #     cursor = await db.execute("SELECT * FROM emails WHERE ...", ...)
        #     results = await cursor.fetchall()
        #     return [convert_to_processed_email(row) for row in results]
        return []

    async def get_stats(self) -> EmailStats:
        """Get stats from SQLite"""
        # Implementation would execute aggregation queries
        # async with aiosqlite.connect(self.db_path) as db:
        #     cursor = await db.execute(
        #         "SELECT COUNT(*), AVG(urgency_score) FROM emails"
        #     )
        #     result = await cursor.fetchone()
        #     return EmailStats(...)
        from .models import EmailStats

        return EmailStats()

    async def disconnect(self) -> None:
        """Close SQLite connection"""
        # Implementation would close connection
        # if self.connection:
        #     await self.connection.close()


class PostgreSQLInterface(DatabaseInterface):
    """PostgreSQL database interface implementation"""

    def __init__(self):
        self.connection_pool = None

    async def connect(self, connection_string: str) -> None:
        """Connect to PostgreSQL"""
        # Implementation would use asyncpg
        # self.connection_pool = await asyncpg.create_pool(connection_string)

    async def store_email(self, email: ProcessedEmail) -> str:
        """Store email in PostgreSQL"""
        DatabaseFormat.from_processed_email(email)
        # Implementation would use asyncpg to insert
        # async with self.connection_pool.acquire() as conn:
        #     await conn.execute("INSERT INTO emails (...) VALUES (...)", ...)
        return email.id

    async def get_email(self, email_id: str) -> Optional[ProcessedEmail]:
        """Retrieve email from PostgreSQL"""
        # Implementation would execute SQL SELECT and convert back
        # async with self.connection_pool.acquire() as conn:
        #     result = await conn.fetchrow(
        #         "SELECT * FROM emails WHERE id = $1", email_id
        #     )
        #     return convert_to_processed_email(result) if result else None

    async def search_emails(self, query: Dict[str, Any]) -> List[ProcessedEmail]:
        """Search emails in PostgreSQL"""
        # Implementation would build SQL WHERE clause from query
        # async with self.connection_pool.acquire() as conn:
        #     results = await conn.fetch("SELECT * FROM emails WHERE ...", ...)
        #     return [convert_to_processed_email(row) for row in results]
        return []

    async def get_stats(self) -> EmailStats:
        """Get stats from PostgreSQL"""
        # Implementation would execute aggregation queries
        # async with self.connection_pool.acquire() as conn:
        #     stats_data = await conn.fetchrow(
        #         "SELECT COUNT(*), AVG(urgency_score) FROM emails"
        #     )
        #     return EmailStats(...)
        from .models import EmailStats

        return EmailStats()

    async def disconnect(self) -> None:
        """Close PostgreSQL connection"""
        # Implementation would close connection pool
        # if self.connection_pool:
        #     await self.connection_pool.close()


# ============================================================================
# AI Analysis Integration Interface
# ============================================================================


class AIAnalysisInterface(ABC):
    """Abstract interface for AI analysis modules"""

    @abstractmethod
    async def analyze_email(self, email_data: EmailData) -> EmailAnalysis:
        """Analyze email and return analysis results"""

    @abstractmethod
    async def batch_analyze(self, emails: List[EmailData]) -> List[EmailAnalysis]:
        """Analyze multiple emails in batch"""

    @abstractmethod
    def get_supported_features(self) -> List[str]:
        """Get list of analysis features this module supports"""

    @abstractmethod
    async def train_model(self, training_data: List[AIAnalysisFormat]) -> None:
        """Train the analysis model with data"""


class OpenAIInterface(AIAnalysisInterface):
    """OpenAI GPT integration for email analysis"""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model

    async def analyze_email(self, email_data: EmailData) -> EmailAnalysis:
        """Analyze email using OpenAI API"""
        # Convert to AI format
        from .models import EmailAnalysis, UrgencyLevel

        # Implementation would call OpenAI API
        # For now, return a placeholder analysis
        return EmailAnalysis(
            urgency_score=50,
            urgency_level=UrgencyLevel.MEDIUM,
            sentiment="neutral",
            confidence=0.8,
            keywords=["ai_analyzed"],
            action_items=["Review AI analysis"],
            temporal_references=[],
            tags=["openai_processed"],
            category="ai_analyzed",
        )

    async def batch_analyze(self, emails: List[EmailData]) -> List[EmailAnalysis]:
        """Batch analyze emails using OpenAI"""
        # Implementation would optimize API calls
        results = []
        for email in emails:
            analysis = await self.analyze_email(email)
            results.append(analysis)
        return results

    def get_supported_features(self) -> List[str]:
        """Features supported by OpenAI analysis"""
        return [
            "sentiment_analysis",
            "urgency_detection",
            "action_item_extraction",
            "category_classification",
            "intent_recognition",
            "summarization",
        ]

    async def train_model(self, training_data: List[AIAnalysisFormat]) -> None:
        """Fine-tune model with training data"""
        # Implementation would use OpenAI fine-tuning API
        # For now, just log the training request
        print(f"Training request for {len(training_data)} samples (placeholder)")


# ============================================================================
# Plugin Architecture
# ============================================================================


class PluginInterface(Protocol):
    """Protocol for email processing plugins"""

    def get_name(self) -> str:
        """Get plugin name"""
        ...

    def get_version(self) -> str:
        """Get plugin version"""
        ...

    def get_dependencies(self) -> List[str]:
        """Get required dependencies"""
        ...

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin with configuration"""
        ...

    async def process_email(self, email: ProcessedEmail) -> ProcessedEmail:
        """Process email and return modified version"""
        ...

    async def cleanup(self) -> None:
        """Cleanup plugin resources"""
        ...


class PluginManager:
    """Manager for email processing plugins"""

    def __init__(self):
        self.plugins: Dict[str, PluginInterface] = {}
        self.plugin_order: List[str] = []
        self.plugin_priorities: Dict[str, int] = {}

    def register_plugin(self, plugin: PluginInterface, priority: int = 100) -> None:
        """Register a plugin with priority (lower = higher priority)"""
        name = plugin.get_name()
        self.plugins[name] = plugin

        # Store priority for this plugin
        self.plugin_priorities[name] = priority

        # Insert in order based on priority (lower = higher priority)
        # Find the correct position to maintain sorted order
        inserted = False
        for i, existing_name in enumerate(self.plugin_order):
            existing_priority = self.plugin_priorities.get(existing_name, 100)
            if priority < existing_priority:
                self.plugin_order.insert(i, name)
                inserted = True
                break

        # If not inserted yet, append at the end
        if not inserted:
            self.plugin_order.append(name)

    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a plugin"""
        if plugin_name in self.plugins:
            del self.plugins[plugin_name]
            self.plugin_order.remove(plugin_name)
            # Clean up priority information
            if plugin_name in self.plugin_priorities:
                del self.plugin_priorities[plugin_name]

    async def process_email_through_plugins(
        self, email: ProcessedEmail
    ) -> ProcessedEmail:
        """Process email through all registered plugins"""
        processed_email = email

        for plugin_name in self.plugin_order:
            plugin = self.plugins[plugin_name]
            try:
                processed_email = await plugin.process_email(processed_email)
            except Exception as e:
                # Log error but continue processing
                print(f"Plugin {plugin_name} failed: {e}")

        return processed_email

    def get_plugin_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered plugins"""
        return {
            name: {
                "name": plugin.get_name(),
                "version": plugin.get_version(),
                "dependencies": plugin.get_dependencies(),
                "priority": self.plugin_priorities.get(name, 100),
            }
            for name, plugin in self.plugins.items()
        }


# ============================================================================
# Data Export Utilities
# ============================================================================


class DataExporter:
    """Utility class for exporting email data in various formats"""

    @staticmethod
    def export_emails(
        emails: List[ProcessedEmail], format_type: ExportFormat, destination: str
    ) -> str:
        """Export emails to specified format and destination"""

        if format_type == ExportFormat.JSON:
            return DataExporter._export_json(emails, destination)
        elif format_type == ExportFormat.CSV:
            return DataExporter._export_csv(emails, destination)
        elif format_type == ExportFormat.JSONL:
            return DataExporter._export_jsonl(emails, destination)
        elif format_type == ExportFormat.PARQUET:
            return DataExporter._export_parquet(emails, destination)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    @staticmethod
    def _export_json(emails: List[ProcessedEmail], destination: str) -> str:
        """Export emails as JSON"""
        ai_formats = [AIAnalysisFormat.from_processed_email(email) for email in emails]
        data = [format_obj.dict() for format_obj in ai_formats]

        with open(destination, "w") as f:
            json.dump(data, f, indent=2, default=str)

        return destination

    @staticmethod
    def _export_csv(emails: List[ProcessedEmail], destination: str) -> str:
        """Export emails as CSV"""
        # Implementation would use pandas or csv module
        # Convert to DatabaseFormat for flat structure
        [DatabaseFormat.from_processed_email(email) for email in emails]
        # Write CSV using db_formats
        return destination

    @staticmethod
    def _export_jsonl(emails: List[ProcessedEmail], destination: str) -> str:
        """Export emails as JSON Lines (streaming format)"""
        ai_formats = [AIAnalysisFormat.from_processed_email(email) for email in emails]

        with open(destination, "w") as f:
            for format_obj in ai_formats:
                f.write(json.dumps(format_obj.dict(), default=str) + "\n")

        return destination

    @staticmethod
    def _export_parquet(emails: List[ProcessedEmail], destination: str) -> str:
        """Export emails as Parquet for analytics"""
        # Implementation would use pandas/pyarrow
        # Convert to DatabaseFormat for tabular structure
        return destination


# ============================================================================
# Integration Registry
# ============================================================================


class IntegrationRegistry:
    """Registry for managing all integrations"""

    def __init__(self):
        self.database_interfaces: Dict[str, DatabaseInterface] = {}
        self.ai_interfaces: Dict[str, AIAnalysisInterface] = {}
        self.plugin_manager = PluginManager()

    def register_database(self, name: str, interface: DatabaseInterface) -> None:
        """Register a database interface"""
        self.database_interfaces[name] = interface

    def register_ai_interface(self, name: str, interface: AIAnalysisInterface) -> None:
        """Register an AI analysis interface"""
        self.ai_interfaces[name] = interface

    def get_database(self, name: str) -> Optional[DatabaseInterface]:
        """Get database interface by name"""
        return self.database_interfaces.get(name)

    def get_ai_interface(self, name: str) -> Optional[AIAnalysisInterface]:
        """Get AI interface by name"""
        return self.ai_interfaces.get(name)

    def list_integrations(self) -> Dict[str, List[str]]:
        """List all available integrations"""
        return {
            "databases": list(self.database_interfaces.keys()),
            "ai_interfaces": list(self.ai_interfaces.keys()),
            "plugins": list(self.plugin_manager.plugins.keys()),
        }


# Global integration registry instance
integration_registry = IntegrationRegistry()

# Register default implementations
integration_registry.register_database("sqlite", SQLiteInterface())
integration_registry.register_database("postgresql", PostgreSQLInterface())
