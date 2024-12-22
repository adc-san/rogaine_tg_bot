import csv
import sqlite3

import bot_utils
import config


# Функция, обрабатывающая отладочную команду /admin
def save_to_csv():
    with open(config.results_filename, 'w', newline='') as csvfile:
        results_writer = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        conn = sqlite3.connect(config.db_filename)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        user_list = cursor.fetchall()
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
                # Записываем строку результатов в CSV, убрав запятые из данных
                results_writer.writerow([command_name.replace(',','.').encode('cp1251', errors='replace').decode('cp1251'), user_str.replace(',','.').encode('cp1251', errors='replace').decode('cp1251')] +
                                        ';'.join(no_cp_list.split(sep=',')).split(sep=' ') + [fin_time,] + all_cp_list.split(sep=','))

print('I will save your results to {} ...'.format(config.results_filename))
save_to_csv()
print('Results were saved. Press Enter to exit.')
s = input()
print('Goodbye.')
