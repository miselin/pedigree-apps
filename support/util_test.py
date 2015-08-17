
import os
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from . import util


class UtilTest(unittest.TestCase):

    def test_expand_nothing(self):
        test = util.expand({}, 'foo')
        self.assertEqual(test, 'foo')

    def test_failed_expand(self):
        test = util.expand({}, '$foo')
        self.assertEqual(test, '$foo')

    def test_working_expand(self):
        test = util.expand({'foo': 'bar'}, '$foo')
        self.assertEqual(test, 'bar')

    def test_environ(self):
        os.environ['__FOO__'] = 'bar'
        test = util.expand({}, '$__FOO__')
        self.assertEqual(test, 'bar')


if __name__ == '__main__':
    unittest.main()
