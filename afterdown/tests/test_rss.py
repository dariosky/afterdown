import os

from afterdown.core.rss import RssParser, zooqle_title_parser, KNOWN_FUTURE_EPISODE


def test_get_zooqle_feed():
    """ Do some test with an example Zooqle rss feed """
    parser = RssParser()
    urls = parser.get_zooqle_feed(
        xml_filename=os.path.join(os.path.dirname(__file__), 'rss.xml'),
    )
    assert len(urls) == 1, 'We have one item in the test RSS'
    assert all(urls.values()), 'We didn\'t knew any of those'
    # add_magnet_url(url) # TMP: temporary disabled


def test_memory_feed():
    parser = RssParser()
    parser.add(
        'The Big Bang Theory – 10x22: The Cognition Regeneration [Std]'
    )
    # we get the same urls as before, but this time we know one
    urls = parser.get_zooqle_feed(
        xml_filename=os.path.join(os.path.dirname(__file__), 'rss.xml'),
    )
    assert len(urls) == 1, 'We have one item in the test RSS'
    for url in urls.values():
        assert url is None, 'Everything should be known'


def test_season_memory_feed():
    parser = RssParser()
    # we add episode 10x23
    parser.add(
        'The Big Bang Theory – 10x23: The Cognition Regeneration [Std]'
    )
    # we get a previous url, but a future one is known
    urls = parser.get_zooqle_feed(
        xml_filename=os.path.join(os.path.dirname(__file__), 'rss.xml'),
    )
    for url in urls.values():
        assert url is None, 'Everything should be known'

    assert len(parser.memory) == 1

    assert parser.memory.knows(
        'The Big Bang Theory – 10x1: XYZ'
    ).startswith(KNOWN_FUTURE_EPISODE)
    assert parser.memory.knows(
        'The Big Bang Theory – 11x1: XYZ'
    ) is False, "Another season is not known"
    assert parser.memory.knows(
        'The Big Bang Theory – 09x1: XYZ'
    ) is False, "Another season is not known"

    parser.add(
        'The Big Bang Theory – 09x1: Nine'
    )

    assert parser.memory.knows(
        'The Big Bang Theory – 09x2: XYZ'
    ) is False, "Another season is not known"


class TestZooqleMatcher(object):
    @staticmethod
    def compare(title, expectation):
        match = zooqle_title_parser(title)
        for k, v in expectation.items():
            assert match[k] == v, "Field %s mismatch" % k

    def test_big(self):
        self.compare(
            title="The Big Bang Theory – 10x22: The Cognition Regeneration [Std]",
            expectation=dict(
                serie='the big bang theory',
                season=10,
                episode=22,
                title='the cognition regeneration',
                match=True
            ))

    def test_mismatch(self):
        self.compare(
            title="This is something nonmatching",
            expectation=dict(
                title="This is something nonmatching",
                match=False,
            ))
