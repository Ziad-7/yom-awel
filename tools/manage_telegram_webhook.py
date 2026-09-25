"""Safe Telegram webhook management utility.

Never embeds, logs, or prints bot tokens or secret values.
Reads secrets from environment variables or secure prompts.
"""

import argparse
import getpass
import os
import sys

import httpx

DEFAULT_WEBHOOK_URL = "https://yom-awel-api.vercel.app/api/v1/telegram/webhook"


def get_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        token = getpass.getpass("Enter TELEGRAM_BOT_TOKEN: ").strip()
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN is required.", file=sys.stderr)
        sys.exit(1)
    return token


def get_secret() -> str:
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    if not secret:
        secret = getpass.getpass("Enter TELEGRAM_WEBHOOK_SECRET: ").strip()
    if not secret:
        print("Error: TELEGRAM_WEBHOOK_SECRET is required.", file=sys.stderr)
        sys.exit(1)
    return secret


def cmd_info(token: str) -> None:
    url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    resp = httpx.get(url, timeout=15)
    data = resp.json()
    if not data.get("ok"):
        print(f"Error from Telegram API: {data.get('description')}", file=sys.stderr)
        sys.exit(1)
    result = data.get("result", {})
    print("Telegram Webhook Info:")
    print(f"  Webhook URL: {result.get('url') or '(none)'}")
    print(f"  Has Custom Certificate: {result.get('has_custom_certificate')}")
    print(f"  Pending Update Count: {result.get('pending_update_count', 0)}")
    print(f"  Allowed Updates: {result.get('allowed_updates', [])}")
    last_error_date = result.get("last_error_date")
    last_error_message = result.get("last_error_message")
    if last_error_date or last_error_message:
        print(f"  Last Error Date: {last_error_date}")
        print(f"  Last Error Message: {last_error_message}")
    else:
        print("  Last Error: None (all healthy)")


def cmd_set(
    token: str, secret: str, webhook_url: str, drop_pending: bool = False
) -> None:
    api_url = f"https://api.telegram.org/bot{token}/setWebhook"
    payload = {
        "url": webhook_url,
        "allowed_updates": ["message"],
        "secret_token": secret,
        "drop_pending_updates": drop_pending,
    }
    resp = httpx.post(api_url, json=payload, timeout=15)
    data = resp.json()
    if not data.get("ok"):
        print(f"Failed to set webhook: {data.get('description')}", file=sys.stderr)
        sys.exit(1)
    print(f"Webhook registered successfully to {webhook_url}")
    print("Verifying via getWebhookInfo...")
    cmd_info(token)


def cmd_delete(token: str, drop_pending: bool = False) -> None:
    api_url = f"https://api.telegram.org/bot{token}/deleteWebhook"
    payload = {"drop_pending_updates": drop_pending}
    resp = httpx.post(api_url, json=payload, timeout=15)
    data = resp.json()
    if not data.get("ok"):
        print(f"Failed to delete webhook: {data.get('description')}", file=sys.stderr)
        sys.exit(1)
    print("Webhook deleted successfully.")
    cmd_info(token)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Yom Awel Telegram Webhook")
    subparsers = parser.add_subparsers(dest="action", required=True)

    subparsers.add_parser("info", help="Get current webhook info")

    set_p = subparsers.add_parser("set", help="Register webhook URL")
    set_p.add_argument("--url", default=DEFAULT_WEBHOOK_URL, help="Target webhook URL")
    set_p.add_argument(
        "--drop-pending-updates",
        action="store_true",
        help="Drop pending updates on set",
    )

    del_p = subparsers.add_parser("delete", help="Delete current webhook")
    del_p.add_argument(
        "--drop-pending-updates",
        action="store_true",
        help="Drop pending updates on delete",
    )

    args = parser.parse_args()

    token = get_token()
    if args.action == "info":
        cmd_info(token)
    elif args.action == "set":
        secret = get_secret()
        cmd_set(token, secret, args.url, drop_pending=args.drop_pending_updates)
    elif args.action == "delete":
        cmd_delete(token, drop_pending=args.drop_pending_updates)


if __name__ == "__main__":
    main()
