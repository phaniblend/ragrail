Perfect! I can see you've started creating the `main.py` file. Now let me give you the complete content to paste in there:

[1 tool called]

**Copy this entire content and paste it into your `main.py` file on GitHub:**

```python
"""
Cursor AI Proxy Server
This acts as a hosted "Cursor AI" instance that your middleware can talk to
It aggregates multiple AI services to provide Cursor-like functionality
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
import json
import anthropic
import time
import uuid

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Create Flask app for the AI proxy
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global session storage
sessions = {}

class AIProxyService:
    def __init__(self):
        self.anthropic_client = None
        self.setup_clients()
    
    def setup_clients(self):
        """Setup AI service clients"""
        try:
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            if anthropic_key:
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
                logger.info("✅ Anthropic client initialized")
        except Exception as e:
            logger.warning(f"Anthropic setup failed: {e}")
    
    def analyze_component(self, component_code, task_type="test_generation"):
        """Analyze React component and generate appropriate response"""
        if task_type == "test_generation":
            return self.generate_unit_tests(component_code)
        else:
            return self.general_analysis(component_code)
    
    def generate_unit_tests(self, component_code):
        """Generate comprehensive unit tests for React component"""
        prompt = f"""You are an expert React testing specialist. Generate comprehensive unit tests with 90%+ coverage for this component.

COMPONENT CODE:
```typescript
{component_code}
```

Requirements:
1. Use Jest + React Testing Library + TypeScript
2. Mock all external dependencies properly
3. Test all state transitions and user interactions
4. Cover edge cases and error scenarios
5. Include proper setup/teardown
6. Target 90%+ code coverage
7. Return COMPLETE, runnable test file

Focus on:
- All hooks (useState, useEffect, custom hooks)
- Props validation and variations
- Conditional rendering paths
- Async operations and loading states
- Event handlers and user interactions
- Error boundaries and edge cases

Return only the complete test file code."""

        # Try Anthropic
        try:
            if self.anthropic_client:
                logger.info("🤖 Using Anthropic for test generation")
                response = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    temperature=0.1,
                    messages=[{"role": "user", "content": prompt}]
                )
                return {
                    'success': True,
                    'result': response.content[0].text,
                    'service': 'anthropic-claude',
                    'task': 'test_generation'
                }
        except Exception as e:
            logger.warning(f"Anthropic failed: {e}")
        
        # Fallback to local analysis
        return self.local_test_generation(component_code)
    
    def local_test_generation(self, component_code):
        """Fallback local test generation"""
        import re
        name_match = re.search(r'(?:function|const)\s+(\w+)', component_code)
        component_name = name_match.group(1) if name_match else 'Component'
        
        hooks = []
        if 'useState' in component_code:
            hooks.append('useState')
        if 'useEffect' in component_code:
            hooks.append('useEffect')
        if 'useIsMutating' in component_code:
            hooks.append('useIsMutating')
        
        tests = f"""import React from 'react';
import {{ render, screen, waitFor }} from '@testing-library/react';
import '@testing-library/jest-dom';
{f'import {{ useIsMutating }} from "@tanstack/react-query";' if 'useIsMutating' in hooks else ''}
import {component_name} from './index';

// Mock external dependencies
{f'jest.mock("@tanstack/react-query");' if 'useIsMutating' in hooks else ''}
{f'jest.mock("@prism-ui/react", () => ({{ PrismLoading: (props: any) => <div data-testid="prism-loading" {{...props}}>Loading...</div> }}));' if 'PrismLoading' in component_code else ''}

{f'const mockUseIsMutating = useIsMutating as jest.MockedFunction<typeof useIsMutating>;' if 'useIsMutating' in hooks else ''}

describe('{component_name}', () => {{
  const defaultProps = {{
    {f'mutationKey: ["test-mutation"],' if 'mutationKey' in component_code else ''}
  }};

  beforeEach(() => {{
    jest.clearAllMocks();
    {f'mockUseIsMutating.mockReturnValue(0);' if 'useIsMutating' in hooks else ''}
  }});

  it('should render without crashing', () => {{
    render(<{component_name} {{...defaultProps}} />);
    expect(screen.getByTestId('map-view-container')).toBeInTheDocument();
  }});

  {f'''it('should show loading when mutations active', async () => {{
    mockUseIsMutating.mockReturnValue(1);
    render(<{component_name} {{...defaultProps}} />);
    await waitFor(() => {{
      expect(screen.getByTestId('prism-loading')).toBeInTheDocument();
    }});
  }});

  it('should show map when not loading', () => {{
    mockUseIsMutating.mockReturnValue(0);
    render(<{component_name} {{...defaultProps}} />);
    expect(screen.getByTestId('map')).toBeInTheDocument();
  }});''' if 'useIsMutating' in hooks else ''}
}});"""

        return {
            'success': True,
            'result': tests,
            'service': 'local-analysis',
            'task': 'test_generation'
        }

# Global AI service instance
ai_service = AIProxyService()

@app.route('/health')
def health_check():
    """Health check for the AI proxy service"""
    return jsonify({
        'status': 'healthy',
        'service': 'cursor-ai-proxy',
        'anthropic_available': ai_service.anthropic_client is not None,
        'timestamp': time.time()
    })

@app.route('/api/cursor/analyze', methods=['POST'])
def cursor_analyze():
    """Main Cursor AI proxy endpoint"""
    try:
        data = request.get_json()
        
        component_code = data.get('component_code', '')
        task_type = data.get('task_type', 'test_generation')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not component_code:
            return jsonify({'error': 'Component code is required'}), 400
        
        logger.info(f"🎯 Cursor AI request - Task: {task_type}, Session: {session_id[:8]}")
        
        # Store session data
        sessions[session_id] = {
            'component_code': component_code,
            'task_type': task_type,
            'timestamp': time.time()
        }
        
        # Process with AI service
        result = ai_service.analyze_component(component_code, task_type)
        
        if result['success']:
            return jsonify({
                'success': True,
                'analysis': result['result'],
                'service_used': result['service'],
                'task_type': result['task'],
                'session_id': session_id,
                'timestamp': time.time()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'AI analysis failed',
                'session_id': session_id
            }), 500
            
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500

if __name__ == '__main__':
    print("🚀 Starting Cursor AI Proxy Server")
    print("==================================")
    print(f"🔑 Anthropic API: {'✅' if os.getenv('ANTHROPIC_API_KEY') else '❌'}")
    print("🌐 This server mimics Cursor AI functionality")
    print("🔄 Acts as proxy between your middleware and AI services")
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)
```
