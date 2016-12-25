import collections

from guessit import guessit


def recursive_update(source_dict, updates):
    """ Recursive update dictionary when the update contain dictionaries
        thanks to the almighty Alex Martelli: http://stackoverflow.com/a/3233356/22136
    """
    for k, v in updates.items():
        if isinstance(v, collections.Mapping):
            r = recursive_update(source_dict.get(k, {}), v)
            source_dict[k] = r
        else:
            source_dict[k] = updates[k]
    return source_dict


def guessit_video_type(filename):
    """ This will return movie or serie given a filename
        All the hard work is done by the guessit library,
        we wrap it just to smooth some corner case
     """
    g = guessit(filename)
    if g.get('type') == 'episode':
        return 'serie'
    if 'part' in g:
        return "serie"
    return g.get('type') or "unknown"


def guessit_video_title(filename):
    """ Get the movie/serie title, from guessit, case normalized """
    g = guessit(filename)
    return g.get('title', '').title()


class CircularDependencyException(Exception):
    pass


def dependency_resolver(objects, get_dependencies_func, process_func):
    """ Call the process_func on all objects, being sure that dependencies
        are preserved. Check if an object depends on another, via get_dependencies_func
    """
    processed = []
    to_be_processed = [x for x in objects]  # create a list to the original objects
    dead_for = 0

    while to_be_processed:
        n = to_be_processed.pop()
        doable = True
        for d in get_dependencies_func(n):
            if d not in processed:
                doable = False

        if doable:
            process_func(n)
            processed.append(n)
            dead_for = 0
        else:
            to_be_processed.insert(0, n)  # add the element back in the list
            dead_for += 1  # we are waiting for dependencies to be solved

        if dead_for > len(to_be_processed):
            raise CircularDependencyException(
                "Circular reference found, cannot process %s" % to_be_processed)
