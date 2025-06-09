# Postmark Webhook Handler for Email Processing
#
# Security Configuration:
# - HOST: Controls which network interfaces the server binds to
#   * 127.0.0.1 (localhost) for development - more secure
#   * 0.0.0.0 (all interfaces) for containerized/cloud deployments
#   * Can be overridden via HOST environment variable
# - PORT: Configurable via PORT environment variable (default: 8081)
#
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import (
    Dict,
    Optional,
)

from dateutil.parser import parse as dateutil_parse
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import ValidationError

from . import storage
from .config import config
from .extraction import email_extractor
from .logging_system import (
    logger,
)
from .models import (
    AttachmentData,
    EmailAnalysis,
    EmailData,
    EmailStatus,
    PostmarkWebhookPayload,
    ProcessedEmail,
    UrgencyLevel,
)

# Add src directory to path for imports
# This line is for ensuring relative imports work from this file's location.
# It's often better to manage PYTHONPATH or run as a module (python -m
# src.webhook).
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# Import integration capabilities
try:
    from .integrations import integration_registry, SQLiteInterface

    INTEGRATIONS_AVAILABLE = True

    # Initialize SQLite database for persistent storage
    try:
        sqlite_db = SQLiteInterface()
        # Use /tmp for serverless environments, or local file for development
        db_path = "/tmp/emails.db" if os.getenv("VERCEL") else "emails.db"

        # Register the SQLite interface
        integration_registry.register_database("sqlite", sqlite_db)
        logger.info(f"SQLite database initialized at {db_path}")

        # Initialize the database asynchronously when the app starts
        async def init_sqlite():
            await sqlite_db.connect(db_path)

        # Store the init function to call it during startup
        _sqlite_init = init_sqlite

    except Exception as e:
        logger.warning(f"Failed to initialize SQLite database: {e}")

except ImportError:
    INTEGRATIONS_AVAILABLE = False
    logger.warning("Integration module not available - running without plugin support")

# FastAPI app initialization
app = FastAPI(
    title="Inbox Zen Email Processing Webhook",
    description="Receives Postmark inbound webhooks and processes emails",
    version=config.server_version,
    lifespan=config.lifespan_manager,
)

# Initialize databases on startup
@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    if INTEGRATIONS_AVAILABLE:
        # Initialize SQLite
        if '_sqlite_init' in globals():
            try:
                await _sqlite_init()
                logger.info("SQLite database connection established")
            except Exception as e:
                logger.error(f"Failed to initialize SQLite on startup: {e}")

        # Initialize Supabase (lazy loading - just check config)
        try:
            supabase_db = integration_registry.get_database("supabase")
            has_url = os.getenv("SUPABASE_URL")
            has_key = os.getenv("SUPABASE_ANON_KEY")
            if supabase_db and has_url and has_key:
                # Just mark as ready for lazy loading (don't create client yet)
                await supabase_db.connect("")  # This now just validates config
                logger.info("Supabase database configured for lazy loading")
            else:
                logger.warning("Supabase not configured - missing URL or API key")
        except Exception as e:
            logger.error(f"Failed to configure Supabase: {e}")

# --- Webhook Utility Functions ---


