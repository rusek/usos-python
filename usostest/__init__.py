import unittest

from . import user


def load_tests(loader, tests, pattern):
    mods = [user]

    return unittest.TestSuite(map(loader.loadTestsFromModule, mods))
