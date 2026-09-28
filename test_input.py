"""Input regressions; uses temporary SQLite and a Telegram stub, without network."""

import contextlib
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


class FakeBot:
    def __init__(self, *args, **kwargs):
        self.messages = []

    def message_handler(self, **kwargs):
        return lambda handler: handler

    def send_message(self, chat_id, text, **kwargs):
        if not text or len(text) > 4096:
            raise AssertionError('Empty or oversized Telegram message')
        self.messages.append(text)

    def infinity_polling(self, **kwargs):
        pass


class InputTests(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.config = types.ModuleType('config')
        self.config.db_filename = str(Path(temp_dir.name) / 'game.db')
        self.config.bot_token = 'unused'
        self.config.secret_dict = {1: 'test', 12: 'answer', 23: 'next', 0: 'finish'}
        self.config.test_cp = 1
        self.config.test_command_name_mode = True
        self.config.fin_cp = 0
        self.config.no_cp_words = ('сорван', 'сорвано')
        self.config.admin_id = (99,)
        self.config.bot_message_org = '@organizer'
        telebot = types.ModuleType('telebot')
        telebot.TeleBot = FakeBot
        telebot.formatting = types.SimpleNamespace(escape_html=html.escape)
        telebot.types = types.SimpleNamespace()
        modules_patch = mock.patch.dict(sys.modules, {'config': self.config, 'telebot': telebot})
        modules_patch.start()
        self.addCleanup(modules_patch.stop)
        self.load_module('bot_messages')
        self.utils = self.load_module('bot_utils')
        with contextlib.redirect_stdout(io.StringIO()):
            self.main = self.load_module('main')
        self.bot = self.main.bot

    @staticmethod
    def load_module(name):
        spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def message(text, user_id=7):
        return types.SimpleNamespace(
            text=text, chat=types.SimpleNamespace(id=user_id),
            from_user=types.SimpleNamespace(id=user_id, username='runner', first_name='Runner', last_name=''))

    def send(self, text):
        self.main.handle_text(self.message(text))

    def stored_name(self, user_id=7):
        with contextlib.closing(sqlite3.connect(self.config.db_filename)) as conn:
            return conn.execute('SELECT command_name FROM users WHERE id=?', (user_id,)).fetchone()[0]

    def test_numeric_team_name_is_saved_even_if_it_matches_a_checkpoint(self):
        self.send('1')
        self.send('12')
        self.assertEqual(self.stored_name(), '12')
        self.assertNotIn(7, self.main.have_cp_list)
        self.assertEqual(self.utils.user_result(7)[0], 0)

    def test_non_decimal_digit_does_not_crash(self):
        self.send('²')
        self.assertEqual(self.bot.messages[-1], self.main.bot_messages.digits_need)
        self.assertNotIn(7, self.main.have_cp_list)

    def test_non_decimal_digit_can_be_a_team_name(self):
        self.send('1')
        self.send('²')
        self.assertEqual(self.stored_name(), '²')

    def test_unicode_decimal_checkpoint_still_works(self):
        self.send('١٢')
        self.assertEqual(self.main.have_cp_list[7], 12)
        self.send('answer')
        self.assertEqual(self.utils.user_result(7)[:2], (1, 1))

    def test_excessively_long_number_does_not_crash(self):
        self.send('9' * 5000)
        self.assertEqual(self.bot.messages[-1], self.main.bot_messages.no_point)

    def test_long_team_name_keeps_previous_name_and_allows_retry(self):
        self.utils.save_user(7, 'runner', 'Runner', '', 'Previous')
        self.send('1')
        self.send('a' * 4090)
        self.assertEqual(self.stored_name(), 'Previous')
        self.assertEqual(self.main.have_cp_list[7], 1)
        self.assertIn('100', self.bot.messages[-1])
        self.send('New team')
        self.assertEqual(self.stored_name(), 'New team')
        self.assertNotIn(7, self.main.have_cp_list)

    def test_limit_counts_name_characters_before_html_escaping(self):
        self.send('1')
        self.send('&' * 100)
        self.assertEqual(self.stored_name(), '&amp;' * 100)
        self.assertIn('&amp;' * 100, self.bot.messages[-1])

    def test_101_character_name_is_rejected(self):
        self.send('1')
        self.send('a' * 101)
        self.assertEqual(self.stored_name(), '')
        self.assertEqual(self.main.have_cp_list[7], 1)

    def test_numeric_input_can_change_a_pending_regular_checkpoint(self):
        self.send('12')
        self.send('23')
        self.assertEqual(self.main.have_cp_list[7], 23)

    def test_test_checkpoint_still_uses_secret_when_name_mode_is_off(self):
        self.config.test_command_name_mode = False
        self.send('1')
        self.send('test')
        self.assertEqual(self.stored_name(), '')
        self.assertNotIn(7, self.main.have_cp_list)
        self.assertIn('КП 1 зачтён', self.bot.messages[-1])

    def test_legacy_names_are_safely_shortened_only_for_display(self):
        original = html.escape('<&' * 3000)
        self.utils.save_user(7, 'runner', 'Runner', '', original)
        with contextlib.closing(sqlite3.connect(self.config.db_filename)) as conn:
            conn.execute('INSERT INTO game (id, cp, ch) VALUES (?, ?, ?)', (7, 12, 1))
            conn.commit()
        expected_name = html.escape(('<&' * 3000)[:99] + '…')
        for handler in (self.main.admin, self.main.a, self.main.nof, self.main.log):
            with self.subTest(handler=handler.__name__):
                self.bot.messages.clear()
                handler(self.message('/admin', user_id=99))
                self.assertIn(expected_name, ''.join(self.bot.messages))
                self.assertEqual(self.stored_name(), original)

    def test_many_legacy_names_are_split_into_nonempty_messages(self):
        for user_id in range(10, 30):
            self.utils.save_user(user_id, 'runner', 'Runner', '', '&amp;' * 5000)
            with contextlib.closing(sqlite3.connect(self.config.db_filename)) as conn:
                conn.execute('INSERT INTO game (id, cp, ch) VALUES (?, ?, ?)', (user_id, 12, 1))
                conn.commit()
        for handler in (self.main.admin, self.main.log):
            with self.subTest(handler=handler.__name__):
                self.bot.messages.clear()
                handler(self.message('/admin', user_id=99))
                self.assertGreater(len(self.bot.messages), 2)


if __name__ == '__main__':
    unittest.main()
