import argparse
from pathlib import Path

from exif import extract_idfs_data

SUFFIXES = ["jpg", "jpeg"] # TODO: Add more
JPEG_SOI = 0xFFD8
JPEG_COM = 0xFFFE
JPEG_EXIF = 0xFFE1 # APP1 segment is mandatory and (usually) comes right after SOI

IFD_ENTRY_LEN = 12 # Bytes

# Initialize argument parser
parser = argparse.ArgumentParser(
    prog="main",
    description="Shows certain EXIF/TIFF data for given JPEG images"
)

parser.add_argument("filenames", nargs="+")
# END: Initialize argument parser

args = parser.parse_args()
paths = [Path(p) for p in args.filenames]

def parse_jpeg_exif(content: bytes) -> bytes:
    """Parses raw APP1 sergment from the raw bytes of a JPEG image."""
    jpeg_marker = int.from_bytes(content[:2])
    if jpeg_marker != JPEG_SOI:
        raise ValueError("Given bytes do not represent a JPEG image!")

    content_len = len(content)
    offset = 2
    exif_raw = b""

    while offset < content_len:
        twobytes = int.from_bytes(content[offset:offset+2])
        if twobytes == JPEG_EXIF:
            offset += 2 # Move to length pair
            seg_len = int.from_bytes(content[offset:offset+2])
            if seg_len > 0:
                exif_raw = content[offset+2:seg_len-2]
            break
        else:
            offset += 1

    return exif_raw


# Open each one and inspect it for meta data
for p in paths:
    if p.suffix.lstrip(".") not in SUFFIXES:
        print(f"'{p.suffix}' file formats are not supported")
        continue

    apps = {}
    app_segment = 0

    try:
        data = p.read_bytes()
        exif = parse_jpeg_exif(data)
        print(f"File '{p.name}' has EXIF segment of {(len(exif)/1024):0.2f} KB")

        idfs = extract_idfs_data(exif)

        for key, tags in idfs.items():
            print(f"\nTags for {key}:")
            for t in tags:
                print(f"{t.name}: {t.data}")

        print("\n")

    except FileNotFoundError:
        print(f"File '{p.name}' does not exist")
    except IsADirectoryError:
        print(f"'{p.name}' is a directory")
    except PermissionError:
        print(f"Cannot access '{p.name}'. Insufficient permissions")
    except Exception as e:
        print(f"Unexpected error for file '{p.name}': {e}")
