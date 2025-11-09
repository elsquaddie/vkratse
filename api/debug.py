"""
Debug endpoint to check environment variables
"""
import os
import json


def handler(request):
    """Check if environment variables are loaded"""

    # Check which env vars are available
    env_status = {
        'TELEGRAM_BOT_TOKEN': 'SET' if os.getenv('TELEGRAM_BOT_TOKEN') else 'NOT SET',
        'ANTHROPIC_API_KEY': 'SET' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET',
        'SUPABASE_URL': 'SET' if os.getenv('SUPABASE_URL') else 'NOT SET',
        'SUPABASE_KEY': 'SET' if os.getenv('SUPABASE_KEY') else 'NOT SET',
        'SECRET_KEY': 'SET' if os.getenv('SECRET_KEY') else 'NOT SET',
    }

    # Show first 10 chars of token if set (for verification)
    token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    token_preview = token[:10] + '...' if token else 'NOT FOUND'

    result = {
        'status': 'ok',
        'env_vars': env_status,
        'telegram_token_preview': token_preview,
        'all_env_vars_set': all(v == 'SET' for v in env_status.values())
    }

    return {
        'statusCode': 200,
        'body': json.dumps(result, indent=2)
    }


def app(environ, start_response):
    """WSGI app for Vercel"""
    from werkzeug.wrappers import Request, Response

    request = Request(environ)
    result = handler(request)

    response = Response(
        result.get('body', '{}'),
        status=result.get('statusCode', 200),
        content_type='application/json'
    )
    return response(environ, start_response)
