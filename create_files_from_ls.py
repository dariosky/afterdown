import os
# This script create a list of file taken from an `ls` output and put them (zero sized) in a destination folder
# it's used to create test files for filesorter

PROJECT_PATH = os.path.dirname(__file__)
ls_file = os.path.join(PROJECT_PATH, "ls_file.txt")
destination_folder = os.path.join(PROJECT_PATH, 'test', 'folder_to_monitor')
print "Creating structure from %s" % ls_file


# get lines from the ls output
lines = [line.strip() for line in file(ls_file).readlines()]
lines = filter(lambda x: x, lines)


def scan_ls_file(lines, destination_folder, only_folders=True):
    current_folder = destination_folder
    for line in lines:
        if line[-1] == ":":  # folders are indicated with a ending colon
            dir_name = line[:-1]
            current_folder = os.path.abspath(os.path.join(destination_folder, dir_name))
            if not os.path.isdir(current_folder):
                print "creating %s" % current_folder
                os.makedirs(current_folder)
        else:
            if only_folders:
                continue
            maybe_file_path = os.path.join(current_folder, line)
            if os.path.isdir(maybe_file_path):  # this file is not a file, is a folder
                continue
            if not os.path.isfile(maybe_file_path):
                print "\t%s" % maybe_file_path
                open(maybe_file_path, 'a').close()

# Do a first scan creating folders...
scan_ls_file(lines, destination_folder, only_folders=True)
# ... then create the files, where they are not a folder
scan_ls_file(lines, destination_folder, only_folders=False)





