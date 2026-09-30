from pathlib import Path
import unittest

from extract_contrib_package import cli


class WorkflowCliTests(unittest.TestCase):
    def test_normalize_workflow_accepts_regen_aliases(self):
        self.assertEqual(cli.normalize_workflow("extract"), "extract")
        self.assertEqual(cli.normalize_workflow("1"), "extract")
        self.assertEqual(cli.normalize_workflow("regen-pi"), "regen-pi")
        self.assertEqual(cli.normalize_workflow("regen"), "regen-pi")
        self.assertEqual(cli.normalize_workflow("2"), "regen-pi")

    def test_build_regen_command_passes_selected_values(self):
        root = Path(r"D:\project")
        config = Path(r"D:\project\JATS\LWW_CONTRIB_PI_CONFIG.xml")
        harness = Path(r"D:\project\JATS")

        command = cli.build_regen_command(root, "LWW", "MD", config, harness)

        self.assertEqual(command[0], cli.sys.executable)
        self.assertTrue(command[1].endswith("regen_compare_v1.py"))
        self.assertEqual(command[2:4], [str(root), str(config)])
        self.assertIn("--client", command)
        self.assertEqual(command[command.index("--client") + 1], "LWW")
        self.assertEqual(command[command.index("--shortcode") + 1], "MD")
        self.assertEqual(command[command.index("--harness") + 1], str(harness))

    def test_normalize_workflow_rejects_unknown_value(self):
        with self.assertRaises(ValueError):
            cli.normalize_workflow("unknown")


if __name__ == "__main__":
    unittest.main()