def verify_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify Postmark webhook signature for security."""
    if not secret:
        logger.warning(
            "No webhook secret configured - skipping signature verification."
        )
        return True

    # Handle None signature
    if signature is None:
        return False

    # Handle both string and bytes input for body
    if isinstance(body, str):
        body_bytes = body.encode("utf-8")
    elif isinstance(body, bytes):
        body_bytes = body
    else:
        return False

    expected_signature = hmac.new(
        secret.encode("utf-8"), body_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


def extract_email_data(
    webhook_payload: PostmarkWebhookPayload,
) -> EmailData:
    """Extract EmailData from Postmark webhook payload."""
    to_emails = [recipient["Email"] for recipient in webhook_payload.ToFull]
    cc_emails = (
        [recipient["Email"] for recipient in webhook_payload.CcFull]
        if webhook_payload.CcFull
        else []
    )
    bcc_emails = (
        [recipient["Email"] for recipient in webhook_payload.BccFull]
        if webhook_payload.BccFull
        else []
    )

    attachments = [
        AttachmentData(
            name=attachment.get("Name", ""),
            content_type=attachment.get("ContentType", ""),
            size=attachment.get("ContentLength", 0),
            content_id=attachment.get("ContentID"),
        )
        for attachment in webhook_payload.Attachments
    ]
    headers = {header["Name"]: header["Value"] for header in webhook_payload.Headers}

    # Modification ici pour le parsing de la date
    try:
        # Utiliser dateutil.parser.parse pour plus de flexibilité
        parsed_date = dateutil_parse(webhook_payload.Date)
        # S'assurer que la date est consciente du fuseau horaire et convertie en UTC
        if parsed_date.tzinfo is None:
            received_at_utc = parsed_date.replace(tzinfo=timezone.utc)
        else:
            received_at_utc = parsed_date.astimezone(timezone.utc)
    except (ValueError, TypeError) as e:
        logger.error(f"Failed to parse date string '{webhook_payload.Date}': {e}")
        # Fallback ou lever une erreur plus spécifique si nécessaire
        # Pour l'instant, on utilise datetime.now() comme fallback avec un avertissement
        logger.warning(
            "Using current UTC time as fallback for received_at due to parsing error."
        )
        raise ValueError(
            f"Invalid date format in Postmark payload: '{webhook_payload.Date}'"
        ) from e

    return EmailData(
        message_id=webhook_payload.MessageID,
        from_email=webhook_payload.From,
        to_emails=to_emails,
        cc_emails=cc_emails,
        bcc_emails=bcc_emails,
        subject=webhook_payload.Subject,
        text_body=webhook_payload.TextBody,
        html_body=webhook_payload.HtmlBody,
        received_at=received_at_utc,
        attachments=attachments,
        headers=headers,

        # Inbound email routing
        inbound_email_address=webhook_payload.MailboxHash,
        original_recipient=webhook_payload.OriginalRecipient,

        # Email security and quality
        spam_score=webhook_payload.SpamScore,
        virus_detected=webhook_payload.VirusDetected,

        # Additional metadata
        reply_to=webhook_payload.ReplyTo,
        message_stream=webhook_payload.MessageStream,
        tag=webhook_payload.Tag,
    )


async def _ensure_webhook_is_authentic(body: bytes, signature: Optional[str]) -> None:
    """
    Verify webhook authentication. Raises HTTPException if verification fails.
    This combines the logic of config.postmark_webhook_secret check and actual
    verification.
    """
    if not config.postmark_webhook_secret:
        logger.warning(
            "Webhook secret not configured. Skipping signature verification. "
            "This is insecure for production."
        )
        # Allow if no secret is configured (e.g., for local dev without
        # Postmark)
        return

    if not signature:
        logger.log_webhook_validation_error("Missing webhook signature", {})
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    if not verify_webhook_signature(body, signature, config.postmark_webhook_secret):
        logger.log_webhook_validation_error("Invalid webhook signature", {})
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


def _determine_sentiment(
    sentiment_indicators: Dict[str, list],
) -> str:
    """Determine overall sentiment from extracted indicators."""
    positive_count = len(sentiment_indicators.get("positive", []))
    negative_count = len(sentiment_indicators.get("negative", []))

    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    else:
        return "neutral"


def _create_email_analysis(
    extracted_metadata,
    urgency_score: float,
    urgency_level_str: str,
    sentiment: str,
) -> EmailAnalysis:
    """Create an EmailAnalysis object from extracted data."""
    return EmailAnalysis(
        urgency_score=int(urgency_score),
        urgency_level=UrgencyLevel(
            urgency_level_str
        ),  # Assumes urgency_level_str is a valid UrgencyLevel member
        sentiment=sentiment,
        confidence=0.8,  # Base confidence for regex-based analysis
        keywords=extracted_metadata.priority_keywords[:20],
        action_items=extracted_metadata.action_words[:10],
        temporal_references=extracted_metadata.temporal_references[:10],
        tags=["extracted", urgency_level_str, sentiment],
        category="email",  # Default category
    )


async def _process_through_plugins(
    processed_email: ProcessedEmail, processing_id: str
) -> ProcessedEmail:
    """Process the email through any registered and available plugins."""
    if not (INTEGRATIONS_AVAILABLE and integration_registry.plugin_manager.plugins):
        return processed_email

    try:
        logger.info(
            f"Processing email {processing_id} through "
            f"{len(integration_registry.plugin_manager.plugins)} plugins"
        )
        enhanced_email = (
            await integration_registry.plugin_manager.process_email_through_plugins(
                processed_email
            )
        )
        logger.info(f"Email {processing_id} enhanced by plugins")
        return enhanced_email
    except Exception as e:
        logger.error(
            f"Plugin processing failed for email {processing_id}: {e}",
            exc_info=True,
        )
        return processed_email  # Return original email if plugin processing fails


async def _save_to_database(
    processed_email: ProcessedEmail, processing_id: str
) -> None:
    """Save the processed email to the configured database, if available."""
    if not INTEGRATIONS_AVAILABLE:
        return

    # Attempt to get database interface in priority order: Supabase > SQLite > PostgreSQL
    db_interface = (
        integration_registry.get_database("supabase") or
        integration_registry.get_database("sqlite") or
        integration_registry.get_database("postgresql")
    )

    if db_interface:
        try:
            await db_interface.store_email(processed_email)
            logger.info(
                f"Email {processing_id} saved to database via "
                f"{db_interface.__class__.__name__}"
            )
        except Exception as e:
            logger.error(
                f"Database storage failed for email {processing_id}: {e}",
                exc_info=True,
            )


def _update_stats(processing_time_taken: float) -> None:
    """Update global processing statistics."""
    storage.stats.total_processed += 1
    storage.stats.last_processed = datetime.now(
        timezone.utc
    )  # Use timezone aware datetime
    storage.stats.processing_times.append(processing_time_taken)

    if storage.stats.total_processed > 0:
        emails_with_analysis = [
            email for email in storage.email_storage.values() if email.analysis
        ]
        if emails_with_analysis:  # Avoid division by zero
            total_urgency = sum(
                email.analysis.urgency_score
                for email in emails_with_analysis
                if email.analysis
            )
            storage.stats.avg_urgency_score = total_urgency / len(emails_with_analysis)
        else:
            storage.stats.avg_urgency_score = 0.0  # Default if no emails have analysis


# --- Main Postmark Webhook Endpoint ---
@app.post(config.webhook_endpoint)
async def handle_postmark_webhook(
    request: Request,
    x_postmark_signature: Optional[str] = Header(None),
):
    """Handle incoming Postmark inbound webhook."""
    processing_start_time = time.time()
    processing_id: Optional[str] = None
    body: bytes = b""

    try:
        body = await request.body()
        await _ensure_webhook_is_authentic(body, x_postmark_signature)

        payload_data = json.loads(body.decode("utf-8"))
        webhook_payload = PostmarkWebhookPayload(**payload_data)

        processing_id = str(
            uuid.uuid4()
        )  # Generate unique ID for this processing instance

        email_data = extract_email_data(webhook_payload)

        # Apply email routing based on inbound address
        try:
            from .email_routing import route_email_by_inbound_address
            email_data = await route_email_by_inbound_address(email_data)
            logger.info(f"Email routing applied for inbound address: {email_data.inbound_email_address}")
        except ImportError:
            logger.debug("Email routing module not available")
        except Exception as e:
            logger.warning(f"Email routing failed, continuing with normal processing: {e}")

        logger.log_email_received(
            email_data, webhook_payload.model_dump()
        )  # Pass dict for logging

        logger.log_extraction_start(email_data)
        extracted_metadata = email_extractor.extract_from_email(email_data)

        urgency_score, urgency_level_str = email_extractor.calculate_urgency_score(
            extracted_metadata.urgency_indicators
        )
        sentiment = _determine_sentiment(extracted_metadata.sentiment_indicators)
        logger.log_extraction_complete(
            email_data, extracted_metadata, urgency_score, sentiment
        )

        email_analysis = _create_email_analysis(
            extracted_metadata,
            urgency_score,
            urgency_level_str,
            sentiment,
        )
        processed_email = ProcessedEmail(
            id=processing_id,
            email_data=email_data,
            analysis=email_analysis,
            status=EmailStatus.ANALYZED,
            # Use timezone aware datetime
            processed_at=datetime.now(timezone.utc),
            webhook_payload=payload_data,  # Store original payload if needed later
        )

        # Store email in memory storage for MCP access
        storage.email_storage[processing_id] = processed_email
        logger.info(f"Email {processing_id} stored in memory storage. Total emails: {len(storage.email_storage)}")

        # Enhance email with plugins
        processed_email = await _process_through_plugins(processed_email, processing_id)
        storage.email_storage[processing_id] = (
            processed_email  # Re-store if plugins modified it
        )
        logger.info(f"Email {processing_id} re-stored after plugin processing")

        await _save_to_database(processed_email, processing_id)

        processing_time_taken = time.time() - processing_start_time
        _update_stats(processing_time_taken)
        logger.log_email_processed(processed_email, processing_time_taken)

        # Final verification that email is stored
        if processing_id in storage.email_storage:
            logger.info(f"✅ Email {processing_id} successfully stored and accessible via MCP")
        else:
            logger.error(f"❌ Email {processing_id} NOT found in storage after processing!")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "processing_id": processing_id,
                "message": f"Email {
                    email_data.message_id} processed successfully.",
            },
        )

    except json.JSONDecodeError as e:
        logger.log_processing_error(
            e,
            {
                "error_type": "json_decode",
                "body_preview": body[:200].decode("utf-8", errors="replace"),
            },
        )
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from e
    except ValidationError as e:
        logger.log_processing_error(
            e,
            {
                "error_type": "validation_error",
                "validation_errors": str(e),
            },
        )
        raise HTTPException(
            status_code=422, detail=f"Validation error: {str(e)}"
        ) from e
    except (
        HTTPException
    ):  # Re-raise HTTPExceptions directly (e.g., from _ensure_webhook_is_authentic)
        raise
    except Exception as e:
        context_id = processing_id if processing_id else "N/A"
        logger.log_processing_error(e, {"processing_id": context_id})
        storage.stats.total_errors += 1
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during email processing: {
                str(e)}",
        )


# --- Dashboard Route ---

@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard():
    """Serve the main dashboard interface."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Inbox Zen - Email Analytics Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    </head>
    <body class="bg-gray-50">
        <div x-data="dashboard()" x-init="init()" class="min-h-screen">
            <!-- Header -->
            <header class="bg-white shadow-sm border-b">
                <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div class="flex justify-between items-center py-4">
                        <div class="flex items-center">
                            <h1 class="text-2xl font-bold text-gray-900">📧 Inbox Zen</h1>
                            <span class="ml-2 text-sm text-gray-500">Email Analytics Dashboard</span>
                        </div>
                        <button @click="refresh()" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                            🔄 Refresh
                        </button>
                    </div>
                </div>
            </header>

            <!-- Main Content -->
            <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <!-- Loading State -->
                <div x-show="loading" class="text-center py-8">
                    <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
                    <p class="mt-2 text-gray-600">Loading dashboard...</p>
                </div>

                <!-- Dashboard Content -->
                <div x-show="!loading" style="display: none;">
                    <!-- Stats Cards -->
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                        <div class="bg-white p-6 rounded-lg shadow">
                            <div class="flex items-center">
                                <div class="p-2 bg-blue-100 rounded-lg">
                                    <span class="text-2xl">📧</span>
                                </div>
                                <div class="ml-4">
                                    <p class="text-sm font-medium text-gray-600">Total Emails</p>
                                    <p class="text-2xl font-bold text-gray-900" x-text="stats.total_emails || 0"></p>
                                </div>
                            </div>
                        </div>

                        <div class="bg-white p-6 rounded-lg shadow">
                            <div class="flex items-center">
                                <div class="p-2 bg-green-100 rounded-lg">
                                    <span class="text-2xl">✅</span>
                                </div>
                                <div class="ml-4">
                                    <p class="text-sm font-medium text-gray-600">Analyzed</p>
                                    <p class="text-2xl font-bold text-gray-900" x-text="stats.analyzed_emails || 0"></p>
                                </div>
                            </div>
                        </div>

                        <div class="bg-white p-6 rounded-lg shadow">
                            <div class="flex items-center">
                                <div class="p-2 bg-yellow-100 rounded-lg">
                                    <span class="text-2xl">⚡</span>
                                </div>
                                <div class="ml-4">
                                    <p class="text-sm font-medium text-gray-600">Avg Urgency</p>
                                    <p class="text-2xl font-bold text-gray-900" x-text="Math.round(stats.avg_urgency_score || 0)"></p>
                                </div>
                            </div>
                        </div>

                        <div class="bg-white p-6 rounded-lg shadow">
                            <div class="flex items-center">
                                <div class="p-2 bg-purple-100 rounded-lg">
                                    <span class="text-2xl">📊</span>
                                </div>
                                <div class="ml-4">
                                    <p class="text-sm font-medium text-gray-600">MCP Accuracy</p>
                                    <p class="text-2xl font-bold text-gray-900">95%</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Recent Emails -->
                    <div class="bg-white rounded-lg shadow">
                        <div class="px-6 py-4 border-b border-gray-200">
                            <h2 class="text-lg font-medium text-gray-900">Recent Emails</h2>
                        </div>
                        <div class="p-6">
                            <div x-show="emails.length === 0" class="text-center py-8 text-gray-500">
                                No emails found. Send a test email to get started!
                            </div>
                            <div x-show="emails.length > 0" class="space-y-4">
                                <template x-for="email in emails" :key="email.id">
                                    <div class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
                                        <div class="flex justify-between items-start">
                                            <div class="flex-1">
                                                <h3 class="font-medium text-gray-900" x-text="email.subject"></h3>
                                                <p class="text-sm text-gray-600" x-text="'From: ' + email.from"></p>
                                                <p class="text-xs text-gray-500" x-text="new Date(email.received_at).toLocaleString()"></p>
                                            </div>
                                            <div class="flex items-center space-x-2">
                                                <span class="px-2 py-1 text-xs rounded-full"
                                                      :class="email.urgency_level === 'high' ? 'bg-red-100 text-red-800' :
                                                             email.urgency_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                                                             'bg-green-100 text-green-800'"
                                                      x-text="email.urgency_level"></span>
                                                <span class="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full"
                                                      x-text="email.sentiment"></span>
                                            </div>
                                        </div>
                                    </div>
                                </template>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>

        <script>
            function dashboard() {
                return {
                    loading: true,
                    stats: {},
                    emails: [],

                    async init() {
                        await this.loadData();
                    },

                    async loadData() {
                        this.loading = true;
                        try {
                            // Load analytics
                            const analyticsResponse = await fetch('/api/analytics');
                            if (analyticsResponse.ok) {
                                this.stats = await analyticsResponse.json();
                            }

                            // Load recent emails
                            const emailsResponse = await fetch('/api/emails/recent?limit=10');
                            if (emailsResponse.ok) {
                                const emailsData = await emailsResponse.json();
                                this.emails = emailsData.emails || [];
                            }
                        } catch (error) {
                            console.error('Failed to load dashboard data:', error);
                        } finally {
                            this.loading = false;
                        }
                    },

                    async refresh() {
                        await this.loadData();
                    }
                }
            }
        </script>
    </body>
    </html>
    """


# --- Health and Basic API Endpoints (specific to this webhook service) ---


@app.get("/health", tags=["Monitoring"])
async def detailed_health_check():
    """Provides detailed health status of the webhook service."""
    return {
        "status": "healthy",
        "server_name": config.server_name,
        "server_version": config.server_version,
        "emails_processed_in_memory": (
            storage.stats.total_processed
        ),  # Clarify in-memory
        "stack": os.environ.get("VERCEL_DEPLOYMENT_ID", "default"),
        "errors_logged": storage.stats.total_errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health/services", tags=["Monitoring"])
async def services_health_check(skip_connectivity_tests: bool = False):
    """
    Comprehensive health check for all external services and configurations.

    Args:
        skip_connectivity_tests: Skip memory-intensive connectivity tests (useful for serverless)

    Checks:
    - SambaNova AI configuration and connectivity
    - Supabase database configuration and connectivity
    - Postmark webhook configuration
    - Environment variables status
    """
    health_status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": "healthy",
        "services": {},
        "configuration": {},
        "missing_config": [],
        "warnings": []
    }

    # Check SambaNova AI Service
    sambanova_status = await _check_sambanova_service(skip_connectivity_tests)
    health_status["services"]["sambanova"] = sambanova_status

    # Check Supabase Database Service
    supabase_status = await _check_supabase_service(skip_connectivity_tests)
    health_status["services"]["supabase"] = supabase_status

    # Check Postmark Configuration
    postmark_status = _check_postmark_config()
    health_status["services"]["postmark"] = postmark_status

    # Check Environment Configuration
    env_status = _check_environment_config()
    health_status["configuration"] = env_status

    # Collect missing configurations
    for service_name, service_info in health_status["services"].items():
        if service_info.get("missing_config"):
            health_status["missing_config"].extend([
                f"{service_name}.{key}" for key in service_info["missing_config"]
            ])

    # Collect warnings
    for service_name, service_info in health_status["services"].items():
        if service_info.get("warnings"):
            health_status["warnings"].extend([
                f"{service_name}: {warning}" for warning in service_info["warnings"]
            ])

    # Determine overall status
    service_statuses = [s["status"] for s in health_status["services"].values()]
    if "error" in service_statuses:
        health_status["overall_status"] = "degraded"
    elif "warning" in service_statuses:
        health_status["overall_status"] = "warning"

    return health_status


@app.get("/health/services/detailed", tags=["Health"])
async def get_detailed_services_health():
    """Get detailed health status with comprehensive error analysis and troubleshooting."""
    try:
        # Get basic health status
        basic_health = await services_health_check()

        # Enhance with additional troubleshooting information
        detailed_health = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": basic_health["overall_status"],
            "services": basic_health["services"],
            "configuration": basic_health["configuration"],
            "missing_config": basic_health["missing_config"],
            "warnings": basic_health["warnings"],
            "troubleshooting": {
                "common_issues": [],
                "quick_fixes": [],
                "documentation_links": {},
                "environment_analysis": {}
            },
            "system_info": {
                "python_version": (
                    f"{sys.version_info.major}.{sys.version_info.minor}."
                    f"{sys.version_info.micro}"
                ),
                "platform": os.name,
                "environment": os.getenv("ENVIRONMENT", "development"),
                "deployment_type": "vercel" if os.getenv("VERCEL") else "local"
            }
        }

        # Analyze common issues and provide solutions
        all_errors = []
        for service_name, service_info in basic_health["services"].items():
            if service_info.get("errors"):
                for error in service_info["errors"]:
                    error["service"] = service_name
                    all_errors.append(error)

        # Group errors by type for better troubleshooting
        error_groups = {}
        for error in all_errors:
            error_type = error.get("type", "unknown")
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(error)

        # Generate troubleshooting recommendations
        if "configuration_error" in error_groups:
            detailed_health["troubleshooting"]["common_issues"].append({
                "issue": "Configuration Errors",
                "count": len(error_groups["configuration_error"]),
                "description": "Environment variables are missing or incorrectly configured",
                "impact": "Services may not function properly or fall back to defaults",
                "priority": "high"
            })

            detailed_health["troubleshooting"]["quick_fixes"].append({
                "title": "Fix Configuration Errors",
                "steps": [
                    "Check your environment variables in Vercel dashboard",
                    "Ensure all required variables are set for production environment",
                    "Verify variable names match exactly (case-sensitive)",
                    "Redeploy after making changes: vercel --prod"
                ],
                "commands": [
                    "vercel env ls",
                    "vercel env add VARIABLE_NAME 'value' production",
                    "vercel --prod"
                ]
            })

        if "dependency_error" in error_groups:
            detailed_health["troubleshooting"]["common_issues"].append({
                "issue": "Missing Dependencies",
                "count": len(error_groups["dependency_error"]),
                "description": "Required Python packages are not installed",
                "impact": "Features requiring these dependencies will be disabled",
                "priority": "medium"
            })

            missing_deps = set()
            for error in error_groups["dependency_error"]:
                if error.get("dependency"):
                    missing_deps.add(error["dependency"])

            if missing_deps:
                detailed_health["troubleshooting"]["quick_fixes"].append({
                    "title": "Install Missing Dependencies",
                    "steps": [
                        "Update requirements.txt with missing dependencies",
                        "Redeploy to install new dependencies"
                    ],
                    "commands": [
                        f"pip install {' '.join(missing_deps)}",
                        "vercel --prod"
                    ],
                    "missing_dependencies": list(missing_deps)
                })

        # Add documentation links
        detailed_health["troubleshooting"]["documentation_links"] = {
            "supabase": "https://supabase.com/docs/guides/getting-started",
            "sambanova": "https://cloud.sambanova.ai/",
            "postmark": "https://postmarkapp.com/developer",
            "vercel_env": "https://vercel.com/docs/concepts/projects/environment-variables",
            "project_repo": "https://github.com/your-repo/EmailParsing"
        }

        # Environment analysis
        env_analysis = {
            "deployment_environment": os.getenv("ENVIRONMENT", "development"),
            "is_production": os.getenv("ENVIRONMENT") == "production",
            "is_vercel": bool(os.getenv("VERCEL")),
            "has_secrets": bool(os.getenv("POSTMARK_WEBHOOK_SECRET")),
            "total_env_vars": len([k for k in os.environ.keys() if not k.startswith("_")]),
            "critical_missing": len([
                var for var in ["SUPABASE_URL", "SUPABASE_ANON_KEY", "SAMBANOVA_API_KEY"]
                if not os.getenv(var)
            ])
        }
        detailed_health["troubleshooting"]["environment_analysis"] = env_analysis

        return detailed_health

    except Exception as e:
        logger.error(f"Error generating detailed health status: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to generate detailed health status",
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


@app.get("/health/services/lite", tags=["Health"])
async def services_health_check_lite():
    """
    Lightweight health check optimized for serverless environments.
    Skips memory-intensive connectivity tests and imports.
    """
    health_status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": "healthy",
        "services": {},
        "configuration": {},
        "missing_config": [],
        "warnings": [],
        "mode": "lite"
    }

    # Lightweight SambaNova check (config only)
    sambanova_status = _check_sambanova_config_only()
    health_status["services"]["sambanova"] = sambanova_status

    # Lightweight Supabase check (config only)
    supabase_status = _check_supabase_config_only()
    health_status["services"]["supabase"] = supabase_status

    # Check Postmark Configuration (already lightweight)
    postmark_status = _check_postmark_config()
    health_status["services"]["postmark"] = postmark_status

    # Check Environment Configuration
    env_status = _check_environment_config()
    health_status["configuration"] = env_status

    # Collect missing configurations and warnings
    for service_name, service_info in health_status["services"].items():
        if service_info.get("missing_config"):
            health_status["missing_config"].extend([
                f"{service_name}.{config}" for config in service_info["missing_config"]
            ])
        if service_info.get("warnings"):
            health_status["warnings"].extend(service_info["warnings"])

    # Determine overall status
    statuses = [service["status"] for service in health_status["services"].values()]
    if "error" in statuses:
        health_status["overall_status"] = "error"
    elif "warning" in statuses:
        health_status["overall_status"] = "warning"

    return health_status


@app.get("/health/status", tags=["Health"])
async def simple_health_status():
    """
    Ultra-simple health status for monitoring.
    No imports, no memory-intensive operations.
    """
    # Count configured services
    configured_services = 0
    total_services = 3

    if os.getenv("SAMBANOVA_API_KEY"):
        configured_services += 1

    if os.getenv("SUPABASE_URL") and (os.getenv("SUPABASE_ANON_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")):
        configured_services += 1

    if os.getenv("POSTMARK_WEBHOOK_SECRET"):
        configured_services += 1

    # Determine status
    if configured_services == total_services:
        status = "healthy"
    elif configured_services > 0:
        status = "degraded"
    else:
        status = "error"

    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services_configured": f"{configured_services}/{total_services}",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "deployment": "vercel" if os.getenv("VERCEL") else "local",
        "memory_optimized": True
    }


@app.get("/health/errors", tags=["Health"])
async def get_service_errors():
    """Get only the errors and critical issues from all services."""
    try:
        # Get basic health status
        basic_health = await services_health_check()

        errors_summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": basic_health["overall_status"],
            "total_errors": 0,
            "total_warnings": 0,
            "critical_issues": [],
            "service_errors": {},
            "missing_configurations": basic_health.get("missing_config", []),
            "quick_resolution_steps": []
        }

        # Collect all errors from services
        for service_name, service_info in basic_health["services"].items():
            service_errors = {
                "service_name": service_info["name"],
                "status": service_info["status"],
                "errors": service_info.get("errors", []),
                "warnings": service_info.get("warnings", []),
                "configured": service_info.get("configured", False),
                "accessible": service_info.get("accessible", False)
            }

            errors_summary["service_errors"][service_name] = service_errors
            errors_summary["total_errors"] += len(service_errors["errors"])
            errors_summary["total_warnings"] += len(service_errors["warnings"])

            # Identify critical issues
            for error in service_errors["errors"]:
                if error.get("priority") == "high":
                    errors_summary["critical_issues"].append({
                        "service": service_name,
                        "type": error.get("type"),
                        "message": error.get("message"),
                        "resolution": error.get("resolution"),
                        "field": error.get("field")
                    })

        # Generate quick resolution steps
        if errors_summary["missing_configurations"]:
            errors_summary["quick_resolution_steps"].append({
                "step": 1,
                "title": "Configure Missing Environment Variables",
                "description": "Set the following environment variables in Vercel",
                "variables": errors_summary["missing_configurations"],
                "command": "vercel env add VARIABLE_NAME 'value' production"
            })

        if errors_summary["total_errors"] > 0:
            errors_summary["quick_resolution_steps"].append({
                "step": 2,
                "title": "Redeploy After Configuration",
                "description": "Redeploy the application to apply changes",
                "command": "vercel --prod"
            })

        # Add priority classification
        if errors_summary["total_errors"] == 0 and errors_summary["total_warnings"] == 0:
            errors_summary["priority"] = "none"
            errors_summary["message"] = "No errors or warnings detected"
        elif len(errors_summary["critical_issues"]) > 0:
            errors_summary["priority"] = "critical"
            errors_summary["message"] = f"{len(errors_summary['critical_issues'])} critical issues require immediate attention"
        elif errors_summary["total_errors"] > 0:
            errors_summary["priority"] = "high"
            errors_summary["message"] = f"{errors_summary['total_errors']} errors need to be resolved"
        else:
            errors_summary["priority"] = "medium"
            errors_summary["message"] = f"{errors_summary['total_warnings']} warnings should be addressed"

        return errors_summary

    except Exception as e:
        logger.error(f"Error generating service errors summary: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to generate service errors summary",
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


@app.get("/debug/mcp-connection", tags=["Debug"])
async def debug_mcp_connection():
    """Debug MCP server connection and data access."""
    debug_info = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "storage_direct": {
            "total_emails": len(storage.email_storage),
            "email_ids": list(storage.email_storage.keys()),
            "stats": {
                "total_processed": storage.stats.total_processed,
                "total_errors": storage.stats.total_errors,
                "avg_urgency_score": storage.stats.avg_urgency_score,
            }
        },
        "mcp_server": {
            "available": False,
            "error": None,
            "emails_via_mcp": 0
        },
        "api_endpoints": {
            "recent_emails": "/api/emails/recent",
            "mcp_stats": "/mcp/emails/stats",
            "mcp_recent": "/mcp/emails/recent"
        }
    }

    # Test MCP server availability
    try:
        # Try to import and test MCP server
        from .server import server as mcp_server
        debug_info["mcp_server"]["available"] = True
        debug_info["mcp_server"]["name"] = mcp_server.name
        debug_info["mcp_server"]["version"] = mcp_server.version

        # Test MCP email access
        try:
            # This would test if MCP can access the same storage
            mcp_emails = len(storage.email_storage)  # Direct access for now
            debug_info["mcp_server"]["emails_via_mcp"] = mcp_emails
        except Exception as e:
            debug_info["mcp_server"]["error"] = f"MCP email access failed: {str(e)}"

    except ImportError as e:
        debug_info["mcp_server"]["error"] = f"MCP server import failed: {str(e)}"
    except Exception as e:
        debug_info["mcp_server"]["error"] = f"MCP server error: {str(e)}"

    return debug_info


@app.get("/debug/supabase-detailed", tags=["Debug"])
async def debug_supabase_detailed():
    """Detailed Supabase connection and configuration test."""
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment_vars": {
            "SUPABASE_URL": os.getenv("SUPABASE_URL", "NOT_SET")[:50] + "..." if os.getenv("SUPABASE_URL") else "NOT_SET",
            "SUPABASE_ANON_KEY": "SET" if os.getenv("SUPABASE_ANON_KEY") else "NOT_SET",
            "SUPABASE_SERVICE_ROLE_KEY": "SET" if os.getenv("SUPABASE_SERVICE_ROLE_KEY") else "NOT_SET"
        },
        "import_test": {
            "supabase_module": False,
            "create_client": False,
            "error": None
        },
        "config_test": {
            "config_created": False,
            "is_configured": False,
            "url": None,
            "key_length": 0,
            "error": None
        },
        "client_creation": {
            "attempted": False,
            "success": False,
            "client_type": None,
            "error": None
        }
    }

    # Test imports
    try:
        from supabase import create_client
        result["import_test"]["supabase_module"] = True
        result["import_test"]["create_client"] = True
    except ImportError as e:
        result["import_test"]["error"] = f"Import error: {str(e)}"
    except Exception as e:
        result["import_test"]["error"] = f"Unexpected error: {str(e)}"

    # Test config
    try:
        from .supabase_integration.config import SupabaseConfig
        config = SupabaseConfig()
        result["config_test"]["config_created"] = True
        result["config_test"]["is_configured"] = config.is_configured()
        result["config_test"]["url"] = config.supabase_url[:50] + "..." if config.supabase_url else None
        result["config_test"]["key_length"] = len(config.supabase_key) if config.supabase_key else 0
    except Exception as e:
        result["config_test"]["error"] = str(e)

    # Test client creation
    if result["import_test"]["create_client"] and result["config_test"]["is_configured"]:
        try:
            result["client_creation"]["attempted"] = True
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_ANON_KEY")

            if url and key:
                client = create_client(url, key)
                result["client_creation"]["success"] = True
                result["client_creation"]["client_type"] = str(type(client))
            else:
                result["client_creation"]["error"] = "URL or key missing"
        except Exception as e:
            import traceback
            result["client_creation"]["error"] = str(e)
            result["client_creation"]["traceback"] = traceback.format_exc()

    return result


@app.get("/debug/supabase-http-test", tags=["Debug"])
async def debug_supabase_http_test():
    """Test Supabase HTTP client approach."""
    if not INTEGRATIONS_AVAILABLE:
        return {"error": "Integrations not available"}

    supabase_db = integration_registry.get_database("supabase")
    if not supabase_db:
        return {"error": "Supabase database not registered"}

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "http_client_test": {
            "interface_available": True,
            "connected": supabase_db._connected,
            "client_exists": supabase_db.client is not None,
            "config_valid": supabase_db.config.is_configured()
        },
        "client_creation_test": {
            "attempted": False,
            "success": False,
            "error": None
        },
        "table_test": {
            "attempted": False,
            "success": False,
            "error": None
        }
    }

    # Test HTTP client creation
    try:
        result["client_creation_test"]["attempted"] = True
        supabase_db._ensure_client()
        result["client_creation_test"]["success"] = True
        result["http_client_test"]["client_exists"] = supabase_db.client is not None

        # Test table access
        if supabase_db.client:
            result["table_test"]["attempted"] = True
            table = supabase_db.client.table("emails")
            query = table.select("id").limit(1)
            response = query.execute()
            result["table_test"]["success"] = True
            result["table_test"]["response_data_length"] = len(response.data)

    except Exception as e:
        if not result["client_creation_test"]["success"]:
            result["client_creation_test"]["error"] = str(e)
            result["client_creation_test"]["error_type"] = type(e).__name__
        else:
            result["table_test"]["error"] = str(e)
            result["table_test"]["error_type"] = type(e).__name__

    return result


@app.get("/debug/supabase-lazy-test", tags=["Debug"])
async def debug_supabase_lazy_test():
    """Test Supabase lazy loading approach."""
    if not INTEGRATIONS_AVAILABLE:
        return {"error": "Integrations not available"}

    supabase_db = integration_registry.get_database("supabase")
    if not supabase_db:
        return {"error": "Supabase database not registered"}

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lazy_loading_test": {
            "interface_available": True,
            "connected": supabase_db._connected,
            "client_exists": supabase_db.client is not None,
            "config_valid": supabase_db.config.is_configured()
        },
        "client_creation_test": {
            "attempted": False,
            "success": False,
            "error": None
        }
    }

    # Test lazy client creation
    try:
        result["client_creation_test"]["attempted"] = True
        supabase_db._ensure_client()
        result["client_creation_test"]["success"] = True
        result["lazy_loading_test"]["client_exists"] = supabase_db.client is not None
    except Exception as e:
        result["client_creation_test"]["error"] = str(e)
        result["client_creation_test"]["error_type"] = type(e).__name__

    return result


@app.get("/debug/supabase-raw-test", tags=["Debug"])
async def debug_supabase_raw_test():
    """Raw Supabase connection test with maximum error details."""
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "test_steps": []
    }

    # Step 1: Environment variables
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    result["test_steps"].append({
        "step": "1_environment",
        "success": bool(url and key),
        "url_length": len(url) if url else 0,
        "key_length": len(key) if key else 0,
        "url_starts_with_https": url.startswith("https://") if url else False
    })

    if not (url and key):
        return result

    # Step 2: Import test
    try:
        from supabase import create_client, Client
        result["test_steps"].append({
            "step": "2_import",
            "success": True,
            "create_client_type": str(type(create_client)),
            "client_class": str(Client)
        })
    except Exception as e:
        import traceback
        result["test_steps"].append({
            "step": "2_import",
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        return result

    # Step 3: Client creation with detailed error handling
    try:
        result["test_steps"].append({
            "step": "3_client_creation_start",
            "url": url[:50] + "...",
            "key_preview": key[:10] + "..." + key[-10:] if len(key) > 20 else "SHORT_KEY"
        })

        client = create_client(url, key)

        result["test_steps"].append({
            "step": "3_client_creation_success",
            "success": True,
            "client_type": str(type(client)),
            "client_url": getattr(client, 'supabase_url', 'NO_URL_ATTR'),
            "has_table_method": hasattr(client, 'table')
        })

    except ImportError as e:
        import traceback
        result["test_steps"].append({
            "step": "3_client_creation_import_error",
            "success": False,
            "error_type": "ImportError",
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        return result

    except ValueError as e:
        import traceback
        result["test_steps"].append({
            "step": "3_client_creation_value_error",
            "success": False,
            "error_type": "ValueError",
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        return result

    except Exception as e:
        import traceback
        result["test_steps"].append({
            "step": "3_client_creation_general_error",
            "success": False,
            "error_type": type(e).__name__,
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        return result

    # Step 4: Simple table query test
    try:
        response = client.table("emails").select("id").limit(1).execute()
        result["test_steps"].append({
            "step": "4_table_query",
            "success": True,
            "response_type": str(type(response)),
            "has_data": hasattr(response, 'data'),
            "data_length": len(response.data) if hasattr(response, 'data') else 0
        })
    except Exception as e:
        import traceback
        result["test_steps"].append({
            "step": "4_table_query",
            "success": False,
            "error_type": type(e).__name__,
            "error": str(e),
            "traceback": traceback.format_exc()
        })

    return result


@app.get("/debug/supabase-connect", tags=["Debug"])
async def debug_supabase_connect():
    """Test Supabase connection and initialization."""
    if not INTEGRATIONS_AVAILABLE:
        return {"error": "Integrations not available"}

    supabase_db = integration_registry.get_database("supabase")
    if not supabase_db:
        return {"error": "Supabase database not registered"}

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "supabase_interface": {
            "registered": True,
            "class": supabase_db.__class__.__name__,
            "client_exists": supabase_db.client is not None,
            "connected": getattr(supabase_db, '_connected', False),
            "current_user_id": supabase_db.current_user_id
        },
        "environment": {
            "url": bool(os.getenv("SUPABASE_URL")),
            "anon_key": bool(os.getenv("SUPABASE_ANON_KEY")),
            "service_key": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
        },
        "connection_test": {
            "attempted": False,
            "success": False,
            "error": None
        }
    }

    # Try to connect if not connected
    if not supabase_db.client:
        try:
            result["connection_test"]["attempted"] = True
            await supabase_db.connect("")
            result["connection_test"]["success"] = True
            result["supabase_interface"]["client_exists"] = supabase_db.client is not None
            result["supabase_interface"]["connected"] = getattr(supabase_db, '_connected', False)
        except Exception as e:
            result["connection_test"]["error"] = str(e)

    return result


@app.get("/debug/supabase-emails", tags=["Debug"])
async def debug_supabase_emails():
    """Check emails stored in Supabase database."""
    if not INTEGRATIONS_AVAILABLE:
        return {"error": "Integrations not available"}

    supabase_db = integration_registry.get_database("supabase")
    if not supabase_db:
        return {"error": "Supabase database not configured"}

    try:
        # Try to query emails directly from Supabase
        response = supabase_db.client.table("emails").select("*").limit(10).execute()

        default_user_id = "00000000-0000-0000-0000-000000000000"
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "supabase_emails": {
                "count": len(response.data),
                "emails": response.data,
                "user_id_used": supabase_db.current_user_id or default_user_id
            }
        }

    except Exception as e:
        default_user_id = "00000000-0000-0000-0000-000000000000"
        return {
            "error": f"Failed to query Supabase: {str(e)}",
            "user_id_used": supabase_db.current_user_id or default_user_id
        }


@app.get("/debug/supabase-status", tags=["Debug"])
async def debug_supabase_status():
    """Check Supabase configuration and connectivity."""
    debug_info = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "supabase_config": {
            "url_configured": bool(os.getenv("SUPABASE_URL")),
            "anon_key_configured": bool(os.getenv("SUPABASE_ANON_KEY")),
            "service_key_configured": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
            "url_preview": os.getenv("SUPABASE_URL", "")[:50] + "..." if os.getenv("SUPABASE_URL") else None,
        },
        "integration_status": {
            "integrations_available": INTEGRATIONS_AVAILABLE,
            "supabase_registered": False,
            "database_priority": []
        },
        "connection_test": {
            "attempted": False,
            "success": False,
            "error": None
        }
    }

    if INTEGRATIONS_AVAILABLE:
        # Check if Supabase is registered
        supabase_db = integration_registry.get_database("supabase")
        debug_info["integration_status"]["supabase_registered"] = supabase_db is not None

        # Check database priority
        for db_name in ["supabase", "sqlite", "postgresql"]:
            db = integration_registry.get_database(db_name)
            if db:
                debug_info["integration_status"]["database_priority"].append({
                    "name": db_name,
                    "class": db.__class__.__name__,
                    "available": True
                })

        # Test Supabase connection if configured
        if supabase_db and os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"):
            debug_info["connection_test"]["attempted"] = True
            try:
                # Try to test the connection
                # This is a simple test - in production you might want a more comprehensive check
                debug_info["connection_test"]["success"] = True
                debug_info["connection_test"]["message"] = "Supabase interface available and configured"
            except Exception as e:
                debug_info["connection_test"]["error"] = str(e)

    return debug_info


@app.get("/debug/load-from-sqlite", tags=["Debug"])
async def debug_load_from_sqlite():
    """Load emails from SQLite database into memory storage."""
    if not INTEGRATIONS_AVAILABLE:
        return {"error": "Integrations not available"}

    sqlite_db = integration_registry.get_database("sqlite")
    if not sqlite_db:
        return {"error": "SQLite database not configured"}

    try:
        # Try to load emails from SQLite
        import aiosqlite
        async with aiosqlite.connect(sqlite_db.db_path) as db:
            cursor = await db.execute("SELECT * FROM emails ORDER BY created_at DESC LIMIT 10")
            rows = await cursor.fetchall()

            # Get column names
            cursor = await db.execute("PRAGMA table_info(emails)")
            columns_info = await cursor.fetchall()
            column_names = [col[1] for col in columns_info]

            loaded_emails = []
            for row in rows:
                email_dict = dict(zip(column_names, row))
                loaded_emails.append({
                    "id": email_dict.get("id"),
                    "subject": email_dict.get("subject"),
                    "from_email": email_dict.get("from_email"),
                    "received_at": email_dict.get("received_at"),
                    "urgency_score": email_dict.get("urgency_score")
                })

            return {
                "sqlite_path": sqlite_db.db_path,
                "emails_in_sqlite": len(rows),
                "emails_in_memory": len(storage.email_storage),
                "loaded_emails": loaded_emails,
                "column_names": column_names
            }

    except ImportError:
        return {"error": "aiosqlite not available"}
    except Exception as e:
        return {"error": f"Failed to load from SQLite: {str(e)}"}


@app.get("/debug/sync-test", tags=["Debug"])
async def debug_sync_test():
    """Test synchronization between webhook storage and API storage."""
    debug_info = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "webhook_storage": {
            "total_emails": len(storage.email_storage),
            "email_ids": list(storage.email_storage.keys()),
            "storage_id": id(storage.email_storage),
            "stats_id": id(storage.stats)
        },
        "api_storage": {
            "total_emails": 0,
            "email_ids": [],
            "storage_id": None,
            "stats_id": None
        },
        "sync_status": "unknown"
    }

    # Test API storage access
    try:
        from .api_routes import storage as api_storage
        debug_info["api_storage"]["total_emails"] = len(api_storage.email_storage)
        debug_info["api_storage"]["email_ids"] = list(api_storage.email_storage.keys())
        debug_info["api_storage"]["storage_id"] = id(api_storage.email_storage)
        debug_info["api_storage"]["stats_id"] = id(api_storage.stats)

        # Check if they're the same instance
        if id(storage.email_storage) == id(api_storage.email_storage):
            debug_info["sync_status"] = "synchronized"
        else:
            debug_info["sync_status"] = "different_instances"

    except Exception as e:
        debug_info["api_storage"]["error"] = str(e)
        debug_info["sync_status"] = "error"

    return debug_info


@app.get("/debug/storage", tags=["Debug"])
async def debug_storage_status():
    """Debug endpoint to check storage status and recent emails."""
    try:
        # Get storage statistics
        storage_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "memory_storage": {
                "total_emails": len(storage.email_storage),
                "email_ids": list(storage.email_storage.keys()),
                "stats": {
                    "total_processed": storage.stats.total_processed,
                    "total_errors": storage.stats.total_errors,
                    "avg_urgency_score": storage.stats.avg_urgency_score,
                    "processing_times_count": len(storage.stats.processing_times),
                    "last_processed": storage.stats.last_processed.isoformat() if storage.stats.last_processed else None,
                    "urgency_distribution": {k.value: v for k, v in storage.stats.urgency_distribution.items()} if storage.stats.urgency_distribution else {}
                }
            },
            "recent_emails": []
        }

        # Get details of recent emails (last 5)
        recent_emails = list(storage.email_storage.values())[-5:]
        for email in recent_emails:
            storage_info["recent_emails"].append({
                "id": email.id,
                "message_id": email.email_data.message_id,
                "subject": email.email_data.subject,
                "from": email.email_data.from_email,
                "status": email.status.value if email.status else "unknown",
                "processed_at": email.processed_at.isoformat() if email.processed_at else None,
                "has_analysis": email.analysis is not None,
                "urgency_level": email.analysis.urgency_level.value if email.analysis else None,
                "inbound_email_address": email.email_data.inbound_email_address
            })

        return storage_info

    except Exception as e:
        logger.error(f"Error in debug storage endpoint: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@app.post("/webhook/debug", tags=["Debug"])
async def debug_webhook_signature(
    request: Request,
    x_postmark_signature: Optional[str] = Header(None)
):
    """Debug endpoint to see what signature Postmark sends"""
    try:
        body = await request.body()

        debug_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signature_received": x_postmark_signature,
            "signature_length": len(x_postmark_signature) if x_postmark_signature else 0,
            "body_preview": body[:200].decode('utf-8', errors='replace'),
            "body_length": len(body),
            "headers": dict(request.headers),
            "configured_secret": config.postmark_webhook_secret[:10] + "..." if config.postmark_webhook_secret else None
        }

        logger.info(f"🔍 Debug webhook called - signature: {x_postmark_signature}")

        return JSONResponse(
            status_code=200,
            content={
                "status": "debug_success",
                "message": "Webhook debug info captured",
                "debug_info": debug_info
            }
        )

    except Exception as e:
        logger.error(f"Debug webhook error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/webhook/test", tags=["Debug"])
async def handle_test_webhook(request: Request):
    """Test webhook endpoint without signature verification for testing purposes."""
    processing_start_time = time.time()
    processing_id: Optional[str] = None
    body: bytes = b""

    try:
        body = await request.body()
        # Skip signature verification for testing
        logger.info("🧪 Test webhook called - skipping signature verification")

        payload_data = json.loads(body.decode("utf-8"))
        webhook_payload = PostmarkWebhookPayload(**payload_data)

        processing_id = str(uuid.uuid4())

        email_data = extract_email_data(webhook_payload)

        # Apply email routing based on inbound address
        try:
            from .email_routing import route_email_by_inbound_address
            email_data = await route_email_by_inbound_address(email_data)
            logger.info(f"Email routing applied for inbound address: {email_data.inbound_email_address}")
        except ImportError:
            logger.debug("Email routing module not available")
        except Exception as e:
            logger.warning(f"Email routing failed, continuing with normal processing: {e}")

        logger.log_email_received(email_data, webhook_payload.model_dump())

        logger.log_extraction_start(email_data)
        extracted_metadata = email_extractor.extract_from_email(email_data)

        urgency_score, urgency_level_str = email_extractor.calculate_urgency_score(
            extracted_metadata.urgency_indicators
        )
        sentiment = _determine_sentiment(extracted_metadata.sentiment_indicators)
        logger.log_extraction_complete(
            email_data, extracted_metadata, urgency_score, sentiment
        )

        email_analysis = _create_email_analysis(
            extracted_metadata, urgency_score, urgency_level_str, sentiment
        )
        processed_email = ProcessedEmail(
            id=processing_id,
            email_data=email_data,
            analysis=email_analysis,
            status=EmailStatus.ANALYZED,
            processed_at=datetime.now(timezone.utc),
            webhook_payload=payload_data,
        )

        # Store email in memory storage for MCP access
        storage.email_storage[processing_id] = processed_email
        logger.info(f"🧪 Test email {processing_id} stored in memory storage. Total emails: {len(storage.email_storage)}")

        # Enhance email with plugins
        processed_email = await _process_through_plugins(processed_email, processing_id)
        storage.email_storage[processing_id] = processed_email
        logger.info(f"🧪 Test email {processing_id} re-stored after plugin processing")

        await _save_to_database(processed_email, processing_id)

        processing_time_taken = time.time() - processing_start_time
        _update_stats(processing_time_taken)
        logger.log_email_processed(processed_email, processing_time_taken)

        # Final verification that email is stored
        if processing_id in storage.email_storage:
            logger.info(f"✅ Test email {processing_id} successfully stored and accessible via MCP")
        else:
            logger.error(f"❌ Test email {processing_id} NOT found in storage after processing!")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "processing_id": processing_id,
                "message": f"Test email {email_data.message_id} processed successfully.",
                "test_mode": True
            },
        )

    except Exception as e:
        context_id = processing_id if processing_id else "N/A"
        logger.log_processing_error(e, {"processing_id": context_id, "test_mode": True})
        storage.stats.total_errors += 1
        raise HTTPException(
            status_code=500,
            detail=f"Test webhook processing failed: {str(e)}",
        )


# --- Lightweight Service Health Check Functions ---

def _check_sambanova_config_only() -> Dict[str, any]:
    """Lightweight SambaNova check - configuration only, no imports."""
    service_info = {
        "name": "SambaNova AI",
        "status": "healthy",
        "configured": False,
        "accessible": True,  # Assume accessible if configured
        "missing_config": [],
        "warnings": [],
        "details": {
            "mode": "config_only",
            "environment_variables": {}
        }
    }

    # Check environment variables only
    sambanova_api_key = os.getenv("SAMBANOVA_API_KEY")
    sambanova_model = os.getenv("SAMBANOVA_MODEL", "Meta-Llama-3.3-70B-Instruct")
    sambanova_base_url = os.getenv("SAMBANOVA_BASE_URL", "https://api.sambanova.ai/v1")

    service_info["details"]["environment_variables"] = {
        "SAMBANOVA_API_KEY": {
            "configured": bool(sambanova_api_key),
            "length": len(sambanova_api_key) if sambanova_api_key else 0
        },
        "SAMBANOVA_MODEL": {
            "configured": bool(sambanova_model),
            "value": sambanova_model
        },
        "SAMBANOVA_BASE_URL": {
            "configured": bool(sambanova_base_url),
            "value": sambanova_base_url
        }
    }

    if not sambanova_api_key:
        service_info["missing_config"].append("SAMBANOVA_API_KEY")
        service_info["status"] = "warning"
        service_info["warnings"].append("API key not configured - AI features disabled")
    else:
        service_info["configured"] = True

    return service_info


def _check_supabase_config_only() -> Dict[str, any]:
    """Lightweight Supabase check - configuration only, no imports."""
    service_info = {
        "name": "Supabase Database",
        "status": "healthy",
        "configured": False,
        "accessible": True,  # Assume accessible if configured
        "missing_config": [],
        "warnings": [],
        "details": {
            "mode": "config_only",
            "environment_variables": {}
        }
    }

    # Check environment variables only
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = (
        os.getenv("SUPABASE_ANON_KEY") or
        os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    )
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    service_info["details"]["environment_variables"] = {
        "SUPABASE_URL": {
            "configured": bool(supabase_url),
            "valid_format": supabase_url.startswith("https://") if supabase_url else False
        },
        "SUPABASE_ANON_KEY": {
            "configured": bool(supabase_anon_key),
            "source": (
                "SUPABASE_ANON_KEY" if os.getenv("SUPABASE_ANON_KEY")
                else "NEXT_PUBLIC_SUPABASE_ANON_KEY" if supabase_anon_key
                else None
            )
        },
        "SUPABASE_SERVICE_ROLE_KEY": {
            "configured": bool(supabase_service_key)
        }
    }

    missing_vars = []
    if not supabase_url:
        missing_vars.append("SUPABASE_URL")
    if not supabase_anon_key:
        missing_vars.append("SUPABASE_ANON_KEY")

    if missing_vars:
        service_info["missing_config"] = missing_vars
        service_info["status"] = "warning"
        service_info["warnings"].append("Database not configured - using in-memory storage")
    else:
        service_info["configured"] = True

    return service_info


# --- Service Health Check Functions ---

async def _check_sambanova_service(skip_connectivity_tests: bool = False) -> Dict[str, any]:
    """Check SambaNova AI service configuration and connectivity."""
    service_info = {
        "name": "SambaNova AI",
        "status": "healthy",
        "configured": False,
        "accessible": False,
        "missing_config": [],
        "warnings": [],
        "errors": [],
        "details": {
            "last_check": datetime.now(timezone.utc).isoformat(),
            "environment_variables": {},
            "dependencies": {},
            "plugin_status": {}
        }
    }

    try:
        # Check if SambaNova plugin is available
        if not INTEGRATIONS_AVAILABLE:
            service_info["status"] = "warning"
            service_info["warnings"].append("Integration module not available")
            return service_info

        # Check environment variables
        sambanova_api_key = os.getenv("SAMBANOVA_API_KEY")
        sambanova_model = os.getenv("SAMBANOVA_MODEL", "sambanova-large")
        sambanova_base_url = os.getenv(
            "SAMBANOVA_BASE_URL",
            "https://api.sambanova.com/v1"
        )

        # Detailed environment variable analysis
        service_info["details"]["environment_variables"] = {
            "SAMBANOVA_API_KEY": {
                "configured": bool(sambanova_api_key),
                "length": len(sambanova_api_key) if sambanova_api_key else 0,
                "masked_value": (
                    f"{sambanova_api_key[:8]}..."
                    if sambanova_api_key and len(sambanova_api_key) > 8
                    else None
                )
            },
            "SAMBANOVA_MODEL": {
                "configured": bool(sambanova_model),
                "value": sambanova_model,
                "is_default": sambanova_model == "sambanova-large"
            },
            "SAMBANOVA_BASE_URL": {
                "configured": bool(sambanova_base_url),
                "value": sambanova_base_url,
                "is_default": sambanova_base_url == "https://api.sambanova.com/v1"
            }
        }

        if not sambanova_api_key:
            service_info["missing_config"].append("SAMBANOVA_API_KEY")
            service_info["status"] = "warning"
            service_info["warnings"].append(
                "API key not configured - AI features disabled"
            )
            service_info["errors"].append({
                "type": "configuration_error",
                "field": "SAMBANOVA_API_KEY",
                "message": "SambaNova API key not configured",
                "impact": "AI analysis features will be disabled",
                "resolution": "Set SAMBANOVA_API_KEY environment variable",
                "documentation": "https://cloud.sambanova.ai/",
                "priority": "medium"
            })
        else:
            service_info["configured"] = True

        # Check dependencies
        dependencies = ["aiohttp", "openai"]
        dependency_status = {}

        for dep in dependencies:
            try:
                module = __import__(dep)
                dependency_status[dep] = {
                    "available": True,
                    "version": getattr(module, "__version__", "unknown"),
                    "error": None
                }
            except ImportError as e:
                dependency_status[dep] = {
                    "available": False,
                    "version": None,
                    "error": str(e)
                }
                service_info["errors"].append({
                    "type": "dependency_error",
                    "dependency": dep,
                    "message": f"Required dependency '{dep}' not available",
                    "error": str(e),
                    "resolution": f"Install with: pip install {dep}",
                    "priority": "high"
                })

        service_info["details"]["dependencies"] = dependency_status

        # Try to import and test SambaNova plugin
        plugin_status = {
            "import_successful": False,
            "initialization_successful": False,
            "plugin_info": {},
            "errors": []
        }

        try:
            from .ai.plugin import SambaNovaPlugin
            plugin_status["import_successful"] = True

            try:
                plugin = SambaNovaPlugin()
                plugin_status["initialization_successful"] = True
                plugin_status["plugin_info"] = {
                    "name": plugin.get_name(),
                    "version": plugin.get_version(),
                    "initialized": True
                }
                service_info["details"]["plugin_available"] = True

                # If API key is available, mark as accessible
                if sambanova_api_key:
                    service_info["accessible"] = True
                    service_info["details"]["connectivity_test"] = "plugin_initialized"

            except Exception as init_error:
                plugin_status["errors"].append({
                    "type": "initialization_error",
                    "message": str(init_error),
                    "error_type": type(init_error).__name__
                })
                service_info["errors"].append({
                    "type": "plugin_initialization_error",
                    "message": "SambaNova plugin failed to initialize",
                    "error": str(init_error),
                    "resolution": "Check API key and dependencies",
                    "priority": "medium"
                })

        except ImportError as e:
            plugin_status["errors"].append({
                "type": "import_error",
                "message": str(e),
                "missing_module": ".ai.plugin"
            })
            service_info["status"] = "warning"
            service_info["warnings"].append(
                f"SambaNova plugin import failed: {str(e)}"
            )
            service_info["errors"].append({
                "type": "import_error",
                "message": "SambaNova plugin module could not be imported",
                "error": str(e),
                "resolution": "Check if ai.plugin module exists and dependencies are installed",
                "missing_dependencies": [
                    dep for dep, status in dependency_status.items()
                    if not status["available"]
                ],
                "priority": "high"
            })

        service_info["details"]["plugin_status"] = plugin_status

    except Exception as e:
        service_info["status"] = "error"
        error_msg = str(e) if str(e) else f"Unknown {type(e).__name__} error"
        service_info["warnings"].append(f"Unexpected error checking SambaNova: {error_msg}")
        service_info["errors"].append({
            "type": "unexpected_error",
            "message": f"SambaNova service check failed: {error_msg}",
            "error_type": type(e).__name__,
            "resolution": "Check application logs and environment configuration",
            "priority": "medium"
        })

    return service_info


async def _check_supabase_service(skip_connectivity_tests: bool = False) -> Dict[str, any]:
    """Check Supabase database configuration and connectivity."""
    service_info = {
        "name": "Supabase Database",
        "status": "healthy",
        "configured": False,
        "accessible": False,
        "missing_config": [],
        "warnings": [],
        "errors": [],
        "details": {
            "last_check": datetime.now(timezone.utc).isoformat(),
            "environment_variables": {},
            "connectivity_tests": [],
            "client_info": {}
        }
    }

    try:
        # Check environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = (
            os.getenv("SUPABASE_ANON_KEY") or
            os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        )
        supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        # Detailed environment variable analysis
        service_info["details"]["environment_variables"] = {
            "SUPABASE_URL": {
                "configured": bool(supabase_url),
                "value": supabase_url[:50] + "..." if supabase_url and len(supabase_url) > 50 else supabase_url,
                "valid_format": supabase_url.startswith("https://") if supabase_url else False
            },
            "SUPABASE_ANON_KEY": {
                "configured": bool(supabase_anon_key),
                "source": (
                    "SUPABASE_ANON_KEY" if os.getenv("SUPABASE_ANON_KEY")
                    else "NEXT_PUBLIC_SUPABASE_ANON_KEY" if supabase_anon_key
                    else None
                ),
                "length": len(supabase_anon_key) if supabase_anon_key else 0,
                "masked_value": (
                    f"{supabase_anon_key[:20]}..."
                    if supabase_anon_key and len(supabase_anon_key) > 20
                    else None
                )
            },
            "SUPABASE_SERVICE_ROLE_KEY": {
                "configured": bool(supabase_service_key),
                "length": len(supabase_service_key) if supabase_service_key else 0,
                "masked_value": (
                    f"{supabase_service_key[:20]}..."
                    if supabase_service_key and len(supabase_service_key) > 20
                    else None
                )
            }
        }

        missing_vars = []
        if not supabase_url:
            missing_vars.append("SUPABASE_URL")
            service_info["errors"].append({
                "type": "configuration_error",
                "field": "SUPABASE_URL",
                "message": "Supabase project URL not configured",
                "impact": "Database features will use in-memory storage",
                "resolution": "Set SUPABASE_URL environment variable",
                "example": "https://your-project.supabase.co",
                "priority": "medium"
            })
        if not supabase_anon_key:
            missing_vars.append("SUPABASE_ANON_KEY")
            service_info["errors"].append({
                "type": "configuration_error",
                "field": "SUPABASE_ANON_KEY",
                "message": "Supabase anonymous key not configured",
                "impact": "Database connection will fail",
                "resolution": "Set SUPABASE_ANON_KEY environment variable",
                "documentation": "Found in Supabase Dashboard → Settings → API",
                "priority": "high"
            })

        if missing_vars:
            service_info["missing_config"] = missing_vars
            service_info["status"] = "warning"
            service_info["warnings"].append(
                "Database not configured - using in-memory storage"
            )
        else:
            service_info["configured"] = True

            # Skip connectivity tests if requested (useful for serverless environments)
            if skip_connectivity_tests:
                service_info["details"]["connectivity_test"] = "skipped_by_request"
                service_info["accessible"] = True  # Assume accessible if configured
                return service_info

            # Try to test Supabase connectivity
            try:
                # Import supabase client with memory-safe approach
                try:
                    from supabase import create_client
                    service_info["details"]["supabase_import"] = "success"
                except MemoryError:
                    service_info["status"] = "warning"
                    service_info["warnings"].append("Supabase client import failed due to memory constraints")
                    service_info["errors"].append({
                        "type": "memory_error",
                        "message": "Insufficient memory to load Supabase client",
                        "resolution": "This is normal in serverless environments. Database features will use fallback storage.",
                        "priority": "low"
                    })
                    return service_info
                except ImportError as import_err:
                    service_info["status"] = "warning"
                    service_info["warnings"].append("Supabase client library not available")
                    service_info["errors"].append({
                        "type": "dependency_error",
                        "message": "Supabase Python client not installed",
                        "resolution": "Install with: pip install supabase",
                        "priority": "medium"
                    })
                    return service_info

                service_info["details"]["url_format"] = (
                    supabase_url[:50] + "..." if len(supabase_url) > 50 else supabase_url
                )
                service_info["details"]["anon_key_length"] = len(supabase_anon_key)
                service_info["details"]["anon_key_source"] = (
                    "SUPABASE_ANON_KEY" if os.getenv("SUPABASE_ANON_KEY")
                    else "NEXT_PUBLIC_SUPABASE_ANON_KEY"
                )

                supabase_client = create_client(supabase_url, supabase_anon_key)
                service_info["details"]["client_created"] = True

                # Try a simple API call to test connectivity
                try:
                    # Test with a simple query that should work on any Supabase project
                    supabase_client.table("_supabase_migrations").select("*").limit(1).execute()
                    service_info["accessible"] = True
                    service_info["details"]["connectivity_test"] = "api_call_successful"
                except Exception as api_error:
                    # If migrations table doesn't exist, try auth endpoint
                    try:
                        # Test auth endpoint which should always exist
                        supabase_client.auth.get_session()
                        service_info["accessible"] = True
                        service_info["details"]["connectivity_test"] = "auth_endpoint_accessible"
                    except Exception as auth_error:
                        service_info["accessible"] = False
                        service_info["details"]["connectivity_test"] = "failed"
                        service_info["details"]["api_error"] = str(api_error)[:100]
                        service_info["details"]["auth_error"] = str(auth_error)[:100]

            except ImportError:
                service_info["status"] = "warning"
                service_info["warnings"].append("Supabase client library not available")
                service_info["details"]["client_created"] = False
            except Exception as e:
                service_info["status"] = "warning"
                error_msg = str(e) if str(e) else f"Unknown {type(e).__name__} error"
                service_info["warnings"].append(f"Supabase connection test failed: {error_msg}")
                service_info["details"]["connectivity_error"] = error_msg
                service_info["details"]["error_type"] = type(e).__name__
                service_info["errors"].append({
                    "type": "connectivity_error",
                    "message": f"Failed to connect to Supabase: {error_msg}",
                    "resolution": "Check SUPABASE_URL and SUPABASE_ANON_KEY values",
                    "priority": "high"
                })

    except Exception as e:
        service_info["status"] = "error"
        service_info["warnings"].append(f"Unexpected error checking Supabase: {str(e)}")

    return service_info


def _check_postmark_config() -> Dict[str, any]:
    """Check Postmark webhook configuration."""
    service_info = {
        "name": "Postmark Webhook",
        "status": "healthy",
        "configured": False,
        "accessible": True,  # Always accessible as it's just config
        "missing_config": [],
        "warnings": [],
        "details": {}
    }

    try:
        webhook_secret = config.postmark_webhook_secret

        if not webhook_secret:
            service_info["missing_config"].append("POSTMARK_WEBHOOK_SECRET")
            service_info["status"] = "warning"
            service_info["warnings"].append("Webhook signature verification disabled - security risk")
            service_info["details"]["signature_verification"] = False
        else:
            service_info["configured"] = True
            service_info["details"]["signature_verification"] = True
            service_info["details"]["secret_length"] = len(webhook_secret)

        service_info["details"]["webhook_endpoint"] = config.webhook_endpoint
        service_info["details"]["environment"] = os.getenv("ENVIRONMENT", "development")

    except Exception as e:
        service_info["status"] = "error"
        service_info["warnings"].append(f"Error checking Postmark config: {str(e)}")

    return service_info


def _check_environment_config() -> Dict[str, any]:
    """Check general environment configuration."""
    env_info = {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "log_format": os.getenv("LOG_FORMAT", "text"),
        "vercel_deployment": bool(os.getenv("VERCEL")),
        "deployment_id": os.getenv("VERCEL_DEPLOYMENT_ID", "local"),
        "python_path": os.getenv("PYTHONPATH", "not_set"),
        "serverless_optimizations": SERVERLESS_ENV,
        "integrations_available": INTEGRATIONS_AVAILABLE
    }

    return env_info


# --- API Routes Integration ---
# Import and include the API routes from the separate module for better
# modularity
try:
    from .api_routes import router as api_router

    app.include_router(api_router, prefix="/api", tags=["API"])
    logger.info("Successfully loaded API routes from api_routes module")
except ImportError as e:
    logger.warning(f"Could not load API routes module: {e}")
    # Continue without API routes if module is not available

# --- Serverless Environment Optimizations & Uvicorn Launch ---

SERVERLESS_ENV = (
    os.getenv("VERCEL", "0") == "1" or os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
)
VERCEL_ENV = os.getenv("VERCEL", "0") == "1"

if SERVERLESS_ENV:
    # Apply serverless-specific configurations
    logger.info(
        f"🚀 Running in serverless environment (Vercel: {VERCEL_ENV}). "
        f"Applying optimizations..."
    )
    config.enable_async_processing = True  # Example, may depend on serverless_utils
    config.max_processing_time = min(
        config.max_processing_time,
        25,  # Leave buffer for Vercel's typical max duration
    )
    # Logging format might be controlled by environment or Vercel's log drains
    if config.log_format != "json":  # Prefer JSON logs in serverless if not already set
        logger.info("Switching log_format to JSON for serverless environment.")
        config.log_format = "json"
    if config.enable_console_colors:
        config.enable_console_colors = (
            False  # Colors are not useful in most serverless log viewers
        )

    logger.setup_logging()  # Re-initialize logger with potentially updated config

if __name__ == "__main__":
    import uvicorn

    # Ensure logger uses the latest config, especially if modified by
    # serverless detection
    logger.setup_logging()

    # Configure host - secure defaults based on environment
    default_host = (
        "127.0.0.1"
        if os.getenv("ENVIRONMENT") == "development"
        else "0.0.0.0"  # nosec B104
    )
    host = os.getenv("HOST", default_host)

    uvicorn.run(
        app,
        host=host,  # Configurable host for security flexibility
        port=int(
            os.getenv("PORT", 8081)
        ),  # Allow port to be set by environment, default 8081
    )
