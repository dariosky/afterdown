from __future__ import unicode_literals

import logging
import os
from collections import OrderedDict
from xml.etree import ElementTree
import codecs
import requests
import six

logger = logging.getLogger("afterdown.rssfeed")


class RssParser:
    def __init__(self):
        self.memory = set()

    def load_memory(self, known_filename):
        if not os.path.exists(known_filename):
            return
        with codecs.open(known_filename, 'r', encoding='utf-8') as f:
            self.memory = set(f.read().splitlines())

    def save_memory(self, known_filename):
        with codecs.open(known_filename, 'w', encoding='utf-8') as f:
            for line in self.memory:
                line += '\n'
                f.write(line)

    def get_zoogle_feed(self, url=None, xml_filename=None):
        """ Connect to url to retrieve a rss feed file
            Then download all the items available
        """
        zooglens = '{https://zooqle.com/xmlns/0.1/}'

        results = OrderedDict()
        if all([url, xml_filename]) or (url is None and xml_filename is None):
            logger.error("Please specify a url OR a file with the rss")
            return
        if xml_filename:
            with open(xml_filename) as f:
                rss_string = f.read()
        else:
            logger.info("Retrieving RSS feed")
            r = requests.get(url)
            rss_string = r.text
        if not isinstance(rss_string, six.binary_type):
            rss_string = rss_string.encode('utf8')  # xml should be binary
        xml = ElementTree.fromstring(rss_string)
        items = list(xml.iter('item'))
        logger.debug("Found %d elements" % len(items))
        if not items:
            logger.warning("There are no items in the RSS feed")
        else:
            for item in items:
                title = item.find('title').text.strip()
                if title in self.memory:
                    logger.debug("%s in the RSS is already known")
                    results[title] = None  # I'll put it as known, but without the url
                    continue
                url = item.find(zooglens + 'magnetURI').text.strip()
                logger.debug('RSS give {title}: {magnet}'.format(title=title,
                                                                 magnet=url))
                # DONE: Zoogle choose the most seeded, we should avoid redownload
                results[title] = url
            self.memory = set(results.keys())  # update memory
        return results


def rss_zoogle_sync(rss_url, known_filename=None,
                    add_callback=None):
    parser = RssParser()
    parser.load_memory(known_filename)
    urls = parser.get_zoogle_feed(url=rss_url)
    if not urls:
        logger.info("Nothing new in the RSS feed")
    else:
        for title, url in urls.items():
            if url:
                logger.info("Found a new URL from RSS - %s" % title)
                if add_callback:
                    add_callback(title, url)
        parser.save_memory(known_filename)
