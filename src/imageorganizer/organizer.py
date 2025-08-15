import os
import shutil
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError, ImageFile
from PIL.Image import Exif
from tqdm import tqdm

ImageFile.LOAD_TRUNCATED_IMAGES = True
UNKNOWN_DIRECTORY: str = "Unknown"


def clean(string_to_parse: str) -> str:
    if not string_to_parse:
        return ""
    return (
        string_to_parse.replace("\x00", "").strip().replace("/", "_").replace("\\", "_")
    )


def get_exif_tag(
    exif_data: Exif,
    tag_id: int,
) -> str:
    return clean(exif_data.get(tag_id, "")) or UNKNOWN_DIRECTORY


def organize_images(
    source_path: Path,
    destination_path: Path,
    disable_duplicates: bool,
    disable_console: bool,
) -> int:
    unprocessable_files_path: Path = destination_path / "Unprocessed"
    unprocessable_files_path.mkdir(parents=True, exist_ok=True)
    directory_duplicates: Path = destination_path / "Duplicated Images"
    directory_duplicates.mkdir(parents=True, exist_ok=True)
    image_count: int = 0

    # Walk over all the files, tqdm will not create a bar because it doesn't have lens it's a generator
    for root, dirs, files in tqdm(
        os.walk(source_path),
        desc="Walking dirs",
        dynamic_ncols=True,
        disable=disable_console,
    ):
        # Iterate over the files in the current directory chosen
        progress = tqdm(
            files, desc="Processing files", dynamic_ncols=True, disable=disable_console
        )
        for file in progress:
            # This is what we want to copy
            file_to_be_copied: Path = Path(root) / file

            try:
                with Image.open(file_to_be_copied) as image:
                    if not disable_console:
                        progress.write(f"[!] File being processed: {file_to_be_copied}")

                    image_exif: Exif = image.getexif()

                    make_tag: str = get_exif_tag(image_exif, 271)  # 0x010F: Make
                    model_tag: str = get_exif_tag(image_exif, 272)  # 0x0110: Model
                    # date_tag: str = get_exif_tag(
                    #    image_exif, 36867
                    # )  # 0x9003: DateTimeOriginal

                    # Determine the path of the directory where it will be copied to
                    new_directory: Path = (
                        destination_path / make_tag / model_tag
                        if model_tag != UNKNOWN_DIRECTORY
                        and make_tag != UNKNOWN_DIRECTORY
                        else destination_path / "Unknown Camera and Model"
                    )

                    if (
                        model_tag == UNKNOWN_DIRECTORY or make_tag == UNKNOWN_DIRECTORY
                    ) and not disable_console:
                        progress.write(
                            f"[!] Couldn't retrieve tags, defaulting to Unknown\n"
                            f"for image: {file_to_be_copied}"
                        )

                    # The full path of the image
                    path_destination_file: Path = new_directory / file_to_be_copied.name
                    new_directory.mkdir(parents=True, exist_ok=True)

                    # Copy image2
                    # TODO: Files with same make/model but different content can lead to the system thinking they are a duplicate
                    # We can solve this by renaming them:
                    # - based on their exif date
                    # - based on their unix date
                    if not path_destination_file.exists():
                        shutil.copy2(file_to_be_copied, path_destination_file)
                        image_count += 1
                        if not disable_console:
                            progress.write(
                                f"[✓] Image successfully copied: {path_destination_file}"
                            )
                    elif not disable_duplicates:
                        # Send duplicate to a dedicated directory with a different filename
                        unique_name = (
                            file_to_be_copied.stem
                            + "_"
                            + uuid4().hex[:8]
                            + file_to_be_copied.suffix
                        )
                        destination_file = directory_duplicates / unique_name

                        shutil.copy2(file_to_be_copied, destination_file)
                        image_count += 1
                        if not disable_console:
                            progress.write(
                                f"[!] Duplicated file: {file_to_be_copied}; will be copied to {directory_duplicates}"
                            )
                    else:
                        if not disable_console:
                            progress.write(
                                f"[!] Duplicated file: {file_to_be_copied} will be ignored!"
                            )

            except UnidentifiedImageError:
                if not disable_duplicates:
                    image_count += 1
                    shutil.copy2(file_to_be_copied, unprocessable_files_path)
                    if not disable_console:
                        progress.write(
                            f"[x] Error attempting to process {file_to_be_copied} as an image file, it will be copied into {unprocessable_files_path}"
                        )
            except OSError as oserr:
                # This will occur normally with truncated files. We set Pillow to allow truncated files
                progress.write(
                    f"[x] Error processing a file, reason: {oserr}. File name: {file_to_be_copied}"
                )
    print(f"[✓] Finished processing. Total images handled: {image_count}")
    return 0
