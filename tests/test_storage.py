"""Unit tests for storage.py - Email Storage System"""

import pytest
from datetime import datetime

from src import storage
from src.models import ProcessedEmail, EmailData, EmailAnalysis, EmailStatus, UrgencyLevel, EmailStats


class TestEmailStorage:
    """Test email storage functionality"""
    
    def setup_method(self):
        """Reset storage before each test"""
        storage.email_storage.clear()
        storage.stats = EmailStats()
    
    def test_storage_initialization(self):
        """Test that storage is initialized correctly"""
        assert isinstance(storage.email_storage, dict)
        assert isinstance(storage.stats, EmailStats)
        assert len(storage.email_storage) == 0
        assert storage.stats.total_processed == 0
    
    def test_store_email(self, sample_email_data, sample_analysis_data):
        """Test storing an email in storage"""
        email_data = EmailData(**sample_email_data)
        analysis = EmailAnalysis(**sample_analysis_data)
        
        processed_email = ProcessedEmail(
            id="storage-test-1",
            email_data=email_data,
            analysis=analysis,
            status=EmailStatus.ANALYZED,
            processed_at=datetime.now()
        )
        
        # Store email
        storage.email_storage["storage-test-1"] = processed_email
        
        # Verify storage
        assert len(storage.email_storage) == 1
        assert "storage-test-1" in storage.email_storage
        
        stored_email = storage.email_storage["storage-test-1"]
        assert stored_email.id == "storage-test-1"
        assert stored_email.email_data.message_id == "test-message-123@example.com"
        assert stored_email.analysis.urgency_score == 75
    
    def test_store_multiple_emails(self, sample_email_data):
        """Test storing multiple emails"""
        # Create multiple emails
        emails = []
        for i in range(3):
            email_data = EmailData(**{
                **sample_email_data,
                "message_id": f"test-{i}",
                "subject": f"Test Email {i}"
            })
            
            processed_email = ProcessedEmail(
                id=f"storage-test-{i}",
                email_data=email_data,
                status=EmailStatus.RECEIVED
            )
            emails.append(processed_email)
        
        # Store all emails
        for email in emails:
            storage.email_storage[email.id] = email
        
        # Verify storage
        assert len(storage.email_storage) == 3
        
        for i in range(3):
            assert f"storage-test-{i}" in storage.email_storage
            stored_email = storage.email_storage[f"storage-test-{i}"]
            assert stored_email.email_data.subject == f"Test Email {i}"
    
    def test_retrieve_email(self, sample_email_data):
        """Test retrieving a specific email"""
        email_data = EmailData(**sample_email_data)
        processed_email = ProcessedEmail(
            id="retrieve-test",
            email_data=email_data
        )
        
        # Store email
        storage.email_storage["retrieve-test"] = processed_email
        
        # Retrieve email
        retrieved = storage.email_storage.get("retrieve-test")
        
        assert retrieved is not None
        assert retrieved.id == "retrieve-test"
        assert retrieved.email_data.message_id == "test-message-123@example.com"
        
        # Test retrieving non-existent email
        non_existent = storage.email_storage.get("non-existent")
        assert non_existent is None
    
    def test_update_email(self, sample_email_data, sample_analysis_data):
        """Test updating an existing email"""
        email_data = EmailData(**sample_email_data)
        
        # Store initial email without analysis
        processed_email = ProcessedEmail(
            id="update-test",
            email_data=email_data,
            status=EmailStatus.RECEIVED
        )
        storage.email_storage["update-test"] = processed_email
        
        # Update with analysis
        analysis = EmailAnalysis(**sample_analysis_data)
        updated_email = ProcessedEmail(
            id="update-test",
            email_data=email_data,
            analysis=analysis,
            status=EmailStatus.ANALYZED,
            processed_at=datetime.now()
        )
        storage.email_storage["update-test"] = updated_email
        
        # Verify update
        stored_email = storage.email_storage["update-test"]
        assert stored_email.status == EmailStatus.ANALYZED
        assert stored_email.analysis is not None
        assert stored_email.analysis.urgency_score == 75
        assert stored_email.processed_at is not None
    
    def test_delete_email(self, sample_email_data):
        """Test deleting an email from storage"""
        email_data = EmailData(**sample_email_data)
        processed_email = ProcessedEmail(
            id="delete-test",
            email_data=email_data
        )
        
        # Store email
        storage.email_storage["delete-test"] = processed_email
        assert len(storage.email_storage) == 1
        
        # Delete email
        del storage.email_storage["delete-test"]
        
        # Verify deletion
        assert len(storage.email_storage) == 0
        assert "delete-test" not in storage.email_storage
    
    def test_clear_storage(self, sample_email_data):
        """Test clearing all emails from storage"""
        # Store multiple emails
        for i in range(5):
            email_data = EmailData(**{
                **sample_email_data,
                "message_id": f"clear-test-{i}"
            })
            processed_email = ProcessedEmail(
                id=f"clear-test-{i}",
                email_data=email_data
            )
            storage.email_storage[f"clear-test-{i}"] = processed_email
        
        assert len(storage.email_storage) == 5
        
        # Clear storage
        storage.email_storage.clear()
        
        # Verify cleared
        assert len(storage.email_storage) == 0
    
    def test_storage_iteration(self, sample_email_data):
        """Test iterating through storage"""
        # Store multiple emails
        email_ids = []
        for i in range(3):
            email_id = f"iteration-test-{i}"
            email_data = EmailData(**{
                **sample_email_data,
                "message_id": f"iter-{i}"
            })
            processed_email = ProcessedEmail(
                id=email_id,
                email_data=email_data
            )
            storage.email_storage[email_id] = processed_email
            email_ids.append(email_id)
        
        # Test iteration over keys
        stored_keys = list(storage.email_storage.keys())
        assert len(stored_keys) == 3
        for email_id in email_ids:
            assert email_id in stored_keys
        
        # Test iteration over values
        stored_emails = list(storage.email_storage.values())
        assert len(stored_emails) == 3
        for email in stored_emails:
            assert email.id in email_ids
        
        # Test iteration over items
        stored_items = list(storage.email_storage.items())
        assert len(stored_items) == 3
        for email_id, email in stored_items:
            assert email_id == email.id
            assert email_id in email_ids


