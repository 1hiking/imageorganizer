import os
import argparse
import shutil
import sys
from argparse import Namespace
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from PIL.Image import Exif
from tqdm import tqdm

# TODO: We still have many strings hardcoded
# add flags fo all of em?

UNKNOWN_DIRECTORY: str = "Unknown"


def clean(string_to_parse: str) -> str:
    if not string_to_parse:
        return ""
    return (
        str(string_to_parse)
        .replace("\x00", "")
        .strip()
        .replace("/", "_")
        .replace("\\", "_")
    )


def get_exif_tag(exif_data: Exif, tag_id: int) -> str:
    return clean(exif_data.get(tag_id, "")) or UNKNOWN_DIRECTORY


def organize_images(
    source_path: Path, destination_path: Path, disable_duplicates: bool
) -> None:
    manufacturer_set = set()  # use set to avoid duplicates
    unprocessable_files_path: Path = destination_path / "Unprocessed"
    unprocessable_files_path.mkdir(parents=True, exist_ok=True)
    directory_duplicates: Path = destination_path / "Duplicated Images"
    directory_duplicates.mkdir(parents=True, exist_ok=True)
    image_count: int = 0

    # Walk over all the files, tqdm will not create a bar because it doesn't have lens it's an iterator
    for root, dirs, files in tqdm(
        os.walk(source_path),
        desc="Walking dirs",
        dynamic_ncols=True,
    ):
        # Iterate over them
        progress = tqdm(files, desc="Processing files", dynamic_ncols=True)
        for file in progress:
            # This is what we want to copy
            file_to_be_copied: Path = Path(root) / file

            try:
                with Image.open(file_to_be_copied) as image:
                    progress.set_description(
                        desc=f"[!] File being processed: {file_to_be_copied}"
                    )

                    image_exif: Exif = image.getexif()

                    make_tag: str = get_exif_tag(image_exif, 271)  # 0x010F: Make
                    model_tag: str = get_exif_tag(image_exif, 272)  # 0x0110: Model

                    # Determine the path of the directory where it will be copied to
                    if model_tag != UNKNOWN_DIRECTORY and make_tag != UNKNOWN_DIRECTORY:
                        # For images which we know their model and make
                        new_directory: Path = destination_path / make_tag / model_tag
                    else:
                        progress.write(
                            f"[!] Couldn't retrieve tags, defaulting to Unknown\n"
                            f"for image: {file_to_be_copied}"
                        )
                        # Otherwise we just make a dir for the unknown
                        new_directory: Path = (
                            destination_path / "Unknown Camera and Model"
                        )

                    # The full path of the image
                    path_destination_file: Path = new_directory / file_to_be_copied.name

                    # Add image to the set and create the directory if not already there
                    # Skip if it's empty string
                    # TODO: Optimize this adding created_dirs = set()
                    if make_tag and model_tag not in manufacturer_set:
                        manufacturer_set.add(make_tag)
                        new_directory.mkdir(parents=True, exist_ok=True)

                    # Copy image
                    if not path_destination_file.exists():
                        image_count += 1
                        shutil.copy2(file_to_be_copied, path_destination_file)
                        progress.write(
                            f"[✓] Image successfully copied: {path_destination_file}"
                        )
                    elif not disable_duplicates:
                        image_count += 1
                        # Send duplicate to a dedicated directory
                        progress.write(
                            f"[!] Duplicated file: {file_to_be_copied}; will be copied to {directory_duplicates}"
                        )
                        shutil.copy2(file_to_be_copied, directory_duplicates)
                    else:
                        progress.write(
                            f"[!] Duplicated file: {file_to_be_copied} will be ignored!"
                        )

            except UnidentifiedImageError:
                if not disable_duplicates:
                    image_count += 1
                    progress.write(
                        f"[x] Error attempting to process {file_to_be_copied} as an image file, it will be copied into {unprocessable_files_path}"
                    )
                    shutil.copy2(file_to_be_copied, unprocessable_files_path)

    print(image_count, "files processed")


if __name__ == "__main__":
    # TODO: Improve description
    parser = argparse.ArgumentParser(
        prog="Image Organizer", description="Organize images by camera Make/Model."
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
        help="Ignore duplicate files. Useful when doing a re-run",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--quiet", help="Supress output", action="store_true", required=False
    )

    args: Namespace = parser.parse_args()

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
            )
        )
