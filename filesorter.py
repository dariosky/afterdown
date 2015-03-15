#!/usr/bin/python
# coding: utf-8
import json
import os

from core.rules import Rule


print "Filesorter 0.031415"
print "Copyright (C) 2015  Dario Varotto\n"

PROJECT_PATH = os.path.dirname(__file__)


class FileSorter(object):
    def __init__(self, config_file=None):
        if config_file is None:
            config_file = os.path.join(PROJECT_PATH, 'rules.json')
        if not os.path.isfile(config_file):
            raise Exception("Config file %s not found." % config_file)
        self.config_file = config_file
        self.config = None

    def run(self):
        if self.config is None:
            self.config = self.read_config()

        root = os.path.abspath(self.config['source'])
        assert os.path.isdir(root), "Cannot find the defined source %s" % root

        print
        for foldername, dirnames, filenames in os.walk(root, followlinks=True):
            print root
            for filename in filenames:
                filepath = os.path.join(foldername[len(root) + 1:], filename)
                print filepath
                # TODO: Check the file is not in use

                break
            break

    def read_config(self):
        config = json.load(file(self.config_file))  # read the config form json
        config = self.prepare_config(config)  # validate and prepare config
        return config

    def prepare_config(self, config):
        assert "source" in config, "The configuration should contain a valid 'source'"
        assert "rules" in config, "The configuration should contain some 'rules'"
        types = {}
        if "types" in config:
            # change config.types to a list of rules
            for denormalized_name, rule_def in config['types'].items():
                rule = Rule(rule_def, name=denormalized_name, previous_rules=types)
                name = rule.name  # the rule does the normalization
                assert name not in types, "Multiple file type definition for %s" % name
                types[name] = rule
                # print pprint(types)

        rules = [Rule(rule_def, previous_rules=types) for rule_def in config["rules"]]
        config["rules"] = rules

        # pprint(config)
        return config


if __name__ == '__main__':
    sorter = FileSorter()
    sorter.run()
