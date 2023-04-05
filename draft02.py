import os
import io
import magic
import time
import re
import gzip
import tarfile
import lxml.etree
import requests
from tqdm import tqdm
import pylatexenc.latexwalker

from utils import _MY_REQUEST_HEADERS, download_url_and_save

# TODO save to database

def get_arxiv_recent_targz_url():
    # TODO title author abstract
    url = "https://arxiv.org/list/quant-ph/recent"
    response = requests.get(url, headers=_MY_REQUEST_HEADERS)
    response.raise_for_status()
    html = lxml.etree.HTML(response.content)
    # TODO print if targz file is missing
    tmp0 = [str(x) for x in html.xpath('//a[@title="Other formats"]/@href')]
    tmp1 = [str(x) for x in html.xpath('//a[@title="Abstract"]/@href')]
    assert all(x.startswith('/format/') for x in tmp0)
    assert all(x.startswith('/abs/') for x in tmp1)
    tmp2 = set(x[5:] for x in tmp1) - set(x[8:] for x in tmp0)
    if len(tmp2)>0:
        print('these arxiv keys are missing targz file:', tmp2)
    ret = ['https://arxiv.org/e-print/'+x[8:] for x in tmp0]
    return ret


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


def download_tex_targz_file(url_list, directory='data'):
    tex_file_list = []
    for url_i in url_list:
        arxiv_key = url_i.rsplit('/',1)[1]
        hf_path = lambda *x: os.path.join(directory, arxiv_key, *x)
        if not os.path.exists(hf_path()):
            os.makedirs(hf_path())
        if not os.path.exists(hf_path('untar')):
            os.makedirs(hf_path('untar'))
        targz_filename = arxiv_key + '.tar.gz'
        if os.path.exists(hf_path(targz_filename)):
            print(f'{targz_filename} already exists, skip downloading')
        else:
            print(f'downloading {url_i}')
            download_url_and_save(url_i, filename=targz_filename, directory=hf_path(), headers=_MY_REQUEST_HEADERS)
            time.sleep(2.5) #avoid being banned
        tag_has_tex = len([x for x in os.listdir(hf_path('untar')) if x.endswith('.tex')])>1
        if not tag_has_tex:
            extract_unknown_arxiv_file(hf_path(targz_filename), hf_path('untar'))
        tmp0 = [hf_path('untar',x) for x in os.listdir(hf_path('untar')) if x.endswith('.tex')]
        if len(tmp0)==0:
            print(f'no tex file for {arxiv_key}')
        else:
            if len(tmp0)>1:
                print(f'more than one tex file in {arxiv_key}, choose the largest one in size')
                tmp0 = sorted(tmp0, key=os.path.getsize, reverse=True)[0]
            else:
                tmp0 = tmp0[0]
            tex_file_list.append(tmp0)
    return tex_file_list


def get_tex_split_text(tex_file):
    # if error, return None
    with open(tex_file, 'r', encoding='utf-8') as fid:
        tex_text = fid.read()
    # split raw text by section
    # TODO finer split: abstract author title paragraph etc.
    tmp0 = pylatexenc.latexwalker.LatexWalker(tex_text.strip()).get_latex_nodes(pos=0)[0]
    tmp1 = [x for x in tmp0 if x.isNodeType(pylatexenc.latexwalker.LatexEnvironmentNode) and x.environmentname=='document']
    if len(tmp1)==0:
        tmp0 = re.search(r'\\begin\{document\}', tex_text)
        tmp1 = re.search(r'\\end\{document\}', tex_text)
        if (tmp0 is None) or (tmp1 is None):
            return None
        ind0 = tmp0.span()[1]
        ind1 = tmp1.span()[0]
        tex_text = tex_text[ind0:ind1]
        tex_nodelist = pylatexenc.latexwalker.LatexWalker(tex_text.strip()).get_latex_nodes(pos=0)[0]
    else:
        assert len(tmp1)==1
        tex_nodelist = tmp1[0].nodelist
    # remove reference
    tex_nodelist = [x for x in tex_nodelist if not (x.isNodeType(pylatexenc.latexwalker.LatexEnvironmentNode) and x.environmentname=='thebibliography')]
    pos_section = [x.pos for x in tex_nodelist if x.isNodeType(pylatexenc.latexwalker.LatexMacroNode) and x.macroname=='section']
    # TODO split by paragraph
    index_split = [tex_nodelist[0].pos] + pos_section + [tex_nodelist[-1].pos + tex_nodelist[-1].len]
    text_split = [tex_text[x:y] for x,y in zip(index_split[:-1], index_split[1:])]
    return text_split

'''
data
├── 2101.00001
│   ├── 2101.00001.pdf
│   ├── 2101.00001.txt
│   ├── 2101.00001.tar.gz
│   ├── untar
│   │   ├── 2101.00001v1
'''

url_list = get_arxiv_recent_targz_url()

tex_file_list = download_tex_targz_file(url_list)
zc0 = [get_tex_split_text(x) for x in tqdm(tex_file_list)]
zc0 = get_tex_split_text(tex_file_list[13])
# TODO 2303.17399 input

tex_file = tex_file_list[13]

# TODO download 2209.10934 (PureB) tex

# url_i = 'https://arxiv.org/e-print//2303.17565'

# arxiv_key = url_i.rsplit('/',1)[1]
# hf_path = lambda *x: os.path.join('data', arxiv_key, *x)
# if not os.path.exists(hf_path()):
#     os.makedirs(hf_path())
# targz_filename = arxiv_key + '.tar.gz' #if exists, then skip all below
# download_url_and_save(url_i, filename=targz_filename, directory=hf_path(), headers=_MY_REQUEST_HEADERS)


# tmp0 = hf_path('untar')
# if os.path.isdir(tmp0):
#     os.rmdir(tmp0)
# with tarfile.open(hf_path(targz_filename), 'r') as fid:
#     fid.extractall(tmp0)

# tmp0 = [x for x in os.listdir(hf_path('untar')) if x.endswith('.tex')]
# assert len(tmp0) == 1
# tex_file = hf_path('untar', tmp0[0])

# with open(tex_file, 'r', encoding='utf-8') as fid:
#     tex_text = fid.read()
