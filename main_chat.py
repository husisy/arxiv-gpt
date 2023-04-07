import os
import dotenv
import openai

from app.controller import ArxivChatGPT

dotenv.load_dotenv()
openai.api_key = os.environ["OPENAI_API_KEY"]

if __name__=='__main__':
    chatgpt = ArxivChatGPT()
    chatgpt.list_arxiv(num_print=5)
    chatgpt.select(2)

    # chatgpt.add_arxiv_paper_to_db('2209.10934')
    # chatgpt.select('2209.10934')

    chatgpt.chat("What is the main contribution of this paper?")

    question = "What is the main contribution of this paper?"
    question = 'What is the key references of this paper?'
    question = 'To fully understand the content, can you list 5 necessary references to read?'


# nohup autossh -NT -L 0.0.0.0:443:127.0.0.1:5001 zhangc@localhost > ~/autossh_443_to_5001.log 2>&1 &
