"""
Minimal test handler to check if Vercel Python runtime works
"""

def handler(request):
    """Minimal test handler"""
    return {
        'statusCode': 200,
        'body': '{"status": "ok", "message": "Test handler works!"}'
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
