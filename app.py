def try_cursor_ai_generation(component_code):
    """Try to use hosted Cursor AI proxy for test generation"""
    try:
        import requests
        
        # Get Cursor proxy URL from environment
        cursor_proxy_url = os.getenv('CURSOR_PROXY_URL', 'http://localhost:8080')
        
        logger.info(f"🔄 Calling hosted Cursor AI proxy at {cursor_proxy_url}")
        
        # Call the hosted Cursor AI proxy
        response = requests.post(
            f"{cursor_proxy_url}/api/cursor/analyze",
            json={
                'component_code': component_code,
                'task_type': 'test_generation',
                'session_id': str(uuid.uuid4())
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                logger.info(f"✅ Hosted Cursor AI successful via {data.get('service_used')}")
                
                return {
                    'tests': data['analysis'],
                    'analysis': f'Generated via hosted Cursor AI proxy ({data.get("service_used")})',
                    'coverage_estimate': '90%+',
                    'ai_source': 'hosted-cursor'
                }
        
        logger.warning("⚠️ Hosted Cursor AI proxy failed")
        return None
        
    except Exception as e:
        logger.warning(f"Hosted Cursor AI error: {e}")
        return None
