#!/usr/bin/env python3
"""
Standalone script to import outreach app templates into Dify.
Run from the api directory: python ../scripts/import_outreach_templates.py

Prerequisites:
1. Dify API server must be running
2. You need a valid API token (from Dify console)
"""

import argparse
import json
import sys
from pathlib import Path

import requests

# Add api directory to path
API_DIR = Path(__file__).parent.parent / "api"
sys.path.insert(0, str(API_DIR))

# Template directory
TEMPLATES_DIR = API_DIR / "services" / "leads" / "app_templates"

# Default Dify API URL
DEFAULT_API_URL = "http://localhost:5001/console/api"


def get_templates():
    """Get list of available templates."""
    templates = []
    for yaml_file in TEMPLATES_DIR.glob("*.yaml"):
        templates.append({
            "name": yaml_file.stem,
            "path": str(yaml_file),
        })
    return templates


def import_template(api_url: str, token: str, template_path: str, name: str = None):
    """Import a single template via API."""
    with open(template_path, "r", encoding="utf-8") as f:
        yaml_content = f.read()

    payload = {
        "mode": "yaml-content",
        "yaml_content": yaml_content,
    }
    if name:
        payload["name"] = name

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{api_url}/apps/imports",
        json=payload,
        headers=headers,
        timeout=30,
    )

    return response.json(), response.status_code


def confirm_import(api_url: str, token: str, import_id: str):
    """Confirm a pending import."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{api_url}/apps/imports/{import_id}/confirm",
        headers=headers,
        timeout=30,
    )

    return response.json(), response.status_code


def main():
    parser = argparse.ArgumentParser(description="Import outreach app templates into Dify")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Dify API URL")
    parser.add_argument("--token", required=True, help="API access token")
    parser.add_argument("--template", help="Specific template to import (optional)")
    parser.add_argument("--list", action="store_true", help="List available templates")
    args = parser.parse_args()

    if args.list:
        print("Available templates:")
        for t in get_templates():
            print(f"  - {t['name']}")
        return

    templates = get_templates()
    if args.template:
        templates = [t for t in templates if t["name"] == args.template]
        if not templates:
            print(f"Template not found: {args.template}")
            return

    print(f"Importing {len(templates)} template(s)...")
    print(f"API URL: {args.api_url}")
    print()

    imported = 0
    for template in templates:
        print(f"📦 Importing: {template['name']}")
        try:
            result, status = import_template(
                args.api_url,
                args.token,
                template["path"],
            )

            if status in (200, 201):
                print(f"   ✓ Success! App ID: {result.get('app_id')}")
                imported += 1
            elif status == 202:
                # Pending - need to confirm
                import_id = result.get("id")
                print(f"   Confirming import {import_id}...")
                result, status = confirm_import(args.api_url, args.token, import_id)
                if status == 200:
                    print(f"   ✓ Success! App ID: {result.get('app_id')}")
                    imported += 1
                else:
                    print(f"   ✗ Confirm failed: {result.get('error')}")
            else:
                print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"   ✗ Error: {e}")

    print()
    print(f"Imported: {imported}/{len(templates)}")


if __name__ == "__main__":
    main()
