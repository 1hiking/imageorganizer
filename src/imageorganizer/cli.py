import argparse
import sys
from pathlib import Path

from .organizer import organize_images


def main():
    parser = argparse.ArgumentParser(
        prog="Image Organizer",
        description=(
            "Organize image files by their camera Make and Model using EXIF metadata.\n"
            "Images are sorted into folders (e.g., Canon/5D) under the destination path.\n"
            "Unprocessable or duplicate files are moved to dedicated folders for review."
        ),
        epilog=(
            "example usage:\n"
            "  python organize.py --path-source ./DCIM --path-destination ./Sorted --ignore-duplicates\n"
            "  python organize.py -ps C:/Photos -pd D:/SortedPhotos"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--path-source",
        "-ps",
        help="Path to the directory containing images to process.",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--path-destination",
        "-pd",
        help="Path to the directory where the images will be stored.",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--ignore-duplicates",
        help="If set, duplicate images will not be copied. Useful when doing a re-run",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--quiet", help="Supress output", action="store_true", required=False
    )

    args = parser.parse_args()

    base_path_source: Path = Path(args.path_source).resolve()
    base_path_destination: Path = Path(args.path_destination).resolve()
    if not base_path_source.is_dir():
        print(f"[!] Error: {base_path_source} is not a valid directory.")
    elif not base_path_destination.is_dir():
        print(f"[!] Error: {base_path_destination} is not a valid directory.")
    else:
        sys.exit(
            organize_images(
                base_path_source,
                base_path_destination,
                args.ignore_duplicates,
                args.quiet,
            )
        )
