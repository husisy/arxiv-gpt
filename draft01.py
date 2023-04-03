# python chat_arxiv.py --query "chatgpt robot" --page_num 2 --max_results 3 --days 2

# paper_list = reader1.get_arxiv_web(args=args, page_num=args.page_num, days=args.days)

# titles, links, dates = self.get_all_titles_from_web(args.query, page_num=page_num, days=days)

def get_all_titles_from_web(self, keyword, page_num=1, days=1):
    title_list, link_list, date_list = [], [], []
    for page in range(page_num):
        url = self.get_url(keyword, page)  # 根据关键词和页码生成链接
        titles, links, dates = self.get_titles(url, days)  # 根据链接获取论文标题
        if not titles:  # 如果没有获取到任何标题，说明已经到达最后一页，退出循环
            break
        for title_index, title in enumerate(titles):  # 遍历每个标题，并打印出来
            print(page, title_index, title, links[title_index], dates[title_index])
        title_list.extend(titles)
        link_list.extend(links)
        date_list.extend(dates)
    print("-" * 40)
    return title_list, link_list, date_list


def get_url(self, keyword, page):
    base_url = "https://arxiv.org/search/?"
    params = {
        "query": keyword,
        "searchtype": "all",  # 搜索所有字段
        "abstracts": "show",  # 显示摘要
        "order": "-announced_date_first",  # 按日期降序排序
        "size": 50  # 每页显示50条结果
    }
    if page > 0:
        params["start"] = page * 50  # 设置起始位置
    return base_url + requests.compat.urlencode(params)

