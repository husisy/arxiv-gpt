# arxiv GPT

for developer

1. read openai's documentation or [husisy/learning/openai/readme.md](https://github.com/husisy/learning/tree/master/python/openai) first
2. do not put API-key (openai, WEAVIATE) in the git history
3. access openai api key only in US-VPS


similar project

1. [arxiv-summary](https://www.arxiv-summary.com) [reddit](https://www.reddit.com/r/MachineLearning/comments/10cgm8d/p_i_built_arxivsummarycom_a_list_of_gpt3/)
2. github-chatpaper
3. arxiv-sanity [github](https://github.com/karpathy/arxiv-sanity-lite) [website](https://arxiv-sanity-lite.com/)

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

```bash
micromamba create -n arxiv
micromamba install -n arxiv -c conda-forge cython matplotlib h5py pillow protobuf scipy requests tqdm flask ipython openai python-dotenv tiktoken lxml tqdm pdfminer.six python-magic
micromamba activate arxiv
```

TODO

1. [ ] naive website
2. [ ] website login to avoid abuse login (api key is expensive)
3. [ ] sqlite: a database to store the path
4. [ ] public `/data` folder to store the downloaded tex file
5. [ ] website: store user's input
6. [ ] website: collect user's feedback, like which papers should be included
7. [ ] website: how to show chating messages

folder structure

```txt
arxiv.sqlite3
arxiv/
├── sqlite3.db
├── 2101.00001/ (arxivID)
│   ├── arxivID.pdf (download if not exists)
│   ├── arxivID.txt (optional)
│   ├── arxivID.tar.gz (download if not exists)
│   ├── arxivID.tex (unique)
│   ├── meta-info.json (abstract, title, author_list, subject)
│   ├── chunk-tex.json (list os string)
│   ├── untar/ (extract if not exist)
│   │   ├── 2101.00001v1
```

`arxiv.sqlite3 table=paper`

```txt
# database paper
pid: int (primary key)
arxivID: str
meta_info_json_path: str
pdf_path: str('' if not exist)
tex_path: str ('' if not exist)
chunk_tex_json_path: str ('' if not exist)
```
