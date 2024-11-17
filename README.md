# Телеграм бот для рогейна.
Это скрипт telegram бота, предназначенный для фиксации результатов участников соревнований по рогейну.

Участники находят КП (контрольные пункты) у которых есть номер и шифр, и отправляют номер и шифр боту. Если, присланный участником шифр совпадает с правильным ответом, то этот КП считается взятым участником и участник получает за него баллы. Бот фиксирует взятие КП каждым участником(командой) и ведёт подсчёт общего количества баллов каждого участника. На финише участник отправляет боту завершающую команду и бот фиксирует время финиша и результат участника в баллах. При отсутствии связи на дистанции клиент telegram накапливает сообщения пользователя и при появлении связи они будут переданны боту.

* Номер - **всегда** двух или трёхзначное число, в котором сотни и десятки - это стоимость КП в баллах, например КП 35 - стоит три балла, КП 108 - десять баллов.
* Шифр - произвольная строка текста, содержащяя хотябы одну букву, при сравнении шифра с правильным ответом бот удаляет пробелы в начале и конце строки, регистр символов не имеет значения. Проверка шифра происходит посимвольно, например шифр **K2** с латинской буквой k и **К2** с русской к, это разные шифры, стоит иметь это в виду при составлении шифров.

## Установка и запуск бота
* создать бота в telegram, создать боту меню с командой `/finish`, запомнить ключ бота
* нужен компьютер с стабильным доступом в интернет (лучше сервер)
* установить python
* установить библиотеку проекта telebot
* скачать последний релиз этого проекта `rogaine_tg_bot`
* распаковать архив
* прописать в файл `confg.py` токен вашего бота:
```
# Секретный токен вашего телеграм бота
bot_token = 'сюда нужно вставить токен'
```
* выполнить `python main.py` или запустить `start.bat` (для Windows)
* бот запустится, в консоли вы увидите сообщение:
```
----------------------------
-   ROGAINE TELEGRAM BOT   -
-     STARTED v0.4         -
-  13:34:15 - 2024/11/17   -
----------------------------
```

## Инструкция участника
* `/start` - начало работы с ботом, приветствие, регистрация и проверка
* Для отметки КП отправьте в одном сообщении номер КП, а в следующем сообщении шифр КП
* `/finish` - завершение соревнования, подсчёт результатов. При случайном нажатии, можно продолжать игру дальше, и при завершении повторно отправить команду `/finish`.
* Для использования тестовой точки и финишной точки следовать инструкциям организатора

## Инструкция администратора
Настройки бота выполняются через файл `config.py`. После изменения файла, сохраните файл и перезапустите бота.
#### Тестовый КП
Для обучения пользователей работе с ботом рекомендуется в список КП добавить специальный тестовый КП, который разместить на старте. Чтобы назначить одно из КП тестовым, нужно прописать КП и шифр в список и в настройке `test_cp` указать его номер, вот так: `test_cp = 99`. Ввод номера и шифра тестового КП пользователем происходит так-же, как и для обычного КП, но это КП **не учитывается в результате**.
#### Тестовый КП с вводом названия команды
Если настройка `test_command_name_mode` установлена в значение `True`, то в ответ на тестовую точку от пользователя принимается любая строка, которая сохраняется как название команды.
#### Финишный КП
Номер финишного КП указывается в настройке `fin_cp`. При взятии финишного КП пользователь завершает игру(автоматически выполняется команда `/finish`). Финишное КП учитывается в результате. Если нужно. чтобы не учитывалось, то выберите номер КП меньше 10, например `fin_cp = 7`.


