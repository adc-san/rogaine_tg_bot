# Секретный токен вашего телеграм бота
bot_token = 'Поместите сюда токен вашего бота'
# Имя файла с БД 
db_filename = 'rogaine_tg_bot_data.db'
# Имя файла с результатами
results_filename = 'results.csv'
# Контакт организатора
bot_message_org = '@IvanovIvanIvanovich'
# Словарь КП и шифров на дистанции
secret_dict = {12: 'два',
               23: 'три',
               34: 'четыре',
               45: 'пять',
               56: 'шесть',
               67: 'семь',
               78: 'восемь',
               89: 'девять',
               90: 'ноль',
               101: 'один',
               1: 'рогейн',
               0: 'финиш',
               }

# Тестовый КП, не учитывается в общей сумме(шифр для КП должен быть в общем списке). При взятии КП в базе обновляется информация о пользователе
test_cp = 1
# Режим ввода имени команды: True - в ответ на тестовую точку принимается любая строка, которая сохраняется как имя команды, False - в ответ на тестовую точку принимается шифр
test_command_name_mode = True
# Финишный КП, учитывается в сумме, если номер меньше 10, то на результат не влияет (шифр для КП должен быть в общем списке)
fin_cp = 0
# Специальные слова, для пометки КП отсутствующим/сорванным (обязательно в нижнем регистре).
no_cp_words = ('сорван', 'сорвано')
# Список id пользователей Телеграм, которые могут управлять ботом (админы)
admin_id = (987654321, 123456789)
