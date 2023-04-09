import os
import re
import json
import shutil
import requests
import time
import numpy as np
import lxml.etree

from .utils import download_url_and_save, _MY_REQUEST_HEADERS
from .text import (extract_unknown_arxiv_file, try_except_make_main_tex_file,
            texpath_to_text_chunk, pdfpath_to_text_chunk, text_chunk_list_to_numpy_vector)
from .database import sqlite_insert_paper_list, vector_database_insert_paper, vector_database_contains_paper


def crawl_arxiv_meta_info(arxivID):
    url = 'https://arxiv.org/abs/' + arxivID
    response = requests.get(url, headers=_MY_REQUEST_HEADERS)
    response.raise_for_status()
    time.sleep(1) #sleep 1 seconds to avoid being banned
    html = lxml.etree.HTML(response.content)

    tmp0 = html.xpath('//div[@id="abs"]')
    assert len(tmp0)==1
    title = tmp0[0].xpath('./h1[@class="title mathjax"]/text()')[0]
    author_list = [str(x) for x in tmp0[0].xpath('./div[@class="authors"]/a/text()')]
    tmp1 = ''.join(tmp0[0].xpath('./blockquote[@class="abstract mathjax"]/text()')).strip()
    abstract = re.sub('\n', ' ', tmp1)
    tmp0 = ''.join(html.xpath('//td[@class="tablecell subjects"]/span/text()'))
    tmp1 = ''.join(html.xpath('//td[@class="tablecell subjects"]/text()'))
    subject = tmp0.strip() + tmp1.strip()
    pdf_url = 'https://arxiv.org' + str(html.xpath('//a[@class="abs-button download-pdf"]/@href')[0])
    tmp0 = html.xpath('//a[@class="abs-button download-format"]/@href')
    if len(tmp0)>0:
        assert str(tmp0[0]).startswith('/format')
        targz_url = 'https://arxiv.org/e-print' + str(tmp0[0][7:])
    else:
        targz_url = ''
    ret = {'title': title, 'author_list': author_list,'abstract': abstract, 'subject': subject, 'pdf_url': pdf_url, 'targz_url': targz_url}
    return ret


