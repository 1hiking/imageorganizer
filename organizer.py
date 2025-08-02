import os
import argparse
import shutil
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from PIL.Image import Exif
from tqdm import tqdm

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


def get_exif_tag(exif_data: object, tag_id: int) -> str:
    return clean(exif_data.get(tag_id, ""))


def organize_images(source_path: Path, destination_path: Path) -> None:
    manufacturer_set = set()  # use set to avoid duplicates
    unprocessable_files_path: Path = destination_path / "Unprocessed"
    unprocessable_files_path.mkdir(parents=True, exist_ok=True)
    directory_duplicates: Path = destination_path / "Duplicated Images"
    directory_duplicates.mkdir(parents=True, exist_ok=True)

    # Walk over all the files
    for root, dirs, files in tqdm(os.walk(source_path), desc="Processing files", dynamic_ncols=True):
        # Iterate over them
        progress = tqdm(files, desc="Processing files", dynamic_ncols=True)
        for file in progress:
            # This is what we want to copy
            file_to_be_copied: Path = Path(root) / file

            try:
                with Image.open(file_to_be_copied) as image:
                    progress.set_description(desc=f"[!] File being processed: {file_to_be_copied}")

                    image_exif: Exif = image.getexif()

                    make_tag: str = get_exif_tag(image_exif, 271)  # 0x010F: Make
                    model_tag: str = get_exif_tag(image_exif, 272)  # 0x0110: Model

                    if make_tag:
                        parsed_make_tag = make_tag
                    else:
                        parsed_make_tag = UNKNOWN_DIRECTORY
                        progress.write(f"[!] Couldn't retrieve Make tag, defaulting to Unknown\n"
                                       f"for image: {file_to_be_copied}")

                    if model_tag:
                        parsed_model_tag = model_tag
                    else:
                        parsed_model_tag = UNKNOWN_DIRECTORY
                        progress.write(f"[!] Couldn't retrieve Model tag, defaulting to {UNKNOWN_DIRECTORY}\n"
                                       f"for image: {file_to_be_copied}")

                    # Determine the path of the directory where it will be copied to
                    if model_tag != UNKNOWN_DIRECTORY and make_tag != UNKNOWN_DIRECTORY:
                        # For images which we know their model and make
                        new_directory: Path = destination_path / parsed_make_tag / parsed_model_tag
                    else:
                        # Otherwise we just make a dir for the unknown
                        new_directory: Path = destination_path / "Unknown Camera and Model"

                    # The full path of the image
                    path_destination_file: Path = new_directory / file_to_be_copied.name

                    # Add image to the set and create the directory if not already there
                    # Skip if it's empty string
                    if parsed_make_tag and parsed_make_tag not in manufacturer_set:
                        manufacturer_set.add(parsed_make_tag)
                        new_directory.mkdir(parents=True, exist_ok=True)

                    # Copy image
                    if not path_destination_file.exists():
                        shutil.copy2(file_to_be_copied, path_destination_file)
                        progress.write(f"[✓] Image successfully copied: {path_destination_file}")
                    else:
                        # Send duplicate to a dedicated directory
                        progress.write(
                            f"[!] Duplicated file: {file_to_be_copied}; will be copied to {directory_duplicates}"
                        )
                        shutil.copy2(file_to_be_copied, directory_duplicates)


            except UnidentifiedImageError as e:
                progress.write(
                    f"[x] Error attempting to process {file_to_be_copied} as an image file, it will be copied into {unprocessable_files_path}")
                shutil.copy2(file_to_be_copied, unprocessable_files_path)
            except OSError as e:
                print(f"[x] Error: {e}")

        print("[!] ALL IMAGES PROCESSED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Image Organizer",
                                     description="Organize images by camera Make/Model."
                                     )
    parser.add_argument(
        "--images_path_source",
        "-ips",
        help="Path to the directory containing images to process.",
        type=str,
    )
    parser.add_argument(
        "--image_path_destination",
        "-ipd",
        help="Path to the directory where the images will be stored.",
        type=str,
    )
    args = parser.parse_args()

    base_path_source = Path(args.images_path_source).resolve()
    base_path_destination = Path(args.image_path_destination).resolve()
    if not base_path_source.is_dir():
        print(f"[!] Error: {base_path_source} is not a valid directory.")
    elif not base_path_destination.is_dir():
        print(f"[!] Error: {base_path_destination} is not a valid directory.")
    else:
        organize_images(base_path_source, base_path_destination)
