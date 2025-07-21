import re
import base64
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

class CodeEmbedder:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        """Initialize the code embedder with a lightweight model"""
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def smart_chunk_code(self, code: str, filename: str, max_chunk_size: int = 500) -> List[Dict]:
        """
        Intelligently chunk code by functions, classes, and logical blocks
        """
        chunks = []
        
        # Language detection based on file extension
        if filename.endswith(('.tsx', '.jsx')):
            lang = 'jsx'
        elif filename.endswith('.ts'):
            lang = 'typescript'
        else:
            lang = 'javascript'
        
        # Split by functions, classes, and React components
        patterns = [
            r'(function\s+\w+\s*\([^)]*\)\s*\{[^}]*\})',  # Functions
            r'(const\s+\w+\s*=\s*\([^)]*\)\s*=>\s*\{[^}]*\})',  # Arrow functions
            r'(class\s+\w+[^{]*\{[^}]*\})',  # Classes
            r'(export\s+(default\s+)?function\s+\w+[^{]*\{[^}]*\})',  # Exported functions
            r'(export\s+const\s+\w+\s*=[^;]*;)',  # Exported constants
            r'(interface\s+\w+\s*\{[^}]*\})',  # TypeScript interfaces
            r'(type\s+\w+\s*=[^;]*;)',  # TypeScript types
        ]
        
        lines = code.split('\n')
        current_chunk = []
        current_size = 0
        
        for i, line in enumerate(lines):
            line_size = len(line)
            
            # Check if this line starts a new logical block
            is_new_block = any(re.match(pattern, line.strip()) for pattern in [
                r'function\s+\w+',
                r'const\s+\w+\s*=\s*\(',
                r'class\s+\w+',
                r'export\s+',
                r'interface\s+\w+',
                r'type\s+\w+',
            ])
            
            # If adding this line would exceed chunk size and we have content, create a chunk
            if current_size + line_size > max_chunk_size and current_chunk:
                chunk_text = '\n'.join(current_chunk)
                if chunk_text.strip():
                    chunks.append({
                        'text': chunk_text,
                        'filename': filename,
                        'start_line': i - len(current_chunk) + 1,
                        'end_line': i,
                        'language': lang,
                        'type': self._detect_chunk_type(chunk_text)
                    })
                current_chunk = []
                current_size = 0
            
            current_chunk.append(line)
            current_size += line_size
        
        # Add the last chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            if chunk_text.strip():
                chunks.append({
                    'text': chunk_text,
                    'filename': filename,
                    'start_line': len(lines) - len(current_chunk) + 1,
                    'end_line': len(lines),
                    'language': lang,
                    'type': self._detect_chunk_type(chunk_text)
                })
        
        logger.info(f"Created {len(chunks)} chunks from {filename}")
        return chunks

    def _detect_chunk_type(self, code: str) -> str:
        """Detect the type of code chunk"""
        code_lower = code.lower()
        
        if 'useeffect' in code_lower or 'usestate' in code_lower:
            return 'react_hook'
        elif 'function' in code_lower and 'component' in code_lower:
            return 'react_component'
        elif 'class' in code_lower and 'extends' in code_lower:
            return 'class_component'
        elif 'interface' in code_lower or 'type' in code_lower:
            return 'typescript_definition'
        elif 'export' in code_lower:
            return 'module_export'
        elif 'import' in code_lower:
            return 'import_statement'
        else:
            return 'code_block'

    def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Generate embeddings for code chunks"""
        try:
            # Prepare texts for embedding
            texts = []
            for chunk in chunks:
                # Create context-rich text for better embeddings
                context_text = f"File: {chunk['filename']}\nType: {chunk['type']}\nCode:\n{chunk['text']}"
                texts.append(context_text)
            
            # Generate embeddings
            logger.info(f"Generating embeddings for {len(texts)} chunks...")
            embeddings = self.model.encode(texts, show_progress_bar=True)
            
            # Add embeddings to chunks
            for i, chunk in enumerate(chunks):
                chunk['embedding'] = embeddings[i].tolist()
            
            logger.info("Successfully generated embeddings")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

    def process_uploaded_files(self, files_data: List[Dict]) -> List[Dict]:
        """
        Process uploaded files and return chunks with embeddings
        files_data: List of {name: str, content: str (base64)}
        """
        all_chunks = []
        
        for file_data in files_data:
            filename = file_data['name']
            
            # Skip non-React files
            if not filename.endswith(('.js', '.jsx', '.ts', '.tsx')):
                continue
                
            try:
                # Decode base64 content
                content = base64.b64decode(file_data['content']).decode('utf-8')
                
                # Skip empty files
                if not content.strip():
                    continue
                
                # Chunk the code
                chunks = self.smart_chunk_code(content, filename)
                all_chunks.extend(chunks)
                
            except Exception as e:
                logger.warning(f"Failed to process file {filename}: {e}")
                continue
        
        # Generate embeddings for all chunks
        if all_chunks:
            all_chunks = self.embed_chunks(all_chunks)
        
        logger.info(f"Processed {len(files_data)} files into {len(all_chunks)} embedded chunks")
        return all_chunks

# Global instance
_embedder = None

def get_embedder():
    """Get or create the global embedder instance"""
    global _embedder
    if _embedder is None:
        _embedder = CodeEmbedder()
    return _embedder