
import mock
import unittest

from . import steps


class StepsTest(unittest.TestCase):

    def setUp(self):
        self.cmd = mock.MagicMock()
        steps.cmd = self.cmd

    def test_get_builddir(self):
        with mock.patch('support.steps.os.makedirs') as os_makedirs:
            self.assertEqual(steps.get_builddir('s', {}, True), 's')
            self.assertEqual(steps.get_builddir('s', {}, False), 's/pedigree-build')
            os_makedirs.assert_called_once_with('s/pedigree-build')

    def test_libtoolize(self):
        steps.libtoolize('.', {})
        steps.cmd.assert_called_with(['/applications/libtoolize', '-i', '-f', '--ltdl'], cwd='.', env={})
        steps.libtoolize('.', {}, ltdl_dir='foo')
        steps.cmd.assert_called_with(['/applications/libtoolize', '-i', '-f', '--ltdl=foo'], cwd='.', env={})

    def test_autoreconf(self):
        env = {'AUTORECONF': 'a'}
        steps.autoreconf('.', env)
        steps.cmd.assert_called_with(['a', '-ifs'], cwd='.', env=env)
        steps.autoreconf('.', env, extra_flags=('foo',))
        steps.cmd.assert_called_with(['a', '-ifs', 'foo'], cwd='.', env=env)


if __name__ == '__main__':
    unittest.main()
