from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Any


class Endianness(StrEnum):
    LITTLE = "little"
    BIG = "big"

class TagType(IntEnum):
    BYTE = 1       # 1 byte uint
    ASCII = 2      # Null-terminated ASCII string
    SHORT = 3      # 2 byte uint
    LONG = 4       # 4 byte uint
    RATIONAL = 5   # Two longs, numerator and denominator
    UNDEFINED = 7  # Undefined 1 byte
    SLONG = 9      # 4 byte signed int
    SRATIONAL = 10 # Signed rational
    UTF = 129      # Null-terminated UTF-8 string

@dataclass(frozen=True)
class Tag:
    name: str
    kind: TagType
    data: Any
