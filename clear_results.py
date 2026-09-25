import sqlite3
import bot_utils
import config


def drop_game_table():
    # Подключение к базе данных SQLite
    conn = sqlite3.connect(config.db_filename)
    cursor = conn.cursor()

    # Удаление таблицы результатов
    cursor.execute('''DROP TABLE IF EXISTS game''')
    # Удаление финишного времени
    cursor.execute("UPDATE users SET finish_time=NULL")
    conn.commit()
    conn.close()


print('Do you really want to delete all results? Type "yes" and press Enter.')
s = input()
if s.strip().lower() == 'yes':
    drop_game_table()
    bot_utils.create_tables() # Создаем пустую таблицу результатов
    print('Results were cleared. Press Enter to exit.')
    s = input()
print('Goodbye.')
