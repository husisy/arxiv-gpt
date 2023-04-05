import os
import dotenv

from database_utils import init_sqlite3_database, sqlite3_load_all_paper_from

from crawl_utils import crawl_arxiv_recent_paper, remove_all_intermidiate_data_in_arxiv

dotenv.load_dotenv()


if __name__=='__main__':
    init_sqlite3_database()
    crawl_arxiv_recent_paper()
