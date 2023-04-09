

import sqlite3


sql_conn0 = sqlite3.connect('arxiv.sqlite3.bak')

sql_conn0.execute("SELECT * FROM sqlite_master where type='table'").fetchall()

sql_conn0 = sqlite3.connect('/public_data/arxiv-gpt/arxiv.sqlite3')
sql_conn1 = sqlite3.connect('test.sqlite3')

sql_conn0.execute('SELECT * FROM paper').fetchall()

tmp0 = 'arxivID meta_info_json_path pdf_path tex_path chunk_text_json_path num_chunk'.split(' ')
tmp2 = ",".join(tmp0)

paper_list = [x[1:] for x in sql_conn0.execute(f'SELECT * FROM paper').fetchall()]
sql_conn1.executemany(f'INSERT INTO paper ({tmp2}) VALUES (?,?,?,?,?,?)', paper_list)

