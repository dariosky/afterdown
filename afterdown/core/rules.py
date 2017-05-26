from __future__ import print_function, unicode_literals

import logging
import os
import random
import shutil
from collections import defaultdict

from afterdown.core.utils import guessit_video_type, guessit_video_title
from subliminal.core import save_subtitles

try:
    from html import escape
except ImportError:
    from cgi import escape

from afterdown.core.constants import OPERATORS_MAP, AttrDict
from afterdown.core.matching import try_match_strings
from afterdown.core.season_info import get_episode_infos

logger = logging.getLogger("afterdown.rules")


def normalize_field(key, value):
    if key == "name":
        return value.lower() if value else None
    elif key == "extensions":
        return value.lower() if value else None
    elif key == "size":
        if value is None:
            return None
        if value.isdigit():
            return "=", int(value)  # only the number means equal to N bytes
        operator = "="
        possibile_starting_operators = ["=", "<=", ">=", "<", ">"]
        for possible_operator in possibile_starting_operators:
            if value.startswith(possible_operator):
                operator = possible_operator
                value = value[len(possible_operator):]
        value = value.lower()
        if value.endswith("b"):
            value = value[
                    :-1]  # trim the eventual ending B, the size will end in MB, KB or M, K
        multiplier = 1
        if value.endswith("m"):
            multiplier = 1024 * 1024
            value = value[:-1]
        elif value.endswith("k"):
            multiplier = 1024
            value = value[:-1]
        value = int(value) * multiplier
        return operator, value
    elif key == "matches":
        return value.lower()
    elif key == "overwrite":
        value = value.lower()
        assert value in ("rename", "skip", "overwrite")
        return value
    else:
        return value


