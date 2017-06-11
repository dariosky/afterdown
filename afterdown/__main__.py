# coding=utf-8
from __future__ import print_function, unicode_literals

import argparse
import datetime
import json
import logging
import os
import sys

from afterdown.core.countersummary import CounterSummary
from afterdown.core.dropboxsync import dropbox_sync, add_magnet_url
from afterdown.core.email.log import BufferedSmtpHandler
from afterdown.core.email.mail_report import AfterMailReport
from afterdown.core.knownfiles import KnownFiles
from afterdown.core.rss import rss_zoogle_sync
from afterdown.core.rules import Rule, ApplyResult
from afterdown.core.utils import recursive_update, dependency_resolver

VERSION = "0.9.9"
FS_ENC = 'UTF-8'
PROJECT_PATH = os.path.dirname(__file__)

try:
    import requests
except ImportError:
    requests = None

print(("AfterDown %s" % VERSION))
print(("Copyright (C) 2015-%s  Dario Varotto\n" % datetime.date.today().year))


class AfterDown(object):
    def get_logger(self, log_path=None, VERBOSE=False):
        l = logging.getLogger("afterdown")
        l.setLevel(logging.DEBUG)
        # log events to console
        console_handler = logging.StreamHandler(sys.stdout)
        l.setLevel(logging.DEBUG if VERBOSE else logging.INFO)
        l.addHandler(console_handler)
        # if log_path is defined log also there
        if log_path:
            log_dir = os.path.dirname(log_path)
            if not os.path.isdir(log_dir):
                os.makedirs(log_dir)
            self.file_logger = logging.FileHandler(log_path)
            self.file_logger.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            l.addHandler(self.file_logger)
        # return the logger now, maybe I will add the mail handler later, after parsing the config
        return l

    def __init__(self, config_file, log_path=None, DEBUG=False, COMMIT=True, VERBOSE=False,
                 override_config=None):
        self.counters = CounterSummary()  # a counter for the possible cases
        self.override_config = override_config
        self.VERBOSE = VERBOSE
        self.COMMIT = COMMIT
        self.DEBUG = DEBUG
        self.log_path = log_path
        self.file_logger = None
        self.logger = self.get_logger(log_path=log_path, VERBOSE=VERBOSE)
        assert config_file, "Please provide me a config file."
        if not os.path.isfile(config_file):
            raise Exception("Config file %s not found." % config_file)
        self.config_file = config_file
        self.config = None
        self.deleteEmptyFolders = True
        self.touched_folders = set()  # source folders touched (by a MOVE or DELETE)
        self.error_mail_handler = None  # BufferedSmtpHandler, flushed when need to send mail
        self.report_mail = None  # the AfterMailReport that will send the pretty report
        self.knownfiles = None

    def run(self):
        if self.config is None:
            self.config = self.read_config()
        self.knownfiles = KnownFiles(self.config["knownfiles"])

        root = os.path.abspath(self.config['source'])
        assert os.path.isdir(root), "Cannot find the defined source %s" % root

        counters = self.counters
        kodi_update_needed = False

        logger = self.logger
        # on walk and on file operations use encoded binary strings
        for foldername, dirnames, filenames in os.walk(root.encode('utf-8'), followlinks=True):
            foldername = foldername.decode(FS_ENC)
            logger.debug(foldername[len(root) + 1:] or "/")
            for filename in filenames:
                filename = filename.decode(FS_ENC)

                counters['_tot'] += 1
                fullpath = os.path.join(foldername, filename)
                filepath = os.path.join(foldername[len(root) + 1:], filename)
                # each file found is a possible candidate...
                candidate = dict(
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
                        done = rule.apply(candidate, commit=self.COMMIT)
                        if done.action in (Rule.ACTION_DELETE, Rule.ACTION_MOVE):
                            target_file = done.filepath
                            touched_folder = os.path.dirname(target_file)
                            self.touched_folders.add(touched_folder)
                        if done.action == Rule.ACTION_MOVE and rule.updateKodi:
                            kodi_update_needed = True
                        logger.info("%s" % done)
                        if self.report_mail:
                            self.report_mail.add_row(done)
                        counters[done.actionName or done.action] += 1
                    else:
                        logger.warning("UNSURE: %s matches %s" % (filepath, matches))
                        if not self.knownfiles.is_known(filepath):
                            # warn for unsure files only when they are new
                            counters['_unsure_new'] += 1
                            if self.report_mail:
                                done = ApplyResult(action=Rule.ACTION_UNSURE, filepath=filepath)
                                # add some forced token to the row
                                # (the rule doesn't know how may rules apply)
                                self.report_mail.add_row(
                                    done,
                                    tokens=done.tokens + [
                                        "%d matching rules" % len(
                                            rules_by_confidence[max_confidence])])
                        else:
                            logger.debug("Unsure file %s is not new" % filepath)
                            counters['_unsure_old'] += 1
                else:
                    logger.info("%s does not match" % filepath)
                    if not self.knownfiles.is_known(filepath):
                        counters['_unknown_new'] += 1
                        # warn for unknow files only when they are new
                        if self.report_mail:
                            done = ApplyResult(action=Rule.ACTION_UNKNOWN, filepath=filepath)
                            self.report_mail.add_row(done)
                    else:
                        logger.debug("Unknown file %s is not new" % filepath)
                        counters['_unknown_old'] += 1

        # LATER: Check the file is not in use
        if kodi_update_needed and self.config.get("kodi", {}).get('requestUpdate',
                                                                  False) and self.COMMIT:
            if not requests:
                logger.error("Requests is needed to syncronize with Kodi.")
                logger.error("Install it with 'pip install requests'.")
            else:
                kodi_host = self.config['kodi'].get('host', 'localhost')
                logger.info(
                    "Something changed on target folder, asking Kodi to update video library.")
                try:
                    response = requests.post(
                        'http://{kodi_host}/jsonrpc'.format(
                            kodi_host=kodi_host
                        ),
                        headers={"Content-Type": "application/json"},
                        data=json.dumps(dict(
                            jsonrpc="2.0",
                            method="VideoLibrary.Scan",
                            params={},
                            id=1
                        )),
                    )
                    if response.status_code != 200 or response.json().get('result') != 'OK':
                        logger.error(
                            "Update Kody library failed, check jsonrpc is enabled."
                        )
                    if self.report_mail:
                        done = ApplyResult(action=Rule.ACTION_KODI_REFRESH, filepath="")
                        self.report_mail.add_row(done)
                except Exception as e:
                    logger.error(
                        "Errors when trying to communicate with Kodi, "
                        "You'll have to update your video library manually.")
                    logger.error(kodi_host)
                    logger.error("%s" % e)

        if self.touched_folders and self.deleteEmptyFolders:
            logger.debug("Touched folders %s", self.touched_folders)
            self.do_delete_touched_folders()
        if "dropbox" in self.config and self.COMMIT:
            self.dropbox_sync()
        if "rssfeed" in self.config and self.COMMIT:
            self.get_rssfeed()

        summary = "%s" % counters
        logger.info(summary)
        if self.report_mail:
            self.report_mail.set_summary(summary)

        if self.error_mail_handler:
            self.error_mail_handler.flush()
        if self.report_mail:
            self.report_mail.send()
        if not self.DEBUG:
            self.knownfiles.save()
        if self.file_logger:
            self.file_logger.close()

    def read_config(self):
        with open(self.config_file) as f:
            config = json.load(f)  # read the config form json
        if self.override_config:
            config = recursive_update(config, self.override_config)
        config = self.prepare_config(config)  # validate and prepare config
        return config

    def prepare_config(self, config):
        assert "source" in config, "The configuration should contain a valid 'source'"
        assert "rules" in config, "The configuration should contain 'rules'"
        # delete all touched empty folders (and parents) when empty
        self.deleteEmptyFolders = config.get('deleteEmptyFolders', True) and True or False
        if "types" in config:
            # Processing the parent rules
            types_definition = []
            for name, rule_def in config['types'].items():
                rule_def['name'] = name  # add the key as the typerule name
                types_definition.append(rule_def)
            config['types'] = {}

            def add_type_to_config(rule_def):
                """
                :type rule_def: dict
                """
                rule_name = rule_def.get('name')  # remove the name we added for dependency solver
                rule = Rule(rule_def, name=rule_name, config=config)
                name = rule.name  # the rule does the normalization
                assert name not in config['types'], "Multiple type definition for %s" % name
                config['types'][name] = rule

            def get_dependencies(rule_def):
                dependencies = []
                for r in types_definition:
                    if r['name'] in rule_def.get('types', []):
                        dependencies.append(r)
                return dependencies

            # change config.types to a list of rules

            dependency_resolver(types_definition, get_dependencies, add_type_to_config)

        config["rules"] = [Rule(rule_def, config=config) for rule_def in config["rules"]]
        # defaults for kodi configuration
        if "kodi" not in config:
            config["kodi"] = dict(host="localhost",
                                  requestUpdate=False)

        if "mail" in config:
            if config['mail']:
                default_mail_settings = dict(
                    subject="Afterdown report",
                    smtp="localhost:25",
                )
                default_mail_settings['from'] = os.getenv("AFTERDOWN_MAIL_FROM")
                default_mail_settings['password'] = os.getenv("AFTERDOWN_MAIL_PASSWORD")
                for key, value in default_mail_settings.items():
                    if key not in config["mail"]:
                        config["mail"][key] = value
                assert config["mail"][
                    "to"], "If you activate the send mail function, specify a recipient \"to\""
                smtp_host = config["mail"]["smtp"]
                if ":" in smtp_host:
                    smtp_host, smtp_port = smtp_host.split(":")
                    config["mail"]["smtp"] = smtp_host
                    config["mail"]["port"] = smtp_port
                else:
                    config["mail"]["port"] = None
                mail_parameters = dict(
                    mailfrom=config["mail"]["from"],
                    mailto=config["mail"]["to"],
                    subject=config["mail"]["subject"] or None,
                    smtp_host=config["mail"]["smtp"],
                    smtp_port=config["mail"]["port"],

                    smtp_username=config["mail"]["from"],
                    smtp_password=config["mail"]["password"],
                    DEBUG=self.DEBUG,
                )
                self.report_mail = AfterMailReport(**mail_parameters)
                self.error_mail_handler = BufferedSmtpHandler(
                    send_mail=True,  # Always send (when we have events)
                    **mail_parameters
                )
                self.error_mail_handler.setLevel(logging.ERROR)  # just send errors with this logger
                self.logger.addHandler(self.error_mail_handler)
            else:
                del config["mail"]

        if "dropbox" in config:
            if not isinstance(config["dropbox"], dict) \
                    or "start_torrents_on" not in config["dropbox"]:
                # if we don't need Dropbox, we can drop it's config
                del config["dropbox"]

        if "knownfiles" not in config or not config["knownfiles"]:
            config["knownfiles"] = ".afterknown"
        if "rssknown" not in config or not config["rssknown"]:
            config["rssknown"] = ".afterknown_rss"
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
                try:
                    os.rmdir(folder_path)
                    self.logger.info("Deleted empty folder: %s" % folder_path)
                except OSError:
                    self.logger.error("Cannot delete folder %s" % folder_path)
                if folder_path != root:
                    parent_folder = os.path.dirname(folder_path)
                    self.touched_folders.add(parent_folder)

    def dropbox_sync(self):
        """
            Try to sync with a dropbox folder for various reason, actually to get a list of torrents
            to pass to Transmission
        """
        source_files = dropbox_sync(
            keyfile=".afterdown_dropbox_keys.json",
            torrents_folder=self.config['dropbox'].get("start_torrents_on"),
            add_to_transmission=self.config['dropbox'].get("add_torrent_to_transmission"),
            move_downloaded_on=self.config['dropbox'].get('move_them_on'),
        )
        if not source_files:
            return  # nothing to report, maybe an error
        if self.report_mail:
            for source_path in source_files:
                if source_path:  # exclude falsey values
                    download_result = ApplyResult(action=Rule.ACTION_DOWNLOAD,
                                                  filepath=source_path)
                    self.report_mail.add_row(download_result)

    def get_rssfeed(self):
        rss_config = self.config['rssfeed']

        def add_url(title, url):
            add_magnet_url(url)
            download_result = ApplyResult(action=Rule.ACTION_DOWNLOAD,
                                          filepath=title)
            self.report_mail.add_row(download_result)

        if rss_config.get('zoogle'):
            rss_zoogle_sync(rss_url=rss_config['zoogle'],
                            known_filename=self.config["rssknown"],
                            add_callback=add_url
                            )


# DONE: keep a list of folder from wich we removed or moved files,
# and at the end delete them if they are empty
# DONE: Send mail of the activities
# DONE: Keep the movie in a separate folder based on the filename without extension
def main():
    parser = argparse.ArgumentParser(
        "Afterdown",
        description="Sort everything in a folder based on some rules you define")
    parser.add_argument("-v", "--version", action="version", version=VERSION)
    parser.add_argument("--debug",
                        help="Run in debug mode, no file moved, no mail sent",
                        default=False,
                        action="store_true")
    parser.add_argument("--verbose",
                        help="Verbose output",
                        default=False,
                        action="store_true")
    parser.add_argument("-c", "--config",
                        help="Select the config json file to use"
                             " (default to rules.json in current folder)",
                        default="rules.json")
    parser.add_argument("--log",
                        help="Specify the log file path (default afterdown.log in current folder)",
                        default=os.path.join(PROJECT_PATH, "logs", "afterdown.log"))
    parser.add_argument("--nodropboxsync",
                        help="Disable Dropbox syncronization",
                        default=False,
                        action="store_true")
    parser.add_argument("--nokodi",
                        help="Disable Kodi updates",
                        default=False,
                        action="store_true")
    parser.add_argument("--nomail",
                        help="Disable all mails",
                        default=False,
                        action="store_true")
    parser.add_argument("--mailto",
                        help="Override the mail recipients",
                        default=None
                        )
    parser.add_argument("--knownfiles",
                        help="Filepath used to save a list of know missed files",
                        default="")
    parser.add_argument("source", help="override the folder to be monitored", default=None,
                        nargs="?")
    parser.add_argument("target", help="override the destination folder", default=None, nargs="?")

    args = parser.parse_args()

    override_config = {}
    if args.source is not None:
        override_config["source"] = args.source
    if args.target is not None:
        override_config["target"] = args.target
    if args.nodropboxsync:
        override_config['dropbox'] = None
    if args.nokodi:
        override_config['kodi'] = None
    if args.nomail:
        if args.mailto:
            raise Exception("You can't specify both nomail and mailto")
        override_config['mail'] = None
    if args.mailto:
        override_config['mail'] = {"to": args.mailto}
    if args.knownfiles:
        override_config['knownfiles'] = args.knownfiles
    sorter = AfterDown(
        config_file=args.config,
        DEBUG=args.debug,  # When debugging no mail are sent
        VERBOSE=args.verbose,  # When verbose we will print on console even debug messages
        COMMIT=not args.debug,
        # When commit we actually move or delete files from the watched folder
        log_path=args.log,
        override_config=override_config,
    )
    sorter.run()


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO, format="%(message)s")

    main()
