#!/usr/bin/python
# coding: utf-8
from collections import defaultdict
import json
import logging
import logging.handlers
import os
from subprocess import call
import posixpath
import sys
import tempfile

from core.email.log import BufferedSmtpHandler
from core.email.mail_report import AfterMailReport


VERSION = "0.3.0"

try:
    import requests
except ImportError:
    requests = None

from core.rules import Rule, ApplyResult

print ("AfterDown %s" % VERSION)
print ("Copyright (C) 2015  Dario Varotto\n")

DROPBOX_KEYFILE = ".afterdown_dropbox_keys.json"


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
            self.file_logger.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            l.addHandler(self.file_logger)
        # return the logger now, maybe I will add the mail handler later, after parsing the config
        return l

    def __init__(self, config_file, log_path=None, DEBUG=False, COMMIT=True, VERBOSE=False,
                 override_config=None):
        self.override_config = override_config
        self.VERBOSE = VERBOSE
        self.COMMIT = COMMIT
        self.DEBUG = DEBUG
        self.logger = self.get_logger(log_path=log_path, VERBOSE=VERBOSE)
        assert config_file, "Please provide me a config file."
        if not os.path.isfile(config_file):
            raise Exception("Config file %s not found." % config_file)
        self.config_file = config_file
        self.config = None
        self.deleteEmptyFolders = True
        self.touched_folders = set()  # the folders on source that have been touched (by a MOVE or DELETE)
        self.error_mail_handler = None  # the eventual BufferedSmtpHandler, will be flushed when need to send mail
        self.report_mail = None  # the AfterMailReport that will send the pretty report

    def run(self):
        if self.config is None:
            self.config = self.read_config()

        root = os.path.abspath(self.config['source'])
        assert os.path.isdir(root), "Cannot find the defined source %s" % root

        counters = defaultdict(int)  # a counter for the possible cases
        actions = []
        kodi_update_needed = False

        logger = self.logger
        for foldername, dirnames, filenames in os.walk(root, followlinks=True):
            logger.debug(foldername[len(root) + 1:] or "/")
            for filename in filenames:
                counters['tot'] += 1
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
                        counters[done.action] += 1
                    else:
                        counters['unsure'] += 1
                        logger.warning("UNSURE: %s matches %s" % (filepath, matches))
                        done = ApplyResult(action=Rule.ACTION_UNSURE, filepath=filepath)
                        # add some forced token to the row (the rule doesn't know how may rules apply)
                        self.report_mail.add_row(
                            done,
                            tokens=done.tokens + ["%d matching rules" % len(rules_by_confidence[max_confidence])])
                else:
                    logger.info("%s does not match" % filepath)
                    counters['unknown'] += 1
                    if self.report_mail:
                        done = ApplyResult(action=Rule.ACTION_UNKNOWN, filepath=filepath)
                        self.report_mail.add_row(done)

        # LATER: Check the file is not in use

        if kodi_update_needed and self.config.get("kodi", {}).get('requestUpdate', False) and self.COMMIT:
            if not requests:
                logger.error("Requests is needed to syncronize with Kodi.")
            else:
                kodi_host = self.config['kodi'].get('host', 'localhost')
                logger.info("Something changed on target folder, asking Kodi to update video library.")
                try:
                    requests.get(
                        'http://{kodi_host}/jsonrpc?request={"jsonrpc":"2.0","method":"VideoLibrary.Scan"}'.format(
                            kodi_host=kodi_host
                        ))
                    if self.report_mail:
                        done = ApplyResult(action=Rule.ACTION_KODI_REFRESH, filepath="")
                        self.report_mail.add_row(done)
                except Exception as e:
                    logger.error("Errors when trying to communicate with Kodi, please do the Video Sync manually.")
                    logger.error("%s" % e)

        if self.touched_folders and self.deleteEmptyFolders:
            logger.debug("Touched folders %s", self.touched_folders)
            self.do_delete_touched_folders()
        if "dropbox" in self.config:
            self.dropbox_sync()

        summary_tokens = [
            "we had %d files" % counters['tot'],
            "%d recognized" % counters["MOVE"] if counters["MOVE"] else None,
            "%d deleted" % counters["DELETE"] if counters["DELETE"] else None,
            "%d unknown" % counters["unknown"] if counters["unknown"] else None,
            "%d unsure" % counters["unsure"] if counters["unsure"] else None,
        ]
        summary = ", ".join(filter(lambda x: x, summary_tokens))  # strip empty tokens
        logger.info(summary)
        if self.report_mail:
            self.report_mail.set_summary(summary)

        if self.error_mail_handler:
            self.error_mail_handler.flush()
        if self.report_mail:
            self.report_mail.send()

    def read_config(self):
        config = json.load(file(self.config_file))  # read the config form json
        if self.override_config:
            config.update(self.override_config)
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

        config["rules"] = [Rule(rule_def, config=config) for rule_def in config["rules"]]
        # defaults for kodi configuration
        if "kodi" not in config:
            config["kodi"] = dict(host="localhost",
                                  requestUpdate=False)

        if "mail" in config:
            default_mail_settings = dict(
                subject="Afterdown report",
                smtp="localhost:25",
            )
            default_mail_settings['from'] = os.getenv("AFTERDOWN_MAIL_FROM")
            default_mail_settings['password'] = os.getenv("AFTERDOWN_MAIL_PASSWORD")
            for key, value in default_mail_settings.items():
                if key not in config["mail"]:
                    config["mail"][key] = value
            assert config["mail"]["to"], "If you activate the send mail function, specify a recipient \"to\""
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
        if "dropbox" in config:
            if not isinstance(config["dropbox"], dict) or "start_torrents_on" not in config["dropbox"]:
                # if we don't need Dropbox, we can drop it's config
                del config["dropbox"]
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
                self.logger.info("Deleting empty folder: %s" % folder_path)
                os.rmdir(folder_path)
                if folder_path != root:
                    parent_folder = os.path.dirname(folder_path)
                    self.touched_folders.add(parent_folder)

    def dropbox_sync(self):
        """
            Try to sync with a dropbox folder for various reason, actually to get a list of torrents
            to pass to Transmission
        """
        try:
            import dropbox
        except ImportError:
            dropbox = None
            self.logger.error("To use Dropbox syncronization you need the Dropbox package.")
            self.logger.error("Use: pip install dropbox.")
            return
        if not os.path.isfile("%s" % DROPBOX_KEYFILE):
            self.logger.error("To sync with Dropbox you need a %s file with app_key and app_secret" % DROPBOX_KEYFILE)
            return
        dropbox_config = json.load(file(DROPBOX_KEYFILE, "r"))
        if "app_key" not in dropbox_config or "app_secret" not in dropbox_config:
            self.logger.error("The dropbox config should be a json file with with app_key and app_secret")
            return
        # everything is ok, we can start the Dropbox OAuth2
        if "access_token" not in dropbox_config:
            # we have the app, but no link to an account, ask to authorize
            app_key, app_secret = dropbox_config["app_key"], dropbox_config["app_secret"]
            print "Everything is set, going to Dropbox"
            flow = dropbox.client.DropboxOAuth2FlowNoRedirect(app_key, app_secret)
            authorize_url = flow.start()
            print '1. Go to: ' + authorize_url
            print '2. Click "Allow" (you might have to log in first)'
            print '3. Copy the authorization code.'
            code = raw_input("Enter the authorization code here: ").strip()
            access_token, user_id = flow.finish(code)
            dropbox_config["access_token"] = access_token
            self.logger.info("Storing access_token to Dropbox account")
            with file(DROPBOX_KEYFILE, "w") as f:
                json.dump(dropbox_config, f)
        else:
            # we can reuse the access_token
            access_token = dropbox_config["access_token"]
        try:
            if self.config['dropbox'].get("start_torrents_on"):
                torrents_folder = self.config['dropbox'].get("start_torrents_on")
                client = dropbox.client.DropboxClient(access_token)
                print "Sync with Dropbox account %s" % client.account_info()['email']
                folder_meta = client.metadata(torrents_folder)
                target_folder = None
                for content in filter(lambda meta: meta.get('mime_type') == u'application/x-bittorrent',
                                      folder_meta['contents']):
                    self.logger.info("%s %s %s" % (content['path'], "by", content["modifier"]["display_name"]))
                    self.process_dropbox_file(client, content)
        except dropbox.rest.ErrorResponse as e:
            self.logger.error(e)

    def process_dropbox_file(self, dropbox_client, filemeta):
        import dropbox

        if self.config['dropbox'].get("add_torrent_to_transmission"):
            # download the file to a temporary folder, then add it to transmission
            source_path = filemeta['path']
            with tempfile.NamedTemporaryFile(prefix="afterdown", suffix="temptorrent", delete=False) as temp:
                # print "Get from torrent to tempfile %s" % temp.name
                with dropbox_client.get_file(source_path) as f:
                    temp.write(f.read())
            try:
                call(["transmission-remote", "-a", temp.name])
                if self.report_mail:
                    download_result = ApplyResult(action=Rule.ACTION_DOWNLOAD, filepath=source_path)
                    self.report_mail.add_row(download_result)
                dropbox_move_target = self.config['dropbox'].get('move_them_on')
                if dropbox_move_target:
                    filename = os.path.basename(source_path)
                    target_path = posixpath.join(dropbox_move_target, filename)
                    try:
                        dropbox_client.file_move(source_path, target_path)
                    except dropbox.rest.ErrorResponse as e:
                        self.logger.error(
                            "Error moving dropbox file from {source} to {target}.\n{error_message}".format(
                                source=source_path, target=target_path, error_message=e.message
                            ))
            except:
                self.logger.error("Error running transmission-remote on file {path}".format(path=source_path))
            os.unlink(temp.name)