class Rule(object):
    """ This object define a sort rule
        It will define a matching rule, or an a type (that is a sort of named rule).
        The rules are composed in order by:
            default rule settings
            the sum of the rule types it inherit
            the definition of the instance

        A rule match if all it's subrules are matching (AND matching)
        a subrule matches if any of its eventual item match (OR matching)...
        Example:
            {size:">500M", extensions:["avi", "mov"]}
            matches if (file size > 500 MB) AND (file extension is AVI or MOV)
    """

    ACTION_MOVE = "MOVE"  # move the file to a position
    ACTION_DELETE = "DELETE"  # delete the file, use with caution
    ACTION_SKIP = "SKIP"  # don't do nothing, just keep the file there

    # some fictional action, they don't do nothing, but can be used for not-rule-action
    ACTION_DOWNLOAD = "DOWNLOAD"
    ACTION_UNKNOWN = "UNKNOWN"
    ACTION_UNSURE = "UNSURE"
    ACTION_KODI_REFRESH = "Kodi Update"

    # define the possible fields - those are also inherited from types
    fields = ['extensions', 'size', 'priority', 'seasonSplit', 'action',
              'actionName', 'className', 'to', 'matches', 'name',
              'overwrite', 'folderSplit', "downloadSubtitles",
              "foundType", "addTitle", 'updateKodi',
              ]

    # those fields are allowed, but are not inherited
    ignored_fields = [
        'types',
    ]

    def __getitem__(self, key):
        return getattr(self, key)

    def __init__(self, rule_def=None, name=None, config=None):
        if config is None:
            previous_rules = {}
        else:
            previous_rules = config.get('types', {})
        if rule_def is None:
            rule_def = {}

        # defaults
        self.extensions = []
        self.size = None
        self.priority = 50
        self.seasonSplit = False
        self.folderSplit = False
        self.action = self.ACTION_MOVE
        self.actionName = None  # the optional beautiful action name
        self.className = None  # the CSS class to be used on the report
        self.to = None
        self.matches = []
        self.types = []
        self.name = None
        self.overwrite = "skip"
        self.updateKodi = True
        self.downloadSubtitles = None
        self.foundType = None  # can be "movie" or "serie"
        self.addTitle = False

        self.config = config

        # add the singular forms, that are sometime more practical
        for singular_form, plural_form in (('match', 'matches'),
                                           ('type', 'types'),
                                           ("extension", "extensions")):
            if singular_form in rule_def:
                plurals = rule_def.get(plural_form, [])
                plurals.append(rule_def[singular_form])
                rule_def[plural_form] = plurals
                del rule_def[singular_form]

        # get from parent rules (types)
        for parent_rule_name in rule_def.get('types', []):
            parent_rule_name = normalize_field('name', parent_rule_name)
            if parent_rule_name not in previous_rules:
                raise Exception("Unknown rule type %s" % parent_rule_name)
            parent_rule = previous_rules[parent_rule_name]
            self.add_rule(parent_rule)
            self.types.append(parent_rule_name)

        # append from the definitions
        for field in rule_def:
            if field not in self.fields and field not in self.ignored_fields:
                raise Exception("Unknown field specified: %s" % field)
        for key in self.fields:
            if key in rule_def:
                value = rule_def[key]
                self.add_field(key, value)

        if self.action == "delete":
            self.action = self.ACTION_DELETE
        elif self.action == "move":
            self.action = self.ACTION_MOVE
        elif self.action == "skip":
            self.action = self.ACTION_SKIP

        assert self.action in (
            self.ACTION_MOVE, self.ACTION_DELETE, self.ACTION_SKIP
        ), "Unknown action %s" % self.action
        self.add_field('name', name)

    def __repr__(self):
        definition = []
        for key in self.fields:
            if key == "name":
                continue
            value = getattr(self, key)
            definition.append("%s:%s" % (key, value))
        return "Rule{name}: {definition}".format(
            name=" " + self.name if self.name else "",
            definition=", ".join(definition) if definition else "-"
        )

    def add_rule(self, parent_rule):
        """
        Add to current rules. Actually it means: all list fields are appended, the others are overwritten
        """
        for key in self.fields:
            parent_value = getattr(parent_rule, key)
            self.add_field(key, parent_value)

    def add_field(self, key, value, normalized=False):
        """ add the value to the key field, if not normalized the value will be normalized """
        current_value = getattr(self, key)

        if isinstance(current_value, list):
            for item in value:
                if not normalized:
                    item = normalize_field(key, item)
                if item not in current_value:
                    current_value.append(item)
        else:
            if not normalized:
                value = normalize_field(key, value)
            setattr(self, key, value)

    def match(self, candidate):
        # candidate is a dictionary with property of a candidate file:
        # for sure there are: filepath (relative path), and fullpath (absolute)
        confidence = self.priority
        if self.extensions:
            if "extension" not in candidate:
                extension = os.path.splitext(candidate['filepath'])[1]
                if extension:
                    extension = extension[
                                1:].lower()  # get the extension lowercased without the initial dot
                candidate["extension"] = extension
            if not candidate['extension'] in self.extensions:
                # logger.debug("Rejected rule %s for extension" % self)
                return False
        if self.matches:
            confidence = try_match_strings(candidate=candidate,
                                           matches=self.matches,
                                           max_priority=self.priority)
            if confidence is False:  # no string match, stop here
                return False
        if self.size is not None:
            if "size" not in candidate:
                candidate['size'] = os.path.getsize(
                    candidate['fullpath'].encode('utf-8')
                )
            size = candidate["size"]
            operator, threshold = self.size  # size is a tuple with operator (=, <, >) and size in bytes
            operator_function = OPERATORS_MAP[operator]
            if not operator_function(size, threshold):
                # logger.debug("Rejected rule {rule} for size: {size}{operator}{threshold}".format(
                #     rule=self,
                #     size=size,
                #     operator=operator,
                #     threshold=threshold,
                # ))
                return False

        if self.foundType:
            filename = os.path.basename(candidate['filepath'])
            guessed_type = guessit_video_type(filename)
            if self.foundType != guessed_type:
                return False

        return confidence

    def apply(self, candidate, commit=True):
        # print "{action} {filepath} {to}".format(action=self.action, filepath=candidate['filepath'], to=[self.to])
        # the object I will return
        result = ApplyResult(
            rule=self,  # a result vinded to a rule
            action=self.action,
            actionName=self.actionName,
            candidate=candidate,
            filepath=candidate['filepath'],
            sub_downloaded=self.downloadSubtitles,
        )
        if self.action == self.ACTION_DELETE:
            if commit:
                try:
                    os.remove(candidate['fullpath'])
                except OSError as e:
                    logger.error(
                        "Error deleting {filename}. {error}".format(filename=candidate['filepath'],
                                                                    error=e))
        elif self.action == self.ACTION_SKIP:
            pass
        elif self.action == self.ACTION_MOVE:
            assert self.to, "When MOVE you have to specify the destination with the 'to' parameter."
            to = self.to
            if self.addTitle:
                # we add the detected serie title from to the destination
                filename = os.path.basename(candidate['filepath'])
                title = guessit_video_title(filename)
                if title:
                    to = os.path.join(to, title)
            if self.seasonSplit:
                season, episode = get_episode_infos(candidate['filepath'])
                if season:
                    to = os.path.join(to, "S%s" % season)
            if self.folderSplit:
                # put the file in a subfolder with the name of the file (without extension)
                folder_name = os.path.splitext(os.path.basename(candidate['filepath']))[0]
                to = os.path.join(to, folder_name)
            assert self.config and self.config['target'], \
                "Applying needs that rules have a configuration, with its target"

            full_target = os.path.join(self.config['target'], to)
            filename = os.path.basename(candidate['fullpath'])
            if commit:
                if not os.path.exists(full_target):
                    logger.info("Creating folder %s" % full_target)
                    os.makedirs(full_target)  # ensure the target folder is there
                while os.path.isfile(os.path.join(full_target, filename)):
                    logger.warning("File %s already exist on %s" % (filename, to))
                    if self.overwrite == "skip":
                        logger.warning("Skipping this file")
                        result['action'] = self.ACTION_SKIP
                        return result
                    elif self.overwrite == "overwrite":
                        logger.info("Overwriting")
                        break
                    elif self.overwrite == "rename":
                        filename = os.path.basename(candidate['fullpath'])
                        name, ext = os.path.splitext(filename)
                        filename = name + "_%s" % str(random.randint(0, 10000)).zfill(5) + ext
                    else:
                        raise Exception("Invalid overwrite value: %s" % self.overwrite)
                full_target_path = os.path.join(full_target, filename)
                try:
                    shutil.move(candidate['fullpath'], full_target_path)
                except OSError as e:
                    logger.error(
                        "Error moving {filename}. {error}".format(filename=candidate['filepath'],
                                                                  error=e))

            else:
                # no commit so return the name as the file is not on target
                filename = os.path.basename(candidate['fullpath'])
                full_target_path = os.path.join(full_target, filename)
            result['target_fullpath'] = full_target_path
            result['target_filepath'] = full_target_path[len(self.config['target']) + 1:]

            if self.downloadSubtitles:
                filename = os.path.basename(result['target_fullpath'])
                from subliminal import download_best_subtitles, Video
                from babelfish import Language
                print("Scanning subtitles for {filename} in {languages}".format(
                    filename=filename, languages=self.downloadSubtitles
                ))
                video = Video.fromname(result['target_fullpath'])
                languages = {Language(lang_str) for lang_str in self.downloadSubtitles.split(',')}
                # my_region = region.configure('dogpile.cache.memory')
                subtitles = download_best_subtitles({video}, languages)
                if subtitles and commit:
                    print("Saving subtitles")
                    save_subtitles(video, subtitles[video])
                    result["sub_downloaded"] = True
                else:
                    print("No subtitles found")
        return result


