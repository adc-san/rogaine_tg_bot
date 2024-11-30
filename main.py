import telebot
import sqlite3
from datetime import datetime

import config
import bot_messages
import bot_utils

# Версия релиза
version = '0.7  '
# Фиксируем время запуска
start_time = datetime.now().strftime("%H:%M:%S - %Y/%m/%d")

# Создаем экземпляр бота, многопоточность отключена для избежания гонок обработки(threaded=False)
bot = telebot.TeleBot(config.bot_token, threaded=False)

# Словарь для хранения последних номеров КП, для которых ожидаем ввод шифра
have_cp_list = dict()

# Функция, обрабатывающая команду /start
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    bot.send_message(message.chat.id, bot_messages.start.format(first_name), reply_markup=bot_utils.make_reply_keyboard())
    if config.test_cp in config.secret_dict:
        bot.send_message(message.chat.id, bot_messages.test)
    if bot_utils.save_user(user_id, username, first_name, last_name, command_name='') is not None:
        bot.send_message(message.chat.id, bot_messages.some_error)  # Неизвестная ошибка БД

# Функция, обрабатывающая команду /finish
@bot.message_handler(commands=["finish"])
def finish(message):
    user_id = message.from_user.id
    cp_count, cp_sum, cp_list, no_cp_list, all_cp_list  = bot_utils.user_result(user_id)
    finish_time = datetime.now().strftime("%H:%M:%S - %Y/%m/%d")
    #Добавляем пробелы для вывода списка КП
    cp_list = ', '.join(cp_list.split(sep=','))
    no_cp_list = ', '.join(no_cp_list.split(sep=','))
    # Записываем время финиша в БД
    bot_utils.user_write_finish_time(user_id, finish_time)
    tmp_message = bot_messages.fin1.format(cp_count, bot_utils.get_total_cp_count(), cp_list, cp_sum)
    if len(no_cp_list) > 0:
        tmp_message += '\n' + bot_messages.fin2.format(no_cp_list)
    tmp_message += '\n' + bot_messages.fin3.format(finish_time, config.bot_message_org)
    bot.send_message(message.chat.id, tmp_message)


# Функция, обрабатывающая отладочную команду /admin
@bot.message_handler(commands=["admin"])
def admin(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, f'{start_time} v{version}')
    if user_id in config.admin_id:
        conn = sqlite3.connect(config.db_filename)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        user_list = cursor.fetchall()
        conn.close()
        tmp_msg = ''
        if len(user_list) > 0:
            for u in user_list:
                user_id = u[0]
                username = u[1]
                first_name = u[2]
                last_name = u[3]
                command_name = u[4]
                fin_time = u[5]
                cp_count, cp_sum, cp_list, no_cp_list, all_cp_list = bot_utils.user_result(user_id)

                
                tmp_part_msg = "<b>{}</b> @{} {} {} id{}\n{}/{}=<b>{}</b>={}({}) {}\n\n".format(
                    command_name or '', username or '', first_name or '', last_name or '', user_id, cp_count, bot_utils.get_total_cp_count(),
                    cp_sum, cp_list, no_cp_list, fin_time or '')
                # Разрываем сообщение, чтобы уложиться в ограничение ТГ в 4095 символов
                if len(tmp_msg) + len(tmp_part_msg)> 4095:
                    bot.send_message(message.chat.id,tmp_msg, parse_mode='HTML')
                    tmp_msg = tmp_part_msg
                else:
                    tmp_msg += tmp_part_msg
        else:
            tmp_msg = bot_messages.admin_nodata
    else:      
        bot.send_message(message.chat.id,tmp_msg, parse_mode='HTML')

