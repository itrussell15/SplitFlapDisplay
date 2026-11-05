import enum
import re
from typing import Any

class FlapEnumMeta(enum.EnumMeta):

    class FlapConversionError(Exception):
        def __init__(self, key: str) -> None:
            super().__init__(f"Unable to translate {key} to Flap")

    lookup_map = {
        0: "ZERO",
        1: "ONE",
        2: "TWO",
        3: "THREE",
        4: "FOUR",
        5: "FIVE",
        6: "SIX",
        7: "SEVEN",
        8: "EIGHT",
        9: "NINE",
        "?": "QUESTION_MARK",
        "!": "EXCLAIMATION_MARK",
        "@": "AT",
        "#": "POUND",
        "$": "DOLLAR",
        "&": "AMPERSAND",
        "[": "LEFT_PAREN",
        "]": "RIGHT_PAREN",
        "-": "HYPHEN",
        "+": "PLUS",
        "=": "EQUALS",
        ":": "COLON",
        "%": "PERCENT",
        "'": "APOSTRAPHE"
    }

    def __getitem__(cls, key: Any):
        def handle_key(key) -> str:
            match key:
                case int():
                    if key > 9 or key < 0:
                        raise cls.FlapConversionError(key)
                    key = cls.lookup_map[key]
                case str():
                    if key.isnumeric():
                        if len(key) > 1:
                            raise cls.FlapConversionError(key)
                        key = cls.lookup_map[int(key)]
                    else:
                        # if len(key) == 1 and key in cls.lookup_map:
                        key = cls.lookup_map[key]
                        
            return key
        try:
            return super().__getitem__(key)
        except KeyError:
                key = handle_key(key)
                return super().__getitem__(key)
        except Exception as e:
            raise e


class Flap(enum.IntEnum, metaclass=FlapEnumMeta):
    BLANK = enum.auto()
    A = enum.auto()
    B = enum.auto()
    C = enum.auto()
    D = enum.auto()
    E = enum.auto()
    F = enum.auto()
    G = enum.auto()
    H = enum.auto()
    I = enum.auto()
    J = enum.auto()
    K = enum.auto()
    L = enum.auto()
    M = enum.auto()
    N = enum.auto()
    O = enum.auto()
    P = enum.auto()
    Q = enum.auto()
    R = enum.auto()
    S = enum.auto()
    T = enum.auto()
    U = enum.auto()
    V = enum.auto()
    W = enum.auto()
    X = enum.auto()
    Y = enum.auto()
    Z = enum.auto()
    ZERO = enum.auto()
    ONE = enum.auto()
    TWO = enum.auto()
    THREE = enum.auto()
    FOUR = enum.auto()
    FIVE = enum.auto()
    SIX = enum.auto()
    SEVEN = enum.auto()
    EIGHT = enum.auto()
    NINE = enum.auto()
    QUESTION_MARK = enum.auto()
    EXCLAIMATION = enum.auto()
    AT = enum.auto()
    POUND = enum.auto()
    DOLLAR = enum.auto()
    AMPERSAND = enum.auto()
    LEFT_PAREN = enum.auto()
    RIGHT_PAREN = enum.auto()
    HYPHEN = enum.auto()
    PLUS = enum.auto()
    EQUALS = enum.auto()
    COLON = enum.auto()
    PERCENT = enum.auto()
    APOSTRAPHE = enum.auto()
    MESSAGE = enum.auto()
    STAR = enum.auto()
    SUN = enum.auto()
    UP = enum.auto()
    DOWN = enum.auto()
    DEGREE = enum.auto()
    SMILEY = enum.auto()
    SMILEY_FILLED =enum.auto()
    HEART = enum.auto()
    MUSIC = enum.auto()
    UMBRELLA = enum.auto()
    LIGHTNING = enum.auto()
    WHITE = enum.auto()

    @classmethod
    def __getitem__(cls, value):
        return super().__getitem__(value)
