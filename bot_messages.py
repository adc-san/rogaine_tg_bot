start = '''Привет, {}!
Это бот "Рогейн в Перми"! 
Я умею считать собранные тобой на КП баллы! 
Отправляй мне номер КП, а после моего ответа вводи шифр. 
Если на дистанции у тебя пропадет интернет, ты можешь внести шифр с КП в чат-бот, он будет обработан при появлении интернета. 
Номер КП вводится цифрой, шифр отдельным сообщением. 

Когда найдешь КП, пришли мне его номер. Вот так: 
23'''
test = 'Проверить работу бота можно на тестовом КП у организатора.'
point = 'Пришли мне номер КП.'
next_point = 'Когда найдешь следующий КП, пришли мне его номер.'
answer = 'Жду твой ответ на КП {}'
fin = '''Ты обнаружил {} из {} КП:
№: {} 
Количество баллов: {} 
Время финиша: {} 
Если хочешь завершить игру, сообщи судье соревнований {}'''
true_answer = '*Верно! КП {} зачтён.*'
true_dub = 'Верно, но КП {} уже принят'
have_kp = 'КП {} уже принят'
false_answer = 'Неверно.'
some_error = 'Извини, у меня проблемы. Ошибка, паника!'
no_point = 'На карте нет такого КП!'
digits_need = 'Ты должен ввести номер КП состоящий только из цифр.'
admin_nodata = 'Админ, список пользователей пуст'
in_finish = 'Ты прибыл на финиш.'
command_name = 'Название твоей команды - {}'