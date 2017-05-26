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


def js_to_py_re(rx):
    """
    Derived from http://stackoverflow.com/questions/11230743/how-to-parse-a-javascript-regexp-in-python
    """
    nonmatching_function = lambda s: False  # not a js regex form
    if not rx or rx[0] != "/":
        return nonmatching_function
    query, params = rx.rsplit('/', 1)
    if len(query) <= 1:
        return nonmatching_function
    else:
        query = query[1:]
    if 'g' in params:
        obj = re.findall
    else:
        obj = re.search

    # May need to make flags= smarter, but just an example...
    return lambda f: obj(query, f, flags=re.I if 'i' in params else 0)


def regex_match(filename, match_string):
    if match_string and match_string[0] == "/":
        searchfunc = js_to_py_re(match_string)
        return searchfunc(filename)
    else:
        return False


MATCH_TESTS = [
    dict(confidence=100, match_func=regex_match),
    dict(confidence=100, match_func=full_case_insensitive_match,
         prepare_filepath=lambda x: x.lower()),
    dict(confidence=80, match_func=justwords_case_insensitive_match,
         prepare_filepath=lambda x: remove_special_chars(x).lower()),
]


def try_match_strings(candidate, matches, max_priority):
    """
        Check the match with various level of confidency, degrading the priority
        an exact contain match gives full priority, a contain ignoring [\s\.-_] gives 20% less confidence...
    """
    result = 0
    for match_string in matches:
        string_confidence = 0
        match = False
        for mt in MATCH_TESTS:
            filepath = candidate['filepath']
            if 'prepare_filepath' in mt:
                filepath = mt['prepare_filepath'](filepath)
            if mt['match_func'](filepath, match_string):
                match = True
                string_confidence = max(string_confidence, max_priority * mt['confidence'] // 100)
        # logger.debug("Rejected rule %s doesn't match." % matches)
        if not match:
            return False
        else:
            result = max(result, string_confidence)
    return result
