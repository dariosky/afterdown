#!/usr/bin/python
# coding: utf-8
from collections import OrderedDict
from copy import copy
import json
import os
from pprint import pprint

print "Filesorter 0.031415"
print "Copyright (C) 2015  Dario Varotto\n"

PROJECT_PATH = os.path.dirname(__file__)


class Rule(object):
    """ This object define a sort rule
        should be applyed on a rule, or an a type (that is a sort of named rule)
    """

    ACTION_MOVE = "move the file to a position"
    ACTION_DELETE = "delete the file, use with caution"
    defaults = OrderedDict([  # define the defaults, that are also the possible fields
                              ("ext", []),
                              ("size", []),
                              ("priority", 50),
                              ("filter_names", []),
                              ("season_split", False),
                              ("target", None),
                              ("action", ACTION_MOVE),
                              ("name", None),
                              ("to", None),
                              ("matches", []),
                              ])

    def __init__(self, rule_def, name=None):
        for key, default_value in self.defaults.items():
            setattr(self, key, rule_def.get(key, copy(default_value)))

        # add the singular forms, that are sometime more practical
        if "match" in rule_def:
            self.matches.append(rule_def["match"])
        if self.action == "delete":
            self.action = self.ACTION_DELETE
        if self.action == "move":
            self.action = self.ACTION_MOVE
        assert self.action in (self.ACTION_MOVE, self.ACTION_DELETE), "Unknown action %s" % self.action
        self.name = name

    def __repr__(self):
        definition = []
        for key, default_value in self.defaults.items():
            if key == "name":
                continue
            value = getattr(self, key)
            if value != default_value:
                definition.append("%s:%s" % (key, value))
        return "Rule{name}: {definition}".format(
            name=" " + self.name if self.name else "",
            definition=", ".join(definition) if definition else "-"
        )

    def __unicode__(self):
        return unicode(self.__str__())


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
        if "types" in config:
            # change config.types to a list of rules
            types = {}
            for denormalized_name, rule_def in config['types'].items():
                name = denormalized_name.lower()  # keep the lowercase file type
                rule = Rule(rule_def, name=name)
                assert name not in types, "Multiple file type definition for %s" % name
                types[name] = rule
            config['types'] = types
        rules = [Rule(rule_def) for rule_def in config["rules"]]
        config["rules"] = rules

        pprint(config)
        return config


if __name__ == '__main__':
    sorter = FileSorter()
    sorter.run()
