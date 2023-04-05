import os
import dotenv

from database import init_sqlite3_database, crawl_arxiv_recent_paper

dotenv.load_dotenv()


if __name__=='__main__':
    init_sqlite3_database()
    crawl_arxiv_recent_paper()
