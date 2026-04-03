# Image Organizer

A CLI tool that sorts images from a source directory into an organized folder tree based on file metadata.

![PyPI - Version](https://img.shields.io/pypi/v/imageorganizer)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/imageorganizer)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/1hiking/imageorganizer/publish.yml)
![PyPI - License](https://img.shields.io/pypi/l/imageorganizer)

## Features

- Recursively scans a source directory for media files
- Organizes images by camera Make/Model EXIF tags
- Creates a `Make/Model` directory structure at the destination
- Handles edge cases cleanly:
  - Duplicates → `Duplicated Images/`
  - Non-image files → `Unprocessed/`
  - Missing EXIF → `Unknown/`
- Doesn't delete or modify your input files!

(Note: There is currently no way of changing these namings)



## Installation
```bash
pip install imageorganizer
```

## Usage
```bash
imageorganizer --path-source /path/to/photos --path-destination /path/to/output
```

## Required dependencies

- Pillow
- pymediainfo
- Rich

### Options

| Flag | Short | Description |
|------|-------|-------------|
| `--path-source` | `-ps` | Source directory to scan (required) |
| `--path-destination` | `-pd` | Destination directory for organized output (required) |
| `--ignore-duplicates` | | Skip duplicate files instead of moving them |
| `--quiet` | | Suppress progress output |

## License

GPL-3.0-or-later