import os
import io
import re
import gzip
import tarfile
import sys
import time
import math
import unicodedata

import chardet
import numpy as np
import openai
import tiktoken
import magic
import pylatexenc.latexwalker
import pdfminer.high_level


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


# TODO replace with re2
_TEX_INPUT_RE = re.compile(r'\\input\{(.*)\}')

def resolve_tex_input(text, directory):
    while True:
        tmp0 = _TEX_INPUT_RE.search(text)
        if tmp0 is None:
            break
        else:
            ind0,ind1 = tmp0.span()
            file_i = os.path.join(directory, tmp0.group(1))
            if (not os.path.exists(file_i)) and (not file_i.endswith('.tex')):
                file_i = os.path.join(directory, tmp0.group(1)+'.tex')
            if os.path.exists(file_i):
                with open(file_i, 'r', encoding='utf-8') as fid:
                    text = text[:ind0] + '\n' + fid.read() + '\n' + text[ind1:]
            else:
                # replace \input{xxx} with input{xxx}
                text = text[:ind0] + text[(ind0+1):]
    return text

_TEX_COMMENT_RE = re.compile(r'(?<!\\)%.*')

def try_except_make_main_tex_file(directory):
    texpath_list = [os.path.join(directory, x) for x in os.listdir(directory) if x.endswith('.tex')]
    text_list = []
    for texpath_i in texpath_list:
        try:
            with open(texpath_i, 'r', encoding='utf-8') as fid:
                text = fid.read()
        except UnicodeDecodeError:
            with open(texpath_i, 'rb') as fid:
                tmp0 = fid.read()
            tmp1 = chardet.detect(tmp0)['encoding']
            print(f'[{texpath_i}] chardet detect encoding: {tmp1}')
            text = tmp0.decode(tmp1)
        if r'\begin{document}' in text:
            try:
                text_list.append(resolve_tex_input(text, os.path.dirname(texpath_i)))
            except Exception as e:
                print(e)
                print(f'Error in resolving tex input "{texpath_i}"')
    # TODO handle other .tex files except main.tex
    if len(text_list)>=1:
        tmp0 = max(text_list, key=len)
        ret = _TEX_COMMENT_RE.sub('', tmp0)
    else:
        ret = None
    return ret


TIKTOKEN_tokenizer = tiktoken.get_encoding("cl100k_base")


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


def texpath_to_text_chunk(tex_file):
    # if error, return None
    with open(tex_file, 'r', encoding='utf-8') as fid:
        tex_text = fid.read()
    # split raw text by section
    # TODO finer split: abstract author title paragraph etc.
    tmp0 = pylatexenc.latexwalker.LatexWalker(tex_text.strip()).get_latex_nodes(pos=0)[0]
    tmp1 = [x for x in tmp0 if x.isNodeType(pylatexenc.latexwalker.LatexEnvironmentNode) and x.environmentname=='document']
    if len(tmp1)==0:
        # [bug] pylatexenc may fail to parse some tex file
        ind0 = re.search(r'\\begin\{document\}', tex_text).span()[1]
        ind1 = re.search(r'\\end\{document\}', tex_text).span()[0]
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

    ARXIVGPT_MAX_TOKEN_PER_CHUNK = int(os.environ['ARXIVGPT_MAX_TOKEN_PER_CHUNK'])
    text_chunk_list = [y for x in text_split for y in split_text_into_chunks(x, ARXIVGPT_MAX_TOKEN_PER_CHUNK, TIKTOKEN_tokenizer)]
    return text_chunk_list



# TODO make a cache
# https://stackoverflow.com/a/93029/7290857
tmp0 = (chr(i) for i in range(sys.maxunicode)) #all character
tmp1 = ''.join(c for c in tmp0 if (unicodedata.category(c)=='Cc') and c not in '\t\n') #all control character
_CONTROL_CHAR_RE = re.compile('[%s]' % re.escape(tmp1))
_REMOVE_BEGIN_ARXIV_RE = re.compile("$(.?\n)+", flags=re.MULTILINE)
_REMOVE_CONNECTING_RE = re.compile('-\n', flags=re.MULTILINE)
_REMOVE_LATEXIT_RE = re.compile('latexit(.*)/latexit', flags=re.MULTILINE)
_REMOVE_NEWLINE_RE = re.compile(r'(\S)\n(\S)', flags=re.MULTILINE)
_MISC00_RE = re.compile('ﬀ')


def pdfpath_to_text_chunk(pdf_path):
    # TODO see github/chatpaper how to cleanup pdf
    assert pdf_path.endswith('.pdf')
    text_path = pdf_path[:-4] + '.txt'

    with open(pdf_path, 'rb') as fid:
        text_ori = pdfminer.high_level.extract_text(fid)
    text0 = _CONTROL_CHAR_RE.sub('', text_ori)
    text1 = _REMOVE_BEGIN_ARXIV_RE.sub('', text0, count=1)
    text2 = _REMOVE_LATEXIT_RE.sub('', text1)

    text3 = _REMOVE_CONNECTING_RE.sub('', text2)
    text4 = _REMOVE_NEWLINE_RE.sub(r'\1 \2', text3)
    text4 = _REMOVE_NEWLINE_RE.sub(r'\1 \2', text4) #sometimes we need do this several time
    text5 = _MISC00_RE.sub('ff', text4)

    text = text5

    ARXIVGPT_MAX_TOKEN_PER_CHUNK = int(os.environ['ARXIVGPT_MAX_TOKEN_PER_CHUNK'])
    text_chunk_list = split_text_into_chunks(text, ARXIVGPT_MAX_TOKEN_PER_CHUNK, TIKTOKEN_tokenizer)
    return text_chunk_list


def text_chunk_list_to_numpy_vector(text_chunk_list, batch_size=20):
    assert all(isinstance(x,str) for x in text_chunk_list)
    num_chunk = len(text_chunk_list)
    tmp0 = [x*batch_size for x in range(math.ceil(num_chunk/batch_size) + 1)]
    text_chunk_list_batch = [text_chunk_list[x:y] for x,y in zip(tmp0,tmp0[1:])]
    embedding_list = []
    for batch_i in text_chunk_list_batch:
        # rate limiting
        # https://platform.openai.com/docs/guides/rate-limits/what-are-the-rate-limits-for-our-api
        time.sleep(2.5) #make sure not exceed 20 requests per minutes
        response = openai.Embedding.create(input=batch_i, engine='text-embedding-ada-002')
        tmp0 = sorted(response['data'], key=lambda x:x.index)
        embedding_list += [x.embedding for x in tmp0]
        print(f'embedding progress: {len(embedding_list)}/{num_chunk}')
    embedding_np = np.array(embedding_list, dtype=np.float64)
    return embedding_np
