"""
Debug endpoint to check environment variables
SIMPLIFIED VERSION - minimal imports
"""
import os


def handler(event, context):
    """Check if environment variables are loaded - AWS Lambda style"""

    # Check which env vars are available
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY', '')
    supabase_url = os.getenv('SUPABASE_URL', '')
    supabase_key = os.getenv('SUPABASE_KEY', '')
    secret_key = os.getenv('SECRET_KEY', '')

    # Build response
    lines = []
    lines.append("=== Environment Variables Debug ===")
    lines.append("")
    lines.append(f"TELEGRAM_BOT_TOKEN: {'SET (' + telegram_token[:10] + '...)' if telegram_token else 'NOT SET'}")
    lines.append(f"ANTHROPIC_API_KEY: {'SET (' + anthropic_key[:10] + '...)' if anthropic_key else 'NOT SET'}")
    lines.append(f"SUPABASE_URL: {'SET (' + supabase_url[:30] + '...)' if supabase_url else 'NOT SET'}")
    lines.append(f"SUPABASE_KEY: {'SET (' + supabase_key[:10] + '...)' if supabase_key else 'NOT SET'}")
    lines.append(f"SECRET_KEY: {'SET' if secret_key else 'NOT SET'}")
    lines.append("")

    all_set = all([telegram_token, anthropic_key, supabase_url, supabase_key, secret_key])
    lines.append(f"All env vars set: {all_set}")

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/plain'},
        'body': '\n'.join(lines)
    }
