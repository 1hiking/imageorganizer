import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageFile, UnidentifiedImageError
from pymediainfo import MediaInfo
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)

from .constants import IMAGE_EXTENSIONS, UNKNOWN_DIRECTORY
from .utils import get_exif_tag, is_file_copiable

ImageFile.LOAD_TRUNCATED_IMAGES = True


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
        directory_duplicates.mkdir(parents=True, exist_ok=True)
        # Send duplicate images to a dedicated directory with a different filename
        unique_name = file.stem + "_" + uuid4().hex[:8] + file.suffix
        destination_file = directory_duplicates / unique_name

        shutil.copy2(file, destination_file)
        progress.console.print(
            f"[!] Duplicated file: {file}; will be copied to {directory_duplicates}"
        )
    else:
        progress.console.print(f"[!] Duplicated file: {file} will be ignored!")


def queue_images(
    source_path: Path,
    destination_path: Path,
    disable_duplicates: bool,
    disable_console: bool,
) -> int:
    images_list = []
    videos_list = []
    # Use rglob to get all the files
    files = [f for f in source_path.rglob("*") if f.is_file()]
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        BarColumn(),
        MofNCompleteColumn(),
        disable=disable_console,
    ) as progress:
        for file in progress.track(files, description="Queueing Images", total=None):
            progress.console.print(f"[!] File being queued: {file}")
            if file.suffix.lower() in IMAGE_EXTENSIONS:
                images_list.append(file)
            else:
                videos_list.append(file)
        progress.console.print(
            "[bold green]✓ Done! All images queued successfully.[/bold green]"
        )
        process_files(
            images_list,
            videos_list,
            destination_path,
            disable_duplicates,
            disable_console,
        )
        return 0


def process_files(
    images: list[Path],
    videos: list[Path],
    destination_path: Path,
    disable_duplicates: bool,
    disable_console: bool,
):
    unprocessable_files_path = destination_path / "Unprocessed"
    unprocessable_files_path.mkdir(parents=True, exist_ok=True)
    directory_duplicates = destination_path / "Duplicated Images"
    multimedia_path = destination_path / "Multimedia"
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        BarColumn(),
        MofNCompleteColumn(),
        disable=disable_console,
    ) as progress:
        progress.console.print(f"[!] Files being processed: {len(images)}")
        for image in progress.track(
            images, description="Processing images", total=len(images)
        ):
            progress.console.print(f"[!] Processing image: {image}")
            try:
                with Image.open(image) as opened_image:
                    image_exif = opened_image.getexif()
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
                            f"[!] Couldn't retrieve tags, defaulting to Unknown for image: {image.name}"
                        )

                    # The full path of the image to be moved
                    path_destination_file = new_directory / image.name

                copy_file(
                    directory_duplicates,
                    disable_duplicates,
                    image,
                    path_destination_file,
                    progress,
                )

            except UnidentifiedImageError:
                if not disable_duplicates:
                    shutil.copy2(image, unprocessable_files_path)
                    progress.console.print(
                        f"[x] Error attempting to process {image} as an image file, it will be copied into {unprocessable_files_path}"
                    )
            except OSError as oserr:
                progress.console.print(
                    f"[x] Error processing a file, reason: {oserr}. File name: {image.name}"
                )
        for video in progress.track(
            videos, description="Processing videos", total=len(videos)
        ):
            progress.console.print(f"[!] Processing video: {video}")
            image_media = MediaInfo.parse(video)
            general = image_media.tracks[0].to_data()
            date_str = general.get("encoded_date") or general.get("tagged_date")
            if date_str:
                date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
            else:
                date = datetime.fromtimestamp(video.stat().st_mtime)
            year = date.strftime("%Y")
            month = date.strftime("%m")
            new_directory = multimedia_path / year / month
            new_directory.mkdir(parents=True, exist_ok=True)
            path_destination_file = new_directory / video.name
            copy_file(
                directory_duplicates,
                disable_duplicates,
                video,
                path_destination_file,
                progress,
            )
