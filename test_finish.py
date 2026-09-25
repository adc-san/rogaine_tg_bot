"""Finish regression tests: temporary SQLite and a fake Telegram transport."""

from contextlib import redirect_stdout
import html
import importlib.util
import io
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest import mock


class TransportError(Exception):
    pass


class FakeBot:
    def __init__(self, *args, **kwargs):
        self.messages = []
        self.fail_on_send = None
        self.before_send = None

    def message_handler(self, *args, **kwargs):
        return lambda handler: handler

    def send_message(self, chat_id, text, **kwargs):
        if self.before_send is not None:
            self.before_send()
        if len(self.messages) + 1 == self.fail_on_send:
            raise TransportError('Telegram unavailable')
        self.messages.append(text)

    def infinity_polling(self, **kwargs):
        # Importing main exercises initialization without contacting Telegram.
        pass


class FinishTests(unittest.TestCase):
    FIRST_TIME = '2026/09/25 - 10:00:00'
    SECOND_TIME = '2026/09/25 - 11:00:00'

    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.db_filename = str(Path(temporary_directory.name) / 'game.db')

        config = types.ModuleType('config')
        config.bot_token = 'fake-token'
        config.db_filename = self.db_filename
        config.secret_dict = {1: 'test', 34: 'forest', 71: 'finish'}
        config.test_cp = 1
        config.test_command_name_mode = True
        config.fin_cp = 71
        config.no_cp_words = ('missing',)
        config.admin_id = (123,)
        config.bot_message_org = '@organizer'

        telebot = types.ModuleType('telebot')
        telebot.TeleBot = FakeBot
        telebot.formatting = types.SimpleNamespace(escape_html=html.escape)
        telebot.types = types.SimpleNamespace()
        modules = mock.patch.dict(sys.modules, {'config': config, 'telebot': telebot})
        modules.start()
        self.addCleanup(modules.stop)
        self.config = config
        self.messages = self.load_module('bot_messages')
        self.utils = self.load_module('bot_utils')
        with redirect_stdout(io.StringIO()):
            self.main = self.load_module('main')
        self.bot = self.main.bot
        clock = mock.patch.object(self.main, 'datetime')
        self.clock = clock.start()
        self.addCleanup(clock.stop)
        self.set_time(self.FIRST_TIME)

    @staticmethod
    def load_module(name):
        path = Path(__file__).resolve().with_name(name + '.py')
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def message(text):
        return types.SimpleNamespace(
            text=text,
            from_user=types.SimpleNamespace(
                id=123, username='team', first_name='Alice', last_name=None),
            chat=types.SimpleNamespace(id=123),
        )

    def set_time(self, value):
        self.clock.now.return_value.strftime.return_value = value

    def send(self, text):
        self.main.handle_text(self.message(text))

    def finish(self):
        self.main.finish(self.message('/finish'))

    def query(self, sql):
        conn = sqlite3.connect(self.db_filename)
        try:
            return conn.execute(sql).fetchall()
        finally:
            conn.close()

    def execute(self, sql):
        conn = sqlite3.connect(self.db_filename)
        try:
            conn.execute(sql)
            conn.commit()
        finally:
            conn.close()

    def block_write(self, table, operation):
        self.execute(
            f"CREATE TRIGGER blocked_write BEFORE {operation} ON {table} "
            "BEGIN SELECT RAISE(ABORT, 'simulated database failure'); END")

    def assert_finish_time(self, value):
        self.assertEqual(self.query('SELECT finish_time FROM users WHERE id=123'), [(value,)])

    def assert_error(self):
        self.assertEqual(self.bot.messages[-1], self.messages.some_error)

    def test_finish_first_command_registers_and_persists_user(self):
        self.finish()
        self.assertEqual(
            self.query('SELECT id, username, first_name, finish_time FROM users'),
            [(123, 'team', 'Alice', self.FIRST_TIME)])
        self.assertIn(self.FIRST_TIME, self.bot.messages[-1])

    def test_finish_button_first_message_persists_user(self):
        self.send(self.utils.get_fin_button())
        self.assert_finish_time(self.FIRST_TIME)

    def test_repeated_finish_and_game_continuation_remain_available(self):
        self.finish()
        self.send('34')
        self.send('forest')
        self.assert_finish_time(self.FIRST_TIME)
        self.set_time(self.SECOND_TIME)
        self.finish()
        self.assert_finish_time(self.SECOND_TIME)
        self.assertEqual(self.utils.user_result(123)[:2], (1, 3))
        self.assertIn('34', self.bot.messages[-1])

    def test_regular_checkpoint_and_duplicate_keep_score_without_finish(self):
        self.send('34')
        self.send('forest')
        self.send('34')
        self.assertEqual(self.query('SELECT cp, ch FROM game'), [(34, 1)])
        self.assert_finish_time(None)
        self.assertEqual(self.utils.user_result(123)[:2], (1, 3))

    def test_missing_regular_checkpoint_can_be_taken_later(self):
        self.send('34')
        self.send('missing')
        self.assertEqual(self.utils.user_result(123)[:2], (0, 0))
        self.send('34')
        self.send('forest')
        self.assertEqual(self.query('SELECT cp, ch FROM game'), [(34, 1)])
        self.assertEqual(self.utils.user_result(123)[:2], (1, 3))
        self.assert_finish_time(None)

    def test_finish_checkpoint_is_committed_before_any_reply(self):
        self.send('71')

        def check_committed():
            self.assertEqual(self.query('SELECT cp, ch FROM game'), [(71, 1)])
            self.assert_finish_time(self.FIRST_TIME)

        self.bot.before_send = check_committed
        self.send('finish')
        self.assertIn(self.FIRST_TIME, self.bot.messages[-1])
        self.assertEqual(self.utils.user_result(123)[:2], (1, 7))

    def test_missing_finish_checkpoint_still_finishes_and_can_be_upgraded(self):
        self.send('71')
        self.send('missing')
        self.assert_finish_time(self.FIRST_TIME)
        self.assertEqual(self.query('SELECT cp, ch FROM game'), [(71, 0)])
        self.assertEqual(self.utils.user_result(123)[:2], (0, 0))
        self.set_time(self.SECOND_TIME)
        self.send('71')
        self.send('finish')
        self.assert_finish_time(self.SECOND_TIME)
        self.assertEqual(self.query('SELECT cp, ch FROM game'), [(71, 1)])
        self.assertEqual(self.utils.user_result(123)[:2], (1, 7))

    def test_repeated_missing_finish_checkpoint_updates_finish_time(self):
        self.send('71')
        self.send('missing')
        self.set_time(self.SECOND_TIME)
        self.send('71')
        self.send('missing')
        self.assert_finish_time(self.SECOND_TIME)
        self.assertEqual(self.query('SELECT cp, ch FROM game'), [(71, 0)])

    def test_acknowledgement_failure_preserves_complete_finish(self):
        self.send('71')
        self.bot.fail_on_send = len(self.bot.messages) + 1
        with self.assertRaises(TransportError):
            self.send('finish')
        self.assertEqual(self.query('SELECT cp, ch FROM game'), [(71, 1)])
        self.assert_finish_time(self.FIRST_TIME)
        self.bot.fail_on_send = None
        self.send('71')
        self.assert_finish_time(self.FIRST_TIME)

    def test_finish_summary_send_failure_does_not_undo_commit(self):
        self.send('71')
        self.bot.fail_on_send = len(self.bot.messages) + 2
        with self.assertRaises(TransportError):
            self.send('finish')
        self.assertEqual(self.query('SELECT cp, ch FROM game'), [(71, 1)])
        self.assert_finish_time(self.FIRST_TIME)

    def test_finish_checkpoint_insert_failure_does_not_record_finish(self):
        self.send('71')
        self.block_write('game', 'INSERT')
        self.send('finish')
        self.assertEqual(self.query('SELECT * FROM game'), [])
        self.assert_finish_time(None)
        self.assert_error()

    def test_finish_time_update_failure_rolls_back_checkpoint_insert(self):
        self.send('71')
        self.block_write('users', 'UPDATE')
        self.send('finish')
        self.assertEqual(self.query('SELECT * FROM game'), [])
        self.assert_finish_time(None)
        self.assert_error()

    def test_finish_time_update_failure_rolls_back_missing_checkpoint_upgrade(self):
        self.send('71')
        self.send('missing')
        self.set_time(self.SECOND_TIME)
        self.block_write('users', 'UPDATE')
        self.send('71')
        self.send('finish')
        self.assertEqual(self.query('SELECT cp, ch FROM game'), [(71, 0)])
        self.assert_finish_time(self.FIRST_TIME)
        self.assert_error()

    def test_checkpoint_upgrade_failure_preserves_previous_finish(self):
        self.send('71')
        self.send('missing')
        self.set_time(self.SECOND_TIME)
        self.block_write('game', 'UPDATE')
        self.send('71')
        self.send('finish')
        self.assertEqual(self.query('SELECT cp, ch FROM game'), [(71, 0)])
        self.assert_finish_time(self.FIRST_TIME)
        self.assert_error()

    def test_finish_command_update_failure_reports_error(self):
        self.finish()
        self.set_time(self.SECOND_TIME)
        self.block_write('users', 'UPDATE')
        self.finish()
        self.assert_finish_time(self.FIRST_TIME)
        self.assert_error()

    def test_finish_command_user_insert_failure_reports_error(self):
        self.block_write('users', 'INSERT')
        self.finish()
        self.assertEqual(self.query('SELECT * FROM users'), [])
        self.assert_error()

    def test_commit_failure_rolls_back_finish_checkpoint_and_time(self):
        self.send('71')
        real_connect = sqlite3.connect

        class FailedCommitConnection(sqlite3.Connection):
            def commit(self):
                raise sqlite3.OperationalError('simulated commit failure')

        def connect(path):
            return real_connect(path, factory=FailedCommitConnection)

        with mock.patch.object(self.main.sqlite3, 'connect', side_effect=connect):
            self.send('finish')
        self.assertEqual(self.query('SELECT * FROM game'), [])
        self.assert_finish_time(None)
        self.assert_error()


if __name__ == '__main__':
    unittest.main()