# Получение сообщений от юзера
@bot.message_handler(content_types=["text"])
def handle_text(message):
    if message.text == bot_utils.get_fin_button():
        finish(message)
        return 0
    user_text_original = message.text  # Сохраняем исходное сообщение
    user_text = bot_utils.normalize_string(user_text_original)  # Переводим в нижний регистр и убираем пробелы по краям и заменяем похожие буквы
    user_id = message.from_user.id

    # Код КП - это число, а шифр - ВСЕГДА не число
    if user_text.isdigit():
        user_cp = int(user_text)
        # Если КП есть на карте
        if user_cp in config.secret_dict:
            # Проверка наличия взятого КП в базе
            conn = sqlite3.connect(config.db_filename)
            cursor = conn.cursor()
            info = cursor.execute('SELECT * FROM game WHERE id=? AND cp=? AND ch=?',
                                  (user_id, user_cp, 1)).fetchone()
            conn.close()
            if info is not None and len(info) > 0:
                # КП уже есть в базе
                bot.send_message(message.chat.id, bot_messages.have_cp.format(user_cp) + ' ' + bot_messages.next_point)
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
            cp_secret = bot_utils.normalize_string(config.secret_dict[user_cp])
            user_command_name = ''
            cp_problem = False
            tmp_problem_cp_words = tuple()
            for t in config.no_cp_words:
                tmp_problem_cp_words += (bot_utils.normalize_string(t),)
            # Если тест в режиме запоминания названия команды
            if user_cp == config.test_cp and config.test_command_name_mode:
                # Запоминаем имя команды и подставляем правильный шифр в качестве ответа
                user_command_name, user_text = user_text_original, cp_secret
            # Если пользователь сообщил что точка сорвана
            elif user_text in tmp_problem_cp_words:
                # Подставляем правильный шифр в качестве ответа
                user_text = cp_secret
                cp_problem = True

            # Если шифр совпадает
            if user_text == cp_secret:
                # Тестовая точка
                if user_cp == config.test_cp:
                    if config.test_command_name_mode:
                        tmp_message = bot_messages.true_answer.format(user_cp) + ' ' + bot_messages.command_name.format(
                            user_command_name) + ' ' + bot_messages.next_point
                    else:
                        if cp_problem:
                            tmp_message = bot_messages.cp_problem_check.format(user_cp) + ' ' + bot_messages.next_point
                        else:
                            tmp_message = bot_messages.true_answer.format(user_cp) + ' ' + bot_messages.next_point
                    # Сохранение пользователя при взятии тестовой точки
                    if bot_utils.save_user(user_id, message.from_user.username, message.from_user.first_name,
                                           message.from_user.last_name, user_command_name) is not None:
                        tmp_message += bot_messages.some_error
                else:
                    # Сохранение информации о КП в базу данных
                    if cp_problem:
                        user_ch = 0
                    else:
                        user_ch = 1
                    conn = sqlite3.connect(config.db_filename)
                    cursor = conn.cursor()
                    try:
                        cursor.execute("INSERT INTO game (id, cp, ch) VALUES (?, ?, ?)",
                                       (user_id, user_cp, user_ch))
                        conn.commit()
                    except sqlite3.IntegrityError:
                        # КП уже взят
                        if cp_problem:
                            tmp_message = bot_messages.dub.format(user_cp)
                        else:
                            # Помечаем КП взятым, на случай если он ранее помечен сорванным
                            try:
                                cursor.execute("UPDATE game SET ch=? WHERE id=? AND cp=?",
                                               (user_ch, user_id, user_cp))
                                conn.commit()
                            except:
                                tmp_message = bot_messages.some_error
                            else:
                                tmp_message = bot_messages.true_answer.format(user_cp)
                                tmp_message += '\n' + bot_messages.next_point


                    except:
                        # Неизвестная ошибка БД
                        tmp_message = bot_messages.some_error
                    else:
                        if cp_problem:
                            tmp_message = bot_messages.cp_problem_check.format(user_cp)
                        else:
                            tmp_message = bot_messages.true_answer.format(user_cp)
                        if user_cp == config.fin_cp:
                            tmp_message += '\n' + bot_messages.in_finish
                        else:
                            tmp_message += '\n' + bot_messages.next_point
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
bot_utils.create_tables()

# Запускаем бота - бесконечный цикл опроса. Используем infinity_polling, чтобы при проблемах со связью бот не падал
bot.infinity_polling(none_stop=True, interval=0)