class TestEmailStats:
    """Test email statistics functionality"""
    
    def setup_method(self):
        """Reset stats before each test"""
        storage.stats = EmailStats()
    
    def test_stats_initialization(self):
        """Test that stats are initialized correctly"""
        assert storage.stats.total_processed == 0
        assert storage.stats.total_errors == 0
        assert storage.stats.avg_urgency_score == 0.0
        assert storage.stats.urgency_distribution == {}
        assert storage.stats.last_processed is None
        assert storage.stats.processing_times == []
    
    def test_update_stats(self):
        """Test updating statistics"""
        # Update processed count
        storage.stats.total_processed = 5
        assert storage.stats.total_processed == 5
        
        # Update error count
        storage.stats.total_errors = 1
        assert storage.stats.total_errors == 1
        
        # Update average urgency score
        storage.stats.avg_urgency_score = 45.5
        assert storage.stats.avg_urgency_score == 45.5
        
        # Update last processed time
        now = datetime.now()
        storage.stats.last_processed = now
        assert storage.stats.last_processed == now
    
    def test_stats_urgency_distribution(self):
        """Test urgency distribution tracking"""
        # Initialize distribution
        storage.stats.urgency_distribution = {
            UrgencyLevel.LOW: 3,
            UrgencyLevel.MEDIUM: 2,
            UrgencyLevel.HIGH: 1
        }
        
        assert storage.stats.urgency_distribution[UrgencyLevel.LOW] == 3
        assert storage.stats.urgency_distribution[UrgencyLevel.MEDIUM] == 2
        assert storage.stats.urgency_distribution[UrgencyLevel.HIGH] == 1
        
        # Update distribution
        storage.stats.urgency_distribution[UrgencyLevel.HIGH] += 1
        assert storage.stats.urgency_distribution[UrgencyLevel.HIGH] == 2
    
    def test_stats_processing_times(self):
        """Test processing times tracking"""
        # Add processing times
        processing_times = [0.1, 0.2, 0.15, 0.3, 0.25]
        storage.stats.processing_times = processing_times
        
        assert len(storage.stats.processing_times) == 5
        assert storage.stats.processing_times == processing_times
        
        # Add new processing time
        storage.stats.processing_times.append(0.18)
        assert len(storage.stats.processing_times) == 6
        assert storage.stats.processing_times[-1] == 0.18
        
        # Calculate average processing time
        avg_time = sum(storage.stats.processing_times) / len(storage.stats.processing_times)
        assert avg_time == pytest.approx(0.196, rel=1e-2)
    
    def test_stats_serialization(self):
        """Test that stats can be serialized"""
        # Set up stats with data
        storage.stats.total_processed = 10
        storage.stats.total_errors = 2
        storage.stats.avg_urgency_score = 55.5
        storage.stats.urgency_distribution = {
            UrgencyLevel.LOW: 4,
            UrgencyLevel.MEDIUM: 4,
            UrgencyLevel.HIGH: 2
        }
        storage.stats.last_processed = datetime.now()
        storage.stats.processing_times = [0.1, 0.2, 0.15]
        
        # Serialize
        stats_dict = storage.stats.model_dump()
        
        # Verify serialization
        assert stats_dict["total_processed"] == 10
        assert stats_dict["total_errors"] == 2
        assert stats_dict["avg_urgency_score"] == 55.5
        assert "urgency_distribution" in stats_dict
        assert "last_processed" in stats_dict
        assert "processing_times" in stats_dict


