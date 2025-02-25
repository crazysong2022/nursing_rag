import requests
import xml.etree.ElementTree as ET


def pubmed_search(query):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": 10  # 最多返回10条结果，可根据需要调整
    }
    response = requests.get(base_url, params=params)
    root = ET.fromstring(response.content)
    id_list = root.find("IdList")
    pubmed_ids = [id.text for id in id_list.findall("Id")]

    # 获取文献详细信息
    base_fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    fetch_params = {
        "db": "pubmed",
        "id": ",".join(pubmed_ids),
        "retmode": "xml"
    }
    fetch_response = requests.get(base_fetch_url, fetch_params)
    fetch_root = ET.fromstring(fetch_response.content)
    articles = []
    for article in fetch_root.findall('.//PubmedArticle'):
        title = article.find('.//ArticleTitle').text
        authors = []
        for author in article.findall('.//Author'):
            last_name_elem = author.find('LastName')
            first_name_elem = author.find('ForeName')
            if last_name_elem is not None and first_name_elem is not None:
                last_name = last_name_elem.text
                first_name = first_name_elem.text
                authors.append(f"{first_name} {last_name}")
            else:
                # 如果没有分开的姓和名，尝试获取全名
                collective_name_elem = author.find('CollectiveName')
                if collective_name_elem is not None:
                    authors.append(collective_name_elem.text)
                else:
                    # 这里可以根据实际情况选择是否跳过该作者，或者记录缺失信息
                    continue
        pub_date = article.find('.//PubMedPubDate')
        year = pub_date.find('Year').text if pub_date is not None and pub_date.find('Year') is not None else 'N/A'
        journal = article.find('.//Title').text
        articles.append({
            "title": title,
            "authors": authors,
            "year": year,
            "journal": journal
        })
    return articles


# 获取用户输入的检索式
query = input("请输入 PubMed 检索式: ")
results = pubmed_search(query)
if results:
    for result in results:
        print("标题:", result["title"])
        print("作者:", ", ".join(result["authors"]))
        print("发表年份:", result["year"])
        print("期刊:", result["journal"])
        print("-" * 50)
else:
    print("未找到符合检索式的文献。")