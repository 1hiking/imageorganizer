import filecmp
import shutil
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageFile, UnidentifiedImageError
from PIL.Image import Exif
from pymediainfo import MediaInfo
from rich.progress import Progress, TimeElapsedColumn

from .constants import IMAGE_EXTENSIONS

ImageFile.LOAD_TRUNCATED_IMAGES = True
UNKNOWN_DIRECTORY: str = "Unknown"


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


def get_exif_tag(exif_data: Mapping[int, str], tag_id: int) -> str:
    """
    Retrieves and sanitizes an EXIF tag value.

    Args:
        exif_data: EXIF metadata object to query.
        tag_id: Numeric EXIF tag identifier.

    Returns:
        Cleaned tag value, or UNKNOWN_DIRECTORY if the tag is missing or empty.
    """
    return clean(exif_data.get(tag_id, "")) or UNKNOWN_DIRECTORY


def is_file_copiable(source: Path, destination: Path) -> bool:
    if not destination.exists():
        return True

    # Return True if names differ OR contents differ
    return (source.name != destination.name) or not filecmp.cmp(
        source, destination, shallow=False
    )


def copy_file(
    directory_duplicates: Path,
    disable_duplicates: bool,
    file: Path,
    path_destination_file: Path,
    progress: Progress,
):
    if is_file_copiable(file, path_destination_file):
        shutil.copy2(file, path_destination_file)
        progress.console.print(
            f"[✓] Image successfully copied: {path_destination_file}"
        )
    elif not disable_duplicates:
        # Send duplicate images to a dedicated directory with a different filename
        unique_name = file.stem + "_" + uuid4().hex[:8] + file.suffix
        destination_file = directory_duplicates / unique_name

        shutil.copy2(file, destination_file)
        progress.console.print(
            f"[!] Duplicated file: {file}; will be copied to {directory_duplicates}"
        )
    else:
        progress.console.print(f"[!] Duplicated file: {file} will be ignored!")


def organize_images(
    source_path: Path,
    destination_path: Path,
    disable_duplicates: bool,
    disable_console: bool,
) -> int:
    unprocessable_files_path = destination_path / "Unprocessed"
    unprocessable_files_path.mkdir(parents=True, exist_ok=True)
    directory_duplicates = destination_path / "Duplicated Images"
    directory_duplicates.mkdir(parents=True, exist_ok=True)

    # Use rglob to get all the files
    files = [f for f in source_path.rglob("*") if f.is_file()]
    with Progress(TimeElapsedColumn(), disable=disable_console) as progress:
        for file in progress.track(files, description="Organizing Images", total=None):
            progress.console.print(f"[!] File being processed: {file}")
            if file.suffix in IMAGE_EXTENSIONS:
                try:
                    with Image.open(file) as image:
                        image_exif: Exif = image.getexif()
                        make = get_exif_tag(image_exif, 271)  # 0x010F: Make
                        model = get_exif_tag(image_exif, 272)  # 0x0110: Model
                        # date_tag: str = get_exif_tag(
                        #    image_exif, 36867
                        # )  # 0x9003: DateTimeOriginal

                        # Determine the path of the directory where it will be copied to
                        new_directory = (
                            destination_path / make / model
                            if model != UNKNOWN_DIRECTORY and make != UNKNOWN_DIRECTORY
                            else destination_path / "Unknown Camera and Model"
                        )
                        new_directory.mkdir(parents=True, exist_ok=True)

                        if model == UNKNOWN_DIRECTORY or make == UNKNOWN_DIRECTORY:
                            progress.console.print(
                                f"[!] Couldn't retrieve tags, defaulting to Unknown for image: {file.name}"
                            )

                        # The full path of the image to be moved
                        path_destination_file = new_directory / file.name

                    copy_file(
                        directory_duplicates,
                        disable_duplicates,
                        file,
                        path_destination_file,
                        progress,
                    )

                except UnidentifiedImageError:
                    if not disable_duplicates:
                        shutil.copy2(file, unprocessable_files_path)
                        progress.console.print(
                            f"[x] Error attempting to process {file} as an image file, it will be copied into {unprocessable_files_path}"
                        )
                except OSError as oserr:
                    progress.console.print(
                        f"[x] Error processing a file, reason: {oserr}. File name: {file.name}"
                    )
            else:
                image_media = MediaInfo.parse(file)
                general = image_media.tracks[0].to_data()
                date_str = general.get("encoded_date") or general.get("tagged_date")
                if date_str:
                    date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
                else:
                    date = datetime.fromtimestamp(file.stat().st_mtime)
                year = date.strftime("%Y")
                month = date.strftime("%m")
                new_directory = destination_path / year / month
                new_directory.mkdir(parents=True, exist_ok=True)
                path_destination_file = new_directory / file.name
                copy_file(
                    directory_duplicates,
                    disable_duplicates,
                    file,
                    path_destination_file,
                    progress,
                )

        return 0
