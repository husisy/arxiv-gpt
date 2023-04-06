import os
import dotenv
import openai

from gpt_utils import ArxivChatGPT

dotenv.load_dotenv()
openai.api_key = os.environ["OPENAI_API_KEY"]

if __name__=='__main__':
    chatgpt = ArxivChatGPT()
    chatgpt.list_arxiv(num_print=5)
    chatgpt.select(1)

    chatgpt.chat("What is the main contribution of this paper?")

    question = "What is the main contribution of this paper?"
    question = 'What is the key references of this paper?'
    question = 'To fully understand the content, can you list 5 necessary references to read?'
