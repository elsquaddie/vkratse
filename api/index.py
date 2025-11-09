"""
DIAGNOSTIC VERSION - Step 3: Adding project imports
Постепенно добавляем импорты проектных модулей
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
# CHECKPOINT 2: Import telegram
# ================================================
try:
    from telegram import Update
    from telegram.ext import Application
    log("✅ CHECKPOINT 2: telegram imports successful")
except Exception as e:
    log(f"❌ CHECKPOINT 2 FAILED: telegram import error: {e}")

# ================================================
# CHECKPOINT 3: Import config
# ================================================
try:
    import config
    from config import logger
    log("✅ CHECKPOINT 3: config import successful")
except Exception as e:
    log(f"❌ CHECKPOINT 3 FAILED: config import error: {e}")

# ================================================
# CHECKPOINT 4: Import services
# ================================================
try:
    from services import DBService
    log("✅ CHECKPOINT 4: services import successful")
except Exception as e:
    log(f"❌ CHECKPOINT 4 FAILED: services import error: {e}")

# ================================================
# CHECKPOINT 5: Import modules
# ================================================
try:
    from modules.commands import start_command, help_command
    from modules.summaries import summary_command, summary_callback
    from modules.judge import judge_command
    from modules.personalities import (
        personality_command,
        personality_callback,
        receive_personality_name,
        receive_personality_description,
        cancel_personality_creation,
        AWAITING_NAME,
        AWAITING_DESCRIPTION
    )
    log("✅ CHECKPOINT 5: modules import successful")
except Exception as e:
    log(f"❌ CHECKPOINT 5 FAILED: modules import error: {e}")

log("✅ CHECKPOINT 6: All imports completed")


# ================================================
# Pure WSGI Application
# ================================================
def application(environ, start_response):
    """
    Pure WSGI application - Vercel Python runtime calls this
    """
    try:
        log("✅ CHECKPOINT 7: WSGI application() called")

        # Get request info from WSGI environ
        method = environ.get('REQUEST_METHOD', 'UNKNOWN')
        path = environ.get('PATH_INFO', 'UNKNOWN')

        log(f"✅ CHECKPOINT 8: Request = {method} {path}")

        # Prepare response
        status = '200 OK'
        headers = [
            ('Content-Type', 'application/json'),
            ('X-Checkpoint', '9')
        ]

        log("✅ CHECKPOINT 9: Preparing response")

        # Start response
        start_response(status, headers)

        log("✅ CHECKPOINT 10: start_response() called")

        # Response body (must be bytes)
        response_data = {
            'status': 'ok',
            'checkpoint': 10,
            'message': 'WSGI with imports working!',
            'method': method,
            'path': path
        }

        response_body = json.dumps(response_data).encode('utf-8')

        log("✅ CHECKPOINT 11: Response ready, returning")

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

log("✅ CHECKPOINT 12: Module fully loaded, 'app' and 'application' defined")


# ================================================
# Local testing
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
