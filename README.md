# Image Organizer

A CLI tool that sorts images from a source directory into an organized folder tree based on camera EXIF data (Make and Model).

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

### Options

| Flag | Short | Description |
|------|-------|-------------|
| `--path-source` | `-ps` | Source directory to scan (required) |
| `--path-destination` | `-pd` | Destination directory for organized output (required) |
| `--ignore-duplicates` | | Skip duplicate files instead of moving them |
| `--quiet` | | Suppress progress output |

## License

GPL-3.0-or-later