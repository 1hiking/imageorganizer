from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from imageorganizer.cli import ProcessorConfig
from imageorganizer.organizer import (
    queue_images,
)
from imageorganizer.utils import clean, get_exif_tag, is_file_copiable

## --- Unit Tests for Helpers ---


def test_clean_utility():
    assert clean(None) == ""
    assert clean("Canon/EOS: 5D\x00") == "Canon_EOS-5D"
    assert clean("  Space Case  ") == "SpaceCase"


def test_get_exif_tag():
    mock_exif = {271: " Nikon ", 272: "D850"}
    assert get_exif_tag(mock_exif, 271) == "Nikon"
    assert get_exif_tag(mock_exif, 999) == "Unknown"


def test_is_file_copiable_table_logic(tmp_path):
    """
    Tests the 4 quadrants of the logic table:
    | Same Content | 2 Diff Names | 2 Equal Names |
    |--------------|--------------|---------------|
    | Yes          | True         | False         |
    | No           | True         | True          |
    """
    src = tmp_path / "photo.jpg"
    src.write_text("content_A")

    # 1. Diff Name, Same Content -> True
    dst_diff_name = tmp_path / "other.jpg"
    dst_diff_name.write_text("content_A")
    assert is_file_copiable(src, dst_diff_name) is True

    # 2. Equal Name, Same Content -> False
    # (Checking against itself or identical file in same place)
    assert is_file_copiable(src, src) is False

    # 3. Diff Name, Diff Content -> True
    dst_diff_both = tmp_path / "different.jpg"
    dst_diff_both.write_text("content_B")
    assert is_file_copiable(src, dst_diff_both) is True

    # 4. Equal Name, Diff Content -> True
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    dst_same_name_diff_content = dest_dir / "photo.jpg"
    dst_same_name_diff_content.write_text("content_B")
    assert is_file_copiable(src, dst_same_name_diff_content) is True


## --- Integration Tests ---


@pytest.fixture
def base_config(tmp_path):
    source = tmp_path / "source"
    dest = tmp_path / "destination"
    source.mkdir()
    dest.mkdir()

    return ProcessorConfig(
        source=source,
        destination=dest,
        ignore_duplicates=False,
        quiet=True,
        dry_run=False,
    )


def test_organize_success_with_exif(base_config):
    src, dst = base_config.source, base_config.destination
    img_path = src / "test.jpg"
    img = Image.new("RGB", (1, 1))
    exif = img.getexif()
    exif[271], exif[272] = "Sony", "A7III"
    img.save(img_path, "JPEG", exif=exif)

    exit_code = queue_images(base_config)
    assert exit_code == 0
    assert (dst / "Sony" / "A7III" / "test.jpg").exists()


def test_organize_success_with_mediainfo(base_config):
    src, dst = base_config.source, base_config.destination

    mock_track = MagicMock()
    mock_track.to_data.return_value = {
        "encoded_date": "2024-06-21 13:56:56 UTC",
        "tagged_date": None,
    }
    mock_media = MagicMock()
    mock_media.tracks = [mock_track]

    img_path = src / "test.mp4"
    img_path.touch()
    dst_mult_path = dst / "Multimedia"
    with patch("pymediainfo.MediaInfo.parse", return_value=mock_media):
        exit_code = queue_images(base_config)

    assert exit_code == 0
    assert (dst_mult_path / "2024" / "06" / "test.mp4").exists()


def test_unidentified_image_error(base_config):
    src, dst = base_config.source, base_config.destination
    bad_file = src / "not_an_image.jpg"
    bad_file.write_text("fake")
    queue_images(base_config)
    assert (dst / "Unprocessed" / "not_an_image.jpg").exists()


def test_duplicate_name_same_content_hits_uuid_block(base_config):
    """
    To hit the UUID renaming block, the file must be 'not copiable'.
    This happens when names ARE equal AND content IS equal.
    """
    src, dst = base_config.source, base_config.destination
    img_path = src / "dup.jpg"
    Image.new("RGB", (1, 1)).save(img_path)

    queue_images(base_config)

    queue_images(base_config)

    dup_dir = dst / "Duplicated Images"
    files = list(dup_dir.glob("dup_*.jpg"))
    assert len(files) == 1


@patch("PIL.Image.open")
def test_os_error_handling(mock_open, base_config, capsys):
    src = base_config.source
    (src / "error.jpg").write_text("dummy")
    mock_open.side_effect = OSError("Simulated drive failure")
    queue_images(base_config)
    mock_open.side_effect = OSError("Simulated drive failure")
    captured = capsys.readouterr()
    assert "Error processing a file" in captured.out


def test_parity_and_nested_walking(tmp_path):
    src = tmp_path / "parent"
    sub = src / "child"
    sub.mkdir(parents=True)
    dst = tmp_path / "out"
    dst.mkdir()
    (sub / "nested.jpg").write_text("fake")
    config = ProcessorConfig(
        source=src,
        destination=dst,
        ignore_duplicates=False,
        quiet=True,
        dry_run=False,
    )
    queue_images(config)
    assert (dst / "Unprocessed" / "nested.jpg").exists()
