import codecs
import csv
from html import escape
import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='.export-tests-', dir=ROOT)
        self.directory = Path(self.temporary.name).resolve()
        self.assertEqual(self.directory.parent, ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.config = types.ModuleType('config')
        self.config.db_filename = str(self.directory / 'test.db')
        self.config.results_filename = str(self.directory / 'results.csv')
        self.config.secret_dict = {1: 'test', 12: 'one', 23: 'two'}
        self.config.test_cp = 1
        telebot = types.ModuleType('telebot')
        telebot.types = types.SimpleNamespace()
        with mock.patch.dict(sys.modules, {'config': self.config, 'telebot': telebot}):
            self.bot_utils = load_module('test_bot_utils', 'bot_utils.py')
            with mock.patch.dict(sys.modules, {'bot_utils': self.bot_utils}):
                self.export = load_module('test_export_results', 'export_results.py')
        self.bot_utils.create_tables()
        self.output = Path(self.config.results_filename)

    def add_user(self, user_id=7, team='Team', first='First', last='Last'):
        conn = sqlite3.connect(self.config.db_filename)
        try:
            conn.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)',
                         (user_id, 'some_name', escape(first), escape(last),
                          escape(team), '2026/09/25 - 12:00:00'))
            conn.executemany('INSERT INTO game (id, cp, ch) VALUES (?, ?, ?)',
                             [(user_id, 12, 1), (user_id, 23, 0)])
            conn.commit()
        finally:
            conn.close()

    def assert_no_temporary_files(self):
        self.assertEqual(list(self.directory.glob('results.csv.*.tmp')), [])

    def assert_previous_preserved(self):
        self.assertEqual(self.output.read_bytes(), b'previous complete export\n')
        self.assert_no_temporary_files()

    def test_unicode_csv_round_trip_and_original_html_text(self):
        team = '🏃 Команда, "Ёж" | A & <B> 東京 &amp;'
        first = 'José, "Я" | 🧭'
        last = '東京 & Пётр'
        self.add_user(team=team, first=first, last=last)
        self.output.write_bytes(b'old result')
        self.export.save_to_csv()
        self.assertTrue(self.output.read_bytes().startswith(codecs.BOM_UTF8))
        with self.output.open(encoding='utf-8-sig', newline='') as source:
            rows = list(csv.reader(source))
        self.assertEqual(rows, [
            ['Name', 'User', 'Problems', 'Fin time', 'CP', 'CP'],
            [team, f'{first} {last} @some_name id7', '23',
             '2026/09/25 - 12:00:00', '12', '_23_'],
        ])
        self.assert_no_temporary_files()

    def test_empty_database_keeps_existing_empty_export_contract(self):
        self.output.write_bytes(b'old result')
        self.export.save_to_csv()
        self.assertEqual(self.output.read_bytes(), b'')
        self.assert_no_temporary_files()

    def test_connection_failure_preserves_previous_export(self):
        self.output.write_bytes(b'previous complete export\n')
        with mock.patch.object(self.export.sqlite3, 'connect',
                               side_effect=sqlite3.OperationalError('cannot open database')):
            with self.assertRaises(sqlite3.OperationalError):
                self.export.save_to_csv()
        self.assert_previous_preserved()

    def test_query_failure_closes_connection_and_preserves_previous_export(self):
        self.output.write_bytes(b'previous complete export\n')
        connection = mock.Mock()
        connection.cursor.return_value.execute.side_effect = sqlite3.OperationalError('no users table')
        with mock.patch.object(self.export.sqlite3, 'connect', return_value=connection):
            with self.assertRaises(sqlite3.OperationalError):
                self.export.save_to_csv()
        connection.close.assert_called_once_with()
        self.assert_previous_preserved()

    def test_failure_after_first_row_preserves_previous_export(self):
        self.add_user(7)
        self.add_user(8)
        self.output.write_bytes(b'previous complete export\n')
        first_result = self.bot_utils.user_result(7)
        with mock.patch.object(self.bot_utils, 'user_result',
                               side_effect=[first_result, sqlite3.OperationalError('read failed')]):
            with self.assertRaises(sqlite3.OperationalError):
                self.export.save_to_csv()
        self.assert_previous_preserved()

    def test_write_failure_preserves_previous_export(self):
        self.add_user()
        self.output.write_bytes(b'previous complete export\n')
        with mock.patch.object(self.export.csv, 'writer') as writer:
            writer.return_value.writerow.side_effect = OSError('disk full')
            with self.assertRaises(OSError):
                self.export.save_to_csv()
        self.assert_previous_preserved()

    def test_replace_failure_preserves_previous_export_and_removes_temp_file(self):
        self.add_user()
        self.output.write_bytes(b'previous complete export\n')

        def failed_replace(source, destination):
            self.assertEqual(Path(source).parent, self.output.parent)
            self.assertEqual(Path(destination), self.output)
            self.assertTrue(Path(source).read_bytes().startswith(codecs.BOM_UTF8))
            raise PermissionError('destination in use')

        with mock.patch.object(self.export.os, 'replace', side_effect=failed_replace):
            with self.assertRaises(PermissionError):
                self.export.save_to_csv()
        self.assert_previous_preserved()

    def test_failed_first_export_leaves_no_partial_output(self):
        self.add_user()
        with mock.patch.object(self.bot_utils, 'user_result', side_effect=RuntimeError('read failed')):
            with self.assertRaises(RuntimeError):
                self.export.save_to_csv()
        self.assertFalse(self.output.exists())
        self.assert_no_temporary_files()

    def test_import_does_not_export_or_prompt(self):
        with mock.patch.dict(sys.modules, {'config': self.config, 'bot_utils': self.bot_utils}):
            with mock.patch('builtins.input', side_effect=AssertionError('unexpected prompt')):
                with mock.patch('sqlite3.connect', side_effect=AssertionError('unexpected export')):
                    load_module('test_import_export', 'export_results.py')
        self.assertFalse(self.output.exists())
        self.assert_no_temporary_files()


if __name__ == '__main__':
    unittest.main()
