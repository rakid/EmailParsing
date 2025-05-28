# Migration Guide for Email Parsing MCP Server

This document outlines migration strategies and compatibility considerations for future data format changes and integrations.

## Overview

The Email Parsing MCP Server is designed with forward compatibility in mind. This guide helps developers understand how to migrate between versions and integrate new capabilities.

## Data Format Migrations

### Version Compatibility Matrix

| Version | EmailData | EmailAnalysis | ProcessedEmail | Breaking Changes           |
| ------- | --------- | ------------- | -------------- | -------------------------- |
| 1.0.x   | v1        | v1            | v1             | None                       |
| 1.1.x   | v1        | v1.1          | v1             | None (backward compatible) |
| 2.0.x   | v2        | v2            | v2             | Yes (see migration steps)  |

### Migration Steps

#### From v1.0 to v1.1 (Non-breaking)

**Changes:**

- Added optional `confidence` field to EmailAnalysis
- Added `processing_times` field to EmailStats
- Enhanced attachment metadata

**Migration:**

```python
# No code changes required
# Existing data remains compatible
# New fields will be populated with defaults
```

#### From v1.x to v2.0 (Breaking Changes)

**Major Changes:**

- EmailData schema restructured for better normalization
- New required fields in EmailAnalysis
- Changed storage format for better performance

**Migration Script:**

```python
from src.integrations import DataExporter, AIAnalysisFormat
from src.models import ProcessedEmail

def migrate_v1_to_v2(v1_data_path: str, v2_data_path: str):
    """Migrate v1 data to v2 format"""

    # 1. Export existing data
    emails = load_v1_emails(v1_data_path)

    # 2. Convert to new format
    migrated_emails = []
    for email in emails:
        # Apply v2 schema transformations
        v2_email = convert_email_v1_to_v2(email)
        migrated_emails.append(v2_email)

    # 3. Export in new format
    DataExporter.export_emails(
        migrated_emails,
        ExportFormat.JSON,
        v2_data_path
    )

def convert_email_v1_to_v2(v1_email: dict) -> ProcessedEmail:
    """Convert v1 email format to v2"""
    # Implementation specific to actual changes
    pass
```

## Database Integration Migrations

### Adding SQLite Support

**Step 1: Install Dependencies**

```bash
pip install aiosqlite
```

**Step 2: Configure Database**

```python
from src.integrations import integration_registry, SQLiteInterface

# Register SQLite interface
sqlite_db = SQLiteInterface()
await sqlite_db.connect("emails.db")
integration_registry.register_database("sqlite", sqlite_db)
```

**Step 3: Migrate Existing Data**

```python
from src.storage import email_storage
from src.integrations import integration_registry

async def migrate_to_sqlite():
    """Migrate in-memory storage to SQLite"""
    db = integration_registry.get_database("sqlite")

    for email_id, email in email_storage.items():
        await db.store_email(email)

    print(f"Migrated {len(email_storage)} emails to SQLite")
```

### Adding PostgreSQL Support

**Step 1: Install Dependencies**

```bash
pip install asyncpg
```

**Step 2: Configure Database**

```python
from src.integrations import PostgreSQLInterface

postgres_db = PostgreSQLInterface()
await postgres_db.connect("postgresql://user:pass@localhost/emaildb")
integration_registry.register_database("postgresql", postgres_db)
```

## AI Integration Migrations

### Adding OpenAI GPT Analysis

**Step 1: Install Dependencies**

```bash
pip install openai
```

**Step 2: Configure AI Interface**

```python
from src.integrations import OpenAIInterface

openai_analyzer = OpenAIInterface(
    api_key="your-api-key",
    model="gpt-3.5-turbo"
)
integration_registry.register_ai_interface("openai", openai_analyzer)
```

**Step 3: Migration Existing Analysis**

```python
async def enhance_with_ai_analysis():
    """Re-analyze existing emails with AI"""
    ai_interface = integration_registry.get_ai_interface("openai")

    for email_id, email in email_storage.items():
        if email.analysis:
            # Enhance existing analysis
            enhanced_analysis = await ai_interface.analyze_email(email.email_data)
            email.analysis = enhanced_analysis
```

## Plugin Architecture Migration

### Creating a Custom Plugin

**Step 1: Implement Plugin Interface**

```python
from src.integrations import PluginInterface, ProcessedEmail

class MyCustomPlugin:
    def get_name(self) -> str:
        return "my-custom-plugin"

    def get_version(self) -> str:
        return "1.0.0"

    def get_dependencies(self) -> List[str]:
        return ["custom-library>=1.0"]

    async def initialize(self, config: Dict[str, Any]) -> None:
        self.config = config

    async def process_email(self, email: ProcessedEmail) -> ProcessedEmail:
        # Custom processing logic
        email.analysis.tags.append("custom-processed")
        return email

    async def cleanup(self) -> None:
        pass
```

**Step 2: Register Plugin**

