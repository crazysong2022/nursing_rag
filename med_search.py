import requests
import xml.etree.ElementTree as ET

def pubmed_search(query, search_field=None):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": 10,  # 最多返回10条结果，可根据需要调整
        "field": search_field if search_field else "",  # 可选字段参数
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
                collective_name_elem = author.find('CollectiveName')
                if collective_name_elem is not None:
                    authors.append(collective_name_elem.text)
                else:
                    continue
        pub_date = article.find('.//PubMedPubDate')
        year = pub_date.find('Year').text if pub_date is not None and pub_date.find('Year') is not None else 'N/A'
        journal = article.find('.//Journal/Title').text
        articles.append({
            "title": title,
            "authors": authors,
            "year": year,
            "journal": journal
        })
    return articles

def main():
    print("请选择检索方法：")
    print("1. 全字段检索（默认）")
    print("2. 仅标题/摘要检索")
    print("3. 结合MeSH和关键词检索")
    choice = input("请输入你的选择（1-3）：")

    if choice == '2':
        search_field = "Title/Abstract"
    elif choice == '3':
        search_field = input("请输入MeSH术语和关键词（用AND连接）：")
    else:
        search_field = None

    query = input("请输入 PubMed 检索式: ")
    results = pubmed_search(query, search_field)

    if results:
        for result in results:
            print("标题:", result["title"])
            print("作者:", ", ".join(result["authors"]))
            print("发表年份:", result["year"])
            print("期刊:", result["journal"])
            print("-" * 50)
    else:
        print("未找到符合检索式的文献。")

if __name__ == "__main__":
    main()