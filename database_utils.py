import os
import sqlite3

from utils import _MY_REQUEST_HEADERS, download_url_and_save


def sqlite_insert_paper_list(paper_list):
    assert all(len(x)==6 for x in paper_list)
    paper_dict = dict()
    for x in paper_list:
        arxivID = x[0]
        paper_dict[arxivID] = x #remove duplicate arxivID
    sql_conn = sqlite3.connect(os.environ['SQLITE3_DB_PATH'])
    for arxivID, x in paper_dict.items():
        sql_conn.execute('DELETE FROM paper WHERE arxivID = ?', (arxivID,)) #remove old first
        # sql_conn.execute('SELECT * FROM paper').fetchall()
    tmp0 = '(arxivID,meta_info_json_path,pdf_path,tex_path,chunk_text_json_path,num_chunk)'
    sql_conn.executemany(f'INSERT INTO paper {tmp0} VALUES (?,?,?,?,?,?)', list(paper_dict.values()))
    sql_conn.commit()
    sql_conn.close()


def init_sqlite3_database():
    sql_conn = sqlite3.connect(os.environ['SQLITE3_DB_PATH'])
    cmd = '''create table if not exists paper (
        pid integer primary key,
        arxivID text,
        meta_info_json_path text,
        pdf_path text,
        tex_path text,
        chunk_text_json_path text,
        num_chunk integer
    )
    '''
    sql_conn.execute(cmd)