# LATER: the size rule, ad example moving films if their size is >500M,
#  should move also the subtitles with same name?

class ApplyResult(AttrDict):
    """ The result of an apply action, is derived from a rule, but can have some more property
        Is also used to pretty print the result in the report

        filepath and action are the minimal infos
    """
    rule = defaultdict(lambda: None)
    action = None
    actionName = None
    filepath = None
    fullpath = None
    target_fullpath = None  # populated in MOVE action (the full path of move target)
    target_filepath = None  # as fullpath, but path is relative to the target folder
    CLASSES = {
        Rule.ACTION_MOVE: "move",
        Rule.ACTION_DELETE: "delete",
        Rule.ACTION_DOWNLOAD: "download",
        Rule.ACTION_UNKNOWN: "unrecognized",
        Rule.ACTION_UNSURE: "unrecognized",
    }

    def __unicode__(self):
        result = "{action}: {filepath}".format(action=self.actionName or self.action,
                                               filepath=self.filepath)
        if self.action == Rule.ACTION_MOVE:
            result += " to: %s" % self.target_filepath
        return result

    @property
    def tokens(self):
        """
            Return token descriptions for the action, all tokens are HTML
        """
        tokens = [self.actionName or self.action]
        dirname, filename = os.path.dirname(self.filepath), os.path.basename(self.filepath)
        if dirname:
            dirname += os.path.sep
        tokens.append("%s<b>%s</b>" % (
            escape(dirname), escape(filename),
        ))
        if self.action == Rule.ACTION_MOVE:
            tokens.append(escape(os.path.dirname(self.target_filepath)))
        return tokens

    @property
    def className(self):
        """
            The className to be used to style this row in pretty report
        """
        if self.rule["className"]:
            return self.rule["className"]
        return self.CLASSES.get(self.action)

    @property
    def important(self):
        # When a rule apply and is important, it deserves to be sent by mail
        return self.action not in {Rule.ACTION_SKIP, Rule.ACTION_KODI_REFRESH}

    def __str__(self):
        return str(self.__unicode__())
