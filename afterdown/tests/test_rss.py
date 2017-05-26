import os

from afterdown.core.rss import RssParser


def test_get_zoogle_feed():
    """ Do some test with an example Zooqle rss feed """
    parser = RssParser()
    urls = parser.get_zoogle_feed(
        xml_filename=os.path.join(os.path.dirname(__file__), 'rss.xml'),
    )
    assert len(urls) == 1, 'We have one item in the test RSS'
    assert all(urls.values()), 'We didn\'t knew any of those'
    # add_magnet_url(url) # TMP: temporary disabled


def test_memory_feed():
    parser = RssParser()
    parser.memory.add(
        'The Big Bang Theory – 10x22: The Cognition Regeneration [Std]'
    )
    # we get the same urls as before, but this time we know one
    urls = parser.get_zoogle_feed(
        xml_filename=os.path.join(os.path.dirname(__file__), 'rss.xml'),
    )
    assert len(urls) == 1, 'We have one item in the test RSS'
    for url in urls.values():
        assert url is None, 'Everything should be known'
