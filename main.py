import telebot
from telebot import types  # для указания типов
import sqlite3
from datetime import datetime

import config
import bot_messages

# Конвертирует список кортежей в строку с разделителями ', '
def convert_list_tup_to_str(list_tup):
    s=''
    for tup in list_tup:
        s+=str(tup[0]) + ', '
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
                  last_name TEXT
                  )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS game (
                      id INTEGER,
                      kp INTEGER,
                      PRIMARY KEY(id, kp)
                      )''')
    conn.close()

version = '0.01 '
have_kp_list = dict()
print('----------------------------')
print('-   ROGAINE TELEGRAM BOT   -')
print(f'-     STARTED v.{version}      -')
print('----------------------------')
# Создаем экземпляр бота
bot = telebot.TeleBot(config.bot_token)

# Создаем для хранения данных
create_tables()

# Функция, обрабатывающая команду /start
@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Продолжить игру")
    btn2 = types.KeyboardButton("Завершить игру")
    markup.add(btn1, btn2)

    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    bot.send_message(message.chat.id, bot_messages.start.format(first_name), reply_markup=markup)
    bot.send_message(message.chat.id, bot_messages.test)

    # Сохранение информации о пользователе в базу данных
    conn = sqlite3.connect('rogaine_tg_bot_data.db')
    cursor = conn.cursor()
    tmp_message = None
    try:
        cursor.execute("INSERT INTO users (id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
                       (user_id, username, first_name, last_name))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Пользователь уже есть в БД
    except:
        tmp_message = bot_messages.some_error
    finally:
        conn.close()
    if tmp_message is not None:
        bot.send_message(message.chat.id, bot_messages.some_error) # Неизвестная ошибка БД

# Функция, обрабатывающая команду /finish
@bot.message_handler(commands=["finish"])
def finish(message):
    # Вычисление суммы очков участника в базе
    conn = sqlite3.connect('rogaine_tg_bot_data.db')
    cursor = conn.cursor()
    user_id = message.from_user.id
    cursor.execute('SELECT SUM(kp / 10) FROM game WHERE id=?', (user_id, ))
    kp_sum = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(kp) FROM game WHERE id=?', (user_id, ))
    kp_count = cursor.fetchone()[0]
    cursor.execute('SELECT kp FROM game WHERE id=?', (user_id, ))
    kp_list = convert_list_tup_to_str(cursor.fetchall())
    conn.close()
    bot.send_message(message.chat.id, bot_messages.fin.format(kp_count, len(config.secret_dict), kp_list, kp_sum, datetime.now().strftime("%H:%M:%S - %Y/%m/%d"), config.bot_message_org))

# Получение сообщений от юзера
@bot.message_handler(content_types=["text"])
def handle_text(message):
    user_text = message.text.strip().lower()  # Убираем пробелы и переводим в нижний регистр
    user_id = message.from_user.id

    # Код КП - это число, а шифр - ВСЕГДА не число
    if user_text.isdigit():
        # Если КП есть на карте
        user_kp = int(user_text)
        if user_kp in config.secret_dict:
            # Проверка наличия взятого КП в базе
            conn = sqlite3.connect('rogaine_tg_bot_data.db')
            cursor = conn.cursor()
            info = cursor.execute('SELECT * FROM game WHERE id=? AND kp=?',
                                  (user_id, user_kp)).fetchone()
            conn.close()
            if info is None: 
                have_kp_list.update({user_id: user_kp})
                bot.send_message(message.chat.id, bot_messages.answer.format(user_kp))
            else:
                 bot.send_message(message.chat.id, bot_messages.have_kp.format(user_kp))
                 bot.send_message(message.chat.id, bot_messages.point) 
        else:
            bot.send_message(message.chat.id, bot_messages.no_point)
    else:
        if user_id in have_kp_list:
            user_kp = have_kp_list[user_id]
            if user_text == config.secret_dict[user_kp].strip().lower():
                # Сохранение информации о КП в базу данных
                conn = sqlite3.connect('rogaine_tg_bot_data.db')
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO game (id, kp) VALUES (?, ?)",
                                   (user_id, user_kp))
                    conn.commit()
                except sqlite3.IntegrityError:
                    # КП уже взят
                    tmp_message = bot_messages.true_dub.format(user_kp)
                except:
                    # Неизвестная ошибка БД
                    tmp_message =  bot_messages.some_error
                else:
                    tmp_message = bot_messages.true_answer + ' ' + bot_messages.point
                finally:
                    conn.close()
                bot.send_message(message.chat.id, tmp_message)  
            else:
                # Не угадал
                bot.send_message(message.chat.id, bot_messages.false_answer)
                bot.send_message(message.chat.id, bot_messages.point)
            if user_id in have_kp_list:
                del have_kp_list[user_id]
        else:
            # Еще не ввёл номер КП
            bot.send_message(message.chat.id, bot_messages.digits_need)


# Запускаем бота
bot.polling(none_stop=True, interval=0)