# DONE: keep a list of folder from wich we removed or moved files, and at the end delete them if they are empty
# DONE: Send mail of the activities
# DONE: Keep the movie in a separate folder based on the filename without extension

if __name__ == '__main__':
    import argparse

    PROJECT_PATH = os.path.dirname(__file__)

    parser = argparse.ArgumentParser("Afterdown",
                                     description="Sort everything in a folder based on some rules you define")
    parser.add_argument("-v", "--version", action="version", version=VERSION)
    parser.add_argument("--debug",
                        help="Run in debug mode, no file moved, no mail sent",
                        default=False,
                        action="store_true")
    parser.add_argument("-c", "--config",
                        help="Select the config json file to use (default to rules.json in current folder)",
                        default="rules.json")
    parser.add_argument("--log",
                        help="Specify the log file path (default afterdown.log in current folder)",
                        default=os.path.join(PROJECT_PATH, "logs", "afterdown.log"))
    parser.add_argument("--nodropboxsync",
                        help="Disable Dropbox syncronization",
                        default=False,
                        action="store_true")
    parser.add_argument("source", help="override the folder to be monitored", default=None, nargs="?")
    parser.add_argument("target", help="override the destination folder", default=None, nargs="?")

    args = parser.parse_args()

    override_config = {}
    if args.source is not None:
        override_config["source"] = args.source
    if args.target is not None:
        override_config["target"] = args.target
    if args.nodropboxsync:
        override_config['dropbox'] = None
    sorter = AfterDown(
        config_file=args.config,
        DEBUG=args.debug,  # When debugging no mail are sent
        VERBOSE=False,  # When verbose we will print on console even debug messages
        COMMIT=not args.debug,  # When commit we actually move or delete files from the watched folder
        log_path=args.log,
        override_config=override_config,
    )
    sorter.run()
