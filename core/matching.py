import logging
import re

logger = logging.getLogger("afterdown.matching")


def full_case_insensitive_match(filename, match_string):
    return match_string.lower() in filename


def remove_special_chars(s):
    return "".join(re.findall(r"[a-zA-Z0-9]", s))


# a list of test to be done in order, keep higher priority first, they are executed in order
def justwords_case_insensitive_match(filename, match_string):
    return remove_special_chars(match_string).lower() in filename


MATCH_TESTS = [
    dict(confidence=100, match_func=full_case_insensitive_match, prepare_filepath=lambda x: x.lower()),
    dict(confidence=80, match_func=justwords_case_insensitive_match,
         prepare_filepath=lambda x: remove_special_chars(x).lower()),
]


def try_match_strings(candidate, matches, max_priority):
    """
        Check the match with various level of confidency, degrading the priority
        an exact contain match gives full priority, a contain ignoring [\s\.-_] gives 20% less confidence...
    """
    for mt in MATCH_TESTS:
        filepath = candidate['filepath']
        if 'prepare_filepath' in mt:
            filepath = mt['prepare_filepath'](filepath)
        for match_string in matches:
            if mt['match_func'](filepath, match_string):
                result = max_priority * mt['confidence'] // 100
                return result
    logger.debug("Rejected rule %s doesn't match." % matches)
    return False
