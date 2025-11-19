#!/usr/bin/env python3
"""
Script to check and set up Telegram webhook
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get bot token
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not found in environment!")
    print("Please set it in .env file or environment variables")
    sys.exit(1)

# Base URL for Telegram API
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def check_webhook():
    """Check current webhook status"""
    print("\n" + "="*60)
    print("📡 Checking current webhook status...")
    print("="*60)

    response = requests.get(f"{BASE_URL}/getWebhookInfo")

    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            webhook_info = data.get('result', {})

            print("\n✅ Current webhook info:")
            print(f"  URL: {webhook_info.get('url', 'NOT SET')}")
            print(f"  Pending updates: {webhook_info.get('pending_update_count', 0)}")
            print(f"  Last error date: {webhook_info.get('last_error_date', 'None')}")
            print(f"  Last error message: {webhook_info.get('last_error_message', 'None')}")

            return webhook_info
        else:
            print(f"❌ Error: {data.get('description', 'Unknown error')}")
            return None
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        return None


def set_webhook(webhook_url):
    """Set webhook to specified URL"""
    print("\n" + "="*60)
    print(f"🔧 Setting webhook to: {webhook_url}")
    print("="*60)

    response = requests.post(
        f"{BASE_URL}/setWebhook",
        json={'url': webhook_url}
    )

    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            print("\n✅ Webhook set successfully!")
            return True
        else:
            print(f"\n❌ Error: {data.get('description', 'Unknown error')}")
            return False
    else:
        print(f"\n❌ HTTP Error: {response.status_code}")
        return False


def delete_webhook():
    """Delete webhook (switch to polling mode)"""
    print("\n" + "="*60)
    print("🗑️ Deleting webhook...")
    print("="*60)

    response = requests.post(f"{BASE_URL}/deleteWebhook")

    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            print("\n✅ Webhook deleted successfully!")
            return True
        else:
            print(f"\n❌ Error: {data.get('description', 'Unknown error')}")
            return False
    else:
        print(f"\n❌ HTTP Error: {response.status_code}")
        return False


def main():
    """Main function"""
    print("\n🤖 Telegram Webhook Setup Tool")

    # Check current webhook
    webhook_info = check_webhook()

    if not webhook_info:
        print("\n❌ Failed to get webhook info. Check your bot token.")
        sys.exit(1)

    current_url = webhook_info.get('url', '')

    # Show menu
    print("\n" + "="*60)
    print("What would you like to do?")
    print("="*60)
    print("\n1. Set webhook to production URL (vkratse.vercel.app)")
    print("2. Set webhook to preview URL (current branch)")
    print("3. Set webhook to custom URL")
    print("4. Delete webhook")
    print("5. Exit")

    choice = input("\nEnter your choice (1-5): ").strip()

    if choice == '1':
        # Production URL
        webhook_url = "https://vkratse.vercel.app"
        set_webhook(webhook_url)
        print("\n✅ Done! Now check the webhook again:")
        check_webhook()

    elif choice == '2':
        # Preview URL (from logs)
        webhook_url = "https://vkratse-dnlhmeuwh-daniils-projects-0a6733a4.vercel.app"
        print(f"\n⚠️ Using preview URL from deployment logs")
        set_webhook(webhook_url)
        print("\n✅ Done! Now check the webhook again:")
        check_webhook()

    elif choice == '3':
        # Custom URL
        webhook_url = input("\nEnter webhook URL (e.g., https://your-domain.com): ").strip()
        if webhook_url.startswith('http'):
            set_webhook(webhook_url)
            print("\n✅ Done! Now check the webhook again:")
            check_webhook()
        else:
            print("\n❌ Invalid URL. Must start with http:// or https://")

    elif choice == '4':
        # Delete webhook
        confirm = input("\n⚠️ Are you sure you want to delete the webhook? (yes/no): ").strip().lower()
        if confirm == 'yes':
            delete_webhook()
            print("\n✅ Done! Now check the webhook again:")
            check_webhook()
        else:
            print("\n❌ Cancelled")

    elif choice == '5':
        print("\n👋 Bye!")

    else:
        print("\n❌ Invalid choice")


if __name__ == '__main__':
    main()
