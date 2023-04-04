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


# TODO make a cache
# https://stackoverflow.com/a/93029/7290857
tmp0 = (chr(i) for i in range(sys.maxunicode)) #all character
tmp1 = ''.join(c for c in tmp0 if (unicodedata.category(c)=='Cc') and c not in '\t\n') #all control character
_CONTROL_CHAR_RE = re.compile('[%s]' % re.escape(tmp1))
_REMOVE_BEGIN_ARXIV_RE = re.compile("$(.?\n)+", flags=re.MULTILINE)
_REMOVE_CONNECTING_RE = re.compile('-\n', flags=re.MULTILINE)
_REMOVE_LATEXIT_RE = re.compile('latexit(.*)/latexit', flags=re.MULTILINE)
_REMOVE_NEWLINE_RE = re.compile('(\S)\n(\S)', flags=re.MULTILINE)
_MISC00_RE = re.compile('ﬀ')


def convert_pdf_to_text(pdf_path_list):
    # TODO see github/chatpaper how to cleanup pdf
    for pdf_path in pdf_path_list:
        assert pdf_path.endswith('.pdf')
        text_path = pdf_path[:-4] + '.txt'
        if os.path.exists(text_path):
            print(f'{text_path} already exists, skip it')
        else:
            print(f'processing {pdf_path}')
            with open(pdf_path, 'rb') as fid:
                text_ori = pdfminer.high_level.extract_text(fid)
            text0 = _CONTROL_CHAR_RE.sub('', text_ori)
            text1 = _REMOVE_BEGIN_ARXIV_RE.sub('', text0, count=1)
            text2 = _REMOVE_LATEXIT_RE.sub('', text1)

            text3 = _REMOVE_CONNECTING_RE.sub('', text2)
            text4 = _REMOVE_NEWLINE_RE.sub(r'\1 \2', text3)
            text4 = _REMOVE_NEWLINE_RE.sub(r'\1 \2', text4) #sometimes we need do this several time
            text5 = _MISC00_RE.sub('ff', text4)
            with open(text_path, 'w', encoding='utf-8') as fid:
                fid.write(text5)


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
