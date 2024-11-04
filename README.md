# Телеграм бот для рогейна.
Это скрипт telegram бота, предназначенный для фиксации результатов участников соревнований по рогейну.

Участники находят КП (контрольные пункты) у которых есть номер и шифр, и отправляют номер и шифр боту. Если, присланный участником шифр совпадает с правильным ответом, то этот КП считается взятым участником и участник получает за него баллы. Бот фиксирует взятие КП каждым участником(командой) и ведёт подсчёт общего количества баллов каждого участника. На финише участник отправляет боту завершающую команду и бот фиксирует время финиша и результат участника в баллах. При отсутствии связи на дистанции клиент telegram накапливает сообщения пользователя и при появлении связи они будут переданны боту.

* Номер - **всегда** двух или трёхзначное число, в котором сотни и десятки - это стоимость КП в баллах, например КП 35 - стоит три балла, КП 108 - десять баллов.
* Шифр - произвольная строка текста, содержащяя хотябы одну букву, при сравнении шифра с правильным ответом бот удаляет пробелы в начале и конце строки, регистр символов не имеет значение. Сравнение происходит посимвольно, например шифр **K2** с латинской буквой k и **К2** с русской к, это разные шифры, стоит иметь это в виду при составлении шифров.

## Установка и запуск бота
* создать бота в telegram, создать боту меню с командой `/finish`, запомнить ключ бота
* нужен компьютер с стабильным доступом в интернет (лучше сервер)
* установить python
* установить библиотеку telebot
* скачать последний релиз этого проекта `rogaine_tg_bot`
* создать в директории проекта файл `confg.py` и прописать в него необходимую информацию. Формат содержимого файла приведён ниже:
```
# Секретный токен вашего телеграм бота
bot_token = 'сюда нужно вставить токен'
# Контакт организатора
bot_message_org = '@IvanovIvanIvanovich'
# Словарь КП и шифров на дистанции
secret_dict = {12: 'два', 23: 'три', 34: 'четыре', 45: 'пять', 56: 'шесть', 67: 'семь', 78: 'восемь', 89: 'девять', 90: 'ноль', 101: 'один'}
# Словарь тестовых КП и шифров
test_dict = {99: 'рогейн',}
```
* запустить main.py 

## Инструкция участника
* `/start` - начало работы с ботом, приветствие, регистрация и проверка
* Для отметки КП отправьте в одном сообщении номер КП, а в следующем сообщении шифр КП
* `/finish` - завершение соревнования, подсчёт результатов. При случайном нажатии, можно продолжать игру дальше, и при завершении повторно отправить команду `/finish`.

## Инструкция администратора
<В разработке>
