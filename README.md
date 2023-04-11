# ArxivChatGPT

Chat with arxiv paper

similar project

1. [arxiv-summary](https://www.arxiv-summary.com) [reddit](https://www.reddit.com/r/MachineLearning/comments/10cgm8d/p_i_built_arxivsummarycom_a_list_of_gpt3/)
2. github-chatpaper
3. arxiv-sanity [github](https://github.com/karpathy/arxiv-sanity-lite) [website](https://arxiv-sanity-lite.com/)

## setup local development environment

NOTICE

1. read openai's documentation or [husisy/learning/openai/readme.md](https://github.com/husisy/learning/tree/master/python/openai) first
2. do **NOT** put API-key (openai, WEAVIATE) in the git history
3. access openai api key only in US-VPS

```bash
micromamba create -n arxiv
micromamba install -n arxiv -c conda-forge cython matplotlib h5py pillow protobuf scipy requests tqdm flask ipython openai python-dotenv tiktoken lxml tqdm pdfminer.six python-magic pylatexenc chardet flask-sqlalchemy flask-migrate flask-login wtforms flask-wtf email_validator waitress
micromamba activate arxiv
pip install weaviate-client
```

1. complete the `.env` file from `.env.example`
2. run `python main_chat.py`
3. (optional) update database: `python main_database.py`

```Python
>>> from main_chat import *
>>> chatgpt.list_arxiv(num_print=5)
>>> chatgpt.select('2304.02241')
>>> chatgpt.chat("What is the main contribution of this paper?")
```

计划

1. 角色：用户，矢量数据库，openai embedding model (ada-002), this repo（以下简称self）
2. 用户：阅读abstract
   * abstract已经足够精炼了，进一步summarize是不必要的，且会丢失信息，当然用户可以在下一步通过chat来summarize
   * reference是结构化数据，不易丢入到chatgpt中
3. 用户：chat来查询文章内容
   * input question `text`
   * question to embedding
   * find similar vector in database
   * concatenate similar paragraph with question
   * input to chatgpt

flow chart

1. 每天从arxiv下载文章列表 `https://arxiv.org/list/quant-ph/recent`
   * `url_list(list,str)`
2. 下载文章对应的LaTeX文件
   * `tex_text(str)`
   * 可能的错误：不存在`。tar.gz`文件，非`.tar.gz`文件格式，多个子目录
3. 解析LaTeX文件，按照section分段，较长section进一步分割
   * `chunk_text_list(list,str)`
   * 可能的错误：多个`.tex文件`，`.tex`文件包含`\input{}`，非`section`分段
   * 超参数，每个chunk的最大token数量
4. 调用openai-ada-002将每个chunk映射为矢量
5. price
   * about `0.01USD` for converting one paper into chunk vectors
   * about `0.002USD` for each question

`.env` environment parameters

```bash
# weaviate database api key
WEAVIATE_API_URL=https://xxx
WEAVIATE_API_KEY=yyy

OPENAI_API_KEY=sk-zzz

# sqlite3 database path
SQLITE3_DB_PATH=/path/to/arxiv.sqlite3

# arxiv data folder
ARXIV_DIRECTORY=/path/to/arxiv-folder

# how many token for each chunk: 400 is chosen without too much consideration
ARXIVGPT_MAX_TOKEN_PER_CHUNK=400

# how many token for each question: 1800 is chosen without too much consideration
ARXIVGPT_MAX_TOKEN_PER_QA=1800

# 1: save chunk-vector.npy locally, mainly for debug
# 0: not save
ARXIVGPT_SAVE_NUMPY_VECTOR=1
```

brainstom: 用户有哪些关心的问题

1. summarize this paper
   * not good question, it's just the abstract
2. what the key contributions of the content
   * not bad
3. the most related paper according to the references
   * bad question, no references input to chatgpt
4. what is the method of this paper
   * good question
5. what is the result of this paper
   * good question
6. TODO
7. explain the word "xxx" in this paper
8. explain the word "xxx" in command sense
9. TODO 常见的问题先问掉并存起来

TODO

1. [ ] naive website
2. [ ] website login to avoid abuse login (api key is expensive)
3. [ ] sqlite: a database to store the path
4. [ ] public `/data` folder to store the downloaded tex file
5. [ ] website: store user's input
6. [ ] website: collect user's feedback, like which papers should be included
7. [ ] website: how to show chating messages

arxiv folder structure

```txt
arxiv/
├── 2101.00001/ (arxivID)
│   ├── main.pdf
│   ├── main.tar.gz
│   ├── main.tex
│   ├── meta-info.json (abstract, title, author_list, subject)
│   ├── chunk-text.json (list os string)
│   ├── chunk-vector.npy (numpy,float64,(N,1536)): optional
│   └── untar/ (extract from .tar.gz)
└── 2304.01411/
    ├── main.pdf
    ├── main.tar.gz
    ├── main.tex
    ├── meta-info.json
    ├── chunk-text.json
    ├── chunk-vector.npy
    └── untar/
```

`arxiv.sqlite3 table=paper`

```txt
# database paper
pid: int (primary key)
arxivID: str
meta_info_json_path: str
pdf_path: str('' if not exist)
tex_path: str ('' if not exist)
chunk_text_json_path: str ('' if not exist)
num_chunk: int
```

`weaviate table=Paper`

```txt
chunk: text
arxiv_id: string
index: int
num_chunk: int
num_token: int
vector (ada-002)
```

misc

```bash
# turn on crawling process
nohup python main_crawl.py >> log/main_crawl.log 2>&1 &

# turn on website
nohup waitress-serve --listen="127.0.0.1:5001" "app:app" >> log/waitress-serve.log 2>&1 &

# turn off crawling process
ps ax | grep main_crawl #get PID
kill <PID> #replace <PID>

# turn off website
ps ax | grep waitress-serve #get PID
kill <PID> #replace <PID>
```
