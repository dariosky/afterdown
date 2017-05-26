import operator

# possible operators map, to be used with size
OPERATORS_MAP = {"=": operator.eq,
                 ">": operator.gt,
                 "<": operator.lt,
                 "<=": operator.le,
                 ">=": operator.ge,
                 }


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self
