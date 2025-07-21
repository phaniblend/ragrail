import chromadb
from chromadb.config import Settings
import os
import uuid
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class CodeVectorStore:
    def __init__(self, persist_directory: str = "data/vector_store"):
        """Initialize ChromaDB with persistence"""
        try:
            # Ensure directory exists
            os.makedirs(persist_directory, exist_ok=True)
            
            # Initialize ChromaDB client with persistence
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            self.collection_name = "react_code_chunks"
            self.collection = self._get_or_create_collection()
            
            logger.info(f"ChromaDB initialized with persistence at {persist_directory}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def _get_or_create_collection(self):
        """Get existing collection or create new one"""
        try:
            # Try to get existing collection
            collection = self.client.get_collection(self.collection_name)
            logger.info(f"Using existing collection: {self.collection_name}")
        except:
            # Create new collection
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "React code chunks with embeddings"}
            )
            logger.info(f"Created new collection: {self.collection_name}")
        
        return collection

    def store_chunks(self, chunks: List[Dict], session_id: Optional[str] = None) -> str:
        """
        Store code chunks in the vector database
        Returns session_id for future retrieval
        """
        if not chunks:
            logger.warning("No chunks to store")
            return ""
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        try:
            # Prepare data for ChromaDB
            documents = []
            embeddings = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                # Create unique ID
                chunk_id = f"{session_id}_{i}"
                
                # Document text (what gets searched)
                doc_text = f"{chunk['filename']}\n{chunk['text']}"
                
                # Metadata (additional info)
                metadata = {
                    'filename': chunk['filename'],
                    'start_line': chunk.get('start_line', 0),
                    'end_line': chunk.get('end_line', 0),
                    'language': chunk.get('language', 'javascript'),
                    'type': chunk.get('type', 'code_block'),
                    'session_id': session_id
                }
                
                documents.append(doc_text)
                embeddings.append(chunk['embedding'])
                metadatas.append(metadata)
                ids.append(chunk_id)
            
            # Store in ChromaDB
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Stored {len(chunks)} chunks with session_id: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to store chunks: {e}")
            raise

    def search_similar_chunks(self, query: str, session_id: str, top_k: int = 5) -> List[Dict]:
        """
        Search for similar code chunks using semantic similarity
        """
        try:
            # Import embedder to encode query
            from .embedder import get_embedder
            embedder = get_embedder()
            
            # Encode the query
            query_embedding = embedder.model.encode([query])[0].tolist()
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={"session_id": session_id}  # Filter by session
            )
            
            # Format results
            chunks = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    chunk = {
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if results['distances'] else 0,
                        'filename': results['metadatas'][0][i]['filename'],
                        'type': results['metadatas'][0][i]['type'],
                        'start_line': results['metadatas'][0][i]['start_line'],
                        'end_line': results['metadatas'][0][i]['end_line']
                    }
                    chunks.append(chunk)
            
            logger.info(f"Found {len(chunks)} similar chunks for query: {query[:50]}...")
            return chunks
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_session_stats(self, session_id: str) -> Dict:
        """Get statistics for a session"""
        try:
            results = self.collection.get(
                where={"session_id": session_id}
            )
            
            total_chunks = len(results['ids']) if results['ids'] else 0
            
            # Count by file type
            file_types = {}
            if results['metadatas']:
                for metadata in results['metadatas']:
                    file_type = metadata.get('type', 'unknown')
                    file_types[file_type] = file_types.get(file_type, 0) + 1
            
            return {
                'session_id': session_id,
                'total_chunks': total_chunks,
                'file_types': file_types
            }
            
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {'session_id': session_id, 'total_chunks': 0, 'file_types': {}}

    def cleanup_old_sessions(self, keep_recent: int = 10):
        """Clean up old sessions to save space"""
        try:
            # Get all sessions
            all_results = self.collection.get()
            if not all_results['metadatas']:
                return
            
            # Group by session_id
            sessions = {}
            for metadata in all_results['metadatas']:
                session_id = metadata.get('session_id')
                if session_id:
                    if session_id not in sessions:
                        sessions[session_id] = []
                    sessions[session_id].append(metadata)
            
            # Keep only recent sessions
            session_ids = list(sessions.keys())
            if len(session_ids) > keep_recent:
                old_sessions = session_ids[:-keep_recent]
                
                for old_session in old_sessions:
                    # Delete chunks from old session
                    self.collection.delete(
                        where={"session_id": old_session}
                    )
                    logger.info(f"Cleaned up old session: {old_session}")
                    
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

    def reset_database(self):
        """Reset the entire database (use with caution!)"""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self._get_or_create_collection()
            logger.info("Database reset successfully")
        except Exception as e:
            logger.error(f"Failed to reset database: {e}")

# Global instance
_vector_store = None

def get_vector_store():
    """Get or create the global vector store instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = CodeVectorStore()
    return _vector_store