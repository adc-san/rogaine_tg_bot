import csv
from html import unescape
import os
from pathlib import Path
import sqlite3
import tempfile

import bot_utils
import config


# Сохраняем результаты, заменяя предыдущий файл только после успешной записи.
def save_to_csv():
    output_path = Path(config.results_filename)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', newline='', encoding='utf-8-sig',
                                         dir=output_path.parent, prefix=output_path.name + '.',
                                         suffix='.tmp', delete=False) as csvfile:
            temporary_path = csvfile.name
            results_writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            conn = sqlite3.connect(config.db_filename)
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users')
                user_list = cursor.fetchall()
            finally:
                conn.close()
            if len(user_list) > 0:
                results_writer.writerow(['Name', 'User', 'Problems','Fin time'] + ['CP'] * bot_utils.get_total_cp_count())
                for u in user_list:
                    user_id = u[0]
                    username = u[1]
                    first_name = u[2]
                    last_name = u[3]
                    command_name = u[4]
                    fin_time = u[5]
                    user_str = f"{first_name or ''} {last_name or ''} @{username or ''} id{str(user_id)}"
                    cp_count, cp_sum, cp_list, no_cp_list, all_cp_list = bot_utils.user_result(user_id)
                    # В БД текст экранирован для HTML; CSV экранирует csv.writer.
                    results_writer.writerow([unescape(command_name or ''), unescape(user_str)] +
                                            ';'.join(no_cp_list.split(sep=',')).split(sep=' ') + [fin_time,] + all_cp_list.split(sep=','))
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass

if __name__ == '__main__':
    print('I will save your results to {} ...'.format(config.results_filename))
    save_to_csv()
    print('Results were saved. Press Enter to exit.')
    s = input()
    print('Goodbye.')
