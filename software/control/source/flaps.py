import enum
import re

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
    BLANK = 0
    A = 1
    B = 2
    C = 3
    D = 4
    E = 5
    F = 6
    G = 7
    H = 8
    I = 9
    J = 10
    K = 11
    L = 12
    M = 13
    N = 14
    O = 15
    P = 16
    Q = 17
    R = 18
    S = 19
    T = 20
    U = 21
    V = 22
    W = 23
    X = 24
    Y = 25
    Z = 26
    ZERO = 27
    ONE = 28
    TWO = 29
    THREE = 30
    FOUR = 31
    FIVE = 32
    SIX = 33
    SEVEN = 34
    EIGHT = 35
    NINE = 36
    QUESTION_MARK = 37
    EXCLAIMATION = 38
    AT = 39
    POUND = 40
    DOLLAR = 41
    AMPERSAND = 42
    LEFT_PAREN = 43
    RIGHT_PAREN = 44
    HYPHEN = 45
    PLUS = 46
    EQUALS = 47
    COLON = 48
    PERCENT = 49
    APOSTRAPHE = 50
    MESSAGE = 51
    STAR = 52
    SUN = 53
    UP = 54
    DOWN = 55
    DEGREE = 56
    SMILEY = 57
    SMILEY_FILLED = 58
    HEART = 59
    MUSIC = 60
    UMBRELLA = 61
    LIGHTNING = 62
    WHITE = 63

    @classmethod
    def __getitem__(cls, value):
        print("HERE")
        return super().__getitem__(value)

if __name__ == "__main__":
    
    print(Flap['?'].name)