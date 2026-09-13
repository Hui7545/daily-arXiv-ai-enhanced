import scrapy
import os
import re


def clean_text(parts, prefix=None):
    """Normalize an XPath text list and remove an optional label."""
    text = " ".join(
        part.strip() for part in parts if part and part.strip()
    )
    text = " ".join(text.split())
    if prefix and text.startswith(prefix):
        text = text[len(prefix) :].strip()
    return text


class ArxivSpider(scrapy.Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categories = os.environ.get("CATEGORIES", "cs.IR,cs.LG,cs.AI")
        categories = categories.split(",")
        # 保存目标分类列表，用于后续验证
        self.target_categories = set(map(str.strip, categories))
        self.max_papers = int(os.environ.get("ARXIV_MAX_PAPERS", "0") or 0)
        self.yielded_papers = 0
        self.start_urls = [
            f"https://arxiv.org/list/{cat}/new" for cat in self.target_categories
        ]  # 起始URL（计算机科学领域的最新论文）

    name = "arxiv"  # 爬虫名称
    allowed_domains = ["arxiv.org"]  # 允许爬取的域名

    def parse(self, response):
        # 提取每篇论文的信息
        anchors = []
        for li in response.css("div[id=dlpage] ul li"):
            href = li.css("a::attr(href)").get()
            if href and "item" in href:
                anchors.append(int(href.split("item")[-1]))

        # 遍历每篇论文的详细信息
        for paper in response.css("dl dt"):
            if self.max_papers > 0 and self.yielded_papers >= self.max_papers:
                return

            paper_anchor = paper.css("a[name^='item']::attr(name)").get()
            if not paper_anchor:
                continue
                
            paper_id = int(paper_anchor.split("item")[-1])
            if anchors and paper_id >= anchors[-1]:
                continue

            # 获取论文ID
            abstract_link = paper.css("a[title='Abstract']::attr(href)").get()
            if not abstract_link:
                continue
                
            arxiv_id = abstract_link.split("/")[-1]
            
            # 获取对应的论文描述部分 (dd元素)
            paper_dd = paper.xpath("following-sibling::dd[1]")
            if not paper_dd:
                continue
            
            title = clean_text(
                [paper_dd.css(".list-title").xpath("string(.)").get()],
                "Title:",
            )
            authors = paper_dd.css(".list-authors a::text").getall()
            authors = [
                clean_text([author]) for author in authors if author.strip()
            ]
            comment = clean_text(
                [paper_dd.css(".list-comments").xpath("string(.)").get()],
                "Comments:",
            )
            summary = clean_text(
                [paper_dd.css("p.mathjax").xpath("string(.)").get()]
            )

            # 提取论文分类信息 - 在subjects部分
            subjects_text = paper_dd.css(".list-subjects").xpath(
                "string(.)"
            ).get()
            
            if subjects_text:
                # 解析分类信息，通常格式如 "Computer Vision and Pattern Recognition (cs.CV)"
                # 提取括号中的分类代码
                categories_in_paper = re.findall(r'\(([^)]+)\)', subjects_text)
                
                # 检查论文分类是否与目标分类有交集
                paper_categories = list(dict.fromkeys(categories_in_paper))
                if set(paper_categories).intersection(self.target_categories):
                    yield {
                        "id": arxiv_id,
                        "categories": paper_categories,
                        "pdf": f"https://arxiv.org/pdf/{arxiv_id}",
                        "abs": f"https://arxiv.org/abs/{arxiv_id}",
                        "authors": authors,
                        "title": title,
                        "comment": comment or None,
                        "summary": summary,
                    }
                    self.yielded_papers += 1
                    self.logger.info(f"Found paper {arxiv_id} with categories {paper_categories}")
                else:
                    self.logger.debug(f"Skipped paper {arxiv_id} with categories {paper_categories} (not in target {self.target_categories})")
            else:
                # 如果无法获取分类信息，记录警告但仍然返回论文（保持向后兼容）
                self.logger.warning(f"Could not extract categories for paper {arxiv_id}, including anyway")
                yield {
                    "id": arxiv_id,
                    "categories": [],
                    "pdf": f"https://arxiv.org/pdf/{arxiv_id}",
                    "abs": f"https://arxiv.org/abs/{arxiv_id}",
                    "authors": authors,
                    "title": title,
                    "comment": comment or None,
                    "summary": summary,
                }
                self.yielded_papers += 1
