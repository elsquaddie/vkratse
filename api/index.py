"""
DIAGNOSTIC VERSION - Step 1: Minimal Vercel Handler
Проверяем базовую работоспособность Vercel
"""

import sys
import traceback
from datetime import datetime


def log(message):
    """Print log with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", file=sys.stderr, flush=True)
    return message


# ================================================
# CHECKPOINT 1: Module loaded
# ================================================
log("✅ CHECKPOINT 1: Module api/index.py loaded successfully")


def handler(request):
    """
    Minimal Vercel handler for diagnostics
    Returns OK on any request
    """
    try:
        log("✅ CHECKPOINT 2: Handler function called")

        # Get request method
        method = getattr(request, 'method', 'UNKNOWN')
        log(f"✅ CHECKPOINT 3: Request method = {method}")

        # Get request path
        path = getattr(request, 'path', 'UNKNOWN')
        log(f"✅ CHECKPOINT 4: Request path = {path}")

        # Try to read request body
        try:
            if hasattr(request, 'get_json'):
                body = request.get_json(force=True, silent=True)
                log(f"✅ CHECKPOINT 5: Request body parsed (Flask): {type(body)}")
            elif hasattr(request, 'json'):
                body = request.json
                log(f"✅ CHECKPOINT 5: Request body parsed (Vercel): {type(body)}")
            else:
                body_raw = request.body if hasattr(request, 'body') else request.data
                log(f"✅ CHECKPOINT 5: Request body raw: {type(body_raw)}")
                body = None
        except Exception as e:
            log(f"⚠️ CHECKPOINT 5: Could not parse body: {e}")
            body = None

        log("✅ CHECKPOINT 6: All checks passed, returning 200 OK")

        # Return success
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': '{"status": "ok", "checkpoint": 6, "message": "Vercel handler working!"}'
        }

    except Exception as e:
        error_msg = f"❌ ERROR: {str(e)}"
        error_trace = traceback.format_exc()
        log(error_msg)
        log(error_trace)

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': f'{{"error": "{str(e)}", "checkpoint": "failed"}}'
        }


# ================================================
# WSGI Application for Vercel
# ================================================
def app(environ, start_response):
    """WSGI app for Vercel Python runtime"""
    try:
        log("✅ CHECKPOINT 7: WSGI app() called")

        # Import Werkzeug
        from werkzeug.wrappers import Request, Response
        log("✅ CHECKPOINT 8: Werkzeug imported")

        # Create request object
        request = Request(environ)
        log(f"✅ CHECKPOINT 9: Request object created: {request.method} {request.path}")

        # Call handler
        result = handler(request)
        log("✅ CHECKPOINT 10: Handler returned result")

        # Create response
        response = Response(
            result.get('body', '{}'),
            status=result.get('statusCode', 200),
            headers=result.get('headers', {'Content-Type': 'application/json'})
        )
        log("✅ CHECKPOINT 11: Response object created")

        return response(environ, start_response)

    except Exception as e:
        error_msg = f"❌ WSGI ERROR: {str(e)}"
        error_trace = traceback.format_exc()
        log(error_msg)
        log(error_trace)

        # Return error response
        error_response = Response(
            f'{{"error": "{str(e)}", "wsgi": true}}',
            status=500,
            content_type='application/json'
        )
        return error_response(environ, start_response)


log("✅ CHECKPOINT 12: Module fully loaded and ready")


# For local testing
if __name__ == '__main__':
    log("🧪 Running in local test mode")

    from flask import Flask, request as flask_request

    flask_app = Flask(__name__)

    @flask_app.route('/', methods=['GET', 'POST'])
    def test_handler():
        log("Flask test route called")
        return handler(flask_request)

    @flask_app.route('/health', methods=['GET'])
    def health():
        log("Health check called")
        return {'status': 'ok', 'mode': 'local_test'}

    log("Starting Flask test server on port 8000...")
    flask_app.run(host='0.0.0.0', port=8000, debug=True)
