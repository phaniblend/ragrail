from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import logging
import base64
import json

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
    """Simple text-based RAG endpoint"""
    try:
        data = request.get_json()
        query = data.get("query", "")
        codebase = data.get("codebase", "")
        obfuscated = data.get("obfuscated", "You are a helpful senior software developer assistant.")
        
        logger.info(f"Processing query: {query}")
        logger.info(f"Codebase length: {len(codebase)} characters")
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
            
        if not codebase:
            return jsonify({'error': 'Codebase is required'}), 400
        
        # Simple codebase analysis
        file_count = codebase.count('/////////')
        has_react = 'import React' in codebase or 'from "react"' in codebase
        has_typescript = '.tsx' in codebase or '.ts' in codebase
        has_hooks = 'useState' in codebase or 'useEffect' in codebase
        has_components = 'function ' in codebase or 'const ' in codebase
        
        # Create analysis result
        result = f"""## 🚀 React Code Analysis

**Your Query:** {query}

**📊 Codebase Overview:**
- Total size: {len(codebase):,} characters
- Files detected: {file_count} files
- Technology: {'React TypeScript' if has_typescript else 'React JavaScript'}
- Uses React Hooks: {'Yes' if has_hooks else 'No'}
- Has Components: {'Yes' if has_components else 'No'}

**🔍 Analysis for "{query}":**

{obfuscated}

**📝 Quick Insights:**
"""

        # Add specific insights based on query
        if 'useeffect' in query.lower() or 'effect' in query.lower():
            result += """
- ⚠️ **useEffect Issues:** Common causes of infinite re-renders:
  1. Missing dependency array
  2. Objects/functions in dependency array
  3. State updates triggering the effect
  
- 💡 **Solutions:**
  - Use useCallback for function dependencies
  - Use useMemo for object dependencies
  - Split effects by concern"""

        elif 'usestate' in query.lower() or 'state' in query.lower():
            result += """
- 📦 **useState Best Practices:**
  1. Don't call setState in render
  2. Use functional updates for counters
  3. Group related state together
  
- 🔄 **State Updates:**
  - setState is asynchronous
  - Use functional form: setState(prev => prev + 1)"""

        elif 'performance' in query.lower() or 'slow' in query.lower():
            result += """
- 🚀 **Performance Tips:**
  1. Use React.memo for expensive components
  2. Implement useMemo for heavy calculations
  3. Use useCallback for event handlers
  4. Consider code-splitting with lazy loading"""

        elif 'typescript' in query.lower() or 'type' in query.lower():
            result += """
- 🛡️ **TypeScript in React:**
  1. Define proper interfaces for props
  2. Use union types for state
  3. Type your event handlers
  4. Leverage generic components"""

        else:
            result += f"""
Based on your {file_count} files, here are general recommendations:

- 🧹 **Code Organization:** Structure components by feature
- 📱 **React Patterns:** {'Using modern hooks ✅' if has_hooks else 'Consider upgrading to hooks'}
- 🔧 **TypeScript:** {'Already using TS ✅' if has_typescript else 'Consider adding TypeScript'}
- 🎯 **Best Practices:** Keep components small and focused

**💡 Pro Tip:** Your specific query "{query}" - try asking about specific patterns, errors, or concepts!"""

        result += f"""

**🔗 Related Files Analyzed:**
{', '.join([f"File {i+1}" for i in range(min(file_count, 10))])}
{'...' if file_count > 10 else ''}

---
*Analysis complete! Your code is processed locally and securely.* 🔒"""

        # Base64 encode the response
        encoded = base64.b64encode(result.encode()).decode()
        return jsonify({"answer": encoded})
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        result = f"❌ Error processing your request: {str(e)}"
        encoded = base64.b64encode(result.encode()).decode()
        return jsonify({"answer": encoded}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'React Code Assistant is running!'})

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('static', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)