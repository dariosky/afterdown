# Create a folder with unicode chars and test that everything works
from __future__ import print_function

import os
import shutil

import pytest

from afterdown import AfterDown
from tests.playground.create_files_from_ls import LSCreator

TESTS_PATH = os.path.dirname(__file__)
PLAYGROUND_FOLDER = os.path.join(TESTS_PATH, "unicodes")

source_folder = None
target_folder = None


@pytest.fixture(scope='module')
def playground_folder(request):
    global source_folder, target_folder

    ls_file = os.path.join(PLAYGROUND_FOLDER, "ls_file.txt")
    source_folder = os.path.join(PLAYGROUND_FOLDER, 'folder_to_monitor')
    print("Creating structure from %s" % ls_file)
    lc = LSCreator(
        ls_file=ls_file,
        destination_folder=source_folder,
    )
    lc.run()

    # now we run the program ...
    # we have the playground ready the rules file with source and target as relative path
    # so change the working path to the playground
    os.chdir(PLAYGROUND_FOLDER)
    config_file = 'rules.json'
    log_path = os.path.join(PLAYGROUND_FOLDER, "log.log")
    sorter = AfterDown(
        config_file=config_file,
        log_path=log_path,
        DEBUG=True,  # When debugging no mail are sent
    )
    sorter.run()

    target_folder = sorter.config["target"]

    # and after all the tests we can delete the target and source folders
    def destroy_fixtures():
        print("Destroying Fixtures")
        shutil.rmtree(source_folder)
        shutil.rmtree(target_folder)
        sorter.file_logger.close()
        os.remove(log_path)

    request.addfinalizer(destroy_fixtures)


def test_realworld_on_source(playground_folder):
    assert len(os.listdir(source_folder)) == 0, "Only one skipped file should remain on source."


def test_one(playground_folder):
    # we expect 4 file in the season Person of Interest, all of them containing 'person'
    one_files = os.listdir(os.path.join(target_folder, 'Serie', 'one'))
    assert len(one_files) == 1
