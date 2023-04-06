import os
import math
import sqlite3
import weaviate
import numpy as np

from utils import _MY_REQUEST_HEADERS, download_url_and_save


def sqlite_insert_paper_list(paper_list):
    paper_dict = {x['arxivID']:x for x in paper_list} #remove duplicate arxivID
    sql_conn = sqlite3.connect(os.environ['SQLITE3_DB_PATH'])
    for arxivID, x in paper_dict.items():
        sql_conn.execute('DELETE FROM paper WHERE arxivID = ?', (arxivID,)) #remove old first
        # sql_conn.execute('SELECT * FROM paper').fetchall()
    tmp0 = 'arxivID meta_info_json_path pdf_path tex_path chunk_text_json_path num_chunk'.split(' ')
    tmp1 = [tuple(x[y] for y in tmp0) for x in paper_dict.values()]
    tmp2 = ",".join(tmp0)
    sql_conn.executemany(f'INSERT INTO paper ({tmp2}) VALUES (?,?,?,?,?,?)', tmp1)
    sql_conn.commit()
    sql_conn.close()


def sqlite3_load_all_paper_from():
    sql_conn = sqlite3.connect(os.environ['SQLITE3_DB_PATH'])
    paper_list = sql_conn.execute('SELECT * FROM paper').fetchall()
    sql_conn.close()
    tmp0 = 'pid arxivID meta_info_json_path pdf_path tex_path chunk_text_json_path num_chunk'.split(' ')
    ret = [{y0:y1 for y0,y1 in zip(tmp0,x)} for x in paper_list]
    return ret

# print('pid | arxivID | meta_info_json_path | pdf_path | tex_path | chunk_text_json_path | num_chunk')
# for x in sqlite3_load_all_paper_from():
#     print(x)


def init_sqlite3_database(remove_if_exist=False):
    sql_conn = sqlite3.connect(os.environ['SQLITE3_DB_PATH'])
    if remove_if_exist:
        sql_conn.execute('DROP TABLE IF EXISTS paper')
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
    sql_conn.commit()
    sql_conn.close()

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
        "name": "num_token",
        "description": "number of token",
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


def init_vector_database(remove_if_exist=False):
    client = _get_vector_database(with_openai_api_key=False)
    tag_exist = 'Paper' in {x['class'] for x in client.schema.get()['classes']}
    if remove_if_exist and tag_exist:
        client.schema.delete_class('Paper')
        tag_exist = False
    if not tag_exist:
        client.schema.create_class(Weaviate_Paper_schema)


'''
chunk: text
arxiv_id: string
index: int
num_token: int
num_chunk: int
vector (ada-002)
'''


def _get_vector_database(with_openai_api_key):
    tmp0 = weaviate.auth.AuthApiKey(os.environ['WEAVIATE_API_KEY'])
    if with_openai_api_key:
        tmp1 = {"X-OpenAI-Api-Key": os.environ['OPENAI_API_KEY']} #optional
    else:
        tmp1 = None
    client = weaviate.Client(url=os.environ['WEAVIATE_API_URL'], auth_client_secret=tmp0, additional_headers=tmp1)
    return client


def vector_database_insert_paper(arxivID, text_chunk_list, vector_list=None):
    # text_chunk_list(list,tuple(str,int))
    client = _get_vector_database(with_openai_api_key=True)
    num_chunk = len(text_chunk_list)
    uuid_list = []
    if vector_list is not None:
        assert len(vector_list)==num_chunk
    with client.batch as batch:
        batch.batch_size = 20 #20-100
        # https://github.com/openai/openai-cookbook/tree/main/examples/vector_databases/weaviate
        # client.batch.configure(batch_size=10,  dynamic=True, timeout_retries=3)
        for ind0 in range(num_chunk):
            tmp0 = dict(arxiv_id=arxivID, num_chunk=num_chunk, index=ind0, chunk=text_chunk_list[ind0][0], num_token=text_chunk_list[ind0][1])
            tmp1 = vector_list[ind0] if vector_list is not None else None
            uuid_list.append(batch.add_data_object(tmp0, class_name='Paper', vector=tmp1))
    return uuid_list


def vector_database_contains_paper(arxivID:str):
    client = _get_vector_database(with_openai_api_key=False)
    tmp0 = {"path": ["arxiv_id"], "operator": "Equal", "valueString": arxivID}
    num_chunk = client.query.aggregate("Paper").with_fields("meta {count}").with_where(tmp0).do()['data']['Aggregate']['Paper'][0]['meta']['count']
    return num_chunk>0

# TODO remove comment
def vector_database_retrieve_paper(arxivID:str, index=None):
    client = _get_vector_database(with_openai_api_key=False)
    # TODO handle error
    if index is None:
        tmp0 = {"path": ["arxiv_id"], "operator": "Equal", "valueString": arxivID}
        num_chunk = client.query.aggregate("Paper").with_fields("meta {count}").with_where(tmp0).do()['data']['Aggregate']['Paper'][0]['meta']['count']
        assert num_chunk>0
        # TODO batch_size=100
        response = client.query.get("Paper", ["chunk", "index"]).with_where(tmp0).with_limit(num_chunk).do()
        tmp1 = sorted(response['data']['Get']['Paper'], key=lambda x:x['index'])
        assert tuple(x['index'] for x in tmp1)==tuple(range(num_chunk))
        text_chunk_list = [x['chunk'] for x in tmp1]
        # vector_np = np.zeros((1, 1536), dtype=np.float64)
        ret = text_chunk_list
    else:
        raise NotImplementedError
        # tmp0 = {"path": ["arxiv_id"], "operator": "Equal", "valueString": arxivID}
        # text_chunk = ''
        # vector_np = np.zeros(1536, dtype=np.float64)
        # return text_chunk, vector_np
    return ret


def vector_database_find_close_chunk(arxivID, message, max_context_len):
    client = _get_vector_database(with_openai_api_key=True)
    nearText = {"concepts": [message]}
    tmp0 = {"path": ["arxiv_id"], "operator": "Equal", "valueString": arxivID}
    result = client.query.get("Paper", ["chunk", "num_token"]).with_near_text(nearText).with_where(tmp0).with_additional(['certainty']).with_limit(6).do()
    certainty = [x['_additional']['certainty'] for x in result['data']['Get']['Paper']] #in descending order
    num_token_list = np.array([x['num_token'] for x in result['data']['Get']['Paper']])
    chunk_text_str_list = [x['chunk'] for x in result['data']['Get']['Paper']]
    tmp0 = np.nonzero((num_token_list + 4).cumsum() > max_context_len)[0].min()
    ret = chunk_text_str_list[:tmp0]
    return ret
