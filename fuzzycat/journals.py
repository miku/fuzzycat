# coding: utf-8

"""
Journal name matching. Includes names from issn database and abbreviations.
"""

import shelve

class JournalLookup:
    """
    Lookup allows to lookup journals, using a database of real journal names.

        >>> lookup = JournalLookup()
        >>> lookup["Philosophica"]
        {'1857-9272', '2232-299X', '2232-3007', '2232-3015'}

    """
    def __init__(self, namedb='namedb'):
        self.db = shelve.open(namedb)

    def __getitem__(self, v):
        return self.db[v]

    def get(self, v, cleanup_pipeline=None):
        if not cleanup_pipeline:
            return self.db[v]
        return self.db[cleanup_pipeline(v)]

    def close(self):
        self.db.close()
