"""
DIAGNOSTIC VERSION - Step 2: Pure WSGI (NO Werkzeug)
Проверяем работу без внешних зависимостей
"""

import sys
import json
from datetime import datetime


def log(message):
    """Print log with timestamp to stderr"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", file=sys.stderr, flush=True)


# ================================================
# CHECKPOINT 1: Module loaded
# ================================================
log("✅ CHECKPOINT 1: Module api/index.py loaded successfully")


# ================================================
# Pure WSGI Application (NO external dependencies)
# ================================================
def application(environ, start_response):
    """
    Pure WSGI application - Vercel Python runtime calls this

    This is the absolute minimum WSGI app possible:
    - No Werkzeug
    - No Flask
    - Just pure WSGI spec
    """
    try:
        log("✅ CHECKPOINT 2: WSGI application() called")

        # Get request info from WSGI environ
        method = environ.get('REQUEST_METHOD', 'UNKNOWN')
        path = environ.get('PATH_INFO', 'UNKNOWN')

        log(f"✅ CHECKPOINT 3: Request = {method} {path}")

        # Prepare response
        status = '200 OK'
        headers = [
            ('Content-Type', 'application/json'),
            ('X-Checkpoint', '4')
        ]

        log("✅ CHECKPOINT 4: Preparing response")

        # Start response
        start_response(status, headers)

        log("✅ CHECKPOINT 5: start_response() called")

        # Response body (must be bytes)
        response_data = {
            'status': 'ok',
            'checkpoint': 5,
            'message': 'Pure WSGI working!',
            'method': method,
            'path': path
        }

        response_body = json.dumps(response_data).encode('utf-8')

        log("✅ CHECKPOINT 6: Response ready, returning")

        # WSGI spec: return iterable of bytes
        return [response_body]

    except Exception as e:
        log(f"❌ ERROR in WSGI app: {e}")

        # Error response
        status = '500 Internal Server Error'
        headers = [('Content-Type', 'application/json')]
        start_response(status, headers)

        error_body = json.dumps({
            'error': str(e),
            'checkpoint': 'failed'
        }).encode('utf-8')

        return [error_body]


# Vercel looks for 'app' or 'application' in WSGI mode
app = application

log("✅ CHECKPOINT 7: Module fully loaded, 'app' and 'application' defined")


# ================================================
# Local testing with minimal Flask
# ================================================
if __name__ == '__main__':
    log("🧪 Running in local test mode")

    # Test the WSGI app directly
    class MockWSGI:
        def __init__(self):
            self.status = None
            self.headers = None

        def start_response(self, status, headers):
            self.status = status
            self.headers = headers

    # Test request
    mock = MockWSGI()
    environ = {
        'REQUEST_METHOD': 'GET',
        'PATH_INFO': '/test'
    }

    result = application(environ, mock.start_response)

    print(f"\nTest result:")
    print(f"Status: {mock.status}")
    print(f"Headers: {mock.headers}")
    print(f"Body: {b''.join(result).decode('utf-8')}")
