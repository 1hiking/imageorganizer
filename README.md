# Organize Images

The script does the following:

* Grabs all the files from a directory recursively
* Organizes them by exif tag (Make and Model)
* Creates directories for each make/model tag combination and copies the images there
* For duplicate files, non-image files and files without exif: They are placed in their respective directories

## How to use

`organize.py -h`