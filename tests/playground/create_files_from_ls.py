from __future__ import print_function

import argparse
import codecs
import os


# This script create a list of file taken from an `ls` output and put them (zero sized)
#  in a destination folder
# it's used to create test files for Afterdown


def scan_ls_file(lines, destination_folder, only_folders=True):
    current_folder = destination_folder
    for line in lines:
        if line[-1] == ":":  # folders are indicated with a ending colon
            dir_name = line[:-1]
            current_folder = os.path.abspath(os.path.join(destination_folder, dir_name))
            if not os.path.isdir(current_folder):
                # print("creating %s" % current_folder)
                os.makedirs(current_folder)
        else:
            if only_folders:
                continue
            maybe_file_path = os.path.join(current_folder, line)
            if os.path.isdir(maybe_file_path):  # this file is not a file, is a folder
                continue
            if not os.path.isfile(maybe_file_path):
                # print("\t%s" % maybe_file_path)
                open(maybe_file_path, 'a').close()


class LSCreator(object):
    def __init__(self, ls_file, destination_folder):
        self.ls_file = ls_file
        self.destination_folder = destination_folder

    def run(self):
        assert os.path.isfile(self.ls_file), "Can't find ls output file %s" % self.ls_file

        # get lines from the ls output
        with codecs.open(self.ls_file, encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines()]
        lines = list(filter(lambda x: x, lines))

        # Do a first scan creating folders...
        scan_ls_file(lines, self.destination_folder, only_folders=True)
        # ... then create the files, where they are not a folder
        scan_ls_file(lines, self.destination_folder, only_folders=False)


if __name__ == '__main__':
    PROJECT_PATH = os.path.dirname(__file__)
    parser = argparse.ArgumentParser(
        "Files from list",
        description="Create directory structure and empty files from the output of"
                    "ls -R1 > output.txt")
    parser.add_argument("source", help="the output of ls -R1", default=None, nargs="?")
    parser.add_argument("target", help="the path of the target folder", default=None, nargs="?")
    args = parser.parse_args()
    ls_file = args.source or os.path.join(PROJECT_PATH, "ls_file.txt")
    destination_folder = args.target or os.path.join(PROJECT_PATH, 'folder_to_monitor')
    print("Creating structure from %s" % ls_file)
    lc = LSCreator(
        ls_file=ls_file,
        destination_folder=destination_folder,
    )
    lc.run()