def crawl_one_arxiv_paper(arxivID, tag_commit_sqlite3=False):
    arxivID = str(arxivID).strip('/')
    url_abs = 'https://arxiv.org/abs/' + arxivID
    try:
        response = requests.get(url_abs, headers=_MY_REQUEST_HEADERS)
        response.raise_for_status()
        time.sleep(1) #sleep 1 seconds to avoid being banned
    except Exception as e:
        print(e)
        print(f'[Error][crawl_utils.py/crawl_one_arxiv_paper] fail to crawl url {url_abs}')
        response = None
    if response is not None:
        html = lxml.etree.HTML(response.content)
        hf_file = lambda *x: os.path.join(os.environ['ARXIV_DIRECTORY'], arxivID, *x)
        if not os.path.exists(hf_file()):
            os.makedirs(hf_file())
        pdf_path = hf_file('main.pdf')
        meta_info_json_path = hf_file('meta-info.json')
        targz_path = hf_file('main.tar.gz')
        tex_path = hf_file('main.tex')
        chunk_text_json_path = hf_file('chunk-text.json')
        vector_npy_path = hf_file('chunk-vector.npy')

        if not os.path.exists(meta_info_json_path):
            print(f'[{arxivID}] crawling meta information')
            meta_info = crawl_arxiv_meta_info(arxivID)
            with open(meta_info_json_path, 'w', encoding='utf-8') as fid:
                json.dump(meta_info, fid, ensure_ascii=False)
        else:
            with open(meta_info_json_path, 'r', encoding='utf-8') as fid:
                meta_info = json.load(fid)

        pdf_url = meta_info['pdf_url']
        if not os.path.exists(pdf_path):
            print(f'[{arxivID}] downloading {pdf_url}')
            download_url_and_save(pdf_url, filename=os.path.basename(pdf_path), directory=hf_file(), headers=_MY_REQUEST_HEADERS)
            time.sleep(3) #sleep 3 seconds to avoid being banned

        targz_url = meta_info['targz_url']
        if targz_url!='':
            if not os.path.exists(targz_path):
                print(f'[{arxivID}] downloading targz file "{targz_url}"')
                download_url_and_save(targz_url, filename=os.path.basename(targz_path), directory=hf_file(), headers=_MY_REQUEST_HEADERS)
                time.sleep(3)
            if not os.path.exists(tex_path):
                if not os.path.exists(hf_file('untar')):
                    print(f'[{arxivID}] extract targz file to untar folder')
                    os.makedirs(hf_file('untar'))
                    extract_unknown_arxiv_file(targz_path, hf_file('untar'))
                print(f'[{arxivID}] make main.tex')
                tex_text = try_except_make_main_tex_file(hf_file('untar'))
                if tex_text is not None:
                    with open(tex_path, 'w', encoding='utf-8') as fid:
                        fid.write(tex_text)
                shutil.rmtree(hf_file('untar'))

        if not os.path.exists(chunk_text_json_path):
            text_list = []
            if os.path.exists(tex_path):
                print(f'[{arxivID}] convert tex to chunk_text')
                try:
                    text_list = texpath_to_text_chunk(tex_path)
                except Exception as e:
                    print(e)
                    print(f'[Error][crawl_utils.py/crawl_one_arxiv_paper] fail to convert tex to chunk_text')
            if len(text_list)==0:
                print(f'[{arxivID}] convert pdf to chunk_text')
                text_list = pdfpath_to_text_chunk(pdf_path)
            with open(chunk_text_json_path, 'w', encoding='utf-8') as fid:
                json.dump(text_list, fid, ensure_ascii=False)
        else:
            with open(chunk_text_json_path, 'r', encoding='utf-8') as fid:
                text_list = json.load(fid)
        num_chunk = len(text_list)

        if os.path.exists(chunk_text_json_path):
            if (os.environ['ARXIVGPT_SAVE_NUMPY_VECTOR']=='1') and (not os.path.exists(vector_npy_path)):
                print(f'[{arxivID}] converting chunk_text to numpy vector')
                embedding_np = text_chunk_list_to_numpy_vector([x[0] for x in text_list])
                np.save(vector_npy_path, embedding_np)
            if vector_database_contains_paper(arxivID):
                print(f'[{arxivID}] vector_database already contains this paper')
            else:
                if os.path.exists(vector_npy_path):
                    embedding_np = np.load(vector_npy_path)
                    assert embedding_np.shape[0] == num_chunk
                else:
                    embedding_np = None
                print(f'[{arxivID}] inserting paper into vector database')
                uuid_list = vector_database_insert_paper(arxivID, text_list, embedding_np)
            # TODO should we save uuid_list to json file?

        ret = dict(arxivID=arxivID, num_chunk=num_chunk, meta_info_json_path=meta_info_json_path, pdf_path=pdf_path, tex_path=tex_path, chunk_text_json_path=chunk_text_json_path)
        for key in list(ret.keys()):
            if key.endswith('_path'):
                value = ret[key]
                if not os.path.exists(value):
                    value = ''
                assert value.startswith(os.environ['ARXIV_DIRECTORY']) or (value=='')
                ret[key] = value[len(os.environ['ARXIV_DIRECTORY']):].lstrip(os.sep)
        sqlite_insert_paper_list([ret])
    else:
        ret = None
    return ret

def crawl_arxiv_recent_paper(url):
    print(f'crawling {url}')
    response = requests.get(url, headers=_MY_REQUEST_HEADERS)
    response.raise_for_status()
    time.sleep(1) #sleep 3 seconds to avoid being banned
    html = lxml.etree.HTML(response.content)
    arxivID_list = [str(x.rsplit('/',1)[1]) for x in html.xpath('//dt/span[@class="list-identifier"]/a[@title="Abstract"]/@href')]
    for x in arxivID_list:
        crawl_one_arxiv_paper(x, tag_commit_sqlite3=True)


def remove_all_intermidiate_data_in_arxiv(directory):
    for x in os.listdir(directory):
        folder = os.path.join(directory, x)
        if os.path.isdir(folder):
            tmp0 = os.path.join(folder, 'untar')
            if os.path.exists(tmp0):
                shutil.rmtree(tmp0)
            tmp0 = os.path.join(folder, 'main.tex')
            if os.path.exists(tmp0):
                os.remove(tmp0)
            tmp0 = os.path.join(folder, 'meta-info.json')
            if os.path.exists(tmp0):
                os.remove(tmp0)
            tmp0 = os.path.join(folder, 'chunk-text.json')
            if os.path.exists(tmp0):
                os.remove(tmp0)
            # tmp0 = os.path.join(folder, 'chunk-vector.npy')
            # if os.path.exists(tmp0):
            #     os.remove(tmp0)


def _update_existing_arxiv_data():
    directory = os.environ['ARXIV_DIRECTORY']
    arxivID_list = [x for x in os.listdir(directory) if os.path.isdir(os.path.join(directory,x))]
    for x in arxivID_list:
        crawl_one_arxiv_paper(x, tag_commit_sqlite3=True)
