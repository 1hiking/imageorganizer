import filecmp
from datetime import datetime
from pathlib import Path
from typing import Mapping

from imageorganizer.constants import UNKNOWN_DIRECTORY


def clean(string_to_parse: str | None) -> str:
    """
    Sanitizes a string for use as a filesystem path component.

    Removes null bytes, strips whitespace, and replaces path-unsafe
    characters: '/' and '\\' become '_', ':' becomes '-', spaces are removed.

    Args:
        string_to_parse: The string to sanitize.

    Returns:
        Sanitized string, or empty string if input is falsy.

    Example:
        >>> clean("hello world/foo:bar")
        'helloworldfoo-bar'
    """
    if not string_to_parse:
        return ""
    return (
        string_to_parse.replace("\x00", "")
        .strip()
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "-")
        .replace(" ", "")
    )


def get_exif_string(exif_data: Mapping[int, str], tag_id: int) -> str:
    """
    Retrieves and sanitizes an EXIF tag value.

    Args:
        exif_data: EXIF metadata object to query.
        tag_id: Numeric EXIF tag identifier.

    Returns:
        Cleaned tag value, or UNKNOWN_DIRECTORY if the tag is missing or empty.
    """
    return clean(exif_data.get(tag_id)) or UNKNOWN_DIRECTORY


def get_exif_date(exif_data: Mapping[int, str], tag_id: int) -> datetime | None:
    try:
        return datetime.strptime(exif_data[tag_id], "%Y:%m:%d %H:%M:%S")
    except (ValueError, TypeError, KeyError):
        return None


def is_file_copiable(source: Path, destination: Path) -> bool:
    if not destination.exists():
        return True

    # Return True if names differ OR contents differ
    return (source.name != destination.name) or not filecmp.cmp(
        source, destination, shallow=False
    )
