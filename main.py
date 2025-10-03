"""
Real Cursor AI Headless Server
Runs actual Cursor in headless mode and exposes it via API
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import subprocess
import tempfile
import shutil
import logging
import uuid
import time

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CursorHeadlessService:
    def __init__(self):
        self.workspace_dir = "/tmp/cursor_workspaces"
        self.sessions = {}
        self.setup_environment()
    
    def setup_environment(self):
        """Setup Cursor environment"""
        try:
            os.makedirs(self.workspace_dir, exist_ok=True)
            
            # Check if cursor is available
            result = subprocess.run(['cursor', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"✅ Cursor CLI available: {result.stdout.strip()}")
            else:
                logger.warning("⚠️ Cursor CLI not found")
                
        except Exception as e:
            logger.error(f"Environment setup failed: {e}")
    
    def create_session(self, session_id=None):
        """Create new Cursor session"""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        session_workspace = os.path.join(self.workspace_dir, session_id)
        os.makedirs(session_workspace, exist_ok=True)
        
        self.sessions[session_id] = {
            'workspace': session_workspace,
            'created': time.time(),
            'files': []
        }
        
        logger.info(f"Created Cursor session: {session_id}")
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
    
    def run_cursor_analysis(self, session_id, query):
        """Run real Cursor AI analysis"""
        try:
            workspace = self.sessions[session_id]['workspace']
            
            # Try cursor headless command
            cursor_cmd = [
                'cursor',
                '--headless',
                '--workspace', workspace,
                '--query', query
            ]
            
            logger.info(f"🤖 Running real Cursor AI")
            
            result = subprocess.run(
                cursor_cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=workspace
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return {
                    'success': True,
                    'analysis': result.stdout.strip(),
                    'service': 'cursor-headless'
                }
            else:
                return {
                    'success': False,
                    'error': 'Cursor AI not available on this server'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Cursor error: {str(e)}'
            }

cursor_service = CursorHeadlessService()

@app.route('/health')
def health_check():
    """Health check"""
    try:
        result = subprocess.run(['cursor', '--version'], capture_output=True, text=True, timeout=5)
        cursor_available = result.returncode == 0
        
        return jsonify({
            'status': 'healthy',
            'service': 'cursor-headless-server',
            'cursor_available': cursor_available,
            'active_sessions': len(cursor_service.sessions)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/cursor/analyze', methods=['POST'])
def cursor_analyze():
    """Main Cursor AI endpoint"""
    try:
        data = request.get_json()
        
        component_code = data.get('component_code', '')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not component_code:
            return jsonify({'error': 'Component code is required'}), 400
        
        logger.info(f"🎯 Real Cursor AI request")
        
        # Create session
        if session_id not in cursor_service.sessions:
            cursor_service.create_session(session_id)
        
        # Add component
        cursor_service.add_file_to_session(session_id, 'Component.tsx', component_code)
        
        # Run Cursor analysis
        query = """Generate comprehensive unit tests for this React component with 90%+ coverage using Jest and React Testing Library. Include proper mocks for all external dependencies."""
        
        result = cursor_service.run_cursor_analysis(session_id, query)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500

if __name__ == '__main__':
    print("🚀 Starting Real Cursor AI Headless Server")
    print("🎯 Running actual Cursor AI in headless mode")
    
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
