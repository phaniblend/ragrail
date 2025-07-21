import re
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class CodeRetriever:
    def __init__(self):
        """Initialize the code retriever"""
        self.react_keywords = {
            'hooks': ['useState', 'useEffect', 'useContext', 'useReducer', 'useMemo', 'useCallback', 'useRef'],
            'lifecycle': ['componentDidMount', 'componentWillUnmount', 'componentDidUpdate'],
            'patterns': ['HOC', 'render props', 'context', 'provider', 'consumer'],
            'issues': ['infinite loop', 're-render', 'memory leak', 'stale closure', 'dependency array']
        }

    def enhance_query(self, query: str) -> List[str]:
        """
        Enhance the user query with related terms for better retrieval
        """
        enhanced_queries = [query]
        query_lower = query.lower()
        
        # Add React-specific enhancements
        if 'useeffect' in query_lower:
            enhanced_queries.extend([
                query + ' dependency array',
                query + ' cleanup function',
                'useEffect infinite loop'
            ])
        
        if 'usestate' in query_lower:
            enhanced_queries.extend([
                query + ' state update',
                query + ' functional update',
                'useState asynchronous'
            ])
        
        if 'infinite' in query_lower or 'loop' in query_lower:
            enhanced_queries.extend([
                'useEffect dependency array',
                'missing dependencies',
                'useCallback memoization'
            ])
        
        if 'render' in query_lower:
            enhanced_queries.extend([
                'React.memo optimization',
                'useMemo performance',
                'unnecessary re-render'
            ])
        
        # Add TypeScript specific terms
        if any(ts_term in query_lower for ts_term in ['type', 'interface', 'generic']):
            enhanced_queries.extend([
                query + ' TypeScript',
                query + ' type definition'
            ])
        
        return enhanced_queries

    def retrieve_relevant_chunks(self, query: str, session_id: str, max_chunks: int = 8) -> List[Dict]:
        """
        Retrieve the most relevant code chunks for a query
        """
        try:
            from .chromadb_store import get_vector_store
            vector_store = get_vector_store()
            
            # Enhance the query
            enhanced_queries = self.enhance_query(query)
            
            all_chunks = []
            seen_chunks = set()
            
            # Search with each enhanced query
            for enhanced_query in enhanced_queries[:3]:  # Limit to avoid too many searches
                chunks = vector_store.search_similar_chunks(
                    enhanced_query, 
                    session_id, 
                    top_k=max_chunks
                )
                
                # Add unique chunks
                for chunk in chunks:
                    chunk_key = f"{chunk['filename']}:{chunk['start_line']}"
                    if chunk_key not in seen_chunks:
                        chunk['relevance_score'] = self._calculate_relevance(query, chunk)
                        all_chunks.append(chunk)
                        seen_chunks.add(chunk_key)
            
            # Sort by relevance and distance
            all_chunks.sort(key=lambda x: (x['relevance_score'], -x['distance']), reverse=True)
            
            # Return top chunks
            result_chunks = all_chunks[:max_chunks]
            
            logger.info(f"Retrieved {len(result_chunks)} relevant chunks for query: {query[:50]}...")
            return result_chunks
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []

    def _calculate_relevance(self, query: str, chunk: Dict) -> float:
        """
        Calculate relevance score based on query and chunk content
        """
        score = 0.0
        query_lower = query.lower()
        chunk_text = chunk['text'].lower()
        chunk_type = chunk['metadata'].get('type', '')
        
        # Exact keyword matches
        query_words = query_lower.split()
        for word in query_words:
            if word in chunk_text:
                score += 1.0
        
        # React-specific bonuses
        if 'useeffect' in query_lower and 'useeffect' in chunk_text:
            score += 2.0
        
        if 'usestate' in query_lower and 'usestate' in chunk_text:
            score += 2.0
        
        if 'infinite' in query_lower and ('dependency' in chunk_text or 'useeffect' in chunk_text):
            score += 1.5
        
        # Type-based bonuses
        if chunk_type == 'react_hook' and any(hook in query_lower for hook in ['hook', 'useeffect', 'usestate']):
            score += 1.0
        
        if chunk_type == 'react_component' and 'component' in query_lower:
            score += 1.0
        
        if chunk_type == 'typescript_definition' and any(ts_term in query_lower for ts_term in ['type', 'interface']):
            score += 1.0
        
        return score

    def format_context_for_ai(self, chunks: List[Dict], query: str) -> str:
        """
        Format retrieved chunks into context for the AI model
        """
        if not chunks:
            return "No relevant code found."
        
        context_parts = []
        context_parts.append(f"## Relevant Code for Query: '{query}'\n")
        
        for i, chunk in enumerate(chunks, 1):
            filename = chunk['filename']
            start_line = chunk['metadata'].get('start_line', 0)
            end_line = chunk['metadata'].get('end_line', 0)
            chunk_type = chunk['metadata'].get('type', 'code')
            
            # Extract just the code part (remove filename prefix)
            text_lines = chunk['text'].split('\n')
            code_text = '\n'.join(text_lines[1:]) if text_lines[0] == filename else chunk['text']
            
            context_parts.append(f"### {i}. {filename} (lines {start_line}-{end_line}) - {chunk_type}")
            context_parts.append(f"```{chunk['metadata'].get('language', 'javascript')}")
            context_parts.append(code_text.strip())
            context_parts.append("```\n")
        
        return '\n'.join(context_parts)

    def get_context_summary(self, chunks: List[Dict]) -> Dict:
        """
        Get a summary of the retrieved context
        """
        if not chunks:
            return {'total_chunks': 0, 'files': [], 'types': []}
        
        files = list(set(chunk['filename'] for chunk in chunks))
        types = list(set(chunk['metadata'].get('type', 'unknown') for chunk in chunks))
        
        return {
            'total_chunks': len(chunks),
            'files': files,
            'types': types,
            'average_relevance': sum(chunk.get('relevance_score', 0) for chunk in chunks) / len(chunks)
        }

# Global instance
_retriever = None

def get_retriever():
    """Get or create the global retriever instance"""
    global _retriever
    if _retriever is None:
        _retriever = CodeRetriever()
    return _retriever