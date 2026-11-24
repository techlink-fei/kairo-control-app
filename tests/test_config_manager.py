import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.models.config import Config, LastRecordingConfig, SingleArmConfig
from backend.services.config_manager import ConfigManager


class ConfigManagerTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "config.json"
        self.manager = ConfigManager(self.path)

    def test_saves_and_loads_unicode_configuration(self):
        config = Config(
            mode="single",
            single_arm=SingleArmConfig(follower_port="can0"),
            last_recording=LastRecordingConfig(task="把积木放到盒子里"),
        )
        self.manager.save_config(config)
        self.assertIn(config.last_recording.task, self.path.read_text(encoding="utf-8"))
        self.assertEqual(self.manager.load_config(), config)

    def test_loads_legacy_partial_config_with_escaped_text(self):
        self.path.write_text(
            json.dumps({"last_recording": {"task": "拾取积木"}}), encoding="utf-8"
        )
        self.assertEqual(self.manager.load_config().last_recording.task, "拾取积木")

    def test_invalid_document_returns_defaults(self):
        for contents in (b"{", b"[]", b"null", b'{"last_recording": 123}', b"\xff"):
            with self.subTest(contents=contents):
                self.path.write_bytes(contents)
                self.assertEqual(self.manager.load_config(), Config())

    def test_interrupted_serialization_keeps_previous_configuration(self):
        previous = Config(mode="single")
        self.manager.save_config(previous)
        before = self.path.read_bytes()

        def interrupted_dump(data, stream, **kwargs):
            stream.write('{"mode":')
            raise OSError("simulated write failure")

        with patch("backend.services.config_manager.json.dump", interrupted_dump):
            with self.assertRaisesRegex(OSError, "simulated"):
                self.manager.save_config(Config())

        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.manager.load_config(), previous)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_reset_is_idempotent(self):
        self.manager.save_config(Config(mode="single"))
        self.assertEqual(self.manager.reset_config(), Config())
        self.assertEqual(self.manager.reset_config(), Config())
        self.assertFalse(self.manager.config_exists())
