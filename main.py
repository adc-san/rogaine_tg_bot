import telebot
from telebot import types  # для указания типов
import sqlite3
from datetime import datetime

import config
import bot_messages


# Версия релиза
version = '0.4  '
# Фиксируем время запуска
start_time = datetime.now().strftime("%H:%M:%S - %Y/%m/%d")

# Создаем экземпляр бота, многопоточность отключена для избежания гонок обработки(threaded=False)
bot = telebot.TeleBot(config.bot_token, threaded=False)

# Словарь для хранения последних номеров КП, для которых ожидаем ввод шифра
have_cp_list = dict()


# Конвертирует список кортежей в строку с разделителями ', '
def convert_list_tup_to_str(list_tup):
    s = ''
    for tup in list_tup:
        s += str(tup[0]) + ', '
    return s.rstrip().rstrip(',')


def create_tables():
    # Создание или подключение к базе данных SQLite
    conn = sqlite3.connect('rogaine_tg_bot_data.db')
    cursor = conn.cursor()

    # Создание таблицы для хранения информации о пользователях
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                   id INTEGER PRIMARY KEY,
                   username TEXT,
                   first_name TEXT,
                   last_name TEXT,
                   command_name TEXT
                  )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS game (
                   num INTEGER PRIMARY KEY AUTOINCREMENT,
                   id INTEGER,
                   cp INTEGER,
                   UNIQUE(id, cp)
                   )''')
    conn.close()


def make_reply_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Финиш")
    markup.add(btn1)
    return markup

def save_user(user_id, username, first_name, last_name, command_name):
    # Сохранение информации о пользователе в базу данных
    conn = sqlite3.connect('rogaine_tg_bot_data.db')
    cursor = conn.cursor()
    tmp_message = None
    try:
        cursor.execute("INSERT INTO users (id, username, first_name, last_name, command_name) VALUES (?, ?, ?, ?, ?)",
                       (user_id, username, first_name, last_name, command_name))
        conn.commit()
    except sqlite3.IntegrityError:
        # Пользователь уже есть в БД
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

# Функция, обрабатывающая команду /start
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    bot.send_message(message.chat.id, bot_messages.start.format(first_name), reply_markup=make_reply_keyboard())
    bot.send_message(message.chat.id, bot_messages.test)
    if save_user(user_id, username, first_name, last_name, user_command_name='') is not None:
        bot.send_message(message.chat.id, bot_messages.some_error)  # Неизвестная ошибка БД

# Вычисление результатов участника в базе
def user_result(user_id):
    conn = sqlite3.connect('rogaine_tg_bot_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(cp / 10) FROM game WHERE id=?', (user_id,))
    cp_sum = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(cp) FROM game WHERE id=?', (user_id,))
    cp_count = cursor.fetchone()[0]
    cursor.execute('SELECT cp FROM game WHERE id=? ORDER BY num', (user_id,))
    cp_list = convert_list_tup_to_str(cursor.fetchall())
    conn.close()
    return cp_count, cp_sum, cp_list

# Функция, обрабатывающая команду /finish
@bot.message_handler(commands=["finish"])
def finish(message):
    user_id = message.from_user.id
    cp_count, cp_sum, cp_list = user_result(user_id)
    bot.send_message(message.chat.id, bot_messages.fin.format(cp_count, len(config.secret_dict), cp_list, cp_sum,
                                                              datetime.now().strftime("%H:%M:%S - %Y/%m/%d"),
                                                              config.bot_message_org))

# Функция, обрабатывающая отладочную команду /admin
@bot.message_handler(commands=["admin"])
def admin(message):
    bot.send_message(message.chat.id, f'{start_time} v{version}')
    conn = sqlite3.connect('rogaine_tg_bot_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users')
    user_list = cursor.fetchall()
    conn.close()
    if len(user_list) > 0:
        for u in user_list:
            user_id = u[0]
            username = u[1]
            first_name = u[2]
            last_name = u[3]
            cp_count, cp_sum, cp_list = user_result(user_id)
            bot.send_message(message.chat.id, "id{}-{}\n{} {}\n{}/{} = {} = {}"
                             .format(user_id, username, first_name, last_name, cp_count, len(config.secret_dict),cp_sum, cp_list))
    else:
        bot.send_message(message.chat.id,bot_messages.admin_nodata)

# Получение сообщений от юзера
@bot.message_handler(content_types=["text"])
def handle_text(message):
    if message.text == 'Финиш':
        finish(message)
        return 0
    user_text = message.text.strip()  # Убираем пробелы по краям
    user_id = message.from_user.id

    # Код КП - это число, а шифр - ВСЕГДА не число
    if user_text.isdigit():
        user_cp = int(user_text)
        # Если КП есть на карте
        if user_cp in config.secret_dict:
            # Проверка наличия взятого КП в базе
            conn = sqlite3.connect('rogaine_tg_bot_data.db')
            cursor = conn.cursor()
            info = cursor.execute('SELECT * FROM game WHERE id=? AND cp=?',
                                  (user_id, user_cp)).fetchone()
            conn.close()
            if info is not None and len(info) > 0:
                # КП уже есть в базе
                bot.send_message(message.chat.id, bot_messages.have_cp.format(user_cp) + message.chat.id, bot_messages.next_point)
            else:
                # КП ещё не взят
                have_cp_list.update({user_id: user_cp})
                bot.send_message(message.chat.id, bot_messages.answer.format(user_cp))
        else:
            # КП нет на карте
            bot.send_message(message.chat.id, bot_messages.no_point)
    else:
        if user_id in have_cp_list:
            user_cp = have_cp_list[user_id]
            cp_secret = config.secret_dict[user_cp].strip().lower()
            user_command_name = ''
            # Если тест в режиме запоминания названия команды
            if user_cp == config.test_cp and config.test_command_name_mode:
                # Запоминаем имя команды и подставляем правильный шифр в качестве ответа
                user_command_name, user_text = user_text, cp_secret
            user_text = user_text.lower() # Переводим в нижний регистр
            # Если шифр совпадает
            if user_text == cp_secret:
                # Тестовая точка
                if user_cp == config.test_cp:
                    if config.test_command_name_mode:
                        tmp_message = bot_messages.true_answer.format(user_cp) + ' ' + bot_messages.command_name.format(user_command_name) + ' ' + bot_messages.next_point
                    else:
                        tmp_message = bot_messages.true_answer.format(user_cp) + ' ' + bot_messages.next_point
                    # Сохранение пользователя при взятии тестовой точки
                    if save_user(user_id, message.from_user.username, message.from_user.first_name, message.from_user.last_name, user_command_name) is not None:
                        tmp_message += bot_messages.some_error
                else:
                    # Сохранение информации о КП в базу данных
                    conn = sqlite3.connect('rogaine_tg_bot_data.db')
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO game (id, cp) VALUES (?, ?)",
                                   (user_id, user_cp))
                        conn.commit()
                    except sqlite3.IntegrityError:
                        # КП уже взят
                        tmp_message = bot_messages.true_dub.format(user_cp)
                    except:
                        # Неизвестная ошибка БД
                        tmp_message = bot_messages.some_error
                    else:
                        tmp_message = bot_messages.true_answer.format(user_cp)
                        if user_cp == config.fin_cp:
                            tmp_message += ' ' + bot_messages.in_finish
                        else:
                            tmp_message += ' ' + bot_messages.next_point
                    finally:
                        conn.close()
                bot.send_message(message.chat.id, tmp_message, parse_mode="Markdown")
                if user_cp == config.fin_cp:
                    finish(message)
            else:
                # Не угадал шифр
                bot.send_message(message.chat.id, bot_messages.false_answer + ' ' + bot_messages.point)
            if user_id in have_cp_list:
                del have_cp_list[user_id]
        else:
            # Еще не ввёл номер КП
            bot.send_message(message.chat.id, bot_messages.digits_need)


# Старт программы-----------------------------------------------------------------------------
print('----------------------------')
print('-   ROGAINE TELEGRAM BOT   -')
print(f'-     STARTED v{version}       -')
print(f'-  {start_time}   -')
print('----------------------------')

# Создаем таблицы для хранения данных
create_tables()

# Запускаем бота - бесконечный цикл опроса
bot.polling(none_stop=True, interval=0)
