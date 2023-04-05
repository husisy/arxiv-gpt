import io
import time
import requests
import re
import json
import lxml.etree
import os
import sqlite3
import magic
import gzip
import tarfile

from utils import _MY_REQUEST_HEADERS, download_url_and_save

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


def extract_unknown_arxiv_file(file, directory):
    desc = magic.from_file(file)
    if desc.startswith('gzip compressed data'):
        with gzip.open(file, 'rb') as fid:
            file_byte = fid.read()
        desc = magic.from_buffer(file_byte[:2048])
        if desc.startswith('POSIX tar archive'):
            with tarfile.open(fileobj=io.BytesIO(file_byte), mode='r') as fid:
                fid.extractall(directory)
        elif desc.startswith('LaTeX 2e document, ASCII text'):
            with open(os.path.join(directory, 'main.tex'), 'wb') as fid:
                fid.write(file_byte)
        else:
            print(f'unknown file type "{file}": {desc}')
    else:
        print(f'unknown file type "{file}": {desc}')


def try_except_make_main_tex_file(directory, target_file):
    pass #TODO


def sqlite_insert_paper_list(paper_list):
    assert all(len(x)==5 for x in paper_list)
    paper_dict = dict()
    for x in paper_list:
        arxivID = x[0]
        paper_dict[arxivID] = x #remove duplicate arxivID
    sql_conn = sqlite3.connect(os.environ['SQLITE3_DB_PATH'])
    for arxivID, x in paper_dict.items():
        sql_conn.execute('DELETE FROM paper WHERE arxivID = ?', (arxivID,)) #remove old first
        # sql_conn.execute('SELECT * FROM paper').fetchall()
    tmp0 = '(arxivID,meta_info_json_path,pdf_path,tex_path,chunk_tex_json_path)'
    sql_conn.executemany(f'INSERT INTO paper {tmp0} VALUES (?,?,?,?,?)', list(paper_dict.values()))
    sql_conn.commit()
    sql_conn.close()


def init_sqlite3_database():
    sql_conn = sqlite3.connect(os.environ['SQLITE3_DB_PATH'])
    cmd = '''create table if not exists paper (
        pid integer primary key,
        arxivID text,
        meta_info_json_path text,
        pdf_path text,
        tex_path text,
        chunk_tex_json_path text
    )
    '''
    sql_conn.execute(cmd)


def crawl_arxiv_recent_paper():
    url = "https://arxiv.org/list/quant-ph/recent"
    response = requests.get(url, headers=_MY_REQUEST_HEADERS)
    response.raise_for_status()
    html = lxml.etree.HTML(response.content)

    db_commit_list = []
    for paper_i in html.xpath('//dt/span[@class="list-identifier"]'):
        href = str(paper_i.xpath('./a[@title="Abstract"]/@href')[0])
        arxivID = href.rsplit('/', 1)[1]
        hf_file = lambda *x: os.path.join(os.environ['ARXIV_DIRECTORY'], arxivID, *x)
        if not os.path.exists(hf_file()):
            os.makedirs(hf_file())

        pdf_url = 'https://arxiv.org' + str(paper_i.xpath('./a[@title="Download PDF"]/@href')[0])
        if not os.path.exists(hf_file(arxivID + '.pdf')):
            filename = arxivID + '.pdf'
            download_url_and_save(pdf_url, filename=filename, directory=hf_file(), headers=_MY_REQUEST_HEADERS)
            time.sleep(3) #sleep 3 seconds to avoid being banned

        meta_info_json_path = hf_file('meta-info.json')
        if not os.path.exists(meta_info_json_path):
            crawl_arxiv_meta_info(arxivID, meta_info_json_path)

        tmp0 = paper_i.xpath('./a[@title="Other formats"]/@href')
        if len(tmp0) > 0:
            assert str(tmp0[0]).startswith('/format')
            targz_url = 'https://arxiv.org/e-print' + str(tmp0[0][7:])
            targz_path = hf_file(arxivID + '.tar.gz')
            if not os.path.exists(targz_path):
                filename = arxivID + '.tar.gz'
                download_url_and_save(targz_url, filename=filename, directory=hf_file(), headers=_MY_REQUEST_HEADERS)
                time.sleep(3)
            if os.path.exists(targz_path):
                if not os.path.exists(hf_file('utar')):
                    os.makedirs(hf_file('utar'))
                    extract_unknown_arxiv_file(targz_path, hf_file('utar'))
                tex_path = hf_file(arxivID+'.tex')
                if not os.path.exists(tex_path):
                    pass #TODO
                    # try_except_find_main_tex_file(hf_file('utar'), tex_path)

        tex_path = hf_file('main.tex')
        if not os.path.exists(tex_path):
            tex_path = ''
        chunk_tex_json_path = hf_file('chunk-tex.json')
        if not os.path.exists(chunk_tex_json_path):
            chunk_tex_json_path = ''
        db_commit_list.append((arxivID, meta_info_json_path, hf_file(arxivID+'.pdf'), tex_path, chunk_tex_json_path))
    sqlite_insert_paper_list(db_commit_list)