```python
from src.integrations import integration_registry

plugin = MyCustomPlugin()
await plugin.initialize({"custom_setting": "value"})
integration_registry.plugin_manager.register_plugin(plugin, priority=50)
```

## Configuration Migration

### Environment Variables Migration

**v1.0 Configuration:**

```bash
POSTMARK_WEBHOOK_SECRET=secret123
LOG_LEVEL=INFO
```

**v2.0 Configuration (Enhanced):**

```bash
# Existing variables (unchanged)
POSTMARK_WEBHOOK_SECRET=secret123
LOG_LEVEL=INFO

# New database configuration
DATABASE_TYPE=sqlite
DATABASE_URL=emails.db

# New AI configuration
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo

# New plugin configuration
PLUGINS_ENABLED=true
PLUGINS_DIR=./plugins
```

### Configuration File Migration

**Create config.yaml:**

```yaml
# Database configuration
database:
  type: sqlite # sqlite, postgresql, memory
  url: emails.db
  pool_size: 10

# AI analysis configuration
ai:
  providers:
    - name: openai
      model: gpt-3.5-turbo
      api_key: ${OPENAI_API_KEY}
      enabled: true
    - name: local_model
      endpoint: http://localhost:8080
      enabled: false

# Plugin configuration
plugins:
  enabled: true
  directory: ./plugins
  auto_load: true

# Export configuration
export:
  formats: [json, csv, parquet]
  compression: gzip
  batch_size: 1000
```

## Backward Compatibility

### Supporting Legacy Clients

**Compatibility Layer:**

```python
from src.integrations import AIAnalysisFormat, DatabaseFormat

class LegacyAPIAdapter:
    """Adapter for legacy API clients"""

    @staticmethod
    def convert_to_legacy_format(email: ProcessedEmail) -> dict:
        """Convert new format to legacy format"""
        return {
            "id": email.id,
            "from": email.email_data.from_email,
            "subject": email.email_data.subject,
            "urgency": email.analysis.urgency_level.value if email.analysis else "low",
            "processed": email.processed_at.isoformat() if email.processed_at else None
        }

    @staticmethod
    def convert_from_legacy_format(legacy_data: dict) -> ProcessedEmail:
        """Convert legacy format to new format"""
        # Implementation for backward compatibility
        pass
```

### API Versioning Strategy

**URL Versioning:**

```
/api/v1/emails  # Legacy API
/api/v2/emails  # New API with enhanced features
```

**Header Versioning:**

```
Accept: application/vnd.emailparser.v1+json
Accept: application/vnd.emailparser.v2+json
```

## Testing Migration

### Validation Scripts

**Data Integrity Validation:**

```python
async def validate_migration(old_data_path: str, new_data_path: str):
    """Validate data migration integrity"""

    old_emails = load_emails(old_data_path)
    new_emails = load_emails(new_data_path)

    assert len(old_emails) == len(new_emails)

    for old_email, new_email in zip(old_emails, new_emails):
        # Validate core fields remain unchanged
        assert old_email.message_id == new_email.message_id
        assert old_email.from_email == new_email.from_email
        assert old_email.subject == new_email.subject
```

**Performance Validation:**

```python
async def validate_performance(emails_count: int = 1000):
    """Validate migration performance"""

    start_time = time.time()

    # Run migration
    await migrate_to_new_format(emails_count)

    end_time = time.time()
    migration_time = end_time - start_time

    # Performance requirements
    assert migration_time < 60  # Migration should complete in under 1 minute
    assert migration_time / emails_count < 0.1  # Under 0.1s per email
```

## Troubleshooting Migration Issues

### Common Issues and Solutions

**Issue 1: Schema Validation Errors**

```
Error: Field 'confidence' is required but missing
Solution: Set default values for new required fields
```

**Issue 2: Performance Degradation**

```
Error: Migration taking too long
Solution: Use batch processing and optimize database queries
```

**Issue 3: Plugin Compatibility**

```
Error: Plugin fails after migration
Solution: Update plugin to use new interfaces
```

### Recovery Procedures

**Rollback Strategy:**

```python
async def rollback_migration(backup_path: str):
    """Rollback to previous version"""

    # 1. Stop current services
    await stop_email_processing()

    # 2. Restore backup
    restore_from_backup(backup_path)

    # 3. Restart with previous version
    await start_email_processing()
```

## Best Practices

1. **Always backup data before migration**
2. **Test migrations on a copy of production data**
3. **Use incremental migration for large datasets**
4. **Monitor performance during migration**
5. **Validate data integrity after migration**
6. **Keep migration scripts for repeatability**
7. **Document all custom modifications**

## Support and Resources

- **Migration Scripts:** `/scripts/migration/`
- **Test Data:** `/tests/fixtures/migration/`
- **Documentation:** `/docs/migration/`
- **Issues:** Report migration issues on GitHub
- **Community:** Join our Discord for migration support
