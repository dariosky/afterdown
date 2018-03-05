from __future__ import unicode_literals

import codecs
import json
import logging
import os
import re
from collections import OrderedDict, defaultdict
from copy import deepcopy
from xml.etree import ElementTree

import requests
import six

logger = logging.getLogger("afterdown.rssfeed")
zooqle_title_matcher = re.compile(
    r"^(?P<serie>.*?)\s*?[–]\s*"
    r"(?P<season>\d+)x\s*(?P<episode>\d+):\s*"
    r"(?P<title>.*?)\s*(?P<format>\[.*\])?$"
)
KNOWN_FUTURE_EPISODE = "We know a future episode"
KNOWN_EPISODE = "This episode is known"


class Memory(object):
    def __init__(self):
        self.exact = set()  # list of exact matches
        # series[serie][season] = {episode:x}
        self.series = defaultdict(lambda: defaultdict(dict))

    def add(self, title):
        parsed = zooqle_title_parser(title)
        if parsed['match']:
            serie = parsed['serie']
            season = parsed['season']
            known_season = self.series[serie][season]
            known_episode = known_season.get('episode', -1)
            if parsed['episode'] > known_episode:
                for field in ('serie', 'season', 'match'):
                    parsed.pop(field)  # pop the non-needed fields
                self.series[serie][season] = parsed
        else:
            self.exact.add(title)  # we remember the exact match

    def knows(self, title):
        if title in self.exact:
            return KNOWN_EPISODE + " Exact match"
        parsed = zooqle_title_parser(title)
        if parsed['match']:
            serie = parsed['serie']
            season = parsed['season']
            known_season = self.series[serie][season]
            known_episode = known_season.get('episode', -1)
            if known_episode == parsed['episode']:
                return KNOWN_EPISODE + " last episode"
            if known_episode > parsed['episode']:
                return KNOWN_FUTURE_EPISODE + " S{season}x{episode}".format(
                    season=season, episode=known_episode
                )
        return False

    def __len__(self):
        return len(self.exact) + len(self.series)

    def __str__(self):
        result = "Memory of %d serie" % len(self.series)
        if self.exact:
            result += "and %d exacts" % len(self.exact)

    def load(self, known_filename):
        if not os.path.exists(known_filename):
            return
        with codecs.open(known_filename, 'r', encoding='utf-8') as f:
            obj = json.load(f)
            self.exact = set(obj.pop('_exact', []))
            for known_serie_name, known_serie in obj.items():
                if known_serie is True:
                    self.exact.append(known_serie)  # backward compatibility
                else:
                    self.series[known_serie_name] = defaultdict(dict)
                    for season, known_season in known_serie.items():
                        self.series[known_serie_name][int(season)] = known_season

    def save(self, known_filename):
        obj = deepcopy(self.series)
        if self.exact:
            obj['_exact'] = list(self.exact)
        dump = json.dumps(obj,
                          sort_keys=True, indent=2,
                          separators=(',', ': '))
        with open(known_filename, 'w', encoding='utf-8') as f:
            f.write(dump)


class RssParser:
    def __init__(self):
        self.memory = Memory()

    def add(self, title):
        self.memory.add(title)

    def get_zooqle_feed(self, url=None, xml_filename=None,
                        forget_old_urls=False):
        """ Connect to url to retrieve a rss feed file
            Then download all the items available
            :param url: str
            :param xml_filename: str
            :type forget_old_urls: bool - should we trust Zooqle? something gone should not return
        """
        zooqlens = '{https://zooqle.com/xmlns/0.1/}'

        results = OrderedDict()
        if all([url, xml_filename]) or (url is None and xml_filename is None):
            logger.error("Please specify a url OR a file with the rss")
            return
        if xml_filename:
            with open(xml_filename) as f:
                rss_string = f.read()
        else:
            logger.info("Retrieving RSS feed: %s" % url)
            r = requests.get(url)
            rss_string = r.text
        if not isinstance(rss_string, six.binary_type):
            rss_string = rss_string.encode('utf8')  # xml should be binary
        xml = ElementTree.fromstring(rss_string)
        items = list(xml.iter('item'))[::-1]  # get the feed from the oldest
        logger.debug("%d elements in the RSS feed" % len(items))
        if not items:
            logger.warning("There are no items in the RSS feed")
        else:
            for item in items:
                title = item.find('title').text.strip()
                known = self.memory.knows(title)
                if known:
                    logger.debug("{title} in the RSS is known: {known}".format(
                        title=title, known=known
                    ))
                    continue
                url = item.find(zooqlens + 'magnetURI').text.strip()
                logger.debug('RSS give {title}: {magnet}'.format(title=title,
                                                                 magnet=url))
                # DONE: Zooqle choose the most seeded, we should avoid redownload
                results[title] = url
                self.memory.add(title)
        return results


def rss_zooqle_sync(rss_url, known_filename=None,
                    add_callback=None):
    parser = RssParser()
    parser.memory.load(known_filename)
    urls = parser.get_zooqle_feed(url=rss_url)
    if not urls:
        logger.info("Nothing new in the RSS feed")
    else:
        for title, url in urls.items():
            if url:
                logger.info("Found a new URL from RSS - %s" % title)
                if add_callback:
                    add_callback(title, url)
        parser.memory.save(known_filename)


def zooqle_title_parser(title):
    """ Parse the zooqle title to get episode infos """
    match = zooqle_title_matcher.match(title)
    if match:
        result = match.groupdict()
        for field in ('season', 'episode'):
            result[field] = int(result[field])
        for field in ('serie', 'title', 'format'):
            if result[field]:
                result[field] = result[field].lower()
        result['match'] = True
        return result
    else:
        return dict(
            match=False,
            title=title
        )
