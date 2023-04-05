import os
import io
import re
import gzip
import tarfile

import tiktoken
import magic
import pylatexenc


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


def try_except_make_main_tex_file(directory):
    texpath_list = [os.path.join(folder_i, x) for x in os.listdir(folder_i) if x.endswith('.tex')]
    text_list = []
    for texpath_i in texpath_list:
        with open(texpath_i, 'r', encoding='utf-8') as fid:
            text = fid.read()
        if r'\begin{document}' in text:
            try:
                text_list.append(resolve_tex_input(text, os.path.dirname(texpath_i)))
            except Exception as e:
                print(e)
                print(f'Error in resolving tex input "{texpath_i}"')
    # TODO handle other .tex files except main.tex
    if len(text_list)>1:
        ret = max(text_list, key=len)
    else:
        ret = None
    return ret


TIKTOKEN_tokenizer = tiktoken.get_encoding("cl100k_base")

def textlist_to_chunk(textlist, chunk_json_path):
    ARXIVGPT_MAX_TOKEN_PER_CHUNK = int(os.environ['ARXIVGPT_MAX_TOKEN_PER_CHUNK'])
    text_chunk_list = [y for x in textlist for y in split_text_into_chunks(x, ARXIVGPT_MAX_TOKEN_PER_CHUNK, TIKTOKEN_tokenizer)]

    pass


def texfile_to_text_chunk(tex_file):
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
    return text_split


folder_list = [os.path.join('data',x,'untar') for x in os.listdir('data')]
folder_i = folder_list[0]
texpath_list = [os.path.join(folder_i, x) for x in os.listdir(folder_i) if x.endswith('.tex')]

text_list = []
for texpath_i in texpath_list:
    with open(texpath_i, 'r', encoding='utf-8') as fid:
        text = fid.read()
    if r'\begin{document}' in text:
        text_list.append(resolve_tex_input(text, os.path.dirname(texpath_i)))
# TODO handle other .tex files except main.tex
with open(os.path.join(os.path.dirname(folder_i), 'main.tex'), 'w', encoding='utf-8') as fid:
    fid.write(max(text_list, key=len))
