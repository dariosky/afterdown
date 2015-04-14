import collections


def recursive_update(source_dict, updates):
    """ Recursive update dictionary when the update contain dictionaries
        thanks to the almighty Alex Martelli: http://stackoverflow.com/a/3233356/22136
    """
    for k, v in updates.iteritems():
        if isinstance(v, collections.Mapping):
            r = recursive_update(source_dict.get(k, {}), v)
            source_dict[k] = r
        else:
            source_dict[k] = updates[k]
    return source_dict
