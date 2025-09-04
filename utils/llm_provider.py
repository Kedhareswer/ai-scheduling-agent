"""
Flexible LLM Provider System
Supports OpenAI, Groq, and Gemini with automatic fallback
"""
import os
from typing import Optional, Union
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import BaseMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMProvider:
    """
    Flexible LLM provider that supports OpenAI, Groq, and Gemini
    Automatically detects available API keys and provides fallback
    """
    
    def __init__(self, preferred_provider: Optional[str] = None):
        self.preferred_provider = preferred_provider
        self.llm = None
        self.active_provider = None
        self._initialize_llm()
    
    def _initialize_llm(self) -> None:
        """Initialize LLM with the first available provider"""
        providers = self._get_provider_priority()
        
        for provider in providers:
            try:
                llm = self._create_llm(provider)
                if llm:
                    self.llm = llm
                    self.active_provider = provider
                    print(f"✅ LLM initialized with {provider}")
                    return
            except Exception as e:
                print(f"❌ Failed to initialize {provider}: {str(e)}")
                continue
        
        print("⚠️ No LLM providers available - using fallback mode")
        self.llm = None
        self.active_provider = None
    
    def _get_provider_priority(self) -> list:
        """Get provider priority list based on preference and available keys"""
        available_providers = []
        
        # Check which API keys are available
        if os.getenv("OPENAI_API_KEY"):
            available_providers.append("openai")
        if os.getenv("GROQ_API_KEY"):
            available_providers.append("groq")
        if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
            available_providers.append("gemini")
        
        # Prioritize preferred provider if specified and available
        if self.preferred_provider and self.preferred_provider in available_providers:
            available_providers.remove(self.preferred_provider)
            available_providers.insert(0, self.preferred_provider)
        
        return available_providers
    
    def _create_llm(self, provider: str) -> Optional[BaseLanguageModel]:
        """Create LLM instance for the specified provider"""
        if provider == "openai":
            return self._create_openai_llm()
        elif provider == "groq":
            return self._create_groq_llm()
        elif provider == "gemini":
            return self._create_gemini_llm()
        return None
    
    def _create_openai_llm(self) -> Optional[BaseLanguageModel]:
        """Create OpenAI LLM instance"""
        try:
            from langchain_openai import ChatOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return None
            
            return ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                openai_api_key=api_key
            )
        except ImportError:
            print("❌ langchain-openai not installed")
            return None
    
    def _create_groq_llm(self) -> Optional[BaseLanguageModel]:
        """Create Groq LLM instance"""
        try:
            from langchain_groq import ChatGroq
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return None
            
            return ChatGroq(
                model="llama-3.1-8b-instant",  # Latest supported fast model
                temperature=0,
                groq_api_key=api_key
            )
        except ImportError:
            print("❌ langchain-groq not installed")
            return None
    
    def _create_gemini_llm(self) -> Optional[BaseLanguageModel]:
        """Create Gemini LLM instance"""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                return None
            
            return ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp",  # Latest experimental model
                temperature=0,
                google_api_key=api_key
            )
        except ImportError:
            print("❌ langchain-google-genai not installed")
            return None
    
    def invoke(self, messages: Union[str, list]) -> Optional[str]:
        """Invoke the LLM with messages"""
        if not self.llm:
            return None
        
        try:
            if isinstance(messages, str):
                from langchain_core.messages import HumanMessage
                messages = [HumanMessage(content=messages)]
            
            response = self.llm.invoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            print(f"❌ LLM invocation failed: {str(e)}")
            return None
    
    def is_available(self) -> bool:
        """Check if any LLM provider is available"""
        return self.llm is not None
    
    def get_provider_info(self) -> dict:
        """Get information about the active provider"""
        return {
            "active_provider": self.active_provider,
            "model": self._get_model_name(),
            "available": self.is_available()
        }
    
    def _get_model_name(self) -> str:
        """Get the model name for the active provider"""
        if not self.active_provider:
            return "None"
        
        model_map = {
            "openai": "gpt-4o-mini",
            "groq": "llama-3.1-8b-instant",
            "gemini": "gemini-2.0-flash-exp"
        }
        return model_map.get(self.active_provider, "Unknown")

# Global LLM provider instance
_global_llm_provider = None

def get_llm_provider(preferred_provider: Optional[str] = None) -> LLMProvider:
    """Get or create global LLM provider instance"""
    global _global_llm_provider
    if _global_llm_provider is None:
        _global_llm_provider = LLMProvider(preferred_provider)
    return _global_llm_provider

def reset_llm_provider():
    """Reset global LLM provider (useful for testing)"""
    global _global_llm_provider
    _global_llm_provider = None
