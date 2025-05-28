# Postmark Webhook Handler for Email Processing
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
import hashlib
import hmac
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import logging

# Add src directory to path for imports
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .models import PostmarkWebhookPayload, EmailData, ProcessedEmail, EmailStatus, AttachmentData, EmailAnalysis, UrgencyLevel
from .config import config
from . import storage  # Import module to use same instance as tests
from .extraction import email_extractor
from .logging_system import logger, log_performance

# Import integration capabilities
try:
    from .integrations import integration_registry
    INTEGRATIONS_AVAILABLE = True
except ImportError:
    INTEGRATIONS_AVAILABLE = False
    print("⚠️ Integration module not available - running without plugin support")

# Set up logging
logging.basicConfig(level=config.log_level)
# Note: The comprehensive logging system will handle its own configuration

app = FastAPI(
    title="Inbox Zen Email Processing Webhook",
    description="Receives Postmark inbound webhooks and processes emails",
    version=config.server_version,
    lifespan=config.lifespan_manager  # Add lifespan manager
)

@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Simple health check endpoint to confirm the server is running."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

def verify_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify Postmark webhook signature for security"""
    if not secret:
        logger.warning("No webhook secret configured - skipping signature verification")
        return True
    
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

def extract_email_data(webhook_payload: PostmarkWebhookPayload) -> EmailData:
    """Extract EmailData from Postmark webhook payload"""
    
    # Parse recipient emails
    to_emails = [recipient["Email"] for recipient in webhook_payload.ToFull]
    cc_emails = []
    if webhook_payload.CcFull:
        cc_emails = [recipient["Email"] for recipient in webhook_payload.CcFull]
    
    bcc_emails = []
    if webhook_payload.BccFull:
        bcc_emails = [recipient["Email"] for recipient in webhook_payload.BccFull]
    
    # Parse attachments
    attachments = []
    for attachment in webhook_payload.Attachments:
        attachments.append(AttachmentData(
            name=attachment.get("Name", ""),
            content_type=attachment.get("ContentType", ""),
            size=attachment.get("ContentLength", 0),
            content_id=attachment.get("ContentID")
        ))
    
    # Parse headers
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
        received_at=datetime.fromisoformat(webhook_payload.Date.replace('Z', '+00:00')),
        attachments=attachments,
        headers=headers
    )

@app.post(config.webhook_endpoint)
async def handle_postmark_webhook(
    request: Request,
    x_postmark_signature: Optional[str] = Header(None)
):
    """Handle incoming Postmark inbound webhook"""
    import time
    processing_start_time = time.time()
    
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Verify webhook signature if secret is configured
        if config.postmark_webhook_secret:
            if not x_postmark_signature:
                logger.log_webhook_validation_error("Missing webhook signature", {})
                raise HTTPException(status_code=401, detail="Missing webhook signature")
            
            if not verify_webhook_signature(body, x_postmark_signature, config.postmark_webhook_secret):
                logger.log_webhook_validation_error("Invalid webhook signature", {})
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse JSON payload
        payload_data = json.loads(body.decode('utf-8'))
        webhook_payload = PostmarkWebhookPayload(**payload_data)
        
        # Generate unique processing ID
        processing_id = str(uuid.uuid4())
        
        # Extract email data
        email_data = extract_email_data(webhook_payload)
        
        # Log email reception
        logger.log_email_received(email_data, payload_data)
        
        # Perform content extraction and analysis
        logger.log_extraction_start(email_data)
        extracted_metadata = email_extractor.extract_from_email(email_data)
        
        # Calculate urgency score and level
        urgency_score, urgency_level = email_extractor.calculate_urgency_score(
            extracted_metadata.urgency_indicators
        )
        
        # Determine sentiment
        sentiment_indicators = extracted_metadata.sentiment_indicators
        if len(sentiment_indicators['positive']) > len(sentiment_indicators['negative']):
            sentiment = "positive"
        elif len(sentiment_indicators['negative']) > len(sentiment_indicators['positive']):
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        # Log extraction completion
        logger.log_extraction_complete(email_data, extracted_metadata, urgency_score, sentiment)
        
        # Create email analysis
        email_analysis = EmailAnalysis(
            urgency_score=urgency_score,
            urgency_level=UrgencyLevel(urgency_level),
            sentiment=sentiment,
            confidence=0.8,  # Base confidence for regex-based analysis
            keywords=extracted_metadata.priority_keywords[:20],  # Limit keywords
            action_items=extracted_metadata.action_words[:10],   # Limit action items
            temporal_references=extracted_metadata.temporal_references[:10],
            tags=["extracted", urgency_level, sentiment],
            category="email"  # Default category
        )
        
        # Create processed email entry
        processed_email = ProcessedEmail(
            id=processing_id,
            email_data=email_data,
            analysis=email_analysis,
            status=EmailStatus.ANALYZED,
            processed_at=datetime.now(),
            webhook_payload=payload_data
        )
        
        # Store in global storage
        storage.email_storage[processing_id] = processed_email
        
        # Process through plugins if available
        if INTEGRATIONS_AVAILABLE and integration_registry.plugin_manager.plugins:
            try:
                logger.info(f"Processing email {processing_id} through {len(integration_registry.plugin_manager.plugins)} plugins")
                enhanced_email = await integration_registry.plugin_manager.process_email_through_plugins(processed_email)
                storage.email_storage[processing_id] = enhanced_email
                processed_email = enhanced_email
                logger.info(f"Email {processing_id} enhanced by plugins")
            except Exception as e:
                logger.error(f"Plugin processing failed for email {processing_id}: {e}")
                # Continue with original email if plugin processing fails
        
        # Save to database if configured
        if INTEGRATIONS_AVAILABLE:
            db_interface = integration_registry.get_database("sqlite") or integration_registry.get_database("postgresql")
            if db_interface:
                try:
                    await db_interface.store_email(processed_email)
                    logger.info(f"Email {processing_id} saved to database")
                except Exception as e:
                    logger.error(f"Database storage failed for email {processing_id}: {e}")
        
        # Update stats
        storage.stats.total_processed += 1
        storage.stats.last_processed = datetime.now()
        processing_time = time.time() - processing_start_time
        storage.stats.processing_times.append(processing_time)
        
        # Calculate average urgency score
        if storage.stats.total_processed > 0:
            total_urgency = sum(
                email.analysis.urgency_score for email in storage.email_storage.values() 
                if email.analysis
            )
            storage.stats.avg_urgency_score = total_urgency / len([
                email for email in storage.email_storage.values() if email.analysis
            ])
        
        # Log successful processing
        logger.log_email_processed(processed_email, processing_time)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "processing_id": processing_id,
                "message": f"Email {email_data.message_id} processed successfully"
            }
        )
        
    except json.JSONDecodeError as e:
        logger.log_processing_error(e, {"error_type": "json_decode", "body_length": len(body)})
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    except HTTPException:
        # Re-raise HTTPExceptions (like 401, 404) without modification
        raise
    
    except Exception as e:
        logger.log_processing_error(e, {"processing_id": processing_id if 'processing_id' in locals() else None})
        storage.stats.total_errors += 1
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "server": config.server_name,
        "version": config.server_version,
        "emails_processed": storage.stats.total_processed,
        "errors": storage.stats.total_errors
    }

@app.get("/api/stats")
async def get_system_stats():
    """Get detailed system statistics"""
    logger.log_system_stats(storage.stats)
    
    # Calculate additional metrics
    avg_processing_time = 0
    if storage.stats.processing_times:
        avg_processing_time = sum(storage.stats.processing_times) / len(storage.stats.processing_times)
    
    urgency_distribution = {}
    for email in storage.email_storage.values():
        if email.analysis:
            level = email.analysis.urgency_level
            urgency_distribution[level] = urgency_distribution.get(level, 0) + 1
    
    return {
        "total_processed": storage.stats.total_processed,
        "total_errors": storage.stats.total_errors,
        "avg_urgency_score": round(storage.stats.avg_urgency_score, 2),
        "avg_processing_time_ms": round(avg_processing_time * 1000, 2),
        "last_processed": storage.stats.last_processed,
        "urgency_distribution": urgency_distribution,
        "processing_times_samples": len(storage.stats.processing_times),
        "emails_in_storage": len(storage.email_storage)
    }

@app.get("/api/emails/recent")
async def get_recent_emails(limit: int = 10):
    """Get recent processed emails for debugging"""
    recent_emails = list(storage.email_storage.values())[-limit:]
    return {
        "count": len(recent_emails),
        "emails": [
            {
                "id": email.id,
                "message_id": email.email_data.message_id,
                "from": email.email_data.from_email,
                "subject": email.email_data.subject,
                "received_at": email.email_data.received_at,
                "status": email.status,
                "analysis": email.analysis.model_dump() if email.analysis else None
            }
            for email in recent_emails
        ]
    }

# Enhanced API endpoints for comprehensive email access
@app.get("/api/emails")
async def get_emails(
    skip: int = 0,
    limit: int = 20,
    urgency_level: Optional[str] = None,
    sentiment: Optional[str] = None,
    search: Optional[str] = None
):
    """Get emails with pagination and filtering"""
    emails = list(storage.email_storage.values())
    
    # Apply filters
    if urgency_level:
        emails = [e for e in emails if e.analysis and e.analysis.urgency_level.value == urgency_level]
    
    if sentiment:
        emails = [e for e in emails if e.analysis and e.analysis.sentiment == sentiment]
    
    if search:
        search_lower = search.lower()
        emails = [
            e for e in emails 
            if search_lower in e.email_data.subject.lower() or 
               search_lower in (e.email_data.text_body or '').lower()
        ]
    
    # Sort by received date (newest first)
    emails.sort(key=lambda x: x.email_data.received_at, reverse=True)
    
    # Apply pagination
    total = len(emails)
    paginated_emails = emails[skip:skip + limit]
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "emails": [
            {
                "id": email.id,
                "message_id": email.email_data.message_id,
                "from": email.email_data.from_email,
                "to": email.email_data.to_emails,
                "subject": email.email_data.subject,
                "received_at": email.email_data.received_at,
                "status": email.status.value,
                "analysis": email.analysis.model_dump() if email.analysis else None
            }
            for email in paginated_emails
        ]
    }

@app.get("/api/emails/{email_id}")
async def get_email(email_id: str):
    """Get specific email by ID"""
    if email_id not in storage.email_storage:
        raise HTTPException(status_code=404, detail="Email not found")
    
    email = storage.email_storage[email_id]
    return {
        "id": email.id,
        "email_data": email.email_data.model_dump(),
        "analysis": email.analysis.model_dump() if email.analysis else None,
        "status": email.status.value,
        "processed_at": email.processed_at,
        "webhook_payload": email.webhook_payload
    }

@app.get("/api/search")
async def search_emails(
    q: str,
    limit: int = 10,
    include_content: bool = False
):
    """Advanced email search with query string"""
    query_lower = q.lower()
    results = []
    
    for email in storage.email_storage.values():
        score = 0
        matches = []
        
        # Search in subject
        if query_lower in email.email_data.subject.lower():
            score += 10
            matches.append("subject")
        
        # Search in body
        if email.email_data.text_body and query_lower in email.email_data.text_body.lower():
            score += 5
            matches.append("body")
        
        # Search in keywords
        if email.analysis and any(query_lower in kw.lower() for kw in email.analysis.keywords):
            score += 3
            matches.append("keywords")
        
        # Search in sender
        if query_lower in email.email_data.from_email.lower():
            score += 2
            matches.append("from")
        
        if score > 0:
            result = {
                "id": email.id,
                "message_id": email.email_data.message_id,
                "from": email.email_data.from_email,
                "subject": email.email_data.subject,
                "received_at": email.email_data.received_at,
                "score": score,
                "matches": matches
            }
            
            if email.analysis:
                result["urgency_score"] = email.analysis.urgency_score
                result["urgency_level"] = email.analysis.urgency_level.value
                result["sentiment"] = email.analysis.sentiment
            
            if include_content:
                result["text_body"] = email.email_data.text_body
            
            results.append(result)
    
    # Sort by score (highest first)
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "query": q,
        "total_found": len(results),
        "results": results[:limit]
    }

@app.get("/api/analytics")
async def get_analytics():
    """Get comprehensive analytics about processed emails"""
    if not storage.email_storage:
        return {"message": "No emails processed yet"}
    
    emails_with_analysis = [e for e in storage.email_storage.values() if e.analysis]
    
    if not emails_with_analysis:
        return {"message": "No analyzed emails found"}
    
    # Urgency distribution
    urgency_dist = {"low": 0, "medium": 0, "high": 0}
    sentiment_dist = {"positive": 0, "negative": 0, "neutral": 0}
    urgency_scores = []
    
    for email in emails_with_analysis:
        urgency_dist[email.analysis.urgency_level.value] += 1
        sentiment_dist[email.analysis.sentiment] += 1
        urgency_scores.append(email.analysis.urgency_score)
    
    # Time series data (last 24 hours)
    from datetime import timedelta
    now = datetime.now()
    hourly_counts = {}
    
    for i in range(24):
        hour_start = now - timedelta(hours=i+1)
        hour_end = now - timedelta(hours=i)
        count = sum(
            1 for email in storage.email_storage.values()
            if hour_start <= email.email_data.received_at <= hour_end
        )
        hourly_counts[f"hour_{i}"] = count
    
    return {
        "total_emails": len(storage.email_storage),
        "analyzed_emails": len(emails_with_analysis),
        "urgency_distribution": urgency_dist,
        "sentiment_distribution": sentiment_dist,
        "urgency_stats": {
            "average": sum(urgency_scores) / len(urgency_scores),
            "max": max(urgency_scores),
            "min": min(urgency_scores)
        },
        "processing_stats": {
            "total_processed": storage.stats.total_processed,
            "total_errors": storage.stats.total_errors,
            "avg_processing_time_ms": (
                sum(storage.stats.processing_times) / len(storage.stats.processing_times) * 1000
                if storage.stats.processing_times else 0
            )
        },
        "hourly_distribution": hourly_counts
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
