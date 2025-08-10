"""Flexible AI Model Switcher for multiple providers."""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import asyncio
import json

from langchain.llms import OpenAI, Anthropic
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.callbacks import get_openai_callback
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from src.config import get_settings

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Supported AI model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    LOCAL = "local"


@dataclass
class ModelConfig:
    """Configuration for an AI model."""
    provider: ModelProvider
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    streaming: bool = False
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    organization: Optional[str] = None
    timeout: int = 60
    retry_attempts: int = 3


@dataclass
class ModelResponse:
    """Standardized model response."""
    content: str
    model_name: str
    provider: ModelProvider
    tokens_used: int = 0
    cost: float = 0.0
    response_time: float = 0.0
    metadata: Dict[str, Any] = None


class ModelSwitcher:
    """Flexible model switcher for multiple AI providers."""
    
    def __init__(self):
        self.settings = get_settings()
        self.models: Dict[str, ModelConfig] = {}
        self.llm_instances: Dict[str, Any] = {}
        self.active_model: str = "gpt-4o-mini"
        
        # Initialize default models
        self._initialize_default_models()
    
    def _initialize_default_models(self):
        """Initialize default model configurations."""
        
        # OpenAI Models
        self.add_model(ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4o-mini",
            temperature=0.7,
            max_tokens=4000,
            api_key=self.settings.openai_api_key
        ))
        
        self.add_model(ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=4000,
            api_key=self.settings.openai_api_key
        ))
        
        self.add_model(ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4-turbo",
            temperature=0.7,
            max_tokens=4000,
            api_key=self.settings.openai_api_key
        ))
        
        # Anthropic Models
        if hasattr(self.settings, 'anthropic_api_key') and self.settings.anthropic_api_key:
            self.add_model(ModelConfig(
                provider=ModelProvider.ANTHROPIC,
                model_name="claude-3-haiku-20240307",
                temperature=0.7,
                max_tokens=4000,
                api_key=self.settings.anthropic_api_key
            ))
            
            self.add_model(ModelConfig(
                provider=ModelProvider.ANTHROPIC,
                model_name="claude-3-sonnet-20240229",
                temperature=0.7,
                max_tokens=4000,
                api_key=self.settings.anthropic_api_key
            ))
            
            self.add_model(ModelConfig(
                provider=ModelProvider.ANTHROPIC,
                model_name="claude-3-opus-20240229",
                temperature=0.7,
                max_tokens=4000,
                api_key=self.settings.anthropic_api_key
            ))
        
        # Azure OpenAI (if configured)
        if hasattr(self.settings, 'azure_openai_api_key') and self.settings.azure_openai_api_key:
            self.add_model(ModelConfig(
                provider=ModelProvider.AZURE,
                model_name="gpt-4",
                temperature=0.7,
                max_tokens=4000,
                api_key=self.settings.azure_openai_api_key,
                base_url=self.settings.azure_openai_endpoint
            ))
    
    def add_model(self, config: ModelConfig):
        """Add a new model configuration."""
        self.models[config.model_name] = config
        logger.info(f"Added model: {config.model_name} ({config.provider.value})")
    
    def remove_model(self, model_name: str):
        """Remove a model configuration."""
        if model_name in self.models:
            del self.models[model_name]
            if model_name in self.llm_instances:
                del self.llm_instances[model_name]
            logger.info(f"Removed model: {model_name}")
    
    def set_active_model(self, model_name: str) -> bool:
        """Set the active model for the application."""
        if model_name in self.models:
            self.active_model = model_name
            logger.info(f"Active model set to: {model_name}")
            return True
        else:
            logger.error(f"Model not found: {model_name}")
            return False
    
    def get_active_model(self) -> ModelConfig:
        """Get the currently active model configuration."""
        return self.models.get(self.active_model, self.models["gpt-4o-mini"])
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models with their configurations."""
        return [
            {
                "name": name,
                "provider": config.provider.value,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "is_active": name == self.active_model
            }
            for name, config in self.models.items()
        ]
    
    def _get_llm_instance(self, model_name: str) -> Any:
        """Get or create LLM instance for a model."""
        if model_name not in self.llm_instances:
            config = self.models[model_name]
            
            # Create callback manager for streaming
            callbacks = []
            if config.streaming:
                callbacks.append(StreamingStdOutCallbackHandler())
            callback_manager = CallbackManager(callbacks) if callbacks else None
            
            # Create LLM instance based on provider
            if config.provider == ModelProvider.OPENAI:
                self.llm_instances[model_name] = ChatOpenAI(
                    model=config.model_name,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    top_p=config.top_p,
                    frequency_penalty=config.frequency_penalty,
                    presence_penalty=config.presence_penalty,
                    streaming=config.streaming,
                    openai_api_key=config.api_key,
                    openai_organization=config.organization,
                    request_timeout=config.timeout,
                    callbacks=callbacks
                )
            
            elif config.provider == ModelProvider.ANTHROPIC:
                self.llm_instances[model_name] = ChatAnthropic(
                    model=config.model_name,
                    temperature=config.temperature,
                    max_tokens_to_sample=config.max_tokens,
                    top_p=config.top_p,
                    anthropic_api_key=config.api_key,
                    callbacks=callbacks
                )
            
            elif config.provider == ModelProvider.AZURE:
                self.llm_instances[model_name] = ChatOpenAI(
                    model=config.model_name,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    openai_api_key=config.api_key,
                    openai_api_base=config.base_url,
                    deployment_name=config.model_name,
                    callbacks=callbacks
                )
            
            logger.info(f"Created LLM instance for: {model_name}")
        
        return self.llm_instances[model_name]
    
    async def generate_response(self, 
                              messages: List[BaseMessage],
                              model_name: Optional[str] = None,
                              **kwargs) -> ModelResponse:
        """Generate a response using the specified or active model."""
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Use specified model or active model
            target_model = model_name or self.active_model
            if target_model not in self.models:
                raise ValueError(f"Model not found: {target_model}")
            
            # Get LLM instance
            llm = self._get_llm_instance(target_model)
            config = self.models[target_model]
            
            # Override config with kwargs
            if 'temperature' in kwargs:
                llm.temperature = kwargs['temperature']
            if 'max_tokens' in kwargs:
                llm.max_tokens = kwargs['max_tokens']
            
            # Generate response
            if config.provider == ModelProvider.OPENAI:
                with get_openai_callback() as cb:
                    response = await llm.agenerate([messages])
                    content = response.generations[0][0].text
                    tokens_used = cb.total_tokens
                    cost = cb.total_cost
            else:
                response = await llm.agenerate([messages])
                content = response.generations[0][0].text
                tokens_used = 0  # Not available for all providers
                cost = 0.0
            
            response_time = asyncio.get_event_loop().time() - start_time
            
            return ModelResponse(
                content=content,
                model_name=target_model,
                provider=config.provider,
                tokens_used=tokens_used,
                cost=cost,
                response_time=response_time,
                metadata={
                    "temperature": llm.temperature,
                    "max_tokens": llm.max_tokens,
                    "provider": config.provider.value
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to generate response with {target_model}: {e}")
            raise
    
    async def generate_streaming_response(self,
                                        messages: List[BaseMessage],
                                        model_name: Optional[str] = None,
                                        **kwargs):
        """Generate a streaming response."""
        try:
            target_model = model_name or self.active_model
            if target_model not in self.models:
                raise ValueError(f"Model not found: {target_model}")
            
            # Get LLM instance with streaming enabled
            config = self.models[target_model]
            config.streaming = True
            llm = self._get_llm_instance(target_model)
            
            # Override config with kwargs
            if 'temperature' in kwargs:
                llm.temperature = kwargs['temperature']
            if 'max_tokens' in kwargs:
                llm.max_tokens = kwargs['max_tokens']
            
            # Stream response
            async for chunk in llm.astream(messages):
                yield chunk.content
                
        except Exception as e:
            logger.error(f"Failed to generate streaming response: {e}")
            raise
    
    def compare_models(self, 
                      prompt: str,
                      models: List[str] = None) -> Dict[str, ModelResponse]:
        """Compare responses from multiple models."""
        try:
            if models is None:
                models = list(self.models.keys())[:3]  # Compare first 3 models
            
            messages = [HumanMessage(content=prompt)]
            results = {}
            
            for model_name in models:
                if model_name in self.models:
                    try:
                        response = asyncio.run(self.generate_response(messages, model_name))
                        results[model_name] = response
                    except Exception as e:
                        logger.error(f"Failed to generate response for {model_name}: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Model comparison failed: {e}")
            return {}
    
    def get_model_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for all models."""
        try:
            stats = {
                "active_model": self.active_model,
                "total_models": len(self.models),
                "providers": list(set(config.provider.value for config in self.models.values())),
                "models": {}
            }
            
            for name, config in self.models.items():
                stats["models"][name] = {
                    "provider": config.provider.value,
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens,
                    "is_active": name == self.active_model
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get model stats: {e}")
            return {}
    
    def update_model_config(self, 
                           model_name: str,
                           **kwargs) -> bool:
        """Update configuration for a specific model."""
        try:
            if model_name not in self.models:
                return False
            
            config = self.models[model_name]
            
            # Update config attributes
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            # Clear cached LLM instance to force recreation
            if model_name in self.llm_instances:
                del self.llm_instances[model_name]
            
            logger.info(f"Updated config for model: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update model config: {e}")
            return False


# Global instance
model_switcher = None


def get_model_switcher() -> ModelSwitcher:
    """Get the global model switcher instance."""
    global model_switcher
    if model_switcher is None:
        model_switcher = ModelSwitcher()
    return model_switcher


async def init_model_switcher():
    """Initialize the model switcher."""
    global model_switcher
    model_switcher = ModelSwitcher()
    logger.info("Model switcher initialized")
    return model_switcher 