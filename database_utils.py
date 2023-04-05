import os
import sqlite3
import weaviate

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


def sqlite3_load_all_paper_from():
    sql_conn = sqlite3.connect(os.environ['SQLITE3_DB_PATH'])
    paper_list = sql_conn.execute('SELECT * FROM paper').fetchall()
    sql_conn.close()
    return paper_list

# print('pid | arxivID | meta_info_json_path | pdf_path | tex_path | chunk_text_json_path | num_chunk')
# for x in sqlite3_load_all_paper_from():
#     print(*x)


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

Weaviate_Paper_schema = {
    "class": "Paper",
    "description": "A collection of arxiv paper",
    "vectorizer": "text2vec-openai",
    "moduleConfig": {
        "text2vec-openai": {
          "model": "ada",
          "modelVersion": "002",
          "type": "text"
        }
    },
    "properties": [{
        "name": "chunk",
        "description": "chunk contents of the paper",
        "dataType": ["text"]
    },
    {
        "name": "arxiv_id",
        "description": "arxiv ID",
        "dataType": ["string"],
        "moduleConfig": { "text2vec-openai": { "skip": True } }
    },
    {
        "name": "num_chunk",
        "description": "total number of chunk",
        "dataType": ["int"],
        "moduleConfig": { "text2vec-openai": { "skip": True } }
    },
    {
        "name": "index",
        "description": "index of the chunk",
        "dataType": ["int"],
        "moduleConfig": { "text2vec-openai": { "skip": True } }
    }]
}


def init_vector_database():
    tmp0 = weaviate.auth.AuthApiKey(os.environ['WEAVIATE_API_KEY'])
    client = weaviate.Client(url=os.environ['WEAVIATE_API_URL'], auth_client_secret=tmp0)
    if 'Paper' not in {x['class'] for x in client.schema.get()['classes']}:
        client.schema.create_class(Weaviate_Paper_schema)
        # client.schema.delete_class('Paper')
