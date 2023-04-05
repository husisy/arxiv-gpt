import os
import re
import json
import shutil
import requests
import time

import lxml.etree

from utils import download_url_and_save, _MY_REQUEST_HEADERS
from text_utils import (extract_unknown_arxiv_file, try_except_make_main_tex_file,
            texpath_to_text_chunk, pdfpath_to_text_chunk)
from database_utils import sqlite_insert_paper_list


def crawl_arxiv_meta_info(arxivID, json_path):
    if not os.path.exists(json_path):
        url = 'https://arxiv.org/abs/' + arxivID
        response = requests.get(url, headers=_MY_REQUEST_HEADERS)
        response.raise_for_status()
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
        with open(json_path, 'w', encoding='utf-8') as fid:
            tmp0 = {'title': title, 'author_list': author_list,'abstract': abstract, 'subject': subject}
            json.dump(tmp0, fid, indent=4, ensure_ascii=False)


def crawl_arxiv_recent_paper():
    url = "https://arxiv.org/list/quant-ph/recent"
    print(f'crawling {url}')
    response = requests.get(url, headers=_MY_REQUEST_HEADERS)
    response.raise_for_status()
    html = lxml.etree.HTML(response.content)

    db_commit_list = []
    for paper_i in html.xpath('//dt/span[@class="list-identifier"]')[:2]: #TODO debugggggggggggggggggggggggggggggg
        href = str(paper_i.xpath('./a[@title="Abstract"]/@href')[0])
        arxivID = href.rsplit('/', 1)[1]
        hf_file = lambda *x: os.path.join(os.environ['ARXIV_DIRECTORY'], arxivID, *x)
        if not os.path.exists(hf_file()):
            os.makedirs(hf_file())
        pdf_path = hf_file(arxivID+'.pdf')
        meta_info_json_path = hf_file('meta-info.json')
        targz_path = hf_file(arxivID + '.tar.gz')
        tex_path = hf_file('main.tex')
        chunk_text_json_path = hf_file('chunk-text.json')

        pdf_url = 'https://arxiv.org' + str(paper_i.xpath('./a[@title="Download PDF"]/@href')[0])
        if not os.path.exists(pdf_path):
            print(f'[{arxivID}] downloading {pdf_url}')
            filename = arxivID + '.pdf'
            download_url_and_save(pdf_url, filename=filename, directory=hf_file(), headers=_MY_REQUEST_HEADERS)
            time.sleep(3) #sleep 3 seconds to avoid being banned

        if not os.path.exists(meta_info_json_path):
            print(f'[{arxivID}] crawling meta information')
            crawl_arxiv_meta_info(arxivID, meta_info_json_path)

        tmp0 = paper_i.xpath('./a[@title="Other formats"]/@href')
        if len(tmp0) > 0:
            assert str(tmp0[0]).startswith('/format')
            targz_url = 'https://arxiv.org/e-print' + str(tmp0[0][7:])
            if not os.path.exists(targz_path):
                print(f'[{arxivID}] downloading targz file "{targz_url}"')
                filename = arxivID + '.tar.gz'
                download_url_and_save(targz_url, filename=filename, directory=hf_file(), headers=_MY_REQUEST_HEADERS)
                time.sleep(3)
            if not os.path.exists(hf_file('untar')):
                print(f'[{arxivID}] extract targz file to untar folder')
                os.makedirs(hf_file('untar'))
                extract_unknown_arxiv_file(targz_path, hf_file('untar'))

            if not os.path.exists(tex_path):
                print(f'[{arxivID}] make main.tex')
                tex_text = try_except_make_main_tex_file(hf_file('untar'))
                if tex_text is not None:
                    with open(tex_path, 'w', encoding='utf-8') as fid:
                        fid.write(tex_text)

        if not os.path.exists(chunk_text_json_path):
            if os.path.exists(tex_path):
                print(f'[{arxivID}] convert tex to chunk_text')
                text_list = texpath_to_text_chunk(tex_path)
            else:
                print(f'[{arxivID}] convert pdf to chunk_text')
                text_list = pdfpath_to_text_chunk(pdf_path)
            with open(chunk_text_json_path, 'w', encoding='utf-8') as fid:
                json.dump(text_list, fid, ensure_ascii=False)
        num_chunk = len(text_list)

        if os

        if not os.path.exists(tex_path):
            tex_path = ''
        if not os.path.exists(chunk_text_json_path):
            chunk_text_json_path = ''
        tmp0 = meta_info_json_path, pdf_path, tex_path, chunk_text_json_path
        assert all(x.startswith(os.environ['ARXIV_DIRECTORY']) for x in tmp0)
        tmp0 = [x[len(os.environ['ARXIV_DIRECTORY']):] for x in tmp0]
        db_commit_list.append((arxivID, *tmp0, num_chunk))
    sqlite_insert_paper_list(db_commit_list)


def remove_all_intermidiate_data_in_arxiv(directory):
    for x in os.listdir(directory):
        folder = os.path.join(directory, x)
        if os.path.isdir(folder):
            tmp0 = os.path.join(folder, 'untar')
            if os.path.exists(tmp0):
                shutil.rmtree(tmp0)
            tmp0 = os.path.join(folder, x+'.tex')
            if os.path.exists(tmp0):
                os.remove(tmp0)
            tmp0 = os.path.join(folder, 'main.tex')
            if os.path.exists(tmp0):
                os.remove(tmp0)
            tmp0 = os.path.join(folder, 'chunk-text.json')
            if os.path.exists(tmp0):
                os.remove(tmp0)
