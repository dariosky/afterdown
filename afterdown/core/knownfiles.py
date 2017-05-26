import logging
import os

logger = logging.getLogger("afterdown.knownfiles")


class KnownFiles(object):
    """ A persistent storage to keep a list of already met files that didn't match
        Asking if a file is known make it being known.
        All not asked files are forgotten at the end.
    """

    def __init__(self, filepath):
        self.filepath = filepath
        self.data = set()
        self.newdata = set()  # all the data added
        logger.debug("Loading %s" % self.filepath)
        if os.path.isfile(filepath):
            with open(self.filepath, 'r') as f:
                self.data = set(map(str.strip, f.readlines()))
                logger.debug("%d known files" % len(self.data))

    def save(self):
        if self.newdata != self.data:
            logger.debug("Saving to %s" % self.filepath)
            with open(self.filepath, 'w') as f:
                f.write("\n".join(sorted(self.newdata)))

    def is_known(self, filename):
        self.newdata.add(filename)
        return filename in self.data
