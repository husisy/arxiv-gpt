# arxiv GPT

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
micromamba install -n arxiv -c conda-forge cython matplotlib h5py pillow protobuf scipy requests tqdm flask ipython openai python-dotenv tiktoken lxml tqdm pdfminer.six
```
