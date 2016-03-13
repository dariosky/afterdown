from core.matching import try_match_strings, remove_special_chars


def test_remove_special_chars():
    assert remove_special_chars("@c.i_a__o78!!!") == "ciao78"


def test_match_exact_string():
    assert try_match_strings(
        candidate=dict(filepath="I have a Big bang THEORY in a video.avi"),
        matches=['big bang Theory'],
        max_priority=100,
    ) == 100


def test_match_in_rule_as_and():
    assert try_match_strings(
        candidate=dict(filepath="Big Bang Theory"),
        matches=['big bang Theory'],
        max_priority=100,
    ) == 100
    assert try_match_strings(
        candidate=dict(filepath="Big Bang Theory ITA"),
        matches=['ita'],
        max_priority=100,
    ) == 100
    assert try_match_strings(
        candidate=dict(filepath="Big Bang Theory ITA"),
        matches=['Big bang theory', 'ita'],
        max_priority=100,
    ) == 100
    assert try_match_strings(
        candidate=dict(filepath="Big Bang Theory"),
        matches=['Big bang theory', 'ita'],
        max_priority=100,
    ) == 0


def test_match_spaced_string():
    assert try_match_strings(
        candidate=dict(filepath="I have a Bigbang-THEORY.in.a.video.avi"),
        matches=['big bang theory'],
        max_priority=100,
    ) == 80


def test_match_regex():
    score = try_match_strings(
        candidate=dict(filepath="44 cats in row by 3 with the remainder of 2.avi"),
        matches=['/\d+\ cats[\w ]+\.avi/'], max_priority=100,
    )
    assert score == 100
