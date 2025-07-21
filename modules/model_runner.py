import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import logging
from typing import Optional, Dict
import gc

logger = logging.getLogger(__name__)

class MistralCodeAnalyzer:
    def __init__(self, model_name: str = "mistralai/Mistral-7B-Instruct-v0.2"):
        """Initialize Mistral-7B with quantization for efficiency"""
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Initializing Mistral model on device: {self.device}")
        self._load_model()

    def _load_model(self):
        """Load the model with quantization to save memory"""
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Add padding token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Configure quantization for memory efficiency
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
            
            # Load model with quantization
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.float16,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            logger.info("Mistral-7B model loaded successfully with 4-bit quantization")
            
        except Exception as e:
            logger.error(f"Failed to load Mistral model: {e}")
            # Fallback: try loading without quantization
            self._load_model_fallback()

    def _load_model_fallback(self):
        """Fallback: load model without quantization"""
        try:
            logger.info("Attempting fallback model loading without quantization...")
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            if self.device == "cpu":
                self.model = self.model.to(self.device)
            
            logger.info("Model loaded successfully without quantization")
            
        except Exception as e:
            logger.error(f"Fallback model loading also failed: {e}")
            raise

    def create_prompt(self, query: str, context: str, obfuscated_prompt: str = "") -> str:
        """Create a well-structured prompt for code analysis"""
        
        system_prompt = """You are a senior React/TypeScript developer and architect with 10+ years of experience. You specialize in identifying bugs, performance issues, and providing best practices. Always provide:

1. **Direct Answer**: Address the specific question first
2. **Code Analysis**: Explain what the code is doing
3. **Issues Found**: Identify any problems, bugs, or anti-patterns
4. **Best Practices**: Suggest improvements and modern React patterns
5. **Example Code**: Provide corrected or improved code examples when relevant

Be concise but thorough. Focus on practical, actionable advice."""

        # Use obfuscated prompt if provided, otherwise use default
        if obfuscated_prompt.strip():
            system_prompt = obfuscated_prompt.strip()

        prompt = f"""<s>[INST] {system_prompt}

## Developer Question:
{query}

## Relevant Code Context:
{context}

Please analyze this code and provide a detailed response addressing the question. Include specific code examples and best practices. [/INST]"""

        return prompt

    def generate_response(self, query: str, context: str, obfuscated_prompt: str = "", max_tokens: int = 1024) -> str:
        """Generate AI response for code analysis"""
        try:
            if not self.model or not self.tokenizer:
                return "❌ Model not loaded. Please check the logs for initialization errors."
            
            # Create prompt
            prompt = self.create_prompt(query, context, obfuscated_prompt)
            
            # Tokenize
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=4000,  # Leave room for generation
                padding=True
            ).to(self.model.device)
            
            # Generate response
            logger.info("Generating response...")
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    repetition_penalty=1.1
                )
            
            # Decode response
            full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract just the generated part (after [/INST])
            if "[/INST]" in full_response:
                response = full_response.split("[/INST]")[-1].strip()
            else:
                response = full_response.strip()
            
            # Clean up response
            response = self._clean_response(response)
            
            logger.info(f"Generated response ({len(response)} characters)")
            return response
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return f"❌ Error generating response: {str(e)}\n\nQuery: {query}\nContext available: {len(context)} characters"

    def _clean_response(self, response: str) -> str:
        """Clean and format the AI response"""
        # Remove any remaining special tokens
        response = response.replace("<s>", "").replace("</s>", "")
        response = response.replace("[INST]", "").replace("[/INST]", "")
        
        # Remove excessive whitespace
        lines = [line.strip() for line in response.split('\n')]
        response = '\n'.join(line for line in lines if line)
        
        # Ensure it starts with a clear answer
        if not response.startswith(('##', '**', '1.', '-', '•')):
            response = f"## Analysis\n\n{response}"
        
        return response

    def get_model_info(self) -> Dict:
        """Get information about the loaded model"""
        return {
            'model_name': self.model_name,
            'device': self.device,
            'model_loaded': self.model is not None,
            'tokenizer_loaded': self.tokenizer is not None,
            'cuda_available': torch.cuda.is_available(),
            'memory_usage': self._get_memory_usage()
        }

    def _get_memory_usage(self) -> Dict:
        """Get current memory usage"""
        memory_info = {}
        
        if torch.cuda.is_available():
            memory_info['cuda_allocated'] = f"{torch.cuda.memory_allocated() / 1024**3:.2f} GB"
            memory_info['cuda_reserved'] = f"{torch.cuda.memory_reserved() / 1024**3:.2f} GB"
        
        return memory_info

    def cleanup(self):
        """Clean up model resources"""
        try:
            if self.model:
                del self.model
            if self.tokenizer:
                del self.tokenizer
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            gc.collect()
            logger.info("Model resources cleaned up")
            
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")

# Global instance
_model_runner = None

def get_model_runner():
    """Get or create the global model runner instance"""
    global _model_runner
    if _model_runner is None:
        _model_runner = MistralCodeAnalyzer()
    return _model_runner

def cleanup_model():
    """Cleanup the global model instance"""
    global _model_runner
    if _model_runner:
        _model_runner.cleanup()
        _model_runner = None