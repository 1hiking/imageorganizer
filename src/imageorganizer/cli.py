import argparse
from pathlib import Path

from .config import ProcessorConfig
from .organizer import queue_images


def main(argv=None):
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
    parser.add_argument(
        "--dry-run",
        help="Don't actually copy images to destination folder",
        action="store_true",
        required=False,
    )

    args = parser.parse_args(argv)
    config = ProcessorConfig(
        source=Path(args.path_source).resolve(),
        destination=Path(args.path_destination).resolve(),
        ignore_duplicates=args.ignore_duplicates,
        quiet=args.quiet,
        dry_run=args.dry_run,
    )
    if error := config.validate():
        print(f"[!] {error}")
        return None
    else:
        # Now queue_images only needs ONE argument
        exit_code = queue_images(config)
        return exit_code
