import argparse
import datetime
import hashlib
import os
import pickle
import shutil
import sys
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
        tags = exifread.process_file(f, details=False)
    return tags


def organize_file(filepath, organized_dir):
    """Copies a file to organized_dir with a date-based directory structure."""

    exif_date_tag = "EXIF DateTimeOriginal"
    exif_date_format = "%Y:%m:%d %H:%M:%S"
    filename_format = "%Y-%m-%d %H.%M.%S"

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


def organize(messy_dir, organized_dir):
    """Organizes a folder of pictures into a date-based structure.

    Takes pictures in messy_dir and copies them into organized_dir, categorizing
    the pictures based on date taken and renaming them to the time taken. If
    there's a file without the EXIF data it's moved to a separate directory.
    Duplicate files are not copied.
    """

    hashes_filename = "hashes.pickle"

    # make the new directory if necessary
    if not os.path.isdir(organized_dir):
        os.mkdir(organized_dir)

    # load/create the hashes already in the organized directory
    hashes = []
    if os.path.isfile(os.path.join(organized_dir, hashes_filename)):
        with open(os.path.join(organized_dir, hashes_filename), "rb") as f:
            hashes = pickle.load(f)
    else:
        hashes, _ = find_duplicates(organized_dir)
        hashes = list(hashes.keys())

    uniques_found = 0
    dupes_found = 0

    # find the total files for progress printing
    total_files = 0
    for _, _, filenames in os.walk(messy_dir):
        total_files += len([f for f in filenames if f[0] != "."])

    # recursively organize the files in messy_dir
    for dirpath, dirnames, filenames in os.walk(messy_dir):
        for filename in filenames:
            # ignore hidden files
            if filename[0] == ".":
                continue

            filepath = os.path.join(dirpath, filename)
            filehash = hash_file(filepath)
            # only sort unique files
            if filehash not in hashes:
                hashes.append(filehash)
                organize_file(filepath, organized_dir)
                uniques_found += 1
            else:
                dupes_found += 1

            # print the progress
            sys.stdout.write("\r{}/{}, {} uniques, {} dupes".format(uniques_found + dupes_found, total_files, uniques_found, dupes_found))
            sys.stdout.flush()

    # save the hashes
    with open(os.path.join(organized_dir, hashes_filename), "wb") as f:
        pickle.dump(hashes, f)

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("messy", help="the directory with unorganized pictures.")
    parser.add_argument("organized", help="the directory to copy organized pictures into.")
    args = parser.parse_args()
    organize(args.messy, args.organized)
