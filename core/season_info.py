import os
import re

RE_GET_SEASON_N_EPISODE = re.compile(r'S(\d+)E(\d+)', re.IGNORECASE | re.VERBOSE)  # SxxExx is clear
RE_INITIAL_EPISODE = re.compile(r'^(\d+)\W', re.IGNORECASE | re.VERBOSE)  # 12- is clear
RE_THREE_NUMBERS = re.compile(r'(\d)(?:[E]|)(\d{2,})', re.IGNORECASE | re.VERBOSE)  # xExx or Xxx


def get_episode_infos(filepath):
    filename = os.path.basename(filepath)
    for regex in [
        RE_GET_SEASON_N_EPISODE,
        RE_INITIAL_EPISODE,
        RE_THREE_NUMBERS,
    ]:
        # test for a list of regex in order to search for a match
        match = re.search(regex, filename)
        if match:
            if len(match.groups()) == 2:
                results = match.group(1), match.group(2)
            else:
                results = (None, match.group(1))  # just the episode name
            return tuple(map(lambda x: x and x.zfill(2) or x, results))
    return (None, None)

if __name__ == '__main__':
    print get_episode_infos('01 - The episode name.mp4')
