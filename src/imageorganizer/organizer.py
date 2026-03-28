import filecmp
import shutil
from pathlib import Path
from uuid import uuid4

from PIL import ExifTags, Image, ImageFile, UnidentifiedImageError
from PIL.Image import Exif
from tqdm import tqdm

ImageFile.LOAD_TRUNCATED_IMAGES = True
UNKNOWN_DIRECTORY: str = "Unknown"


def clean(string_to_parse: str) -> str:
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


def get_exif_tag(
    exif_data: Exif,
    tag_id: int,
) -> str:
    return clean(exif_data.get(tag_id, "")) or UNKNOWN_DIRECTORY


def is_file_copiable(source: Path, destination: Path) -> bool:
    if not destination.exists():
        return True

    # Return True if names differ OR contents differ
    return (source.name != destination.name) or not filecmp.cmp(
        source, destination, shallow=False
    )


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
    image_count = 0

    files = [f for f in source_path.rglob("*") if f.is_file()]
    # Walk over all the files, tqdm will not create a bar because it doesn't have lens it's a generator
    with tqdm(
        files, desc="Processing", disable=disable_console, dynamic_ncols=True
    ) as progress:
        for file_to_copy in progress:
            try:
                with Image.open(file_to_copy) as image:
                    if not disable_console:
                        progress.write(f"[!] File being processed: {file_to_copy}")

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

                    if (
                        model == UNKNOWN_DIRECTORY or make == UNKNOWN_DIRECTORY
                    ) and not disable_console:
                        progress.write(
                            f"[!] Couldn't retrieve tags, defaulting to Unknown\n"
                            f"for image: {file_to_copy}"
                        )

                    # The full path of the image
                    path_destination_file = new_directory / file_to_copy.name
                    new_directory.mkdir(parents=True, exist_ok=True)

                    if is_file_copiable(file_to_copy, path_destination_file):
                        shutil.copy2(file_to_copy, path_destination_file)
                        image_count += 1
                        if not disable_console:
                            progress.write(
                                f"[✓] Image successfully copied: {path_destination_file}"
                            )
                    elif not disable_duplicates:
                        # Send duplicate images to a dedicated directory with a different filename
                        unique_name = (
                            file_to_copy.stem
                            + "_"
                            + uuid4().hex[:8]
                            + file_to_copy.suffix
                        )
                        destination_file = directory_duplicates / unique_name

                        shutil.copy2(file_to_copy, destination_file)
                        image_count += 1
                        if not disable_console:
                            progress.write(
                                f"[!] Duplicated file: {file_to_copy}; will be copied to {directory_duplicates}"
                            )
                    else:
                        if not disable_console:
                            progress.write(
                                f"[!] Duplicated file: {file_to_copy} will be ignored!"
                            )

            except UnidentifiedImageError:
                if not disable_duplicates:
                    image_count += 1
                    shutil.copy2(file_to_copy, unprocessable_files_path)
                    if not disable_console:
                        progress.write(
                            f"[x] Error attempting to process {file_to_copy} as an image file, it will be copied into {unprocessable_files_path}"
                        )
            except OSError as oserr:
                # This will occur normally with truncated files. We set Pillow to allow truncated files
                progress.write(
                    f"[x] Error processing a file, reason: {oserr}. File name: {file_to_copy}"
                )
    print(f"[✓] Finished processing. Total images handled: {image_count}")
    return 0
