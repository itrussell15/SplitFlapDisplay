#!/usr/bin/env python3

import os
import sys
from typing import List

import requests

DEFAULT_CHARACTERS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789?!@#$&[]-+=:%'✉★☀↑↓°☺☻♥♫☂a■"
WHITE = "#FFFFFF"


def main() -> int:
    api_base = os.environ.get("API_BASE_URL", "http://localhost:8011/api/v1")
    endpoint = f"{api_base.rstrip('/')}/flaps/"

    chars = list(DEFAULT_CHARACTERS)
    if len(chars) != 64:
        raise ValueError(f"Expected 64 default flap characters, got {len(chars)}")

    print(f"Posting {len(chars)} default flap definitions to {endpoint}")

    for index, character in enumerate(chars):
        payload = {
            "position": index,
            "character": character,
            "color_hex": WHITE,
        }
        try:
            response = requests.put(endpoint, json=payload, timeout=10)
            if response.status_code not in (200, 201):
                print(f"Failed at position {index}: {response.status_code} - {response.text}")
                response.raise_for_status()
                print(f"{index:02d}: {character!r} -> {response.status_code}")
        except Exception as e:
            print(str(e))
    print("All default flaps sent successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        raise SystemExit(130)
