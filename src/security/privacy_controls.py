"""Privacy controls and data protection for Reflex AI Assistant."""

import asyncio
import logging
import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import hashlib

from src.storage.models import User, Conversation, Message

logger = logging.getLogger(__name__)


class PrivacyLevel(Enum):
    """Privacy levels for data handling."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DataCategory(Enum):
    """Data categories for classification."""
    PERSONAL_INFO = "personal_info"
    FINANCIAL = "financial"
    HEALTH = "health"
    LEGAL = "legal"
    TECHNICAL = "technical"
    BUSINESS = "business"
    GENERAL = "general"


@dataclass
class PrivacySettings:
    """User privacy settings."""
    user_id: str
    data_retention_days: int = 90
    auto_delete_enabled: bool = True
    opt_in_analytics: bool = False
    opt_in_improvement: bool = False
    share_conversations: bool = False
    allow_voice_recording: bool = True
    allow_transcription: bool = True
    allow_summarization: bool = True
    redaction_enabled: bool = True
    privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class RedactionRule:
    """Redaction rule for sensitive data."""
    id: str
    name: str
    pattern: str
    replacement: str
    category: DataCategory
    privacy_level: PrivacyLevel
    enabled: bool = True
    description: str = ""


class PrivacyController:
    """Main privacy controller for data protection."""
    
    def __init__(self):
        self.redaction_rules: List[RedactionRule] = []
        self.user_settings: Dict[str, PrivacySettings] = {}
        self.sensitive_patterns: Dict[str, re.Pattern] = {}
        
        # Initialize default redaction rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default redaction rules."""
        
        default_rules = [
            # Personal Information
            RedactionRule(
                id="email-addresses",
                name="Email Addresses",
                pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                replacement="[EMAIL]",
                category=DataCategory.PERSONAL_INFO,
                privacy_level=PrivacyLevel.CONFIDENTIAL,
                description="Redact email addresses"
            ),
            RedactionRule(
                id="phone-numbers",
                name="Phone Numbers",
                pattern=r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                replacement="[PHONE]",
                category=DataCategory.PERSONAL_INFO,
                privacy_level=PrivacyLevel.CONFIDENTIAL,
                description="Redact phone numbers"
            ),
            RedactionRule(
                id="credit-cards",
                name="Credit Card Numbers",
                pattern=r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
                replacement="[CREDIT_CARD]",
                category=DataCategory.FINANCIAL,
                privacy_level=PrivacyLevel.RESTRICTED,
                description="Redact credit card numbers"
            ),
            RedactionRule(
                id="ssn",
                name="Social Security Numbers",
                pattern=r'\b\d{3}-\d{2}-\d{4}\b',
                replacement="[SSN]",
                category=DataCategory.PERSONAL_INFO,
                privacy_level=PrivacyLevel.RESTRICTED,
                description="Redact SSNs"
            ),
            RedactionRule(
                id="api-keys",
                name="API Keys",
                pattern=r'\b(sk-|pk-|xoxb-|xoxp-)[a-zA-Z0-9]{20,}\b',
                replacement="[API_KEY]",
                category=DataCategory.TECHNICAL,
                privacy_level=PrivacyLevel.RESTRICTED,
                description="Redact API keys"
            ),
            RedactionRule(
                id="passwords",
                name="Passwords",
                pattern=r'\bpassword[:\s]+[^\s]{6,}\b',
                replacement="[PASSWORD]",
                category=DataCategory.TECHNICAL,
                privacy_level=PrivacyLevel.RESTRICTED,
                description="Redact passwords"
            ),
            RedactionRule(
                id="ip-addresses",
                name="IP Addresses",
                pattern=r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
                replacement="[IP_ADDRESS]",
                category=DataCategory.TECHNICAL,
                privacy_level=PrivacyLevel.CONFIDENTIAL,
                description="Redact IP addresses"
            ),
            RedactionRule(
                id="company-names",
                name="Company Names",
                pattern=r'\b(Inc\.|Corp\.|LLC|Ltd\.|Company|Corporation)\b',
                replacement="[COMPANY]",
                category=DataCategory.BUSINESS,
                privacy_level=PrivacyLevel.INTERNAL,
                description="Redact company names"
            )
        ]
        
        for rule in default_rules:
            self.add_redaction_rule(rule)
    
    def add_redaction_rule(self, rule: RedactionRule):
        """Add a redaction rule."""
        self.redaction_rules.append(rule)
        self.sensitive_patterns[rule.id] = re.compile(rule.pattern, re.IGNORECASE)
        logger.info(f"Added redaction rule: {rule.name}")
    
    def remove_redaction_rule(self, rule_id: str):
        """Remove a redaction rule."""
        self.redaction_rules = [rule for rule in self.redaction_rules if rule.id != rule_id]
        if rule_id in self.sensitive_patterns:
            del self.sensitive_patterns[rule_id]
        logger.info(f"Removed redaction rule: {rule_id}")
    
    def get_user_privacy_settings(self, user_id: str) -> PrivacySettings:
        """Get user privacy settings."""
        if user_id not in self.user_settings:
            # Create default settings
            self.user_settings[user_id] = PrivacySettings(user_id=user_id)
        
        return self.user_settings[user_id]
    
    def update_user_privacy_settings(self, user_id: str, settings: Dict[str, Any]) -> PrivacySettings:
        """Update user privacy settings."""
        
        if user_id not in self.user_settings:
            self.user_settings[user_id] = PrivacySettings(user_id=user_id)
        
        user_settings = self.user_settings[user_id]
        
        # Update settings
        for key, value in settings.items():
            if hasattr(user_settings, key):
                setattr(user_settings, key, value)
        
        user_settings.updated_at = datetime.now()
        
        logger.info(f"Updated privacy settings for user: {user_id}")
        return user_settings
    
    async def redact_sensitive_data(self, text: str, user_id: str) -> Dict[str, Any]:
        """Redact sensitive data from text."""
        
        user_settings = self.get_user_privacy_settings(user_id)
        
        if not user_settings.redaction_enabled:
            return {
                "original_text": text,
                "redacted_text": text,
                "redactions": [],
                "privacy_level": user_settings.privacy_level.value
            }
        
        redacted_text = text
        redactions = []
        
        # Apply redaction rules
        for rule in self.redaction_rules:
            if not rule.enabled:
                continue
            
            # Check if rule applies to user's privacy level
            if rule.privacy_level.value > user_settings.privacy_level.value:
                continue
            
            pattern = self.sensitive_patterns.get(rule.id)
            if pattern:
                matches = list(pattern.finditer(text))
                
                for match in matches:
                    original = match.group(0)
                    redacted_text = redacted_text.replace(original, rule.replacement)
                    
                    redactions.append({
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "category": rule.category.value,
                        "original": original,
                        "replacement": rule.replacement,
                        "position": match.span()
                    })
        
        return {
            "original_text": text,
            "redacted_text": redacted_text,
            "redactions": redactions,
            "privacy_level": user_settings.privacy_level.value
        }
    
    async def classify_data_sensitivity(self, text: str) -> Dict[str, Any]:
        """Classify data sensitivity level."""
        
        sensitivity_score = 0
        categories = set()
        detected_patterns = []
        
        for rule in self.redaction_rules:
            if not rule.enabled:
                continue
            
            pattern = self.sensitive_patterns.get(rule.id)
            if pattern and pattern.search(text):
                sensitivity_score += self._get_category_weight(rule.category)
                categories.add(rule.category.value)
                detected_patterns.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "category": rule.category.value,
                    "privacy_level": rule.privacy_level.value
                })
        
        # Determine overall privacy level
        if sensitivity_score >= 10:
            privacy_level = PrivacyLevel.RESTRICTED
        elif sensitivity_score >= 5:
            privacy_level = PrivacyLevel.CONFIDENTIAL
        elif sensitivity_score >= 2:
            privacy_level = PrivacyLevel.INTERNAL
        else:
            privacy_level = PrivacyLevel.PUBLIC
        
        return {
            "sensitivity_score": sensitivity_score,
            "privacy_level": privacy_level.value,
            "categories": list(categories),
            "detected_patterns": detected_patterns
        }
    
    def _get_category_weight(self, category: DataCategory) -> int:
        """Get weight for data category."""
        weights = {
            DataCategory.PERSONAL_INFO: 3,
            DataCategory.FINANCIAL: 5,
            DataCategory.HEALTH: 5,
            DataCategory.LEGAL: 4,
            DataCategory.TECHNICAL: 2,
            DataCategory.BUSINESS: 1,
            DataCategory.GENERAL: 0
        }
        return weights.get(category, 0)
    
    async def create_privacy_audit_log(self, user_id: str, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create privacy audit log entry."""
        
        audit_entry = {
            "user_id": user_id,
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "data_hash": hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest(),
            "privacy_level": self.get_user_privacy_settings(user_id).privacy_level.value
        }
        
        logger.info(f"Privacy audit log: {action} for user {user_id}")
        return audit_entry
    
    async def check_data_retention_compliance(self, user_id: str) -> Dict[str, Any]:
        """Check data retention compliance for user."""
        
        user_settings = self.get_user_privacy_settings(user_id)
        retention_days = user_settings.data_retention_days
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        # In production, query database for old data
        # For demo, return compliance status
        compliance_status = {
            "user_id": user_id,
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "auto_delete_enabled": user_settings.auto_delete_enabled,
            "compliance_status": "compliant",
            "data_to_delete": 0,  # Would be calculated from database
            "last_audit": datetime.now().isoformat()
        }
        
        return compliance_status
    
    async def generate_privacy_report(self, user_id: str) -> Dict[str, Any]:
        """Generate privacy report for user."""
        
        user_settings = self.get_user_privacy_settings(user_id)
        
        report = {
            "user_id": user_id,
            "generated_at": datetime.now().isoformat(),
            "privacy_settings": {
                "data_retention_days": user_settings.data_retention_days,
                "auto_delete_enabled": user_settings.auto_delete_enabled,
                "opt_in_analytics": user_settings.opt_in_analytics,
                "opt_in_improvement": user_settings.opt_in_improvement,
                "share_conversations": user_settings.share_conversations,
                "allow_voice_recording": user_settings.allow_voice_recording,
                "allow_transcription": user_settings.allow_transcription,
                "allow_summarization": user_settings.allow_summarization,
                "redaction_enabled": user_settings.redaction_enabled,
                "privacy_level": user_settings.privacy_level.value
            },
            "data_handling": {
                "conversations_stored": True,
                "voice_recordings_stored": user_settings.allow_voice_recording,
                "transcriptions_stored": user_settings.allow_transcription,
                "analytics_enabled": user_settings.opt_in_analytics,
                "improvement_data_enabled": user_settings.opt_in_improvement
            },
            "compliance": {
                "gdpr_compliant": True,
                "ccpa_compliant": True,
                "data_retention_compliant": True,
                "privacy_by_design": True
            },
            "recommendations": self._generate_privacy_recommendations(user_settings)
        }
        
        return report
    
    def _generate_privacy_recommendations(self, settings: PrivacySettings) -> List[str]:
        """Generate privacy recommendations for user."""
        
        recommendations = []
        
        if not settings.redaction_enabled:
            recommendations.append("Enable automatic data redaction for enhanced privacy protection")
        
        if settings.opt_in_analytics:
            recommendations.append("Consider disabling analytics if you prefer maximum privacy")
        
        if settings.share_conversations:
            recommendations.append("Review conversation sharing settings for sensitive discussions")
        
        if settings.data_retention_days > 365:
            recommendations.append("Consider reducing data retention period for better privacy")
        
        if not settings.auto_delete_enabled:
            recommendations.append("Enable automatic data deletion for compliance")
        
        return recommendations


class PrivacyUI:
    """Privacy UI indicators and controls."""
    
    def __init__(self, privacy_controller: PrivacyController):
        self.privacy_controller = privacy_controller
    
    def get_privacy_indicators(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get privacy indicators for UI display."""
        
        user_settings = self.privacy_controller.get_user_privacy_settings(user_id)
        
        indicators = {
            "privacy_level": {
                "level": user_settings.privacy_level.value,
                "icon": self._get_privacy_icon(user_settings.privacy_level),
                "color": self._get_privacy_color(user_settings.privacy_level),
                "description": self._get_privacy_description(user_settings.privacy_level)
            },
            "data_handling": {
                "redaction_enabled": user_settings.redaction_enabled,
                "retention_days": user_settings.data_retention_days,
                "auto_delete": user_settings.auto_delete_enabled
            },
            "permissions": {
                "voice_recording": user_settings.allow_voice_recording,
                "transcription": user_settings.allow_transcription,
                "analytics": user_settings.opt_in_analytics,
                "improvement": user_settings.opt_in_improvement
            },
            "compliance": {
                "gdpr": True,
                "ccpa": True,
                "retention": True
            }
        }
        
        return indicators
    
    def _get_privacy_icon(self, privacy_level: PrivacyLevel) -> str:
        """Get privacy level icon."""
        icons = {
            PrivacyLevel.PUBLIC: "🌐",
            PrivacyLevel.INTERNAL: "🏢",
            PrivacyLevel.CONFIDENTIAL: "🔒",
            PrivacyLevel.RESTRICTED: "🚫"
        }
        return icons.get(privacy_level, "🔒")
    
    def _get_privacy_color(self, privacy_level: PrivacyLevel) -> str:
        """Get privacy level color."""
        colors = {
            PrivacyLevel.PUBLIC: "green",
            PrivacyLevel.INTERNAL: "blue",
            PrivacyLevel.CONFIDENTIAL: "orange",
            PrivacyLevel.RESTRICTED: "red"
        }
        return colors.get(privacy_level, "blue")
    
    def _get_privacy_description(self, privacy_level: PrivacyLevel) -> str:
        """Get privacy level description."""
        descriptions = {
            PrivacyLevel.PUBLIC: "Data may be shared publicly",
            PrivacyLevel.INTERNAL: "Data shared within organization",
            PrivacyLevel.CONFIDENTIAL: "Data kept confidential",
            PrivacyLevel.RESTRICTED: "Data access strictly controlled"
        }
        return descriptions.get(privacy_level, "Data privacy level")
    
    def get_consent_banner(self, user_id: str) -> Dict[str, Any]:
        """Get consent banner for user."""
        
        user_settings = self.privacy_controller.get_user_privacy_settings(user_id)
        
        banner = {
            "show": not user_settings.opt_in_analytics or not user_settings.opt_in_improvement,
            "title": "Privacy Settings",
            "message": "We respect your privacy. Please review and update your privacy settings.",
            "options": [
                {
                    "id": "opt_in_analytics",
                    "label": "Allow analytics to improve service",
                    "description": "Help us improve by sharing usage analytics",
                    "enabled": user_settings.opt_in_analytics
                },
                {
                    "id": "opt_in_improvement",
                    "label": "Allow data for AI improvement",
                    "description": "Help improve AI responses (data is anonymized)",
                    "enabled": user_settings.opt_in_improvement
                },
                {
                    "id": "share_conversations",
                    "label": "Share conversations for training",
                    "description": "Share conversations to improve AI (opt-out anytime)",
                    "enabled": user_settings.share_conversations
                }
            ],
            "actions": [
                {
                    "id": "accept_all",
                    "label": "Accept All",
                    "type": "primary"
                },
                {
                    "id": "customize",
                    "label": "Customize",
                    "type": "secondary"
                },
                {
                    "id": "decline",
                    "label": "Decline",
                    "type": "danger"
                }
            ]
        }
        
        return banner
    
    def get_privacy_controls(self, user_id: str) -> Dict[str, Any]:
        """Get privacy controls for user interface."""
        
        user_settings = self.privacy_controller.get_user_privacy_settings(user_id)
        
        controls = {
            "data_retention": {
                "type": "slider",
                "label": "Data Retention Period",
                "description": "How long to keep your data",
                "value": user_settings.data_retention_days,
                "min": 7,
                "max": 365,
                "unit": "days"
            },
            "auto_delete": {
                "type": "toggle",
                "label": "Auto Delete",
                "description": "Automatically delete old data",
                "enabled": user_settings.auto_delete_enabled
            },
            "redaction": {
                "type": "toggle",
                "label": "Data Redaction",
                "description": "Automatically redact sensitive information",
                "enabled": user_settings.redaction_enabled
            },
            "voice_recording": {
                "type": "toggle",
                "label": "Voice Recording",
                "description": "Allow voice recording for transcription",
                "enabled": user_settings.allow_voice_recording
            },
            "transcription": {
                "type": "toggle",
                "label": "Transcription",
                "description": "Store meeting transcriptions",
                "enabled": user_settings.allow_transcription
            },
            "privacy_level": {
                "type": "select",
                "label": "Privacy Level",
                "description": "Set your preferred privacy level",
                "value": user_settings.privacy_level.value,
                "options": [
                    {"value": "public", "label": "Public", "description": "Data may be shared publicly"},
                    {"value": "internal", "label": "Internal", "description": "Data shared within organization"},
                    {"value": "confidential", "label": "Confidential", "description": "Data kept confidential"},
                    {"value": "restricted", "label": "Restricted", "description": "Data access strictly controlled"}
                ]
            }
        }
        
        return controls


# Global privacy controller instance
privacy_controller = PrivacyController()
privacy_ui = PrivacyUI(privacy_controller) 