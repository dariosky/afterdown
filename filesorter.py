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

        counters = dict(tot=0, one=0, unsure=0, none=0, applied=0)  # a counter for the possible cases

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
                        done = rule.apply(candidate, commit=True)
                        print done
                        counters['applied'] += 1
                    else:
                        counters['unsure'] += 1
                        print "UNSURE: %s matches %s" % (filepath, matches)
                else:
                    print filepath, "Does not match"
                    counters['none'] += 1
                    # break  # just one folder test
                    # TODO: Check the file is not in use
                    # print
        print "we had {tot} files: {applied} actions taken, {unsure} uncertain, {none} unrecognized.".format(**counters)

    def read_config(self):
        config = json.load(file(self.config_file))  # read the config form json
        config = self.prepare_config(config)  # validate and prepare config
        return config

    def prepare_config(self, config):
        assert "source" in config, "The configuration should contain a valid 'source'"
        assert "rules" in config, "The configuration should contain 'rules'"
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

        # pprint(config)
        return config


if __name__ == '__main__':
    sorter = FileSorter()
    sorter.run()
