import os
import re
import sys
import unicodedata
import requests
from tqdm import tqdm
import pdfminer.high_level
import openai

_MY_REQUEST_HEADERS = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'}


def download_url_and_save(url, filename=None, directory='.', headers=None, proxies=None):
    assert os.path.exists(directory)
    response = requests.get(url, headers=headers, proxies=proxies, stream=True)
    response.raise_for_status()
    if filename is None:
        filepath = os.path.join(directory, url.rsplit('/',1)[1])
    else:
        filepath = os.path.join(directory, filename)
    if not os.path.exists(filepath):
        tmp_filepath = filepath + '.incomplete'
        tmp0 = {'total':int(response.headers['content-length']), 'unit':'iB', 'unit_scale':True}
        with open(tmp_filepath, 'wb') as fid, tqdm(**tmp0) as progress_bar:
            for x in response.iter_content(chunk_size=1024): #1kiB
                progress_bar.update(len(x))
                fid.write(x)
        os.rename(tmp_filepath, filepath)
    return filepath


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
            raise NotImplementedError

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
