import streamlit as st
from openai import OpenAI
import requests
import json
import xml.etree.ElementTree as ET
from sqlalchemy.orm import sessionmaker
from models.database import engine
from models.project_models import User, MyGoals
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 创建数据库会话
Session = sessionmaker(bind=engine)
session = Session()

# 初始化 OpenAI 客户端
try:
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
except Exception as e:
    st.error(f"初始化 OpenAI 客户端失败，请检查配置。错误信息: {e}")

# MeSH 的 API 调用
def get_mesh_terms(keywords, match="exact", year="current", limit=10):
    lookup_descriptor_url = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    params = {
        "label": " OR ".join(keywords),
        "match": match,
        "year": year,
        "limit": limit
    }
    try:
        response = requests.get(lookup_descriptor_url, params=params)
        response.raise_for_status()
        results = response.json()
        if results:
            descriptors = [result["label"] for result in results]
            st.write(f"在 MeSH 中找到相关描述词: {descriptors}")
            return descriptors
        else:
            st.write(f"在 MeSH 中未找到相关描述词，将直接用关键词 '{keywords}' 在 Title/Abstract 进行检索")
            return keywords
    except requests.RequestException as e:
        st.error(f"MeSH API 请求失败: {e}")
        return keywords
    except (KeyError, ValueError, IndexError) as e:
        st.error(f"解析 MeSH API 响应失败: {e}")
        return keywords

# 提取关键词
def extract_keywords_with_ai(topic):
    prompt = f"""
    你是一名医学信息检索领域的专家，
    你的任务是根据用户提供的自然语言描述，提取 PICOS 模型中的关键信息，并生成多个英文关键词，其他的一句话也不要生成：
    P（参与者/患者/人群）： <参与者/患者/人群>
    I（干预措施）： <干预措施>
    C（对照条件）： <对照条件>
    O（结局指标）： <结局指标>
    S（研究设计）： <研究设计>
    用户输入：{topic}
    """
    try:
        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "你是一名医学信息检索领域的专家。"},
                {"role": "user", "content": prompt}
            ],
            stream=False
        )
        response = completion.choices[0].message.content
        if not response:
            raise Exception("AI 没有返回任何内容，请检查输入或 API 配置。")
        return response
    except Exception as e:
        raise Exception(f"调用 AI 分析失败，请检查配置。错误信息: {e}")

# 将文本转换为 JSON 格式
def text_to_json(text):
    try:
        keywords = json.loads(text)
    except json.JSONDecodeError:
        keywords = {}
        lines = text.split("\n")
        for line in lines:
            if line.strip():
                parts = line.split("：", 1)
                if len(parts) == 2:
                    key, value = parts
                    keywords[key.strip()] = value.strip().split("，")
                else:
                    st.error(f"Invalid format in AI response: {line}")
    return keywords

# 生成布尔逻辑检索式
def generate_query(picos, terms):
    query = []
    for key, values in picos.items():
        terms_list = " OR ".join(terms.get(key, values))
        query.append(f"({key}: {terms_list})")
    return " AND ".join(query)

# PubMed检索
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

# 主函数
def main():
    st.title("医学文献检索与管理")

    # 获取当前用户
    username = st.session_state.get('user')
    user = session.query(User).filter(User.username == username).first()
    if not user:
        st.error("未找到当前用户，请登录后再试。")
        return

    # 获取当前用户的 my_goals
    my_goals = session.query(MyGoals).filter(MyGoals.user_id == user.id).all()
    if not my_goals:
        st.info("您还没有创建任何选题，请先在选题模块中添加选题。")
        return

    # 下拉框：选择 my_topics
    selected_goal = st.selectbox("请选择选题内容", my_goals, format_func=lambda goal: goal.my_topics)

    # 提取关键词
    if st.button("提取关键词"):
        try:
            keywords_text = extract_keywords_with_ai(selected_goal.my_topics)
            st.write("AI 生成的关键词文本：")
            st.write(keywords_text)
            st.session_state.keywords_text = keywords_text
            st.write("关键词提取完成，您可以选择下一步或重新生成关键词。")
        except Exception as e:
            st.error(f"提取关键词时发生错误: {e}")

    # 将文本转换为 JSON 格式
    if hasattr(st.session_state, 'keywords_text'):
        if st.button("下一步"):
            try:
                keywords = text_to_json(st.session_state.keywords_text)
                st.write("转换为 JSON 格式的关键词：")
                st.write(keywords)
                st.session_state.keywords = keywords
                st.write("关键词转换完成，您可以选择 MeSH 获取同义词。")
            except Exception as e:
                st.error(f"将文本转换为 JSON 格式时发生错误: {e}")
        if st.button("重新生成关键词"):
            try:
                keywords_text = extract_keywords_with_ai(selected_goal.my_topics)
                st.write("AI 重新生成的关键词文本：")
                st.write(keywords_text)
                st.session_state.keywords_text = keywords_text
                st.write("关键词重新提取完成，您可以选择下一步或重新生成关键词。")
            except Exception as e:
                st.error(f"重新提取关键词时发生错误: {e}")

    # 主题词和同义词检索
    if hasattr(st.session_state, 'keywords'):
        database = st.selectbox("选择数据库", ["MeSH"])
        selected_keyword = st.selectbox("选择关键词", list(st.session_state.keywords.values()))

        match_options = ["exact", "contains", "startswith"]
        match = st.selectbox("选择匹配方式", match_options, index=0)

        year_options = ["current", "2025", "2024", "2023"]
        year = st.selectbox("选择查询年份", year_options, index=0)

        limit = st.number_input("选择返回结果数量", min_value=1, value=10)

        if st.button("获取同义词"):
            try:
                terms = get_mesh_terms(selected_keyword, match, year, limit)
                st.write(f"获取的 {database} 主题词和同义词：")
                st.write(terms)
            except Exception as e:
                st.error(f"获取同义词时发生错误: {e}")

    # 生成布尔逻辑检索式
    if hasattr(st.session_state, 'keywords'):
        if st.button("生成布尔逻辑检索式"):
            try:
                all_terms = {}
                for key, values in st.session_state.keywords.items():
                    all_terms[key] = get_mesh_terms(values, "contains", "current", 10)
                query = generate_query(st.session_state.keywords, all_terms)
                st.write("生成的布尔逻辑检索式：")
                st.write(query)
                st.session_state.query = query
                st.write("布尔逻辑检索式生成完成。")

                # 新增调用PubMed检索按钮
                if st.button("在PubMed中检索"):
                    pubmed_results = pubmed_search(query)
                    for result in pubmed_results:
                        st.write("标题:", result["title"])
                        st.write("作者:", ", ".join(result["authors"]))
                        st.write("发表年份:", result["year"])
                        st.write("期刊:", result["journal"])
                        st.write("-" * 50)

            except Exception as e:
                st.error(f"生成布尔逻辑检索式时发生错误: {e}")

if __name__ == "__main__":
    main()