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
-     STARTED v0.9         -
-  13:34:15 - 2024/12/22   -
----------------------------
```
#### Установка и запуск в ОС Windows 10


## Инструкция участника
* `/start` - начало работы с ботом, приветствие.
* Для взятия КП отправьте в одном сообщении номер КП, а в следующем сообщении шифр КП.
* Если вы считаете что КП сорван, отправьте вместо шифра слово `сорван`, КП будет зафиксирован в вашем списке как сорванный и организатор на финише проведёт проверку. Если вы ошибочно пометили КП сорванным, вы можете взять КП, введя шифр.
* `/finish` - завершение соревнования, подсчёт результатов. При случайном нажатии, можно продолжать игру дальше, и при завершении повторно отправить команду `/finish`.
* Для использования тестовой точки и финишной точки следовать инструкциям организатора

## Инструкция администратора
### Команды администратора
Администраторы, чьи telegram id указанны в конфигурации, имеют право отправлять боту дополнительные команды:
* `/admin` - вывод полного списка пользователей с полной информацией и сортировкой по финишному времени и названию команды
* `/a` - вывод списка пользователей, которые взяли хоть один КП в сокращённом виде
* `/non` - вывод списка пользователей, которые не задали имея команды в полном виде
* `/nof` - вывод списка нефинишировавших пользователей, которые не задали имея команды в полном виде
* `/log` - вывод последовательности взятых и сорванных КП, в формате `<номер записи>) <номер КП> <название команды>`, например `1) 11 Кукушка`. КП, которые были помечены сорванными, отображаются зачёркнутым шрифтом. Последовательность записей не изменяется со временем, например если пользователь сначала пометил КП сорванным, а через некоторое время ввёл корректный шифр, то запись о КП останется на своём месте в списке, но КП будет отображен, как взятый.  

### Настройки бота
Настройки бота выполняются через файл `config.py`. После изменения файла, сохраните файл и перезапустите бота.
#### Секретный токен вашего телеграм бота
`bot_token = '...'` Вместо трёх точек в этой настройке вы должны вставить токен вашего бота телеграм.
#### Имя файла с БД 
`db_filename = 'rogaine_tg_bot_data.db'` - файл с таким именем будет создан после запуска бота, в нём будут храниться все данные игры
#### Имя файла с результатами
`results_filename = 'results.csv'` - файл с таким именем будет создан при экспорте
#### Контакт организатора
`bot_message_org = '@IvanovIvanIvanovich'`
#### Тестовый КП
Для обучения пользователей работе с ботом рекомендуется в список КП добавить специальный тестовый КП, который разместить на старте. Чтобы назначить один из КП тестовым, нужно прописать КП и шифр в общий список, затем в настройке `test_cp` указать его номер, вот так: `test_cp = 99`. Ввод номера и шифра тестового КП пользователем происходит так-же, как и для обычного КП, но это КП **не учитывается в результате**.
#### Тестовый КП с вводом названия команды
Если настройка `test_command_name_mode` установлена в значение `True`, то в ответ на тестовую точку от пользователя принимается любая строка, которая сохраняется как название команды, если же для этой настройки указано значение `False`, то тестовый КП работает как описано в пункте выше.
#### Финишный КП
Номер финишного КП указывается в настройке `fin_cp`. При взятии финишного КП пользователь завершает игру(автоматически выполняется команда `/finish`). Финишный КП учитывается в результате. Если нужно, чтобы не учитывался, то выберите номер КП меньше 10, например `fin_cp = 7`.
#### Специальные слова, для пометки КП отсутствующим/сорванным (обязательно в нижнем регистре).
`no_cp_words = ('сорван', 'сорвано')` При вводе пользователем одного из этих слов - КП записывается в списке взятых пользователем, как сорванное. Позже пользователь имеет возможность взять КП, если введёт правильный шифр. Слова указанные в этой настройке не могут быть использованы как шифры для КП.
#### Список id пользователей Телеграм, которые могут управлять ботом (админы)
`admin_id = (987654321, 1234567899)` В этой настройке нужно перечислить всех пользователей которые имеют право отправлять команды для получения результатов.

#### Ошибки
Файл конфигурации бота - это код на языке Python, при правке файла нужно соблюдать правила языка, например числа не должны начинаться с 0, `fin_cp = 7` - правильно, `fin_cp = 07` - вызовет ошибку при запуске бота. Если при запуске бота возникнет ошибка, то в консоли вы увидите номер строки в файлах кода, которые связаны с ошибкой, если ошибка появилась после правки файла конфига, ищите в тексте ошибки упоминание файла config.py и номер строки в нём.
* `ConnectionError` или что-то про `Timeout` - скорее всего у вас нет доступа к интернету или серверу Telegram.
* `A request to the Telegram API was unsuccessful. Error code: 401. Description: Unauthorized` - у вас ошибка в токене
