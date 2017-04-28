from collections import defaultdict

PRETTY_NAMES = {
    "_tot": "We had {value} files",
    "_unknown_old": "{value} unknown already met",
    "_unsure_old": "{value} unsure already met",
    "_unknown_new": "{value} new unknown",
    "_unsure_new": "{value} new unsure",
}


class CounterSummary(object):
    """ A class with counter for the various action, that returns a pretty summary line

        The counters key are named with a starting underscore
         when they are special to keep them first
     """

    def __init__(self):
        self.action_counters = defaultdict(int)
        self.special_counters = defaultdict(int)
        self.special_key_order = []

    def __getitem__(self, key):
        if key.startswith("_"):
            return self.special_counters[key]
        else:
            return self.action_counters[key]

    def __setitem__(self, key, value):
        if key.startswith("_"):
            self.special_counters[key] = value
            if key not in self.special_key_order:
                self.special_key_order.append(key)
        else:
            self.action_counters[key] = value

    def __str__(self):
        summary_tokens = []
        for key in self.special_key_order:
            if key in PRETTY_NAMES:
                summary_tokens.append(
                    PRETTY_NAMES[key].format(value=self.special_counters[key], name=key))
            else:
                summary_tokens.append(
                    "{value} {name}".format(value=self.special_counters[key], name=key))
        for key in sorted(self.action_counters):
            summary_tokens.append(
                "{value} {name}".format(value=self.action_counters[key], name=key))
        summary = ". ".join(
            filter(lambda x: x, summary_tokens)) or "Nothing new"  # strip empty tokens
        return summary
