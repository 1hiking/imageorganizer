import os
import argparse
import shutil
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS


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


def get_exif_tag(exif_data, tag_id):
    return clean(exif_data.get(tag_id, ""))


def organize_images(source_path: Path, destination_path: Path):
    manufacturer_set = set()  # use set to avoid duplicates
    unprocessable_files_path = destination_path / "Unprocessed"
    duplicate_count = 0
    # Walk over all the files
    for root, dirs, files in os.walk(source_path):
        # Iterate over them
        for file in files:
            # This is what we want to manipulate
            file_path = Path(root) / file

            try:
                with Image.open(file_path) as image:
                    print(
                        f"[✓] {file_path} | {image.format}, {image.size} | Mode: {image.mode}"
                    )

                    # Start EXIF tasks
                    image_exif = image.getexif()

                    make_tag = get_exif_tag(image_exif, 271)  # 0x010F: Make
                    model_tag = get_exif_tag(image_exif, 272)  # 0x0110: Model

                    clean_make = make_tag if make_tag else "Unknown"
                    clean_model = model_tag if model_tag else "Unknown"

                    if clean_make == "Unknown":
                        print(
                            f"[!] Couldn't retrieve Make tag, defaulting to Unknown\n"
                            f"for image: {file_path}"
                        )

                    if clean_model == "Unknown":
                        print(f"[!] Couldn't retrieve Model tag, defaulting to Unknown\n"
                              f"for image: {file_path}")

                    # End EXIF tasks

                    dest_dir = destination_path / clean_make / clean_model

                    # Add image to the set and create the directory
                    if clean_make not in manufacturer_set:
                        manufacturer_set.add(clean_make)
                        dest_dir.mkdir(parents=True, exist_ok=True)

                    # Copy image (skip if it's already in target)
                    dest_file = dest_dir / file_path.name
                    if not dest_file.exists():
                        shutil.copy2(file_path, dest_file)
                    else:
                        print(
                            f"[!] Skipping duplicate: {dest_file}; duplicate origin is: {file_path}"
                        )
                        duplicate_count += 1

            except (UnidentifiedImageError, OSError) as e:
                print(f"[x] Error with file {file_path}: {e}")
                unprocessable_files_path.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, unprocessable_files_path)

        print("[!] ALL IMAGES PROCESSED")
        print("[!] FINAL DUPLICATE COUNT IS: " + duplicate_count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Organize images by camera Make/Model."
    )
    parser.add_argument(
        "images_path_source",
        help="Path to the directory containing images to process.",
        type=str,
    )
    parser.add_argument(
        "image_path_destination",
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
