# API Routes Module for Email Processing Service
"""
This module contains all API routes that were previously planned to be in webhook.py.
These routes provide REST API access to email data, analytics, and system statistics.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from . import storage
from .logging_system import logger

# Create APIRouter instance
router = APIRouter()


@router.get("/stats")
async def get_system_stats():
    """Get comprehensive system processing statistics."""
    try:
        avg_processing_time_ms = 0
        processing_times_samples = len(storage.stats.processing_times)

        if storage.stats.processing_times:
            avg_processing_time_ms = (
                sum(storage.stats.processing_times)
                / len(storage.stats.processing_times)
            ) * 1000  # Convert to milliseconds

        return {
            "total_processed": storage.stats.total_processed,
            "total_errors": storage.stats.total_errors,
            "avg_urgency_score": storage.stats.avg_urgency_score,
            "avg_processing_time_ms": avg_processing_time_ms,
            "processing_times_samples": processing_times_samples,
            "last_processed": (
                storage.stats.last_processed.isoformat()
                if storage.stats.last_processed
                else None
            ),
            "uptime_start": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error retrieving system stats: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve system statistics"
        )


@router.get("/emails/recent")
async def get_recent_emails(limit: int = Query(10, ge=1, le=100)):
    """Get recently processed emails."""
    try:
        emails = list(storage.email_storage.values())
        # Sort by processed_at timestamp, most recent first
        emails.sort(
            key=lambda x: x.processed_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        # Apply limit
        recent_emails = emails[:limit]

        return {
            "count": len(recent_emails),
            "emails": [
                {
                    "id": email.id,
                    "subject": email.email_data.subject,
                    "from": email.email_data.from_email,
                    "received_at": email.email_data.received_at.isoformat(),
                    "processed_at": (
                        email.processed_at.isoformat() if email.processed_at else None
                    ),
                    "urgency_level": (
                        email.analysis.urgency_level.value
                        if email.analysis
                        else "unknown"
                    ),
                    "urgency_score": (
                        email.analysis.urgency_score if email.analysis else 0
                    ),
                    "sentiment": (
                        email.analysis.sentiment if email.analysis else "neutral"
                    ),
                    "status": (
                        email.status.value
                        if hasattr(email.status, "value")
                        else str(email.status)
                    ),
                }
                for email in recent_emails
            ],
        }
    except Exception as e:
        logger.error(f"Error retrieving recent emails: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent emails")


@router.get("/emails")
async def get_emails(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    urgency_level: Optional[str] = Query(None, pattern="^(low|medium|high)$"),
    sentiment: Optional[str] = Query(None, pattern="^(positive|neutral|negative)$"),
    search: Optional[str] = Query(None, min_length=1),
):
    """Get emails with pagination and filtering options."""
    try:
        emails = list(storage.email_storage.values())

        # Apply filters
        if urgency_level:
            emails = [
                email
                for email in emails
                if email.analysis
                and email.analysis.urgency_level.value == urgency_level
            ]

        if sentiment:
            emails = [
                email
                for email in emails
                if email.analysis and email.analysis.sentiment == sentiment
            ]

        if search:
            search_lower = search.lower()
            emails = [
                email
                for email in emails
                if (
                    search_lower in email.email_data.subject.lower()
                    or search_lower in email.email_data.text_body.lower()
                    or search_lower in email.email_data.from_email.lower()
                )
            ]

        # Sort by processed_at timestamp, most recent first
        emails.sort(
            key=lambda x: x.processed_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        # Apply pagination
        total = len(emails)
        paginated_emails = emails[skip : skip + limit]

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "emails": [
                {
                    "id": email.id,
                    "subject": email.email_data.subject,
                    "from": email.email_data.from_email,
                    "to": email.email_data.to_emails,
                    "received_at": email.email_data.received_at.isoformat(),
                    "processed_at": (
                        email.processed_at.isoformat() if email.processed_at else None
                    ),
                    "urgency_level": (
                        email.analysis.urgency_level.value
                        if email.analysis
                        else "unknown"
                    ),
                    "urgency_score": (
                        email.analysis.urgency_score if email.analysis else 0
                    ),
                    "sentiment": (
                        email.analysis.sentiment if email.analysis else "neutral"
                    ),
                    "status": (
                        email.status.value
                        if hasattr(email.status, "value")
                        else str(email.status)
                    ),
                    "keywords": email.analysis.keywords if email.analysis else [],
                    "action_items": (
                        email.analysis.action_items if email.analysis else []
                    ),
                }
                for email in paginated_emails
            ],
        }
    except Exception as e:
        logger.error(f"Error retrieving emails: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve emails")


@router.get("/emails/{email_id}")
async def get_specific_email(email_id: str):
    """Get a specific email by ID."""
    try:
        if email_id not in storage.email_storage:
            raise HTTPException(status_code=404, detail="Email not found")

        email = storage.email_storage[email_id]

        return {
            "id": email.id,
            "email_data": {
                "message_id": email.email_data.message_id,
                "from_email": email.email_data.from_email,
                "to_emails": email.email_data.to_emails,
                "cc_emails": email.email_data.cc_emails,
                "bcc_emails": email.email_data.bcc_emails,
                "subject": email.email_data.subject,
                "text_body": email.email_data.text_body,
                "html_body": email.email_data.html_body,
                "received_at": email.email_data.received_at.isoformat(),
                "attachments": (
                    [
                        {
                            "name": att.name,
                            "content_type": att.content_type,
                            "size": att.size,
                            "content_id": att.content_id,
                        }
                        for att in email.email_data.attachments
                    ]
                    if email.email_data.attachments
                    else []
                ),
                "headers": email.email_data.headers,
            },
            "analysis": (
                {
                    "urgency_score": email.analysis.urgency_score,
                    "urgency_level": email.analysis.urgency_level.value,
                    "sentiment": email.analysis.sentiment,
                    "confidence": email.analysis.confidence,
                    "keywords": email.analysis.keywords,
                    "action_items": email.analysis.action_items,
                    "temporal_references": email.analysis.temporal_references,
                    "tags": email.analysis.tags,
                    "category": email.analysis.category,
                }
                if email.analysis
                else None
            ),
            "status": (
                email.status.value
                if hasattr(email.status, "value")
                else str(email.status)
            ),
            "processed_at": (
                email.processed_at.isoformat() if email.processed_at else None
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving email {email_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve email")


@router.get("/search")
async def search_emails(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=100),
):
    """Search emails by content, subject, or sender."""
    try:
        query_lower = q.lower()
        emails = list(storage.email_storage.values())

        # Search in various fields
        matching_emails = []
        for email in emails:
            if (
                query_lower in email.email_data.subject.lower()
                or query_lower in email.email_data.text_body.lower()
                or query_lower in email.email_data.from_email.lower()
                or any(
                    query_lower in to_email.lower()
                    for to_email in email.email_data.to_emails
                )
                or (
                    email.analysis
                    and any(
                        query_lower in keyword.lower()
                        for keyword in email.analysis.keywords
                    )
                )
            ):
                matching_emails.append(email)

        # Sort by relevance (could be improved with scoring)
        matching_emails.sort(
            key=lambda x: x.processed_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        # Apply limit
        limited_results = matching_emails[:limit]

        return {
            "query": q,
            "total_found": len(matching_emails),
            "returned": len(limited_results),
            "results": [
                {
                    "id": email.id,
                    "subject": email.email_data.subject,
                    "from": email.email_data.from_email,
                    "received_at": email.email_data.received_at.isoformat(),
                    "urgency_level": (
                        email.analysis.urgency_level.value
                        if email.analysis
                        else "unknown"
                    ),
                    "sentiment": (
                        email.analysis.sentiment if email.analysis else "neutral"
                    ),
                    "keywords": email.analysis.keywords if email.analysis else [],
                }
                for email in limited_results
            ],
        }
    except Exception as e:
        logger.error(f"Error searching emails with query '{q}': {e}")
        raise HTTPException(status_code=500, detail="Failed to search emails")


@router.get("/analytics")
async def get_analytics():
    """Get comprehensive email analytics and insights."""
    try:
        emails = list(storage.email_storage.values())
        emails_with_analysis = [email for email in emails if email.analysis]

        if not emails_with_analysis:
            return {
                "message": "No emails processed yet",
                "total_emails": 0,
                "analyzed_emails": 0,
            }

        # Calculate urgency distribution
        urgency_distribution = {"low": 0, "medium": 0, "high": 0}
        for email in emails_with_analysis:
            urgency_level = email.analysis.urgency_level.value
            if urgency_level in urgency_distribution:
                urgency_distribution[urgency_level] += 1

        # Calculate sentiment distribution
        sentiment_distribution = {"positive": 0, "neutral": 0, "negative": 0}
        for email in emails_with_analysis:
            sentiment = email.analysis.sentiment
            if sentiment in sentiment_distribution:
                sentiment_distribution[sentiment] += 1

        # Calculate urgency statistics
        urgency_scores = [
            email.analysis.urgency_score for email in emails_with_analysis
        ]
        urgency_stats = {
            "average": (
                sum(urgency_scores) / len(urgency_scores) if urgency_scores else 0
            ),
            "min": min(urgency_scores) if urgency_scores else 0,
            "max": max(urgency_scores) if urgency_scores else 0,
        }

        # Calculate hourly distribution (simplified - just by hour of day)
        hourly_distribution = {}
        for email in emails:
            if email.email_data.received_at:
                hour = email.email_data.received_at.hour
                hourly_distribution[str(hour)] = (
                    hourly_distribution.get(str(hour), 0) + 1
                )

        # Processing statistics
        processing_stats = {
            "total_processed": storage.stats.total_processed,
            "total_errors": storage.stats.total_errors,
            "avg_processing_time": (
                sum(storage.stats.processing_times)
                / len(storage.stats.processing_times)
                if storage.stats.processing_times
                else 0
            ),
            "processing_rate_success": (
                (
                    storage.stats.total_processed
                    / (storage.stats.total_processed + storage.stats.total_errors)
                )
                if (storage.stats.total_processed + storage.stats.total_errors) > 0
                else 1.0
            ),
        }

        return {
            "total_emails": len(emails),
            "analyzed_emails": len(emails_with_analysis),
            "urgency_distribution": urgency_distribution,
            "sentiment_distribution": sentiment_distribution,
            "urgency_stats": urgency_stats,
            "processing_stats": processing_stats,
            "hourly_distribution": hourly_distribution,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error generating analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate analytics")
