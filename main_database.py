import os
import dotenv
import openai

from database_utils import init_sqlite3_database, sqlite3_load_all_paper_from, init_vector_database

from crawl_utils import crawl_arxiv_recent_paper, remove_all_intermidiate_data_in_arxiv, _update_existing_arxiv_data

from gpt_utils import NaiveChatGPT, ContextChatGPT, ArxivChatGPT

dotenv.load_dotenv()
openai.api_key = os.environ["OPENAI_API_KEY"]


if __name__=='__main__':
    init_sqlite3_database()
    init_vector_database()

    # TODO make it a crontab (run every day)
    crawl_arxiv_recent_paper()
    # _update_existing_arxiv_data()
