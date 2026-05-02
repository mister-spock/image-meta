from typing import Any

from exif._constants import TAG_NAMES

from ._types import Endianness, Tag, TagType


def extract_idfs_data(exif: bytes) -> dict[str, list[Tag]]:
    """Extracts TIFF data tags from the raw Exif data."""
    header = exif[:4].decode()
    if header != "Exif":
        raise ValueError("Incorrect Exif header in given bytes")

    padding = int.from_bytes(exif[4:6])
    if padding != 0:
        raise ValueError("Incorrect Exif padding in given bytes")

    # Shift over the header
    tiff = exif[6:]

    bom = _parse_byte_order(tiff[:2])

    if int.from_bytes(tiff[2:4], bom.value) != 0x002A:
        raise ValueError("Invalid padding after byte order mark!")

    ifds = {}
    ifd = 1
    offset = _get_ifd_offset(tiff, 4, bom) # first offset
    gps_offset = 0

    # Read ALL directories (IFDs)
    while True:
        # Offset = 0 means no more directories
        if offset == 0:
            break

        tags, end_offset = _parse_tag_data(tiff, offset, bom)

        # See if we have GPS data so we could parse it as a separate IFD
        for t in tags:
            if t.name == "GPS Info":
                gps_offset = t.data
                break

        offset = _get_ifd_offset(tiff, end_offset, bom)
        ifds[f"IFD{ifd}"] = tags
        ifd += 1

    # Read GPS IFD
    if gps_offset > 0:
        tags, _ = _parse_tag_data(tiff, gps_offset, bom)
        ifds["GPS Info"] = tags

    return ifds


def _parse_byte_order(raw: bytes) -> Endianness:
    """Parses byte order (endianness) from given 2 bytes of raw data."""
    if len(raw) != 2:
        raise ValueError("Cannot parse byte order mark. Must be 2 bytes long.")

    match raw.decode():
        case "MM":
            return Endianness.BIG
        case "II":
            return Endianness.LITTLE
        case _ as x:
            raise ValueError(f"Cannot figure out Exif byte order. Unknown value '{x}'")

def _get_ifd_offset(tiff: bytes, offset: int, bom: Endianness) -> int:
    """Return the offset value for the next IFD directory."""
    return int.from_bytes(tiff[offset:offset+2], bom.value)

def _parse_tag_data(tiff: bytes, start_offset: int, bom: Endianness) -> tuple[list[Tag], int]:
    """Parses IFD tags from given start offset. Returns tags as tuples and end offset."""
    num_tags = int.from_bytes(tiff[start_offset:start_offset+2], bom.value)
    if num_tags == 0:
        raise ValueError("No tags in IFD! Cannot proceed...")

    raw_tags = tiff[start_offset+2:]
    tags = []

    for i in range(num_tags):
        offset = 12 * i
        tag = raw_tags[offset:offset+12]

        try:
            tag_id = int.from_bytes(tag[:2], bom.value)
            tag_name = TAG_NAMES.get(tag_id, hex(tag_id))
            tag_type = TagType(int.from_bytes(tag[2:4], bom.value))
            tag_count = int.from_bytes(tag[4:8], bom.value)
            tag_value = _parse_value(tiff, tag_count, tag_type, tag[8:12], bom)

            tag = Tag(tag_name, tag_type, tag_value)
            tags.append(tag)
        except Exception as e:
            print(f"Failed to process tag with: {e}")

    # End offset is start offset + full IFD payload
    end_offset = start_offset + 2 + 12 * num_tags
    return tags, end_offset

def _parse_value(tiff: bytes, count: int, kind: TagType, val: bytes, bom: Endianness) -> Any:
    """Parses the value of the tag"""
    match kind:
        case TagType.BYTE:
            buffer = tiff if count > 4 else val
            return _parse_number(buffer, count, 1, bom)

        case TagType.SHORT:
            buffer = tiff if count > 2 else val
            return _parse_number(buffer, count, 2, bom)

        case TagType.LONG|TagType.SLONG as t:
            signed = True if t is TagType.SLONG else False
            buffer = tiff if count > 1 else val
            return _parse_number(buffer, count, 4, bom, signed)

        case TagType.RATIONAL|TagType.SRATIONAL as t:
            signed = True if t is TagType.SLONG else False
            offset = int.from_bytes(val, bom.value)
            return _parse_rational(tiff[offset:offset+(count*8)], count, bom, signed)

        case TagType.ASCII|TagType.UTF as t:
            encoding = "ascii" if t is TagType.ASCII else "utf-8"
            data = val
            if count > 4:
                offset = int.from_bytes(val, bom.value)
                data = tiff[offset:offset+count]
            return data.decode(encoding).rstrip("\0")

    return val.hex()

def _parse_number(buffer: bytes, count: int, width: int, bom: Endianness, signed: bool = False) -> int|list[int]:
    """Parse variable width integers from buffer."""
    offset = 0
    vals = []
    while count > 0:
        vals.append(int.from_bytes(buffer[offset:offset+width], bom.value, signed=signed))
        offset += width
        count -= 1
    return vals if len(vals) > 1 else vals.pop()

def _parse_rational(buffer: bytes, count: int, bom: Endianness, signed: bool = False) -> list[float]:
    """Parse rational numbers from buffer."""
    offset = 0
    vals = []
    while count > 0:
        num = int.from_bytes(buffer[offset:offset+4], bom.value, signed=signed)
        den = int.from_bytes(buffer[offset+4:offset+8], bom.value, signed=signed)
        vals.append(num / den)
        offset += 8
        count -= 1
    return vals if len(vals) > 1 else vals.pop()
