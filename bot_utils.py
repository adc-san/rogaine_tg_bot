import sqlite3
from telebot import types  # для указания типов
import config
import bot_messages

# Переводим в нижний регистр, убираем пробелы по краям, заменяем похожие буквы
def normalize_string(s):
    s = s.strip().lower().replace('ё','е').replace('й','и').replace('щ','ш').replace('ъ','ь')
    return s

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

def get_fin_button():
    return '🏁 Финиш 🏁'

def make_reply_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton(get_fin_button())
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
    cursor.execute('SELECT cp,ch FROM game WHERE id=? ORDER BY num', (user_id,))
    tmp_list = cursor.fetchall()
    conn.close()
    # Разбираем список КП пользователя
    all_cp_list = ''
    cp_list = ''
    cp_count = 0
    cp_sum = 0
    no_cp_list = ''
    for tup in tmp_list:
        # Если КП сорван
        if tup[1] == 0:
            all_cp_list += str(tup[0]) + ','
            no_cp_list += str(tup[0]) + ','         
        # Если КП взят 
        elif tup[1] == 1:
            all_cp_list += str(tup[0]) + ','
            cp_list += str(tup[0]) + ','
            cp_count += 1
            cp_sum += tup[0] // 10
    cp_list = cp_list.rstrip(',')
    no_cp_list = no_cp_list.rstrip(',')
    all_cp_list = all_cp_list.rstrip(',')
    # Сорванные КП выделяем символами '_'
    if len(all_cp_list) > 0:
        tmp_list = list()
        for cp in all_cp_list.split(','):
            if cp in no_cp_list:
                tmp_list.append(f'_{cp}_')
            else:
                tmp_list.append(cp)   
            all_cp_list = ','.join(tmp_list)
    return cp_count, cp_sum, cp_list, no_cp_list, all_cp_list


# Функция записывает время финиша в БД
def user_write_finish_time(user_id, finish_time, conn=None):
    own_connection = conn is None
    if own_connection:
        conn = sqlite3.connect(config.db_filename)
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET finish_time=? WHERE id=?",
                       (finish_time, user_id))
        if cursor.rowcount != 1:
            raise sqlite3.IntegrityError('User not found')
        if own_connection:
            conn.commit()
    finally:
        if own_connection:
            conn.close()

# Количество КП в списке, кроме тестового
def get_total_cp_count():
    cp_count = len(config.secret_dict)
    if cp_count > 0 and config.test_cp in config.secret_dict:
        cp_count -= 1
    return cp_count
