import os
import time
import pickle
import dotenv
import requests
from tqdm import tqdm
import lxml.etree
import tiktoken
import openai
import openai.embeddings_utils
import numpy as np

from utils import download_url_and_save, convert_pdf_to_text, _MY_REQUEST_HEADERS, NaiveChatGPT

dotenv.load_dotenv()
openai.api_key = os.environ["OPENAI_API_KEY"]

if not os.path.exists('data'):
    os.makedirs('data')

chatgpt = NaiveChatGPT()

def get_arxiv_recent_url_pdf():
    url = "https://arxiv.org/list/quant-ph/recent"
    response = requests.get(url, headers=_MY_REQUEST_HEADERS)
    response.raise_for_status()
    z0 = lxml.etree.HTML(response.content)
    ret = ['https://arxiv.org'+str(x) for x in z0.xpath('//a[@title="Download PDF"]/@href')]
    # TODO title author abstract
    return ret

def download_arxiv_pdf(url_pdf_list, directory='data'):
    # TODO download and read from tex file
    for url_i in url_pdf_list:
        print(url_i)
        filename = url_i.rsplit('/',1)[1] + '.pdf'
        filepath = os.path.join(directory, filename)
        if not os.path.exists(filepath):
            download_url_and_save(url_i, filename=filename, directory=directory, headers=_MY_REQUEST_HEADERS)
            time.sleep(3) #sleep 3 seconds to avoid being banned
        else:
            print(f'{filename} already downloaded, skip it')


def split_text_into_chunks(text, max_token, tokenizer):
    sentence_list = text.split('. ')
    num_token_list = [len(tokenizer.encode(" " + x)) for x in sentence_list]
    ret = []
    num_token_current = 0
    chunk = []
    for sentence, num_token in zip(sentence_list, num_token_list):
        if num_token_current + num_token > max_token:
            ret.append(". ".join(chunk) + ".")
            chunk = []
            num_token_current = 0
        if num_token > max_token: #TODO possible loss information here
            continue
        chunk.append(sentence)
        num_token_current = num_token_current + num_token + 1
    ret = [(x,len(tokenizer.encode(x))) for x in ret]
    return ret


def get_arxiv_text_embedding(txt_file, max_tokens=None, tokenizer=None):
    # (ret0) chunked_text_list (list,tuple(text:str, num_token:int))
    # (ret1) embedding_np (np.float64, (N,1536))
    assert txt_file.endswith('.txt')
    pkl_file = txt_file[:-4] + '.pkl'
    if os.path.exists(pkl_file):
        with open(pkl_file, 'rb') as fid:
            tmp0 = pickle.load(fid)
            chunked_list = tmp0['chunked_list']
            embedding_np = tmp0['embedding_np']
    else:
        assert max_tokens is not None
        with open(txt_file, 'r', encoding='utf-8') as fid:
            text = fid.read()
        chunked_list = split_text_into_chunks(text, max_tokens, tokenizer)
        embbeding_list = []
        # TODO rate limiting
        # https://platform.openai.com/docs/guides/rate-limits/what-are-the-rate-limits-for-our-api
        for x,_ in tqdm(chunked_list):
            time.sleep(2.5) #make sure not exceed 20 requests per minutes
            tmp0 = np.array(openai.Embedding.create(input=x, engine='text-embedding-ada-002')['data'][0]['embedding'], dtype=np.float64)
            embbeding_list.append(tmp0)
        embedding_np = np.stack(embbeding_list, axis=0)
        with open(pkl_file, 'wb') as fid:
            tmp0 = dict(chunked_list=chunked_list, embedding_np=embedding_np)
            pickle.dump(tmp0, fid)
    return chunked_list, embedding_np


_openai_qa_template = ("Answer the question based on the context below, and if the question can't be answered based on the context, "
            "say \"I don't know\"\n\nContext: {context}\n\n---\n\nQuestion: {question}\nAnswer:")

def answer_question(question, text_list, embedding_np, max_context_len=1800, tag_print_context=False):
    """
    Answer a question based on the most similar context from the dataframe texts
    text_list(list, tuple(text:str, num_token:int))
    TODO response_max_tokens=150
    """
    assert all(len(x)==2 for x in text_list)
    assert len(text_list) == embedding_np.shape[0]
    text_len_list = np.array([x[1] for x in text_list])
    text_str_list = [x[0] for x in text_list]

    q_embedding = openai.Embedding.create(input=question, engine='text-embedding-ada-002')['data'][0]['embedding']
    distance = np.array(openai.embeddings_utils.distances_from_embeddings(q_embedding, embedding_np, distance_metric='cosine')) # 0: cloest
    ind0 = np.argsort(distance)
    tmp0 = np.nonzero((text_len_list[ind0] + 4).cumsum() > max_context_len)[0].min()
    context_text_list = [text_str_list[x] for x in ind0[:tmp0]]
    context_text = "\n\n###\n\n".join(context_text_list)
    if tag_print_context:
        print(f"Context:\n{context_text}\n\n")
    prompt = _openai_qa_template.format(context=context_text, question=question)
    try:
        chatgpt.reset()
        ret = chatgpt.chat(prompt, tag_print=False, tag_return=True)
    except Exception as e:
        print(e)
        ret = ""
    return ret



url_i = 'https://arxiv.org/pdf/2209.10934'

url_pdf_list = get_arxiv_recent_url_pdf()
download_arxiv_pdf(url_pdf_list)

pdf_file_list = [os.path.join('data',x) for x in os.listdir('data') if x.endswith('.pdf')]
convert_pdf_to_text(pdf_file_list)


tokenizer = tiktoken.get_encoding("cl100k_base")
max_token_per_chunk = 300

txt_file_list = [os.path.join('data',x) for x in os.listdir('data') if x.endswith('.txt')]

txt_file = 'data/2209.10934.txt'
chunked_list, embedding_np = get_arxiv_text_embedding(txt_file, max_token_per_chunk, tokenizer)

question = "What is the main contribution of this paper?"
question = 'What is the key references of this paper?'
question = 'To fully understand the content, can you list 5 necessary references to read?'
answer = answer_question(question, chunked_list, embedding_np, tag_print_context=True)
print(answer)
