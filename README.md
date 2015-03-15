Filesorter is meant to monitor a folder with complete downloads, or something similar.
It should run in a cron job periodically checking the folder for new files
 these will be moved away based on a set of rules (when they are not in use)
 and some mail will be sent to notify the status.

An example rules files is `rules.json`
To test the program an example `ls_file.txt` is provided and a `create_files_from_ls.py` script will
generate the empty files based on that
