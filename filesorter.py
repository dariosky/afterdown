#!/usr/bin/python
# coding: utf-8
import json
import logging
import os
import sys

try:
    import requests
except ImportError:
    requests = None

from core.rules import Rule

print "Filesorter 0.031415"
print "Copyright (C) 2015  Dario Varotto\n"

PROJECT_PATH = os.path.dirname(__file__)
COMMIT = True
VERBOSE = False

def get_logger():
    l = logging.getLogger("filesorter")
    l.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    l.setLevel(logging.DEBUG if VERBOSE else logging.WARNING)
    l.addHandler(handler)

    return l


logger = get_logger()


class FileSorter(object):
    def __init__(self, config_file=None):
        if config_file is None:
            config_file = os.path.join(PROJECT_PATH, 'rules.json')
        if not os.path.isfile(config_file):
            raise Exception("Config file %s not found." % config_file)
        self.config_file = config_file
        self.config = None
        self.deleteEmptyFolders = True
        self.touched_folders = set()  # the folders on source that have been touched (by a MOVE or DELETE)

    def run(self):
        if self.config is None:
            self.config = self.read_config()

        root = os.path.abspath(self.config['source'])
        assert os.path.isdir(root), "Cannot find the defined source %s" % root

        counters = dict(tot=0, one=0, unsure=0, none=0, applied=0)  # a counter for the possible cases
        actions = []

        for foldername, dirnames, filenames in os.walk(root, followlinks=True):
            # print foldername[len(root) + 1:] or "/"
            for filename in filenames:
                counters['tot'] += 1
                fullpath = os.path.join(foldername, filename)
                filepath = os.path.join(foldername[len(root) + 1:], filename)
                # print filepath
                candidate = dict(  # each file found is a possible candidate...
                                   filepath=filepath,  # with a path relative to the source
                                   fullpath=fullpath,  # the fullpath, needed if the rule wants to access the file
                                   # other eventual things will be added from the rules when needed...
                                   # possible candidates are: extension, filesize, xmp tags or things like that
                                   )
                matches = []
                for rule in self.config["rules"]:
                    confidence = rule.match(candidate)
                    if confidence is not False:
                        matches.append((confidence, rule))
                if matches:
                    # print "It matches %d rules: %s" % (len(matches), matches)
                    if len(matches) == 1:
                        counters['one'] += 1

                    # sort by confidence
                    rules_by_confidence = {}
                    max_confidence = 0
                    for confidence, rule in matches:
                        # group by confidence
                        rules = rules_by_confidence.get(confidence, [])
                        rules.append(rule)
                        rules_by_confidence[confidence] = rules
                        if confidence > max_confidence:
                            max_confidence = confidence

                    # if there is only one rule with top confidence apply it
                    if len(rules_by_confidence[max_confidence]) == 1:
                        rule = rules_by_confidence[max_confidence][0]
                        done = rule.apply(candidate, commit=COMMIT)
                        if done.action in (Rule.ACTION_DELETE, Rule.ACTION_MOVE):
                            target_file = done.filepath
                            touched_folder = os.path.dirname(target_file)
                            self.touched_folders.add(touched_folder)
                        print done
                        actions.append(done)
                        counters['applied'] += 1
                    else:
                        counters['unsure'] += 1
                        print "UNSURE: %s matches %s" % (filepath, matches)
                else:
                    print filepath, "Does not match"
                    counters['none'] += 1
                    # break  # just one folder test
                    # LATER: Check the file is not in use
                    # print
        moved_actions = filter(lambda d: d.action == Rule.ACTION_MOVE, actions)
        if moved_actions and self.config.get("kodi", {}).get('request_update', False) and COMMIT:
            if not requests:
                logger.error("requests is needed to syncronize with Kodi.")
            else:
                kodi_host = self.config['kodi'].get('host', 'localhost')
                logger.info("Something changed on target folder, telling Kodi to update video library.")
                try:
                    requests.get(
                        'http://{kodi_host}/jsonrpc?request={"jsonrpc":"2.0","method":"VideoLibrary.Scan"}'.format(
                            kodi_host=kodi_host
                        ))
                except Exception as e:
                    logger.error("Errors when trying to communicate with Kodi, please do the Video Sync manually.")
                    logger.error("%s" % e)

        if self.touched_folders and self.deleteEmptyFolders:
            print "Touched folders", self.touched_folders
            self.do_delete_touched_folders()
        print "we had {tot} files: {applied} actions taken, {unsure} uncertain, {none} unrecognized.".format(**counters)

    def read_config(self):
        config = json.load(file(self.config_file))  # read the config form json
        config = self.prepare_config(config)  # validate and prepare config
        return config

    def prepare_config(self, config):
        assert "source" in config, "The configuration should contain a valid 'source'"
        assert "rules" in config, "The configuration should contain 'rules'"
        # delete all touched empty folders (and parents) when empty
        self.deleteEmptyFolders = config.get('deleteEmptyFolders', True) and True or False
        if "types" in config:
            types_definition = config['types']
            config['types'] = {}
            # change config.types to a list of rules
            for denormalized_name, rule_def in types_definition.items():
                rule = Rule(rule_def, name=denormalized_name, config=config)
                name = rule.name  # the rule does the normalization
                assert name not in config['types'], "Multiple file type definition for %s" % name
                config['types'][name] = rule
                # print pprint(types)

        config["rules"] = [Rule(rule_def, config=config) for rule_def in config["rules"]]
        # defaults for kodi configuration
        if "kodi" not in config:
            config["kodi"] = dict(host="localhost",
                                  request_update=False)
        # pprint(config)
        return config

    def do_delete_touched_folders(self):
        """
        Delete all empty touched folder recurring on ancestor until root
        """
        root = os.path.abspath(self.config['source'])
        while self.touched_folders:
            folder = self.touched_folders.pop()
            folder_path = os.path.join(root, folder)
            if folder and os.path.isdir(folder_path) \
                    and folder_path.startswith(root) and folder_path != root \
                    and not os.listdir(folder_path):
                logger.info("Deleting empty folder:", folder_path)
                os.rmdir(folder_path)
                if folder_path != root:
                    parent_folder = os.path.dirname(folder_path)
                    self.touched_folders.add(parent_folder)

# DONE: keep a list of folder from wich we removed or moved files, and at the end delete them if they are empty
# TODO: handle calling parameters to become an usable command getargs
# TODO: Send mail of the activities
# DONE: Keep the movie in a separate folder based on the filename without extension

if __name__ == '__main__':
    sorter = FileSorter()
    sorter.run()
