import pytest

from afterdown.core.rules import Rule

if __name__ == '__main__':
    pytest.main()


def test_default_rule():
    rule = Rule()
    assert rule
    assert rule.priority == 50


def test_singular_forms():
    config = {'types': {"video": Rule({"extension": "avi", "match": "parent-filter"})}}
    child_rule = Rule({'type': "video", "match": "child-filter"}, config=config)
    assert "video" in child_rule.types, "Singular forms doesn't work for types."
    # test inheritance
    assert "avi" in child_rule.extensions
    assert "parent-filter" in child_rule.matches
    assert "child-filter" in child_rule.matches


def test_duplicate_removal():
    config = {'types': {"video": Rule({"extensions": ["foo", "bar"], })}}
    child_rule = Rule({'type': "video", "extensions": ["FOO"]}, config=config)
    assert len(child_rule.extensions) == 2, "Seems extensions duplicates are not removed"


def test_sizes():
    rule = Rule({"size": "10"})
    assert rule.size == ("=", 10)
    rule = Rule({"size": ">100"})
    assert rule.size == (">", 100)
    rule = Rule({"size": "<=1000"})
    assert rule.size == ("<=", 1000)
    rule = Rule({"size": "=1kB"})
    assert rule.size == ("=", 1024)
    rule = Rule({"size": ">=1M"})
    assert rule.size == (">=", 1024 * 1024)
