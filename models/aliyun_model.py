"""
Aliyun Cloud Model API Wrapper
"""
import os
import dashscope
from dashscope import Generation
import json
from typing import List, Dict, Optional, Any
from config import ALIYUN_API_BASE


class AliyunModel:
    """Wrapper for Aliyun Cloud Model API"""
    
    def __init__(self, api_key: str, model_name: str = None):
        """
        Initialize Aliyun model
        
        Args:
            api_key: Aliyun API key
            model_name: Model name (default: qwen-max)
        """
        dashscope.api_key = api_key
        # Configure base endpoint if provided
        if ALIYUN_API_BASE:
            dashscope.base_http_api_url = ALIYUN_API_BASE
            if hasattr(dashscope, "base_websocket_api_url"):
                dashscope.base_websocket_api_url = ALIYUN_API_BASE
        # Allow override via env; default to qwen3-coder-plus for code-specific tasks
        self.model_name = model_name or os.getenv("ALIYUN_MODEL_NAME", "qwen3-coder-plus")
    
    def generate(self, 
                 prompt: str, 
                 system_prompt: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = None,
                 stop: Optional[List[str]] = None,
                 timeout: int = 600) -> str:  # Default 10 minutes for long responses
        """
        Generate text using Aliyun API
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            timeout: Request timeout (seconds)
            
        Returns:
            Generated text
        """
        from config import CLOUD_MAX_TOKENS
        if max_tokens is None:
            max_tokens = CLOUD_MAX_TOKENS

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = Generation.call(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop if stop else None,
                timeout=timeout
            )
            
            if response.status_code != 200:
                error_msg = getattr(response, 'message', getattr(response, 'code', 'Unknown error'))
                raise Exception(f"API call failed (status {response.status_code}): {error_msg}")

            out = getattr(response, "output", None)
            if out is None:
                return str(response)

            # If output is a dict
            if isinstance(out, dict):
                if out.get("choices"):
                    return out["choices"][0]["message"]["content"]
                if "text" in out:
                    return out["text"]
            # If output is an object
            if hasattr(out, "choices") and out.choices:
                return out.choices[0].message.content
            if hasattr(out, "text"):
                return out.text

            # Fallback: try direct attributes
            if hasattr(response, 'choices') and response.choices:
                return response.choices[0].message.content
            if hasattr(response, 'text'):
                return response.text

            return str(response)
        except Exception as e:
            raise Exception(f"Error calling Aliyun API: {str(e)}")
    
    def generate_stream(self,
                       prompt: str,
                       system_prompt: Optional[str] = None,
                       temperature: float = 0.7,
                       max_tokens: int = None,
                       timeout: int = 40) -> str:
        """
        Generate text with streaming (for long responses)
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        from config import CLOUD_MAX_TOKENS
        if max_tokens is None:
            max_tokens = CLOUD_MAX_TOKENS

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            full_response = ""
            responses = Generation.call(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                timeout=timeout
            )
            
            for response in responses:
                if response.status_code != 200:
                    error_msg = getattr(response, 'message', 'Unknown error')
                    raise Exception(f"API call failed: {error_msg}")

                out = getattr(response, "output", None)
                if out is None:
                    continue
                if isinstance(out, dict):
                    if out.get("choices"):
                        full_response += out["choices"][0]["message"]["content"]
                    elif "text" in out:
                        full_response += out["text"]
                elif hasattr(out, "choices") and out.choices:
                    full_response += out.choices[0].message.content
                elif hasattr(out, "text"):
                    full_response += out.text
                else:
                    full_response += str(response)
            
            return full_response
        except Exception as e:
            raise Exception(f"Error calling Aliyun API: {str(e)}")

