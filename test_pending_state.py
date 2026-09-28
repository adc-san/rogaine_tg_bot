from contextlib import contextmanager, redirect_stdout
from html import escape
import importlib.util
import io
import os
from pathlib import Path
import runpy
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


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(previous)


class FakeBot:
    def __init__(self, *args, **kwargs):
        self.sent = []
        self.infinity_polling = mock.Mock()

    def message_handler(self, *args, **kwargs):
        return lambda handler: handler

    def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text))


class PendingStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='.pending-tests-', dir=ROOT)
        self.directory = Path(self.temporary.name).resolve()
        self.assertEqual(self.directory.parent, ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.config = types.ModuleType('config')
        self.config.db_filename = str(self.directory / 'rogaine_tg_bot_data.db')
        self.config.bot_token = 'test-token'
        self.config.secret_dict = {1: 'test', 12: 'alpha', 23: 'bravo', 0: 'finish'}
        self.config.test_cp = 1
        self.config.fin_cp = 0
        self.config.test_command_name_mode = True
        self.config.no_cp_words = ('сорван', 'сорвано')
        self.config.admin_id = ()
        self.config.bot_message_org = '@organizer'
        self.telebot = types.ModuleType('telebot')
        self.telebot.types = types.SimpleNamespace()
        self.telebot.formatting = types.SimpleNamespace(escape_html=escape)
        self.telebot.TeleBot = FakeBot
        with mock.patch.dict(sys.modules, {'config': self.config, 'telebot': self.telebot}):
            self.bot_utils = load_module('test_bot_utils', 'bot_utils.py')
        self.main = self.restart()

    def restart(self):
        with mock.patch.dict(sys.modules, {
            'config': self.config, 'telebot': self.telebot, 'bot_utils': self.bot_utils,
        }):
            with redirect_stdout(io.StringIO()):
                main = load_module('test_main', 'main.py')
        main.bot.infinity_polling.assert_called_once_with(none_stop=True, interval=0)
        return main

    def message(self, text, user_id=7):
        return types.SimpleNamespace(
            text=text,
            chat=types.SimpleNamespace(id=user_id),
            from_user=types.SimpleNamespace(id=user_id, username=f'user{user_id}',
                                            first_name='First', last_name='Last'),
        )

    def rows(self, sql):
        conn = sqlite3.connect(self.config.db_filename)
        try:
            return conn.execute(sql).fetchall()
        finally:
            conn.close()

    def execute(self, sql):
        conn = sqlite3.connect(self.config.db_filename)
        try:
            conn.execute(sql)
            conn.commit()
        finally:
            conn.close()

    def clear_results(self):
        with working_directory(self.directory):
            with mock.patch.dict(sys.modules, {'bot_utils': self.bot_utils}):
                with mock.patch('builtins.input', side_effect=['yes', '']):
                    with redirect_stdout(io.StringIO()):
                        runpy.run_path(str(ROOT / 'clear_results.py'), run_name='__main__')

    def test_restart_recovers_two_independent_participants(self):
        self.main.handle_text(self.message('12', 7))
        self.main.handle_text(self.message('23', 8))
        restarted = self.restart()
        self.assertEqual(restarted.have_cp_list, {7: 12, 8: 23})
        restarted.handle_text(self.message('alpha', 7))
        self.assertEqual(restarted.have_cp_list, {8: 23})
        self.assertEqual(self.bot_utils.load_pending_cp(), {8: 23})
        restarted.handle_text(self.message('bravo', 8))
        self.assertEqual(self.rows('SELECT id, cp, ch FROM game ORDER BY id'),
                         [(7, 12, 1), (8, 23, 1)])
        self.assertEqual(self.restart().have_cp_list, {})

    def test_wrong_answer_clears_state_and_requires_number_again(self):
        self.main.handle_text(self.message('12'))
        restarted = self.restart()
        restarted.handle_text(self.message('wrong'))
        self.assertEqual(self.bot_utils.load_pending_cp(), {})
        self.assertEqual(restarted.have_cp_list, {})
        restarted.handle_text(self.message('alpha'))
        self.assertEqual(restarted.bot.sent[-1][1], restarted.bot_messages.digits_need)
        self.assertEqual(self.rows('SELECT * FROM game'), [])
        restarted.handle_text(self.message('12'))
        restarted.handle_text(self.message('alpha'))
        self.assertEqual(self.rows('SELECT id, cp, ch FROM game'), [(7, 12, 1)])

    def test_changing_selection_updates_only_that_participant(self):
        self.main.handle_text(self.message('12', 7))
        self.main.handle_text(self.message('12', 8))
        self.main.handle_text(self.message('23', 7))
        self.assertEqual(self.bot_utils.load_pending_cp(), {7: 23, 8: 12})
        self.assertEqual(self.restart().have_cp_list, {7: 23, 8: 12})

    def test_selection_is_persisted_before_prompt(self):
        def check_prompt(chat_id, text, **kwargs):
            if text == self.main.bot_messages.answer.format(12):
                self.assertEqual(self.bot_utils.load_pending_cp(), {7: 12})

        with mock.patch.object(self.main.bot, 'send_message', side_effect=check_prompt) as send:
            self.main.handle_text(self.message('12'))
        send.assert_called_once_with(7, self.main.bot_messages.answer.format(12), parse_mode='HTML')

    def test_save_failure_does_not_replace_previous_pending_or_prompt(self):
        self.main.handle_text(self.message('12'))
        real_connect = sqlite3.connect

        def read_only_connection(*args, **kwargs):
            conn = real_connect(*args, **kwargs)
            conn.execute('PRAGMA query_only=ON')
            return conn

        with mock.patch.object(self.bot_utils.sqlite3, 'connect', side_effect=read_only_connection):
            self.main.handle_text(self.message('23'))
        self.assertEqual(self.main.have_cp_list, {7: 12})
        self.assertEqual(self.bot_utils.load_pending_cp(), {7: 12})
        self.assertEqual(self.main.bot.sent[-1], (7, self.main.bot_messages.some_error))
        self.assertEqual(len(self.main.bot.sent), 2)

    def test_first_save_failure_does_not_create_memory_state(self):
        with mock.patch.object(self.bot_utils, 'save_pending_cp',
                               side_effect=sqlite3.OperationalError('database is locked')):
            self.main.handle_text(self.message('12'))
        self.assertEqual(self.main.have_cp_list, {})
        self.assertEqual(self.bot_utils.load_pending_cp(), {})
        self.assertEqual(self.main.bot.sent, [(7, self.main.bot_messages.some_error)])

    def test_delete_failure_keeps_memory_and_database_consistent(self):
        self.main.handle_text(self.message('12'))
        with mock.patch.object(self.bot_utils, 'delete_pending_cp',
                               side_effect=sqlite3.OperationalError('database is locked')):
            self.main.handle_text(self.message('wrong'))
        self.assertEqual(self.main.have_cp_list, {7: 12})
        self.assertEqual(self.bot_utils.load_pending_cp(), {7: 12})
        self.assertEqual(self.main.bot.sent[-1], (7, self.main.bot_messages.some_error))

    def test_recreating_tables_preserves_pending_state(self):
        self.main.handle_text(self.message('12'))
        self.bot_utils.create_tables()
        self.bot_utils.create_tables()
        self.assertEqual(self.bot_utils.load_pending_cp(), {7: 12})

    def test_removed_checkpoint_is_discarded_on_restart(self):
        self.main.handle_text(self.message('12', 7))
        self.main.handle_text(self.message('23', 8))
        del self.config.secret_dict[12]
        restarted = self.restart()
        self.assertEqual(restarted.have_cp_list, {8: 23})
        self.assertEqual(self.bot_utils.load_pending_cp(), {8: 23})
        restarted.handle_text(self.message('alpha', 7))
        self.assertEqual(restarted.bot.sent[-1], (7, restarted.bot_messages.digits_need))

    def test_team_name_selection_survives_restart(self):
        self.main.handle_text(self.message('1'))
        restarted = self.restart()
        restarted.handle_text(self.message('Команда'))
        self.assertEqual(self.rows('SELECT command_name FROM users WHERE id=7'), [('Команда',)])
        self.assertEqual(self.bot_utils.load_pending_cp(), {})
        self.assertEqual(restarted.have_cp_list, {})

    def test_missing_checkpoint_answer_clears_pending(self):
        self.main.handle_text(self.message('12'))
        restarted = self.restart()
        restarted.handle_text(self.message('сорван'))
        self.assertEqual(self.rows('SELECT id, cp, ch FROM game'), [(7, 12, 0)])
        self.assertEqual(self.bot_utils.load_pending_cp(), {})

    def test_clear_results_clears_pending_and_keeps_users(self):
        self.main.handle_text(self.message('12'))
        self.main.handle_text(self.message('alpha'))
        self.main.handle_text(self.message('23'))
        self.execute("UPDATE users SET finish_time='2026/09/25 - 12:00:00'")
        self.clear_results()
        self.assertEqual(self.bot_utils.load_pending_cp(), {})
        self.assertEqual(self.rows('SELECT * FROM game'), [])
        self.assertEqual(self.rows('SELECT id, finish_time FROM users'), [(7, None)])
        self.assertEqual(self.restart().have_cp_list, {})

    def test_clear_results_works_with_legacy_database_without_pending_table(self):
        self.execute('DROP TABLE pending_cp')
        self.clear_results()
        self.assertEqual(self.bot_utils.load_pending_cp(), {})


if __name__ == '__main__':
    unittest.main()
