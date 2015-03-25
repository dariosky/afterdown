# Test to populate the folder to monitor (using create_files_from_ls) run the rules and check the results
import os
from filesorter import FileSorter
import pytest
import shutil
from tests.playground.create_files_from_ls import LSCreator

TESTS_PATH = os.path.dirname(__file__)
PLAYGROUND_FOLDER = os.path.join(TESTS_PATH, "playground")


@pytest.fixture(scope='module')
def playground_folder(request):
    ls_file = os.path.join(PLAYGROUND_FOLDER, "ls_file.txt")
    destination_folder = os.path.join(PLAYGROUND_FOLDER, 'folder_to_monitor')
    print "Creating structure from %s" % ls_file
    lc = LSCreator(
        ls_file=ls_file,
        destination_folder=destination_folder,
    )
    lc.run()

    # now we run the filesorter ...
    # we have the playground ready the rules file with source and target as relative path
    # so change the working path to the playground
    os.chdir(PLAYGROUND_FOLDER)
    config_file = 'rules.json'

    sorter = FileSorter(
        config_file=config_file,
        log_path=os.path.join(PLAYGROUND_FOLDER, "log.log"),
        DEBUG=True,  # When debugging no mail are sent
    )
    sorter.run()

    target_folder = sorter.config["target"]

    # and after all the tests we can delete the target and source folders
    def destroy_fixtures():
        print "Destroying Fixtures"
        shutil.rmtree(destination_folder)
        shutil.rmtree(target_folder)

    request.addfinalizer(destroy_fixtures)


def test_realworld(playground_folder):
    pass
