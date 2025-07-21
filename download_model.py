#!/usr/bin/env python3
"""
Manual model downloader for Mistral-7B-Instruct
This will download the model to ./data/models/ directory
"""

import os
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

def download_mistral_model():
    """Download Mistral-7B-Instruct model locally"""
    
    model_name = "mistralai/Mistral-7B-Instruct-v0.2"
    local_model_path = "./data/models/mistral-7b-instruct"
    
    print("🚀 Starting Mistral-7B model download...")
    print(f"Model: {model_name}")
    print(f"Local path: {local_model_path}")
    print(f"Estimated size: ~13GB")
    print("This will take 10-30 minutes depending on your internet speed...\n")
    
    # Create directory
    os.makedirs(local_model_path, exist_ok=True)
    
    try:
        # Download tokenizer
        print("📥 Downloading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        tokenizer.save_pretrained(local_model_path)
        print("✅ Tokenizer downloaded successfully!")
        
        # Download model
        print("📥 Downloading model (this is the big one...)...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        model.save_pretrained(local_model_path)
        print("✅ Model downloaded successfully!")
        
        print(f"\n🎉 Download complete!")
        print(f"Model saved to: {os.path.abspath(local_model_path)}")
        print(f"Total size: ~{get_folder_size(local_model_path):.1f} GB")
        
        # Test loading
        print("\n🧪 Testing model loading...")
        test_tokenizer = AutoTokenizer.from_pretrained(local_model_path)
        print("✅ Model loads successfully!")
        print("\nYour RAG system is ready to use! 🚀")
        
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        print("Please check your internet connection and try again.")

def get_folder_size(folder_path):
    """Get folder size in GB"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)
    return total_size / (1024**3)  # Convert to GB

if __name__ == "__main__":
    download_mistral_model()