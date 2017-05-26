# Test to populate the folder to monitor (using create_files_from_ls) run the rules and check the results
from __future__ import print_function

import os
import shutil

import pytest

from afterdown.__main__ import AfterDown
from afterdown.tests.playground.create_files_from_ls import LSCreator

TESTS_PATH = os.path.dirname(__file__)
PLAYGROUND_FOLDER = os.path.join(TESTS_PATH, "known")

source_folder = "source"
target_folder = None


def getSorter():
    config_file = 'rules.json'
    sorter = AfterDown(
        config_file=config_file,
        log_path=None,
    )
    return sorter


@pytest.fixture(scope='module')
def unknownsorter(request):
    global source_folder, target_folder

    ls_file = os.path.join(PLAYGROUND_FOLDER, "ls_many_unknown.txt")
    source_folder = os.path.join(PLAYGROUND_FOLDER, 'source')
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
    sorter = getSorter()
    sorter.run()

    target_folder = sorter.config["target"]

    # and after all the tests we can delete the target and source folders
    def destroy_fixtures():
        print("Destroying Fixtures")
        shutil.rmtree(source_folder)
        shutil.rmtree(target_folder)
        os.remove(".afterknown")
        if sorter.log_path:
            os.remove(sorter.log_path)

    request.addfinalizer(destroy_fixtures)
    return sorter


def test_known_on_source(unknownsorter):
    assert len(os.listdir(source_folder)) == 2, "should have 2 file b.avi and x.avi"


def test_counters(unknownsorter):
    assert unknownsorter.counters.special_counters['_tot'] == 3, "Should have 3 files"
    assert unknownsorter.counters.special_counters['_unknown_new'] == 2, \
        "Should have 2 files unrecognized the first time"


def test_rerun(unknownsorter):
    """ Test that when running a 2nd time, all the previously file _unknown_new are not _unknown_old """
    resorter = getSorter()
    resorter.run()
    assert resorter.counters.special_counters['_unknown_old'] == 2, \
        "Should have 2 files unrecognized already known the 2nd time"


def test_forgot_when_missing(unknownsorter):
    """ Test that when a known file is removed, after a run it's forgotten """
    os.remove(os.path.join(source_folder, "x.avi"))
    resorter = getSorter()
    resorter.run()
    assert len(resorter.knownfiles.newdata) == resorter.counters.special_counters['_unknown_old']
