import os
import dotenv

from database_utils import init_sqlite3_database

from crawl_utils import crawl_arxiv_recent_paper

dotenv.load_dotenv()


if __name__=='__main__':
    init_sqlite3_database()
    crawl_arxiv_recent_paper()
