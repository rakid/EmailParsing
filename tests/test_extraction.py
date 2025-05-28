"""
Unit tests for email extraction and analysis functionality
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from extraction import EmailExtractor, ExtractedMetadata
from models import EmailData


class TestEmailExtractor:
    """Test the main EmailExtractor class"""
    
    def test_extractor_initialization(self):
        """Test that EmailExtractor initializes correctly"""
        extractor = EmailExtractor()
        assert hasattr(extractor, 'compiled_patterns')
        assert isinstance(extractor.compiled_patterns, dict)
    
    def test_extract_from_email_basic(self, sample_email_data):
        """Test basic metadata extraction from EmailData"""
        extractor = EmailExtractor()
        
        email = EmailData(
            message_id=sample_email_data["message_id"],
            from_email=sample_email_data["from_email"],
            to_emails=sample_email_data["to_emails"],
            subject=sample_email_data["subject"],
            text_body=sample_email_data["text_body"],
            html_body=sample_email_data.get("html_body", ""),
            received_at=sample_email_data["received_at"],
            attachments=sample_email_data.get("attachments", [])
        )
        
        metadata = extractor.extract_from_email(email)
        
        assert isinstance(metadata, ExtractedMetadata)
        assert isinstance(metadata.urgency_indicators, dict)
        assert isinstance(metadata.temporal_references, list)
        assert isinstance(metadata.contact_info, dict)
        assert isinstance(metadata.action_words, list)
        assert isinstance(metadata.sentiment_indicators, dict)
        assert isinstance(metadata.priority_keywords, list)
        assert isinstance(metadata.links, list)
    
    def test_extract_high_urgency_indicators(self, sample_email_data):
        """Test that urgent emails are properly identified"""
        extractor = EmailExtractor()
        
        # Create email with urgent content
        email = EmailData(
            message_id="urgent-test",
            from_email="boss@company.com",
            to_emails=["employee@company.com"],
            subject="URGENT: Critical deadline today!",
            text_body="This is urgent and needs immediate attention ASAP!",
            html_body="",
            received_at=datetime.now(),
            attachments=[]
        )
        
        metadata = extractor.extract_from_email(email)
        
        # Should detect high urgency indicators
        assert len(metadata.urgency_indicators['high']) > 0
        assert any('urgent' in indicator for indicator in metadata.urgency_indicators['high'])
    
    def test_extract_low_urgency_indicators(self, sample_low_urgency_email):
        """Test that low urgency emails are properly identified"""
        extractor = EmailExtractor()
        
        email = EmailData(
            message_id=sample_low_urgency_email["message_id"],
            from_email=sample_low_urgency_email["from_email"],
            to_emails=sample_low_urgency_email["to_emails"],
            subject=sample_low_urgency_email["subject"],
            text_body=sample_low_urgency_email["text_body"],
            html_body="",
            received_at=sample_low_urgency_email["received_at"],
            attachments=sample_low_urgency_email.get("attachments", [])
        )
        
        metadata = extractor.extract_from_email(email)
        
        # Should have fewer or no high urgency indicators
        assert len(metadata.urgency_indicators['high']) == 0 or len(metadata.urgency_indicators['low']) > 0
    
    def test_clean_text_function(self):
        """Test text cleaning functionality"""
        extractor = EmailExtractor()
        
        html_text = "<p>This is <strong>HTML</strong> content with &amp; entities.</p>"
        cleaned = extractor.clean_text(html_text)
        
        assert "<" not in cleaned
        assert ">" not in cleaned
        assert "&amp;" not in cleaned
        assert "HTML" in cleaned
    
    def test_extract_temporal_references(self):
        """Test temporal reference extraction"""
        extractor = EmailExtractor()
        
        text_with_time = "The meeting is tomorrow at 2 PM. Due date is next week."
        references = extractor.extract_temporal_references(text_with_time)
        
        assert len(references) > 0
        assert any('tomorrow' in ref for ref in references)
    
    def test_extract_contact_info(self):
        """Test contact information extraction"""
        extractor = EmailExtractor()
        
        text_with_contacts = "Call me at 555-123-4567 or email john@example.com. Visit https://example.com"
        contact_info = extractor.extract_contact_info(text_with_contacts)
        
        assert 'phone' in contact_info
        assert 'email' in contact_info
        assert 'url' in contact_info
        assert len(contact_info['phone']) > 0
        assert len(contact_info['email']) > 0
        assert len(contact_info['url']) > 0
    
    def test_extract_action_words(self):
        """Test action word extraction"""
        extractor = EmailExtractor()
        
        text_with_actions = "Please review the document and send me your feedback. Call the client."
        actions = extractor.extract_action_words(text_with_actions)
        
        assert len(actions) > 0
        assert any('review' in action for action in actions)
    
    def test_extract_sentiment_indicators(self):
        """Test sentiment indicator extraction"""
        extractor = EmailExtractor()
        
        positive_text = "Thank you for the excellent work! Great job on this project."
        sentiment = extractor.extract_sentiment_indicators(positive_text)
        
        assert 'positive' in sentiment
        assert 'negative' in sentiment
        assert 'neutral' in sentiment
        assert len(sentiment['positive']) > 0
    
    def test_calculate_urgency_score(self):
        """Test urgency score calculation"""
        extractor = EmailExtractor()
        
        # High urgency indicators
        high_indicators = {
            'high': ['urgent', 'asap', 'critical'],
            'medium': ['please'],
            'low': []
        }
        
        score, level = extractor.calculate_urgency_score(high_indicators)
        
        assert isinstance(score, int)
        assert level in ['low', 'medium', 'high']
        assert score >= 0 and score <= 100
        assert level == 'high'  # Should be high with multiple high indicators


class TestEmailExtractionIntegration:
    """Test integration scenarios for email extraction"""
    
    def test_empty_email_handling(self):
        """Test extraction with empty email content"""
        extractor = EmailExtractor()
        
        email = EmailData(
            message_id="empty-test",
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            subject="",
            text_body="",
            html_body="",
            received_at=datetime.now(),
            attachments=[]
        )
        
        metadata = extractor.extract_from_email(email)
        
        # Should handle empty content gracefully
        assert isinstance(metadata, ExtractedMetadata)
        assert isinstance(metadata.urgency_indicators, dict)
        assert isinstance(metadata.temporal_references, list)
    
    def test_special_characters_handling(self):
        """Test extraction with special characters and emojis"""
        extractor = EmailExtractor()
        
        email = EmailData(
            message_id="special-test",
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            subject="Spéciål Chåràctërs 🎉",
            text_body="Émojis 🚀💡 and spëciål chäräctërs ñoño",
            html_body="",
            received_at=datetime.now(),
            attachments=[]
        )
        
        metadata = extractor.extract_from_email(email)
        
        # Should handle special characters gracefully
        assert isinstance(metadata, ExtractedMetadata)
    
    def test_very_long_content(self):
        """Test extraction with very long content"""
        extractor = EmailExtractor()
        
        long_content = "This is a very long email content. " * 1000
        
        email = EmailData(
            message_id="long-test",
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            subject="Long Content Test",
            text_body=long_content,
            html_body="",
            received_at=datetime.now(),
            attachments=[]
        )
        
        metadata = extractor.extract_from_email(email)
        
        # Should handle long content without errors
        assert isinstance(metadata, ExtractedMetadata)
        assert len(metadata.priority_keywords) > 0  # Should still extract something


class TestRegexPatterns:
    """Test regex pattern matching accuracy"""
    
    def test_email_pattern_matching(self):
        """Test email address pattern matching"""
        extractor = EmailExtractor()
        
        test_texts = [
            "Contact me at john.doe@example.com for more info",
            "Send it to support@company.co.uk and admin@site.org",
        ]
        
        for text in test_texts:
            contact_info = extractor.extract_contact_info(text)
            assert len(contact_info['email']) > 0
    
    def test_phone_pattern_matching(self):
        """Test phone number pattern matching"""
        extractor = EmailExtractor()
        
        text_with_phones = "Call me at 555-123-4567 or (555) 987-6543"
        contact_info = extractor.extract_contact_info(text_with_phones)
        
        assert len(contact_info['phone']) > 0
    
    def test_url_pattern_matching(self):
        """Test URL pattern matching"""
        extractor = EmailExtractor()
        
        text_with_urls = "Visit https://example.com or www.site.org"
        contact_info = extractor.extract_contact_info(text_with_urls)
        
        assert len(contact_info['url']) > 0


@pytest.mark.edge_case
class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_none_values_handling(self):
        """Test extraction with None values"""
        extractor = EmailExtractor()
        
        email = EmailData(
            message_id="none-test",
            from_email="test@example.com",
            to_emails=["recipient@example.com"],
            subject="Test",
            text_body=None,  # None value
            html_body=None,  # None value
            received_at=datetime.now(),
            attachments=[]
        )
        
        # Should handle None values gracefully without throwing errors
        metadata = extractor.extract_from_email(email)
        assert isinstance(metadata, ExtractedMetadata)
    
    def test_malformed_content_handling(self):
        """Test extraction with malformed content"""
        extractor = EmailExtractor()
        
        # Test with various malformed inputs
        malformed_inputs = [
            "",  # Empty string
            "   ",  # Whitespace only
            "\n\n\n",  # Newlines only
            "a" * 10000,  # Very long single word
        ]
        
        for content in malformed_inputs:
            references = extractor.extract_temporal_references(content)
            contact_info = extractor.extract_contact_info(content)
            actions = extractor.extract_action_words(content)
            
            # Should return valid structures even with malformed input
            assert isinstance(references, list)
            assert isinstance(contact_info, dict)
            assert isinstance(actions, list)
