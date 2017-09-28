import os

from afterdown.tests.test_known import getSorter

current_folder = os.path.dirname(__file__)
sorter = getSorter(
    config_filename=os.path.join(
        current_folder, 'test_dropbox_rules.json')
)  # a minimum config accessing dropbox
sorter.config = sorter.read_config()
sorter.dropbox_sync()
