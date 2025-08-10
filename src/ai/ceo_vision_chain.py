"""Enhanced CEO Vision AI Chain with comprehensive organizational template."""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import speech_recognition as sr
import pyttsx3
from pydub import AudioSegment
from pydub.playback import play

from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.chat_models import ChatOpenAI

from src.ai.model_switcher import get_model_switcher
from src.kb.enhanced_retriever import get_enhanced_kb_retriever
from src.analytics.telemetry import get_telemetry_service, EventType
from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CEOVisionContext:
    """Enhanced context for CEO vision conversations with comprehensive template."""
    company_name: str
    ceo_name: str
    industry: str
    current_year: int
    vision_data: Dict[str, Any]
    conversation_history: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.current_year is None:
            self.current_year = datetime.now().year


class CEOVisionChain:
    """Enhanced AI chain for CEO vision and leadership guidance with comprehensive template."""
    
    def __init__(self):
        self.settings = get_settings()
        self.model_switcher = get_model_switcher()
        self.kb_retriever = get_enhanced_kb_retriever()
        self.telemetry = get_telemetry_service()
        
        # Voice recognition and synthesis
        self.recognizer = sr.Recognizer()
        self.speaker = pyttsx3.init()
        self.voice_enabled = True
        
        # Enhanced CEO Vision template structure
        self.vision_template = self._load_comprehensive_vision_template()
        
        # Initialize voice settings
        self._setup_voice()
    
    def _load_comprehensive_vision_template(self) -> Dict[str, Any]:
        """Load the comprehensive CEO vision template structure."""
        return {
            "leadership_roles": {
                "executive_team": [],
                "key_roles": {},
                "decision_authority": {},
                "reporting_relationships": {}
            },
            "organizational_structure": {
                "departments": [],
                "business_units": [],
                "geographic_regions": [],
                "functional_areas": [],
                "team_hierarchy": {}
            },
            "decision_escalation_paths": {
                "decision_types": {},
                "escalation_flows": {},
                "approval_matrices": {},
                "emergency_procedures": {}
            },
            "core_processes_workflows": {
                "operational_processes": [],
                "approval_workflows": [],
                "handoff_procedures": [],
                "documentation_requirements": {},
                "quality_controls": {}
            },
            "performance_metrics_kpis": {
                "business_metrics": {},
                "operational_metrics": {},
                "financial_metrics": {},
                "team_metrics": {},
                "customer_metrics": {},
                "tracking_frequency": {}
            },
            "strategic_goals_vision": {
                "short_term_goals": {},  # 6-12 months
                "medium_term_goals": {},  # 1-3 years
                "long_term_goals": {},  # 3+ years
                "strategic_themes": [],
                "vision_statement": "",
                "mission_statement": "",
                "competitive_positioning": ""
            },
            "values_operating_principles": {
                "core_values": [],
                "operating_principles": [],
                "cultural_expectations": [],
                "decision_frameworks": [],
                "ethical_guidelines": []
            },
            "products_services_technology": {
                "products": [],
                "services": [],
                "key_technologies": [],
                "innovation_priorities": [],
                "technology_stack": {},
                "development_methodologies": []
            },
            "risk_compliance_restrictions": {
                "compliance_standards": [],
                "regulatory_requirements": [],
                "market_restrictions": [],
                "activity_restrictions": [],
                "known_risks": {},
                "mitigation_plans": {},
                "risk_tolerance_levels": {}
            },
            "ai_roles_functions": {
                "ai_personas": [],
                "ai_functions": {},
                "ai_limitations": [],
                "ai_guidelines": {},
                "ai_decision_authority": {}
            },
            "review_update_cycle": {
                "review_frequency": "",
                "update_triggers": [],
                "version_control": {},
                "stakeholder_approval": {},
                "change_management": {}
            }
        }
    
    def _setup_voice(self):
        """Setup voice recognition and synthesis."""
        try:
            # Configure voice synthesis
            voices = self.speaker.getProperty('voices')
            if voices:
                self.speaker.setProperty('voice', voices[0].id)
            self.speaker.setProperty('rate', 150)  # Speed of speech
            self.speaker.setProperty('volume', 0.9)  # Volume level
            
            logger.info("Voice capabilities initialized successfully")
        except Exception as e:
            logger.warning(f"Voice setup failed, falling back to text-only: {e}")
            self.voice_enabled = False
    
    async def initialize_ceo_vision(self, 
                                  company_name: str,
                                  ceo_name: str,
                                  industry: str,
                                  vision_data: Optional[Dict[str, Any]] = None) -> CEOVisionContext:
        """Initialize comprehensive CEO vision context."""
        try:
            context = CEOVisionContext(
                company_name=company_name,
                ceo_name=ceo_name,
                industry=industry,
                vision_data=vision_data or self.vision_template
            )
            
            # Store in knowledge base
            await self._store_comprehensive_vision_in_kb(context)
            
            # Track initialization
            await self.telemetry.track_event(
                EventType.FEATURE_USED,
                metadata={
                    "feature": "comprehensive_ceo_vision_initialization",
                    "company": company_name,
                    "industry": industry,
                    "template_sections": len(self.vision_template.keys())
                }
            )
            
            logger.info(f"Comprehensive CEO vision initialized for {company_name}")
            return context
            
        except Exception as e:
            logger.error(f"Failed to initialize comprehensive CEO vision: {e}")
            raise
    
    async def _store_comprehensive_vision_in_kb(self, context: CEOVisionContext):
        """Store comprehensive CEO vision data in knowledge base."""
        try:
            vision_content = f"""
            Company: {context.company_name}
            CEO: {context.ceo_name}
            Industry: {context.industry}
            
            COMPREHENSIVE ORGANIZATIONAL TEMPLATE:
            
            1. LEADERSHIP & KEY ROLES:
            {json.dumps(context.vision_data.get('leadership_roles', {}), indent=2)}
            
            2. ORGANIZATIONAL STRUCTURE:
            {json.dumps(context.vision_data.get('organizational_structure', {}), indent=2)}
            
            3. DECISION & ESCALATION PATHS:
            {json.dumps(context.vision_data.get('decision_escalation_paths', {}), indent=2)}
            
            4. CORE PROCESSES & WORKFLOWS:
            {json.dumps(context.vision_data.get('core_processes_workflows', {}), indent=2)}
            
            5. PERFORMANCE METRICS (KPIs):
            {json.dumps(context.vision_data.get('performance_metrics_kpis', {}), indent=2)}
            
            6. STRATEGIC GOALS & VISION:
            {json.dumps(context.vision_data.get('strategic_goals_vision', {}), indent=2)}
            
            7. VALUES & OPERATING PRINCIPLES:
            {json.dumps(context.vision_data.get('values_operating_principles', {}), indent=2)}
            
            8. PRODUCTS, SERVICES & TECHNOLOGY:
            {json.dumps(context.vision_data.get('products_services_technology', {}), indent=2)}
            
            9. RISK, COMPLIANCE & RESTRICTIONS:
            {json.dumps(context.vision_data.get('risk_compliance_restrictions', {}), indent=2)}
            
            10. AI ROLES & FUNCTIONS:
            {json.dumps(context.vision_data.get('ai_roles_functions', {}), indent=2)}
            
            11. REVIEW & UPDATE CYCLE:
            {json.dumps(context.vision_data.get('review_update_cycle', {}), indent=2)}
            """
            
            await self.kb_retriever.add_document(
                content=vision_content,
                metadata={
                    "type": "comprehensive_ceo_vision",
                    "company": context.company_name,
                    "ceo": context.ceo_name,
                    "industry": context.industry,
                    "template_version": "comprehensive_v2",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to store comprehensive vision in KB: {e}")
    
    async def process_voice_input(self, audio_data: bytes) -> str:
        """Process voice input and convert to text."""
        try:
            if not self.voice_enabled:
                raise Exception("Voice capabilities not available")
            
            # Convert audio data to speech recognition format
            audio = sr.AudioData(audio_data, sample_rate=16000, sample_width=2)
            
            # Recognize speech
            text = self.recognizer.recognize_google(audio)
            
            logger.info(f"Voice input recognized: {text}")
            return text
            
        except sr.UnknownValueError:
            raise Exception("Could not understand audio")
        except sr.RequestError as e:
            raise Exception(f"Speech recognition service error: {e}")
        except Exception as e:
            logger.error(f"Voice processing failed: {e}")
            raise
    
    async def generate_voice_response(self, text: str) -> bytes:
        """Generate voice response from text."""
        try:
            if not self.voice_enabled:
                raise Exception("Voice capabilities not available")
            
            # Convert text to speech
            self.speaker.say(text)
            self.speaker.runAndWait()
            
            # For now, return empty bytes (in production, would capture audio)
            return b""
            
        except Exception as e:
            logger.error(f"Voice response generation failed: {e}")
            raise
    
    async def ceo_conversation(self, 
                             context: CEOVisionContext,
                             message: str,
                             voice_input: bool = False,
                             voice_output: bool = False) -> Dict[str, Any]:
        """Process CEO conversation with comprehensive vision context."""
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Process voice input if needed
            if voice_input:
                message = await self.process_voice_input(message.encode())
            
            # Build comprehensive conversation context
            conversation_context = self._build_comprehensive_conversation_context(context, message)
            
            # Generate AI response
            response = await self._generate_comprehensive_ceo_response(conversation_context)
            
            # Generate voice output if requested
            voice_data = None
            if voice_output and self.voice_enabled:
                voice_data = await self.generate_voice_response(response['content'])
            
            # Update conversation history
            context.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "user_message": message,
                "ai_response": response['content'],
                "voice_input": voice_input,
                "voice_output": voice_output,
                "context_sections_used": response.get('context_sections_used', [])
            })
            
            # Track conversation
            response_time = asyncio.get_event_loop().time() - start_time
            await self.telemetry.track_ai_performance(
                user_id=context.ceo_name,
                model_name="comprehensive-ceo-vision-model",
                performance={
                    "response_time": response_time,
                    "tokens_used": response.get('tokens_used', 0),
                    "cost": response.get('cost', 0.0),
                    "success": True,
                    "model_name": "comprehensive-ceo-vision-specialized"
                }
            )
            
            return {
                "content": response['content'],
                "voice_data": voice_data,
                "context_used": response.get('context_used', []),
                "confidence": response.get('confidence', 0.8),
                "suggested_actions": response.get('suggested_actions', []),
                "template_sections_referenced": response.get('template_sections_referenced', [])
            }
            
        except Exception as e:
            logger.error(f"Comprehensive CEO conversation failed: {e}")
            await self.telemetry.track_error(
                "comprehensive_ceo_conversation_failed",
                str(e),
                metadata={"company": context.company_name}
            )
            raise
    
    def _build_comprehensive_conversation_context(self, context: CEOVisionContext, message: str) -> str:
        """Build comprehensive conversation context with all template sections."""
        return f"""
        You are an AI executive assistant for {context.company_name}, working directly with CEO {context.ceo_name}.
        
        Company Context:
        - Industry: {context.industry}
        - Current Year: {context.current_year}
        
        Your role is to provide comprehensive executive support based on the complete organizational template:
        
        1. LEADERSHIP & KEY ROLES:
        {json.dumps(context.vision_data.get('leadership_roles', {}), indent=2)}
        
        2. ORGANIZATIONAL STRUCTURE:
        {json.dumps(context.vision_data.get('organizational_structure', {}), indent=2)}
        
        3. DECISION & ESCALATION PATHS:
        {json.dumps(context.vision_data.get('decision_escalation_paths', {}), indent=2)}
        
        4. CORE PROCESSES & WORKFLOWS:
        {json.dumps(context.vision_data.get('core_processes_workflows', {}), indent=2)}
        
        5. PERFORMANCE METRICS (KPIs):
        {json.dumps(context.vision_data.get('performance_metrics_kpis', {}), indent=2)}
        
        6. STRATEGIC GOALS & VISION:
        {json.dumps(context.vision_data.get('strategic_goals_vision', {}), indent=2)}
        
        7. VALUES & OPERATING PRINCIPLES:
        {json.dumps(context.vision_data.get('values_operating_principles', {}), indent=2)}
        
        8. PRODUCTS, SERVICES & TECHNOLOGY:
        {json.dumps(context.vision_data.get('products_services_technology', {}), indent=2)}
        
        9. RISK, COMPLIANCE & RESTRICTIONS:
        {json.dumps(context.vision_data.get('risk_compliance_restrictions', {}), indent=2)}
        
        10. AI ROLES & FUNCTIONS:
        {json.dumps(context.vision_data.get('ai_roles_functions', {}), indent=2)}
        
        11. REVIEW & UPDATE CYCLE:
        {json.dumps(context.vision_data.get('review_update_cycle', {}), indent=2)}
        
        Current Conversation History:
        {json.dumps(context.conversation_history[-5:], indent=2)}
        
        CEO Message: {message}
        
        Respond as an executive assistant who understands the complete organizational context and can provide guidance across all areas: leadership, operations, strategy, compliance, technology, and team management. Be strategic, actionable, and aligned with the company's values, goals, and operational framework.
        """
    
    async def _generate_comprehensive_ceo_response(self, conversation_context: str) -> Dict[str, Any]:
        """Generate AI response for comprehensive CEO conversation."""
        try:
            # Use model switcher for optimal response
            model_switcher = get_model_switcher()
            
            messages = [
                SystemMessage(content="You are an executive AI assistant with comprehensive organizational knowledge, specializing in CEO vision alignment, strategic guidance, operational support, and team leadership."),
                HumanMessage(content=conversation_context)
            ]
            
            response = await model_switcher.generate_response(
                messages=messages,
                model_name="gpt-4o",  # Use high-quality model for CEO interactions
                temperature=0.7
            )
            
            # Extract context and suggestions
            context_used = await self._extract_relevant_context(conversation_context)
            suggested_actions = await self._generate_comprehensive_suggested_actions(response.content)
            template_sections = await self._identify_template_sections_used(conversation_context)
            
            return {
                "content": response.content,
                "tokens_used": response.tokens_used,
                "cost": response.cost,
                "context_used": context_used,
                "suggested_actions": suggested_actions,
                "confidence": 0.9,
                "template_sections_referenced": template_sections
            }
            
        except Exception as e:
            logger.error(f"Failed to generate comprehensive CEO response: {e}")
            raise
    
    async def _extract_relevant_context(self, conversation: str) -> List[str]:
        """Extract relevant context from conversation."""
        try:
            # Search knowledge base for relevant information
            results = await self.kb_retriever.search(
                query=conversation,
                method='hybrid',
                top_k=5
            )
            
            return [result.content for result in results]
            
        except Exception as e:
            logger.error(f"Failed to extract context: {e}")
            return []
    
    async def _generate_comprehensive_suggested_actions(self, response: str) -> List[str]:
        """Generate comprehensive suggested actions based on response."""
        try:
            # Analyze response for action items across all template sections
            actions = []
            
            # Look for action-oriented phrases across different areas
            action_phrases = {
                "leadership": ["schedule meeting", "review performance", "delegate", "escalate"],
                "operations": ["optimize process", "improve workflow", "streamline", "automate"],
                "strategy": ["update goals", "review strategy", "pivot", "expand"],
                "compliance": ["audit", "review compliance", "update policies", "risk assessment"],
                "technology": ["upgrade", "implement", "integrate", "develop"],
                "team": ["train", "mentor", "hire", "restructure"]
            }
            
            for area, phrases in action_phrases.items():
                for phrase in phrases:
                    if phrase in response.lower():
                        actions.append(f"{area.title()}: {phrase}")
            
            return actions[:5]  # Limit to top 5 suggestions
            
        except Exception as e:
            logger.error(f"Failed to generate comprehensive actions: {e}")
            return []
    
    async def _identify_template_sections_used(self, conversation: str) -> List[str]:
        """Identify which template sections are being referenced."""
        try:
            sections = []
            section_keywords = {
                "leadership_roles": ["leadership", "roles", "executive", "team"],
                "organizational_structure": ["structure", "department", "organization", "hierarchy"],
                "decision_escalation_paths": ["decision", "escalation", "approval", "authority"],
                "core_processes_workflows": ["process", "workflow", "procedure", "handoff"],
                "performance_metrics_kpis": ["kpi", "metric", "performance", "target"],
                "strategic_goals_vision": ["strategy", "goal", "vision", "objective"],
                "values_operating_principles": ["value", "principle", "culture", "ethics"],
                "products_services_technology": ["product", "service", "technology", "innovation"],
                "risk_compliance_restrictions": ["risk", "compliance", "restriction", "regulation"],
                "ai_roles_functions": ["ai", "automation", "assistant", "function"],
                "review_update_cycle": ["review", "update", "cycle", "frequency"]
            }
            
            for section, keywords in section_keywords.items():
                for keyword in keywords:
                    if keyword in conversation.lower():
                        sections.append(section)
                        break
            
            return list(set(sections))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Failed to identify template sections: {e}")
            return []
    
    async def get_comprehensive_vision_summary(self, context: CEOVisionContext) -> Dict[str, Any]:
        """Get comprehensive summary of CEO vision and current status."""
        try:
            vision_data = context.vision_data
            
            summary = {
                "company": context.company_name,
                "ceo": context.ceo_name,
                "industry": context.industry,
                "template_completion": {},
                "key_metrics": {},
                "conversation_stats": {
                    "total_conversations": len(context.conversation_history),
                    "last_conversation": context.conversation_history[-1] if context.conversation_history else None
                }
            }
            
            # Check template completion for each section
            for section_name, section_data in vision_data.items():
                if isinstance(section_data, dict):
                    completion = len([k for k, v in section_data.items() if v]) / len(section_data) * 100
                elif isinstance(section_data, list):
                    completion = 100 if section_data else 0
                else:
                    completion = 100 if section_data else 0
                
                summary["template_completion"][section_name] = completion
            
            # Extract key metrics
            kpis = vision_data.get('performance_metrics_kpis', {})
            summary["key_metrics"] = {
                "total_kpis": len(kpis),
                "business_metrics": len(kpis.get('business_metrics', {})),
                "operational_metrics": len(kpis.get('operational_metrics', {})),
                "financial_metrics": len(kpis.get('financial_metrics', {}))
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive vision summary: {e}")
            raise
    
    async def update_comprehensive_vision_data(self, 
                                             context: CEOVisionContext,
                                             updates: Dict[str, Any]) -> bool:
        """Update comprehensive CEO vision data."""
        try:
            # Update vision data
            for key, value in updates.items():
                if key in context.vision_data:
                    if isinstance(context.vision_data[key], dict):
                        context.vision_data[key].update(value)
                    else:
                        context.vision_data[key] = value
                else:
                    context.vision_data[key] = value
            
            # Re-store in knowledge base
            await self._store_comprehensive_vision_in_kb(context)
            
            # Track update
            await self.telemetry.track_event(
                EventType.FEATURE_USED,
                metadata={
                    "feature": "comprehensive_ceo_vision_update",
                    "company": context.company_name,
                    "updates": list(updates.keys()),
                    "template_sections_updated": len(updates)
                }
            )
            
            logger.info(f"Comprehensive vision data updated for {context.company_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update comprehensive vision data: {e}")
            return False


# Global instance
ceo_vision_chain = None


def get_ceo_vision_chain() -> CEOVisionChain:
    """Get the global CEO vision chain instance."""
    global ceo_vision_chain
    if ceo_vision_chain is None:
        ceo_vision_chain = CEOVisionChain()
    return ceo_vision_chain


async def init_ceo_vision_chain():
    """Initialize the CEO vision chain."""
    global ceo_vision_chain
    ceo_vision_chain = CEOVisionChain()
    logger.info("Comprehensive CEO vision chain initialized")
    return ceo_vision_chain 