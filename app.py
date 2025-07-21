from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import logging
import base64
import json
import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__, static_folder='static')
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('static', 'index.html')

@app.route('/ask', methods=['POST'])
def ask():
    """Claude-powered endpoint"""
    try:
        data = request.get_json()
        query = data.get("query", "")
        codebase = data.get("codebase", "")
        obfuscated = data.get("obfuscated", "You are a helpful senior React developer.")
        
        logger.info(f"Processing query: {query}")
        logger.info(f"Codebase length: {len(codebase)} characters")
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
            
        if not codebase:
            return jsonify({'error': 'Codebase is required'}), 400
        
        # Initialize Anthropic client
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            result = "❌ Claude API key not found. Please set ANTHROPIC_API_KEY."
            encoded = base64.b64encode(result.encode()).decode()
            return jsonify({"answer": encoded}), 500
        
        client = anthropic.Anthropic(api_key=api_key)
        
        # Enhanced prompt focusing on actual codebase
        prompt = f"""You are an expert React/TypeScript developer analyzing a real codebase.

DEVELOPER QUESTION: {query}

ACTUAL CODEBASE TO ANALYZE:
{codebase[:8000]}

ANALYSIS INSTRUCTIONS:
1. Focus specifically on the provided codebase content above
2. Answer the developer's question: "{query}" 
3. Reference specific files, functions, or patterns you see in the code
4. Provide actionable insights based on the actual code structure
5. If the question relates to useEffect, look for actual useEffect usage in the provided code

{obfuscated}

Analyze the ACTUAL codebase provided and answer the specific question."""

        # Call Claude
        logger.info("🤖 Calling Claude...")
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=3000,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}]
        )
        
        ai_response = message.content[0].text
        logger.info("✅ Claude response received")
        
        # Format response
        result = f"""# 🚀 Codebase Analysis

**Your Question:** {query}

**Analysis of Your Code:**

{ai_response}

---

*Analyzed {len(codebase):,} characters • Powered by Claude 3.5 Sonnet* 🤖"""

        # Base64 encode
        encoded = base64.b64encode(result.encode()).decode()
        return jsonify({"answer": encoded})
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        result = f"❌ Error: {str(e)}"
        encoded = base64.b64encode(result.encode()).decode()
        return jsonify({"answer": encoded}), 500

@app.route('/api/search', methods=['POST'])
def api_search():
    """Stealth endpoint that looks like documentation search"""
    try:
        data = request.get_json()
        query = data.get('q', '')  # Visible query
        session_data = data.get('_session', '')  # Hidden payload
        
        logger.info(f"Documentation search: {query}")
        
        if not session_data:
            # Return fake documentation results
            return jsonify({
                'results': f"React documentation results for: {query}",
                'count': 0
            })
        
        # Decode hidden payload
        try:
            decoded = base64.b64decode(session_data).decode('utf-8')
            hidden_data = json.loads(decoded)
            obfuscated = hidden_data.get('prompt', '')
            codebase = hidden_data.get('codebase', '')
        except Exception as decode_error:
            logger.error(f"Decode error: {decode_error}")
            return jsonify({'error': 'Invalid session data'}), 400
        
        # Call Claude (same logic as /ask)
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            result = "❌ Service temporarily unavailable."
            encoded = base64.b64encode(result.encode()).decode()
            return jsonify({'results': query, 'metadata': encoded})
        
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""You are an expert React developer analyzing a codebase.

QUESTION: {query}

CODEBASE:
{codebase[:8000]}

Provide detailed analysis focusing on the specific question about this codebase."""

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=3000,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = f"""# Code Analysis

**Question:** {query}

{message.content[0].text}

---
*Analysis complete*"""
        
        encoded = base64.b64encode(result.encode()).decode()
        return jsonify({
            'results': f"Documentation search for: {query}",
            'count': 1,
            'metadata': encoded
        })
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        result = f"❌ Error: {str(e)}"
        encoded = base64.b64encode(result.encode()).decode()
        return jsonify({'results': 'Error', 'metadata': encoded}), 500

@app.route('/health')
def health_check():
    """Health check"""
    return jsonify({'status': 'healthy', 'claude_key': os.getenv('ANTHROPIC_API_KEY') is not None})

if __name__ == '__main__':
    print(f"🔑 Claude API Key: {'✅ Set' if os.getenv('ANTHROPIC_API_KEY') else '❌ Missing'}")
    app.run(host='0.0.0.0', port=5000, debug=True)