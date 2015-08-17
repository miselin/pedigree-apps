
import os
import mock
import unittest

import environment


class EnvironmentTest(unittest.TestCase):

    def test_nooverride(self):
        d = environment.OverridableDict()
        d['foo'] = 'bar'
        d['foo'] = 'baz'
        self.assertEqual(d['foo'], 'baz')

    def test_override(self):
        d = environment.OverridableDict()

        d['foo'] = 'qux'
        d.track()
        d['foo'] = 'bar'
        d.track(tracking=False)
        d['foo'] = 'baz'

        self.assertEqual(d['foo'], 'bar')
        self.assertTrue(d.has_overrides())


if __name__ == '__main__':
    unittest.main()