class TestStorageIntegration:
    """Test storage integration scenarios"""
    
    def setup_method(self):
        """Reset storage before each test"""
        storage.email_storage.clear()
        storage.stats = EmailStats()
    
    def test_storage_with_stats_update(self, sample_email_data, sample_analysis_data):
        """Test storing emails and updating stats together"""
        # Store first email
        email_data1 = EmailData(**sample_email_data)
        analysis1 = EmailAnalysis(**sample_analysis_data)
        
        processed_email1 = ProcessedEmail(
            id="integration-1",
            email_data=email_data1,
            analysis=analysis1,
            status=EmailStatus.ANALYZED,
            processed_at=datetime.now()
        )
        
        storage.email_storage["integration-1"] = processed_email1
        storage.stats.total_processed += 1
        storage.stats.last_processed = datetime.now()
        storage.stats.processing_times.append(0.15)
        
        # Store second email with different urgency
        analysis2_data = {**sample_analysis_data, "urgency_score": 30, "urgency_level": UrgencyLevel.LOW}
        analysis2 = EmailAnalysis(**analysis2_data)
        
        processed_email2 = ProcessedEmail(
            id="integration-2",
            email_data=EmailData(**{**sample_email_data, "message_id": "test-456"}),
            analysis=analysis2,
            status=EmailStatus.ANALYZED,
            processed_at=datetime.now()
        )
        
        storage.email_storage["integration-2"] = processed_email2
        storage.stats.total_processed += 1
        storage.stats.processing_times.append(0.22)
        
        # Update urgency distribution
        storage.stats.urgency_distribution = {
            UrgencyLevel.HIGH: 1,
            UrgencyLevel.LOW: 1
        }
        
        # Calculate average urgency score
        total_urgency = sum(
            email.analysis.urgency_score for email in storage.email_storage.values()
            if email.analysis
        )
        storage.stats.avg_urgency_score = total_urgency / len(storage.email_storage)
        
        # Verify integration
        assert len(storage.email_storage) == 2
        assert storage.stats.total_processed == 2
        assert storage.stats.avg_urgency_score == 52.5  # (75 + 30) / 2
        assert storage.stats.urgency_distribution[UrgencyLevel.HIGH] == 1
        assert storage.stats.urgency_distribution[UrgencyLevel.LOW] == 1
        assert len(storage.stats.processing_times) == 2
    
    def test_concurrent_access_simulation(self, sample_email_data):
        """Test simulated concurrent access to storage"""
        import threading
        import time
        
        def store_email(email_id, delay=0):
            """Function to store an email with optional delay"""
            if delay:
                time.sleep(delay)
            
            email_data = EmailData(**{
                **sample_email_data,
                "message_id": f"concurrent-{email_id}"
            })
            processed_email = ProcessedEmail(
                id=f"concurrent-{email_id}",
                email_data=email_data
            )
            storage.email_storage[f"concurrent-{email_id}"] = processed_email
        
        # Simulate concurrent storage operations
        threads = []
        for i in range(5):
            thread = threading.Thread(target=store_email, args=(i, 0.01))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all emails were stored
        assert len(storage.email_storage) == 5
        for i in range(5):
            assert f"concurrent-{i}" in storage.email_storage
    
    def test_storage_memory_usage(self, sample_email_data):
        """Test storage behavior with many emails (memory usage)"""
        import sys
        
        # Store a moderate number of emails to test memory behavior
        num_emails = 100
        
        for i in range(num_emails):
            email_data = EmailData(**{
                **sample_email_data,
                "message_id": f"memory-test-{i}",
                "text_body": f"This is email number {i} with some content to test memory usage."
            })
            processed_email = ProcessedEmail(
                id=f"memory-test-{i}",
                email_data=email_data
            )
            storage.email_storage[f"memory-test-{i}"] = processed_email
        
        # Verify all emails are stored
        assert len(storage.email_storage) == num_emails
        
        # Check memory size (rough estimate)
        storage_size = sys.getsizeof(storage.email_storage)
        assert storage_size > 0  # Basic sanity check
        
        # Clear half the emails
        for i in range(0, num_emails, 2):
            del storage.email_storage[f"memory-test-{i}"]
        
        # Verify partial cleanup
        assert len(storage.email_storage) == num_emails // 2
    
    def test_storage_persistence_simulation(self, sample_email_data):
        """Test simulated persistence behavior"""
        # Store emails
        emails_data = []
        for i in range(3):
            email_data = EmailData(**{
                **sample_email_data,
                "message_id": f"persist-{i}"
            })
            processed_email = ProcessedEmail(
                id=f"persist-{i}",
                email_data=email_data
            )
            storage.email_storage[f"persist-{i}"] = processed_email
            emails_data.append(processed_email.model_dump())
        
        # Simulate saving to persistence layer (export data)
        exported_data = {
            "emails": [email.model_dump() for email in storage.email_storage.values()],
            "stats": storage.stats.model_dump()
        }
        
        # Verify export
        assert len(exported_data["emails"]) == 3
        assert exported_data["stats"]["total_processed"] == 0  # Default value
        
        # Simulate clearing storage (restart scenario)
        storage.email_storage.clear()
        storage.stats = EmailStats()
        
        # Simulate loading from persistence layer (import data)
        for email_data in exported_data["emails"]:
            email = ProcessedEmail(**email_data)
            storage.email_storage[email.id] = email
        
        storage.stats = EmailStats(**exported_data["stats"])
        
        # Verify restoration
        assert len(storage.email_storage) == 3
        for i in range(3):
            assert f"persist-{i}" in storage.email_storage
