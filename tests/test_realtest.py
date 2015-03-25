# Test to populate the folder to monitor (using create_files_from_ls) run the rules and check the results
import os
from filesorter import FileSorter
import pytest
import shutil
from tests.playground.create_files_from_ls import LSCreator

TESTS_PATH = os.path.dirname(__file__)
PLAYGROUND_FOLDER = os.path.join(TESTS_PATH, "playground")

source_folder = None
target_folder = None


@pytest.fixture(scope='module')
def playground_folder(request):
    global source_folder, target_folder

    ls_file = os.path.join(PLAYGROUND_FOLDER, "ls_file.txt")
    source_folder = os.path.join(PLAYGROUND_FOLDER, 'folder_to_monitor')
    print "Creating structure from %s" % ls_file
    lc = LSCreator(
        ls_file=ls_file,
        destination_folder=source_folder,
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
        shutil.rmtree(source_folder)
        shutil.rmtree(target_folder)

    request.addfinalizer(destroy_fixtures)


def test_realworld_on_source(playground_folder):
    assert len(os.listdir(source_folder)) == 1, "Only one skipped file should remain on source."


def test_realworld(playground_folder):
    # we expect 4 file in the season Person of Interest, all of them containing 'person'
    poi_files = os.listdir(os.path.join(target_folder, 'Serie', 'Person of Interest', 'S04'))
    assert len(poi_files) == 4
    assert len(filter(lambda x: "person" in os.path.basename(x).lower(), poi_files)) == 4

