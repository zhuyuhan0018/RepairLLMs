"""
Local Model Wrapper for Qwen2
"""
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import List, Optional
import os


class LocalModel:
    """Wrapper for locally deployed Qwen2 model"""
    
    def __init__(self, model_path: str, device: Optional[str] = None):
        """
        Initialize local model
        
        Args:
            model_path: Path to the model
            device: Device to use (cuda/cpu), auto-detect if None
        """
        self.model_path = model_path
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        print(f"Loading model from {model_path} on {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            trust_remote_code=True,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None
        )
        if self.device == "cpu":
            self.model = self.model.to(self.device)
        self.model.eval()
        print("Model loaded successfully!")
    
    def generate(self,
                 prompt: str,
                 system_prompt: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 2048,
                 stop: Optional[List[str]] = None) -> str:
        """
        Generate text using local model
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            
        Returns:
            Generated text
        """
        # Format prompt according to Qwen2 chat format
        if system_prompt:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        else:
            messages = [{"role": "user", "content": prompt}]
        
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        generated_text = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        )
        
        # Apply stop sequences if provided
        if stop:
            for stop_seq in stop:
                if stop_seq in generated_text:
                    generated_text = generated_text.split(stop_seq)[0]
        
        return generated_text.strip()
    
    def compute_perplexity(self, text: str) -> float:
        """
        Compute perplexity of given text
        
        Args:
            text: Text to compute perplexity for
            
        Returns:
            Perplexity score
        """
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs, labels=inputs.input_ids)
            loss = outputs.loss
            perplexity = torch.exp(loss).item()
        
        return perplexity
    
    def compute_perplexity_segments(self, text: str, segment_length: int = 100) -> List[float]:
        """
        Compute perplexity for text segments
        
        Args:
            text: Text to analyze
            segment_length: Length of each segment in tokens
            
        Returns:
            List of perplexity scores for each segment
        """
        tokens = self.tokenizer.encode(text)
        perplexities = []
        
        for i in range(0, len(tokens), segment_length):
            segment_tokens = tokens[i:i + segment_length]
            if len(segment_tokens) < 10:  # Skip very short segments
                continue
            
            segment_text = self.tokenizer.decode(segment_tokens, skip_special_tokens=True)
            perplexity = self.compute_perplexity(segment_text)
            perplexities.append(perplexity)
        
        return perplexities

