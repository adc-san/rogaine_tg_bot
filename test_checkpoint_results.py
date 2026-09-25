from contextlib import closing
import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


class CheckpointResultsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = types.SimpleNamespace(
            db_filename=str(Path(self.temp.name) / 'results.db'))
        spec = importlib.util.spec_from_file_location(
            'checkpoint_utils', Path(__file__).with_name('bot_utils.py'))
        self.utils = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {
            'config': self.config,
            'telebot': types.SimpleNamespace(types=types.SimpleNamespace()),
            'bot_messages': types.SimpleNamespace(some_error='database error'),
        }):
            spec.loader.exec_module(self.utils)
        self.utils.create_tables()

    def result(self, visits):
        with closing(sqlite3.connect(self.config.db_filename)) as conn:
            conn.executemany('INSERT INTO game (id, cp, ch) VALUES (1, ?, ?)', visits)
            conn.commit()
        return self.utils.user_result(1)

    def test_missing_90_does_not_mark_visited_finish_0(self):
        self.assertEqual(
            self.result([(90, 0), (0, 1)]),
            (1, 0, '0', '90', '_90_,0'))

    def test_two_digit_checkpoint_is_not_part_of_three_digit_checkpoint(self):
        self.assertEqual(
            self.result([(101, 0), (10, 1), (45, 1)]),
            (2, 5, '10,45', '101', '_101_,10,45'))

    def test_only_exact_missing_checkpoints_are_marked_in_visit_order(self):
        self.assertEqual(
            self.result([(23, 1), (12, 0), (34, 0)]),
            (1, 2, '23', '12,34', '23,_12_,_34_'))

    def test_empty_result(self):
        self.assertEqual(self.result([]), (0, 0, '', '', ''))


if __name__ == '__main__':
    unittest.main()
