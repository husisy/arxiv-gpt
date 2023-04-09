# https://arxiv.org/list/cs.PF/recent
# https://arxiv.org/list/quant-ph/recent
import os
import datetime
import time
import sqlite3
import dotenv
import openai

import crawl_arxiv

dotenv.load_dotenv()
openai.api_key = os.environ["OPENAI_API_KEY"]

# sqlite3 PaperParseQueue table


def insert_only_user():
    from werkzeug.security import generate_password_hash
    sql_conn = sqlite3.connect(os.environ['SQLITE3_DB_PATH'])
    tmp0 = os.environ['ONLY_USER_NAME'], 'xxx@email.com', generate_password_hash(os.environ['ONLY_USER_PASS'])
    sql_conn.execute('INSERT INTO User (username,email,password_hash) VALUES (?,?,?)', tmp0)


if __name__=='__main__':
    # TODO make it a crontab (run every day)
    # crawl_arxiv_recent_paper()
    # _update_existing_arxiv_data()

    recent_url_list = ['https://arxiv.org/list/quant-ph/recent']
    arxivID_time_list = []
    last_query_time = None
    num_paper_limit_one_day = int(os.environ['CRAWL_ONE_DAY_LIMIT'])
    sql_conn = sqlite3.connect(os.environ['SQLITE3_DB_PATH'])
    while True:
        if (last_query_time is None) or (datetime.datetime.now()-last_query_time).days >= 1:
            last_query_time = datetime.datetime.now()
            for url in recent_url_list:
                crawl_arxiv.crawl.crawl_arxiv_recent_paper(url)

        time.sleep(10) #query every 10 seconds
        arxiv_list = [x[0] for x in sql_conn.execute('SELECT arxivID FROM paper_parse_queue').fetchall()]

        sql_conn.execute('DELETE FROM paper_parse_queue')
        for x in arxiv_list:
            sql_conn.execute('DELETE FROM paper_parse_queue WHERE arxivID = ?', (x,))
        sql_conn.commit()

        tmp0 = [sql_conn.execute('SELECT arxivID FROM paper WHERE arxivID = ?', (x,)).fetchone() for x in arxiv_list]
        existed_list = [x[0] for x in tmp0 if x is not None]
        arxiv_list = list(set(arxiv_list) - set(existed_list))

        if len(arxiv_list)>0:
            for arxivID in arxiv_list:
                arxivID_time_list = [x for x in arxivID_time_list if (datetime.datetime.now() - x[1]).days < 1]
                if len(arxivID_time_list)>num_paper_limit_one_day:
                    print(f'Limit reached: {len(arxivID_time_list)}')
                    tmp0 = max(1, 60*60*24 - (datetime.datetime.now()-arxivID_time_list[0][1]).total_seconds())
                    time.sleep(tmp0)
                tmp0 = crawl_arxiv.crawl.crawl_one_arxiv_paper(arxivID, tag_commit_sqlite3=True)
                arxivID_time_list.append((arxivID, datetime.datetime.now()))
    sql_conn.close()
