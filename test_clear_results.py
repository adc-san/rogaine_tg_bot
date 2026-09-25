from contextlib import closing
import ast
from pathlib import Path
import sqlite3
import tempfile
import types
import unittest


class ClearResultsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def make_database(self, name):
        path = self.directory / name
        with closing(sqlite3.connect(path)) as conn:
            conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, finish_time TEXT)')
            conn.execute('CREATE TABLE game (id INTEGER, cp INTEGER)')
            conn.execute("INSERT INTO users VALUES (1, '2026/09/25 - 10:00:00')")
            conn.execute('INSERT INTO game VALUES (1, 12)')
            conn.commit()
        return path

    def clear(self, path):
        # Load the function without executing the interactive deletion prompt.
        source = Path(__file__).with_name('clear_results.py')
        tree = ast.parse(source.read_text(encoding='utf-8'))
        tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        namespace = {
            'sqlite3': sqlite3,
            'config': types.SimpleNamespace(db_filename=str(path)),
        }
        exec(compile(tree, str(source), 'exec'), namespace)
        namespace['drop_game_table']()

    def test_configured_database_is_cleared_without_touching_default_file(self):
        current = self.make_database('competition.db')
        old = self.make_database('rogaine_tg_bot_data.db')
        self.clear(current)
        with closing(sqlite3.connect(current)) as conn:
            self.assertIsNone(conn.execute('SELECT finish_time FROM users').fetchone()[0])
            self.assertIsNone(conn.execute(
                "SELECT name FROM sqlite_master WHERE name='game'").fetchone())
        with closing(sqlite3.connect(old)) as conn:
            self.assertEqual(conn.execute('SELECT cp FROM game').fetchall(), [(12,)])
            self.assertIsNotNone(conn.execute('SELECT finish_time FROM users').fetchone()[0])

    def test_default_filename_still_works_when_configured(self):
        path = self.make_database('rogaine_tg_bot_data.db')
        self.clear(path)
        with closing(sqlite3.connect(path)) as conn:
            self.assertIsNone(conn.execute('SELECT finish_time FROM users').fetchone()[0])


if __name__ == '__main__':
    unittest.main()
