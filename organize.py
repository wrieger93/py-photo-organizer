import argparse
import datetime
import hashlib
import os
import shutil
import uuid

import exifread


def hash_file(path, blocksize=65536):
    """Returns the hash of a file."""

    hasher = hashlib.sha1()
    with open(path, "rb") as f:
        block = f.read(blocksize)
        while len(block) > 0:
            hasher.update(block)
            block = f.read(blocksize)
    return hasher.hexdigest()


def find_duplicates(basedir):
    """Recursively finds duplicate files in a directory.

    Returns a tuple unique_files, duplicate_files.
    unique_files is a dictionary whose keys are the hashes and
    duplicate_files is a list.
    """

    unique_files = {}
    dupe_files = []
    for dirpath, dirnames, filenames in os.walk(basedir):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            filehash = hash_file(filepath)
            if filehash not in unique_files:
                unique_files[filehash] = filepath
            else:
                dupe_files.append(filepath)
    return unique_files, dupe_files


def get_exif_tags(filepath):
    """Returns the EXIF tags for a file."""

    with open(filepath, "rb") as f:
        tags = exifread.process_file(f)
    return tags


def organize(messy_dir, organized_dir):
    """Organizes a folder of pictures into a date-based structure.

    Takes pictures in messy_dir and copies them into organized_dir, categorizing
    the pictures based on date taken and renaming them to the time taken. If
    there's a file without the EXIF data it's moved to a separate directory.
    Duplicate files are not copied.
    """

    exif_date_tag = "EXIF DateTimeOriginal"
    exif_date_format = "%Y:%m:%d %H:%M:%S"
    filename_format = "%Y-%m-%d %H:%M:%S"

    # make the new directory if necessary
    if not os.path.exists(organized_dir):
        os.mkdir(organized_dir)

    uniques, dupes = find_duplicates(messy_dir)
    print("unique/duplicates: {}/{}".format(len(uniques), len(dupes)))

    files_copied = 0

    for filepath in uniques.values():
        ext = os.path.splitext(filepath)[1]
        tags = get_exif_tags(filepath)

        if exif_date_tag in tags:
            # has the proper EXIF data
            pictime_str = str(tags[exif_date_tag])
            pictime = datetime.datetime.strptime(pictime_str, exif_date_format)

            yearstr = pictime.strftime("%Y")
            monthstr = pictime.strftime("%m")
            daystr = pictime.strftime("%d")
            sort_dir = os.path.join(organized_dir, "{}/{}/{}".format(yearstr, monthstr, daystr))
            filename = pictime.strftime(filename_format) + ext.lower()
        else:
            # doesn't have the proper EXIF data
            sort_dir = os.path.join(organized_dir, "no_EXIF")
            filename = os.path.basename(filepath)

        # make the directory to copy into if necessary
        if not os.path.exists(sort_dir):
            os.makedirs(sort_dir)

        # if file already exists, give it a unique name
        if os.path.exists(os.path.join(sort_dir, filename)):
            name, ext = os.path.splitext(filename)
            filename = name + " " + str(uuid.uuid4()) + ext

        # copy the file
        shutil.copy(filepath, os.path.join(sort_dir, filename))
        files_copied += 1

    print("organized {} files".format(files_copied))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("messy", help="the directory with unorganized pictures.")
    parser.add_argument("organized", help="the directory to copy organized pictures into.")
    args = parser.parse_args()
    organize(args.messy, args.organized)
