
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

    def test_fhs_environment(self):
        env = environment.generate_environment("amd64", recurse=False)
        self.assertEqual(env["CROSS_TARGET"], "x86_64-pedigree")
        self.assertEqual(env["CROSS_BASE"], "/opt/pedigree")
        self.assertEqual(
            env["CROSS_LD"],
            "/opt/pedigree/bin/x86_64-pedigree-ld",
        )
        self.assertEqual(env["TARGET_CONFIG_SITE"], "/workspace/config.site")
        self.assertNotIn("CONFIG_SITE", env)
        self.assertTrue(env["OUTPUT_BASE"].endswith("/newpacks/x86_64"))
        self.assertTrue(env["CCACHE_DIR"].endswith("/.build/x86_64/ccache"))


if __name__ == '__main__':
    unittest.main()
