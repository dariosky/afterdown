class Rule(object):
    """ This object define a sort rule
        It will define a matching rule, or an a type (that is a sort of named rule).
        The rules are composed in order by:
            default rule settings
            the sum of the rule types it inherit
            the definition of the instance
    """

    ACTION_MOVE = "MOVE"  # move the file to a position
    ACTION_DELETE = "DELETE"  # delete the file, use with caution

    # define the possible fields
    fields = ['extensions', 'size', 'priority', 'season_split', 'action', 'to', 'matches', 'name']

    def __init__(self, rule_def=None, name=None, previous_rules=None):
        if not previous_rules:
            previous_rules = {}
        if rule_def is None:
            rule_def = {}

        # defaults
        self.extensions = []
        self.size = []
        self.priority = 50
        self.season_split = False
        self.action = self.ACTION_MOVE
        self.to = None
        self.matches = []
        self.types = []
        self.name = None

        # add the singular forms, that are sometime more practical
        for singular_form, plural_form in (('match', 'matches'),
                                           ('type', 'types'),
                                           ("extension", "extensions")):
            if singular_form in rule_def:
                plurals = rule_def.get(plural_form, [])
                plurals.append(rule_def[singular_form])
                rule_def[plural_form] = plurals
                del rule_def[singular_form]

        # get from parent rules (types)
        for parent_rule_name in rule_def.get('types', []):
            parent_rule_name = self.normalize_field('name', parent_rule_name)
            if parent_rule_name not in previous_rules:
                raise Exception("Unknown rule type %s" % parent_rule_name)
            parent_rule = previous_rules[parent_rule_name]
            self.add_rule(parent_rule)
            self.types.append(parent_rule_name)

        # append from the definitions
        for key in self.fields:
            if key in rule_def:
                value = rule_def[key]
                self.add_field(key, value)

        if self.action == "delete":
            self.action = self.ACTION_DELETE
        if self.action == "move":
            self.action = self.ACTION_MOVE
        assert self.action in (self.ACTION_MOVE, self.ACTION_DELETE), "Unknown action %s" % self.action
        self.add_field('name', name)

    def __repr__(self):
        definition = []
        for key in self.fields:
            if key == "name":
                continue
            value = getattr(self, key)
            definition.append("%s:%s" % (key, value))
        return "Rule{name}: {definition}".format(
            name=" " + self.name if self.name else "",
            definition=", ".join(definition) if definition else "-"
        )

    def __unicode__(self):
        return unicode(self.__str__())

    def add_rule(self, parent_rule):
        """
        Add to current rules. Actually it means: all list fields are appended, the others are overwritten
        """
        for key in self.fields:
            parent_value = getattr(parent_rule, key)
            self.add_field(key, parent_value)

    def add_field(self, key, value, normalized=False):
        """ add the value to the key field, if not normalized the value will be normalized """
        current_value = getattr(self, key)

        if isinstance(current_value, list):
            for item in value:
                if not normalized:
                    item = self.normalize_field(key, item)
                if item not in current_value:
                    current_value.append(item)
        else:
            if not normalized:
                value = self.normalize_field(key, value)
            setattr(self, key, value)

    def normalize_field(self, key, value):
        if key == "name":
            return value.lower() if value else None
        elif key == "extensions":
            return value.lower() if value else None
        else:
            return value
