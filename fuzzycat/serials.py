# coding: utf-8
"""
Serial name matching. Includes names from issn database.
"""

import os
import shelve

__all__ = ["serialsdb"]


class SerialsDatabase:
    """
    Lookup allows to lookup serial names, using a database of real serial names.

        >>> from serials import serialsdb
        >>> serialsdb.get("Philosophica")
        {'1857-9272', '2232-299X', '2232-3007', '2232-3015'}

    """
    def __init__(self, path=None):
        """
        Note that shelve appends "db" to the name automatically. TODO: make this
        auto-download into a cache directory.
        """
        if path is None:
            path = os.path.join(os.path.expanduser("~"), ".cache/fuzzycat/names")
        self.db = shelve.open(path, flag='r')

    def __getitem__(self, v):
        return self.db[v]

    def get(self, v, default=None, cleanup_pipeline=None):
        if not cleanup_pipeline:
            return self.db.get(v, default=default)
        return self.db.get(cleanup_pipeline(v), default=default)

    def close(self):
        self.db.close()


# A singleton.
serialsdb = SerialsDatabase()
