"""
Real Cursor AI Headless Server
Uses Anthropic Claude as the backend AI (since actual Cursor CLI can't run on Render)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
import uuid
import time

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CursorAIService:
    def __init__(self):
        self.workspace_dir = "/tmp/cursor_workspaces"
        self.sessions = {}
        self.anthropic_client = None
        self.setup_environment()
    
    def setup_environment(self):
        """Setup environment - use Anthropic as Cursor AI backend"""
        try:
            os.makedirs(self.workspace_dir, exist_ok=True)
            
            # Initialize Anthropic client
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            if anthropic_key:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
                logger.info("✅ Cursor AI backend ready (powered by Anthropic Claude)")
            else:
                logger.error("❌ ANTHROPIC_API_KEY not found")
                
        except Exception as e:
            logger.error(f"Environment setup failed: {e}")
    
    def create_session(self, session_id=None):
        """Create new session"""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        session_workspace = os.path.join(self.workspace_dir, session_id)
        os.makedirs(session_workspace, exist_ok=True)
        
        self.sessions[session_id] = {
            'workspace': session_workspace,
            'created': time.time(),
            'files': []
        }
        
        logger.info(f"Created session: {session_id}")
        return session_id
    
    def add_file_to_session(self, session_id, filename, content):
        """Add file to session"""
        if session_id not in self.sessions:
            session_id = self.create_session(session_id)
        
        workspace = self.sessions[session_id]['workspace']
        file_path = os.path.join(workspace, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.sessions[session_id]['files'].append(filename)
        return file_path
    
    def generate_tests_with_cursor_ai(self, component_code, session_id):
        """Generate tests using Anthropic Claude (Cursor AI backend)"""
        try:
            if not self.anthropic_client:
                return {
                    'success': False,
                    'error': 'Cursor AI backend not available'
                }
            
            # Cursor AI style prompt for comprehensive test generation
            prompt = f"""You are Cursor AI, an expert code analysis and testing specialist. Generate comprehensive unit tests for this React component with 90%+ coverage.

COMPONENT CODE:
```typescript
{component_code}
```

CURSOR AI ANALYSIS REQUIREMENTS:
1. Use Jest + React Testing Library + TypeScript
2. Mock ALL external dependencies properly (@tanstack/react-query, @prism-ui/react, etc.)
3. Test ALL state transitions and user interactions
4. Cover edge cases and error scenarios thoroughly
5. Include proper setup/teardown with beforeEach/afterEach
6. Target 90%+ code coverage with comprehensive test scenarios
7. Return COMPLETE, immediately runnable test file

FOCUS AREAS (Cursor AI Analysis):
- All React hooks (useState, useEffect, useIsMutating, etc.)
- Props validation and all prop variations
- Conditional rendering paths (loading vs loaded states)
- Async operations and loading state management
- Event handlers and user interactions
- Error boundaries and edge cases
- Data attributes and accessibility

TESTING STRATEGY:
- Test component in isolation with proper mocks
- Test all code branches and conditional logic
- Test state changes and their effects on rendering
- Test props changes and their impact
- Test error scenarios and edge cases

Return ONLY the complete test file code that I can immediately copy and run."""

            logger.info("🤖 Cursor AI generating comprehensive tests via Claude")
            
            # Call Claude with Cursor AI persona
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return {
                'success': True,
                'analysis': response.content[0].text,
                'service': 'cursor-ai-claude',
                'session_id': session_id
            }
            
        except Exception as e:
            logger.error(f"Cursor AI generation error: {e}")
            return {
                'success': False,
                'error': f'Cursor AI error: {str(e)}',
                'session_id': session_id
            }

# Global service instance
cursor_ai_service = CursorAIService()

@app.route('/health')
def health_check():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'cursor-ai-proxy',
        'anthropic_available': cursor_ai_service.anthropic_client is not None,
        'active_sessions': len(cursor_ai_service.sessions),
        'backend': 'anthropic-claude'
    })

@app.route('/api/cursor/analyze', methods=['POST'])
def cursor_analyze():
    """Main Cursor AI endpoint"""
    try:
        data = request.get_json()
        
        component_code = data.get('component_code', '')
        task_type = data.get('task_type', 'test_generation')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not component_code:
            return jsonify({'error': 'Component code is required'}), 400
        
        logger.info(f"🎯 Cursor AI request - Task: {task_type}")
        
        # Create session if needed
        if session_id not in cursor_ai_service.sessions:
            cursor_ai_service.create_session(session_id)
        
        # Add component to session
        cursor_ai_service.add_file_to_session(session_id, 'Component.tsx', component_code)
        
        # Generate tests with Cursor AI
        result = cursor_ai_service.generate_tests_with_cursor_ai(component_code, session_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500

@app.route('/api/cursor/session/<session_id>', methods=['DELETE'])
def cleanup_session(session_id):
    """Cleanup session"""
    try:
        if session_id in cursor_ai_service.sessions:
            import shutil
            workspace = cursor_ai_service.sessions[session_id]['workspace']
            shutil.rmtree(workspace, ignore_errors=True)
            del cursor_ai_service.sessions[session_id]
            logger.info(f"🗑️ Cleaned up session: {session_id}")
        
        return jsonify({'success': True, 'message': 'Session cleaned up'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Cursor AI Proxy Server")
    print("==================================")
    print("🎯 Backend: Anthropic Claude (Cursor AI compatible)")
    print("🔄 Provides Cursor AI functionality via Claude")
    
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
