import os
import json
import requests
from tqdm import tqdm
import openai
import openai.embeddings_utils
import numpy as np

from .database_utils import sqlite3_load_all_paper_from, vector_database_find_close_chunk
from .crawl_utils import crawl_one_arxiv_paper

# caller's duty to set openai.api_key
class NaiveChatGPT:
    def __init__(self) -> None:
        self.message_list = [{"role": "system", "content": "You are a helpful assistant."},]
        self.response = None #for debug only

    def reset(self):
        self.message_list = self.message_list[:1]

    def chat(self, message='', tag_print=True, tag_return=False):
        message = str(message)
        if message: #skip if empty
            self.message_list.append({"role": "user", "content": str(message)})
            self.response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=self.message_list)
            tmp0 = self.response.choices[0].message.content
            self.message_list.append({"role": "assistant", "content": tmp0})
            if tag_print:
                print(tmp0)
            if tag_return:
                return tmp0


class ContextChatGPT:
    def __init__(self):
        self.message_list = [{"role": "system", "content": "You are a helpful assistant. Answer the question based on the context below, "
                              "and if the question can't be answered based on the context, say \"I don't know\""},]
        self.response = None

    def reset(self):
        self.message_list = self.message_list[:1]

    def set_context(self, context, use_gpt_reply=False):
        tmp0 = '\nAbove is some context, no need to reply and just acknowledge it with "..."'
        self.message_list.append({'role':'user', 'content': context+tmp0})
        if use_gpt_reply:
            self.response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=self.message_list)
            tmp0 = self.response.choices[0].message.content
            self.message_list.append({"role": "assistant", "content": tmp0})
        else:
            self.message_list.append({"role": "assistant", "content": '...'})

    def chat(self, message, tag_print=True, tag_return=False):
        message = str(message)
        if message: #skip if empty
            self.message_list.append({"role": "user", "content": str(message)})
            self.response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=self.message_list)
            tmp0 = self.response.choices[0].message.content
            self.message_list.append({"role": "assistant", "content": tmp0})
            if tag_print:
                print(tmp0)
            if tag_return:
                return tmp0


class ArxivChatGPT:
    def __init__(self, use_local_npy=False):
        self.message_list = [{"role": "system", "content": "You are a helpful assistant. Answer the question based on the context below, "
                              "and if the question can't be answered based on the context, say \"I don't know\""},]
        self.response = None

        self._db_paper_list = sqlite3_load_all_paper_from()
        self.arxivID_list = [x['arxivID'] for x in self._db_paper_list]

        self._db_paper_i = None
        self.use_local_npy = use_local_npy

    def add_arxiv_paper_to_db(self, arxivID):
        assert isinstance(arxivID, str)
        crawl_one_arxiv_paper(arxivID, tag_commit_sqlite3=True)
        self._db_paper_list = sqlite3_load_all_paper_from()
        self.arxivID_list = [x['arxivID'] for x in self._db_paper_list]

    def list_arxiv(self, num_print=-1):
        db_paper_list = self._db_paper_list
        if num_print>0:
            db_paper_list = db_paper_list[:num_print]
        for ind0,x in enumerate(db_paper_list):
            tmp0 = os.path.join(os.environ['ARXIV_DIRECTORY'], x['meta_info_json_path'])
            with open(tmp0, 'r') as f:
                meta_info = json.load(f)
            print(f'[{ind0}]', x['arxivID'], meta_info['title'])

    def select(self, index):
        if isinstance(index, str):
            arxivID = index
            if arxivID not in self.arxivID_list:
                print(f'Error: {arxivID} not in arxivID_list')
                return
            index = self.arxivID_list.index(arxivID)
        else:
            if (index<0) or (index>=len(self.arxivID_list)):
                print(f'Error: index {index} out of range [0, {len(self.arxivID_list)-1}]')
                return
        self._db_paper_i = self._db_paper_list[index]
        tmp0 = os.path.join(os.environ['ARXIV_DIRECTORY'], self._db_paper_i['meta_info_json_path'])
        with open(tmp0, 'r') as f:
            meta_info = json.load(f)
        for key,value in meta_info.items():
            print(f'[{key}]: {value}')
        self.reset()

    def reset(self):
        self.message_list = self.message_list[:1]

    def set_context(self, context, use_gpt_reply=False):
        tmp0 = '\nAbove is some context, no need to reply and just acknowledge it with "..."'
        self.message_list.append({'role':'user', 'content': context+tmp0})
        if use_gpt_reply:
            self.response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=self.message_list)
            tmp0 = self.response.choices[0].message.content
            self.message_list.append({"role": "assistant", "content": tmp0})
        else:
            self.message_list.append({"role": "assistant", "content": '...'})

    def _find_related_chunk(self, message):
        max_context_len = int(os.environ['ARXIVGPT_MAX_TOKEN_PER_QA'])
        if self.use_local_npy:
            q_embedding = openai.Embedding.create(input=message, engine='text-embedding-ada-002')['data'][0]['embedding']
            tmp0 = os.path.join(os.environ['ARXIV_DIRECTORY'], self._db_paper_i['chunk_text_json_path'])
            assert os.path.exists(tmp0)
            with open(tmp0, 'r') as fid:
                chunk_text_list = json.load(fid)
                chunk_text_len_list = np.array([x[1] for x in chunk_text_list])
                chunk_text_str_list = [x[0] for x in chunk_text_list]
            tmp0 = os.path.join(os.environ['ARXIV_DIRECTORY'], self._db_paper_i['arxivID'], 'chunk-vector.npy')
            assert os.path.exists(tmp0)
            embedding_np = np.load(tmp0)
            distance = np.array(openai.embeddings_utils.distances_from_embeddings(q_embedding, embedding_np, distance_metric='cosine')) # 0: cloest
            ind0 = np.argsort(distance)
            tmp0 = np.nonzero((chunk_text_len_list[ind0] + 4).cumsum() > max_context_len)[0].min()
            context_text_list = [chunk_text_str_list[x] for x in ind0[:tmp0]]
        else:
            context_text_list = vector_database_find_close_chunk(self._db_paper_i['arxivID'], message, max_context_len)
        for x in context_text_list:
            self.set_context(x, use_gpt_reply=False)

    def chat(self, message, tag_reset=True, tag_print=True, tag_return=False):
        assert self._db_paper_i is not None
        if tag_reset:
            self.reset()
        message = str(message)
        if message: #skip if empty
            self._find_related_chunk(message)
            self.message_list.append({"role": "user", "content": str(message)})
            self.response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=self.message_list)
            tmp0 = self.response.choices[0].message.content
            self.message_list.append({"role": "assistant", "content": tmp0})
            if tag_print:
                print(tmp0)
            if tag_return:
                return tmp0
