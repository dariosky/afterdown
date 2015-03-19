from core.match_string import try_match_strings, remove_special_chars


def test_remove_special_chars():
    assert remove_special_chars("@c.i_a__o78!!!") == "ciao78"


def test_match_exact_string():
    assert try_match_strings(
        candidate=dict(filepath="I have a Big bang THEORY in a video.avi"),
        matches=['big bang Theory'],
        max_priority=100,
    ) == 100


def test_match_spaced_string():
    assert try_match_strings(
        candidate=dict(filepath="I have a Bigbang-THEORY.in.a.video.avi"),
        matches=['big bang theory'],
        max_priority=100,
    ) == 80
