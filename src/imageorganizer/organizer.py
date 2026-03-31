import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageFile, UnidentifiedImageError
from pymediainfo import MediaInfo
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

from .config import ProcessorConfig
from .constants import UNKNOWN_DIRECTORY
from .utils import get_exif_tag, is_file_copiable

ImageFile.LOAD_TRUNCATED_IMAGES = True


def copy_file(
    directory_duplicates: Path,
    file: Path,
    path_destination_file: Path,
    progress: Progress,
    task_id: TaskID,
    config: ProcessorConfig,
):
    if is_file_copiable(file, path_destination_file):
        shutil.copy2(file, path_destination_file)
        progress.update(
            task_id,
            advance=1,
        )
    elif not config.ignore_duplicates:
        directory_duplicates.mkdir(parents=True, exist_ok=True)
        # Send duplicate images to a dedicated directory with a different filename
        unique_name = file.stem + "_" + uuid4().hex[:8] + file.suffix
        destination_file = directory_duplicates / unique_name

        shutil.copy2(file, destination_file)
        progress.console.print(
            f"[yellow][!] Duplicate:[/] {file.name} -> {directory_duplicates.name}"
        )
        progress.update(task_id, advance=1)
    else:
        progress.console.print(f"[dim][!] Ignored:[/] {file.name}")
        progress.update(task_id, advance=1)


def queue_images(
    config: ProcessorConfig,
) -> int:
    images_list = []
    videos_list = []
    # Use rglob to get all the files
    files = [f for f in config.source.rglob("*") if f.is_file()]
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        BarColumn(),
        MofNCompleteColumn(),
        disable=config.quiet,
    ) as progress:
        for file in progress.track(files, description="Queueing Images", total=None):
            # We check if Pillow can process it rather than hardcoding our formats
            if file.suffix.lower() in Image.registered_extensions():
                images_list.append(file)
            else:
                videos_list.append(file)
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(process_images, images_list, config, progress)
            executor.submit(process_videos, videos_list, config, progress)
        return 0


def process_images(images: list[Path], config: ProcessorConfig, progress: Progress):
    unprocessable_files_path = config.destination / "Unprocessed"
    unprocessable_files_path.mkdir(parents=True, exist_ok=True)
    directory_duplicates = config.destination / "Duplicated Images"

    task_id = progress.add_task("[!] Processing images", total=len(images))
    for image in images:
        progress.update(task_id, description=f"[!] Processing image: {image}")
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
                    config.destination / make / model
                    if model != UNKNOWN_DIRECTORY and make != UNKNOWN_DIRECTORY
                    else config.destination / "Unknown Camera and Model"
                )
                new_directory.mkdir(parents=True, exist_ok=True)

                if model == UNKNOWN_DIRECTORY or make == UNKNOWN_DIRECTORY:
                    progress.update(
                        task_id,
                        description=f"[!] Couldn't retrieve tags, defaulting to Unknown for image: {image.name}",
                    )

                # The full path of the image to be moved
                path_destination_file = new_directory / image.name

            copy_file(
                directory_duplicates,
                image,
                path_destination_file,
                progress,
                task_id,
                config,
            )

        except UnidentifiedImageError:
            if not config.ignore_duplicates:
                shutil.copy2(image, unprocessable_files_path)
                progress.console.print(
                    f"[yellow][x] Not a valid image:[/] {image.name}"
                )
                progress.update(task_id, advance=1)
        except OSError as e:
            progress.console.print(f"[red][bold]![/] System Error on {image.name}: {e}")
            progress.update(task_id, advance=1)


def process_videos(
    videos: list[Path],
    config: ProcessorConfig,
    progress: Progress,
):
    multimedia_path = config.destination / "Multimedia"
    directory_duplicates = config.destination / "Duplicated Images"

    task_id = progress.add_task("[blue]Processing Videos", total=len(videos))
    for video in videos:
        try:
            progress.update(task_id, description=f"[!] Processing video: {video}")
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
                video,
                path_destination_file,
                progress,
                task_id,
                config,
            )
        except Exception as e:
            progress.console.print(f"[red][x] Video Error {video.name}: {e}[/]")
            progress.update(task_id, advance=1)
