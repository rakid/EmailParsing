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

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

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
    from .integrations import integration_registry

    INTEGRATIONS_AVAILABLE = True
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

# --- Webhook Utility Functions ---


def verify_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify Postmark webhook signature for security."""
    if not secret:
        logger.warning(
            "No webhook secret configured - skipping signature verification."
        )
        return True

    expected_signature = hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256
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

    return EmailData(
        message_id=webhook_payload.MessageID,
        from_email=webhook_payload.From,
        to_emails=to_emails,
        cc_emails=cc_emails,
        bcc_emails=bcc_emails,
        subject=webhook_payload.Subject,
        text_body=webhook_payload.TextBody,
        html_body=webhook_payload.HtmlBody,
        received_at=datetime.fromisoformat(webhook_payload.Date.replace("Z", "+00:00")),
        attachments=attachments,
        headers=headers,
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

    # Attempt to get either sqlite or postgresql database interface
    db_interface = integration_registry.get_database(
        "sqlite"
    ) or integration_registry.get_database("postgresql")

    if db_interface:
        try:
            await db_interface.store_email(processed_email)
            logger.info(
                f"Email {processing_id} saved to database via {
                    db_interface.__class__.__name__}"
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

        storage.email_storage[processing_id] = processed_email

        # Enhance email with plugins
        processed_email = await _process_through_plugins(processed_email, processing_id)
        storage.email_storage[processing_id] = (
            processed_email  # Re-store if plugins modified it
        )

        await _save_to_database(processed_email, processing_id)

        processing_time_taken = time.time() - processing_start_time
        _update_stats(processing_time_taken)
        logger.log_email_processed(processed_email, processing_time_taken)

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
        "errors_logged": storage.stats.total_errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


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
