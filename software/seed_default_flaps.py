#!/usr/bin/env python3

import os
from typing import List, Tuple

import requests

WHITE = "#FFFFFF"

DEFAULT_FLAPS: List[Tuple[str, str]] = [
    ("BLANK", " "),
    ("A", "A"),
    ("B", "B"),
    ("C", "C"),
    ("D", "D"),
    ("E", "E"),
    ("F", "F"),
    ("G", "G"),
    ("H", "H"),
    ("I", "I"),
    ("J", "J"),
    ("K", "K"),
    ("L", "L"),
    ("M", "M"),
    ("N", "N"),
    ("O", "O"),
    ("P", "P"),
    ("Q", "Q"),
    ("R", "R"),
    ("S", "S"),
    ("T", "T"),
    ("U", "U"),
    ("V", "V"),
    ("W", "W"),
    ("X", "X"),
    ("Y", "Y"),
    ("Z", "Z"),
    ("ZERO", "0"),
    ("ONE", "1"),
    ("TWO", "2"),
    ("THREE", "3"),
    ("FOUR", "4"),
    ("FIVE", "5"),
    ("SIX", "6"),
    ("SEVEN", "7"),
    ("EIGHT", "8"),
    ("NINE", "9"),
    ("QUESTION_MARK", "?"),
    ("EXCLAIMATION", "!"),
    ("AT", "@"),
    ("POUND", "#"),
    ("DOLLAR", "$"),
    ("AMPERSAND", "&"),
    ("LEFT_PAREN", "["),
    ("RIGHT_PAREN", "]"),
    ("HYPHEN", "-"),
    ("PLUS", "+"),
    ("EQUALS", "="),
    ("COLON", ":"),
    ("PERCENT", "%"),
    ("APOSTRAPHE", "'"),
    ("MESSAGE", "✉"),
    ("STAR", "★"),
    ("SUN", "☀"),
    ("UP", "↑"),
    ("DOWN", "↓"),
    ("DEGREE", "°"),
    ("SMILEY", "☺"),
    ("SMILEY_FILLED", "☻"),
    ("HEART", "♥"),
    ("MUSIC", "♫"),
    ("UMBRELLA", "☂"),
    ("LIGHTNING", "⚡︎"),
    ("WHITE", "■"),
]


def main() -> int:
    api_base = os.environ.get("API_BASE_URL", "http://localhost:8111/api/v1")
    endpoint = f"{api_base.rstrip('/')}/flaps/"

    if len(DEFAULT_FLAPS) != 64:
        raise ValueError(f"Expected 64 default flap definitions, got {len(DEFAULT_FLAPS)}")

    print(f"Posting {len(DEFAULT_FLAPS)} default flap definitions to {endpoint}")

    for position, (key, glyph) in enumerate(DEFAULT_FLAPS):
        payload = {
            "position": position,
            "key": key,
            "glyph": glyph,
            "color_hex": WHITE,
        }
        try:
            response = requests.post(endpoint, json=payload, timeout=10)
            if response.status_code not in (200, 201):
                if response.status_code in (400, 409, 422):
                    response = requests.put(endpoint, json=payload, timeout=10)
                if response.status_code not in (200, 201):
                    print(f"Failed at position {position}: {response.status_code} - {response.text}")
                    response.raise_for_status()
            print(f"{position:02d}: {key} -> {glyph!r} :: {response.status_code}")
        except Exception as exc:
            print(f"Error at position {position}: {exc}")
            return 1

    print("All default flaps sent successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        raise SystemExit(130)
