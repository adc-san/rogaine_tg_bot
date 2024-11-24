import sqlite3
from telebot import types  # для указания типов
import config
import bot_messages

# Конвертирует список кортежей в строку с разделителями ', '
def convert_list_tup_to_str(list_tup):
    s = ''
    for tup in list_tup:
        s += str(tup[0]) + ','
    return s.rstrip(',')

def create_tables():
    # Создание или подключение к базе данных SQLite
    conn = sqlite3.connect(config.db_filename)
    cursor = conn.cursor()

    # Создание таблицы для хранения информации о пользователях
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                   id INTEGER PRIMARY KEY,
                   username TEXT,
                   first_name TEXT,
                   last_name TEXT,
                   command_name TEXT,
                   finish_time TEXT
                  )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS game (
                   num INTEGER PRIMARY KEY AUTOINCREMENT,
                   id INTEGER,
                   cp INTEGER,
                   ch INTEGER,
                   UNIQUE(id, cp)
                   )''')
    conn.close()


def make_reply_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("🏁 Финиш 🏁")
    markup.add(btn1)
    return markup

def save_user(user_id, username, first_name, last_name, command_name):
    # Сохранение информации о пользователе в базу данных
    conn = sqlite3.connect(config.db_filename)
    cursor = conn.cursor()
    tmp_message = None
    try:
        cursor.execute("INSERT INTO users (id, username, first_name, last_name, command_name) VALUES (?, ?, ?, ?, ?)",
                       (user_id, username, first_name, last_name, command_name))
        conn.commit()
    except sqlite3.IntegrityError:
        # Пользователь уже есть в БД.
        # Сохраняем только имя команды, если оно передано
        if len(command_name) > 0:
            try:
                cursor.execute("UPDATE users SET command_name=? WHERE id=?",
                               (command_name, user_id))
                conn.commit()
            except:
                tmp_message = bot_messages.some_error
    except:
        tmp_message = bot_messages.some_error
    finally:
        conn.close()
    return tmp_message


# Вычисление результатов участника в базе
def user_result(user_id):
    conn = sqlite3.connect(config.db_filename)
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(cp / 10) FROM game WHERE id=? AND ch=? ', (user_id, 1))
    cp_sum = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(cp) FROM game WHERE id=? AND ch=? ', (user_id, 1))
    cp_count = cursor.fetchone()[0]
    cursor.execute('SELECT cp FROM game WHERE id=? AND ch=? ORDER BY num', (user_id, 1))
    cp_list = convert_list_tup_to_str(cursor.fetchall())
    cursor.execute('SELECT cp FROM game WHERE id=? AND ch=? ORDER BY num', (user_id, 0))
    no_cp_list = convert_list_tup_to_str(cursor.fetchall())

    conn.close()
    return cp_count, cp_sum, cp_list, no_cp_list


# Функция записывает время финиша в БД
def user_write_finish_time(user_id, finish_time):
    conn = sqlite3.connect(config.db_filename)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET finish_time=? WHERE id=?",
                       (finish_time, user_id))
        conn.commit()
    except:
        pass

# Количество КП в списке, кроме тестового
def get_total_cp_count():
    cp_count = len(config.secret_dict)
    if cp_count > 0 and config.test_cp in config.secret_dict:
        cp_count -= 1
    return cp_count
