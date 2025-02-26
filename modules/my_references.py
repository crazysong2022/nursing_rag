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
            st.write(f"在 MeSH 中未找到相关描述词，将尝试使用 AI 生成同义词")
            return []
    except requests.RequestException as e:
        st.error(f"MeSH API 请求失败: {e}")
        return []
    except (KeyError, ValueError, IndexError) as e:
        st.error(f"解析 MeSH API 响应失败: {e}")
        return []

# 使用大模型生成同义词
def generate_synonyms_with_ai(keyword):
    prompt = f"""
    你是一名医学领域的专家，请为以下关键词生成多个相关的同义词或近义词：
    关键词：{keyword}
    请严格按照以下 JSON 格式返回结果：
    {{
        "synonyms": ["同义词1", "同义词2", "同义词3"]
    }}
    """
    try:
        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "你是一名医学领域的专家。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},  # 强制返回 JSON 格式
            stream=False
        )
        response = completion.choices[0].message.content
        
        # 打印 AI 原始响应，用于调试
        st.write(f"AI 原始响应: {response}")
        
        if not response:
            raise Exception("AI 没有返回任何内容，请检查输入或 API 配置。")
        
        # 解析 JSON 响应
        synonyms = json.loads(response).get("synonyms", [])
        st.write(f"AI 生成的同义词: {synonyms}")
        return synonyms
    except Exception as e:
        st.error(f"调用 AI 生成同义词失败，请检查配置。错误信息: {e}")
        return []

# 合并 MeSH 和 AI 生成的同义词
def get_combined_terms(keywords):
    combined_terms = {}
    for key, values in keywords.items():
        # 对每个 PICOS 项逐一处理
        for value in values:
            # 先尝试从 MeSH 获取同义词
            mesh_terms = get_mesh_terms([value], match="contains", year="current", limit=10)
            
            # 如果 MeSH 结果不足，调用 AI 生成同义词
            if len(mesh_terms) < 5:  # 假设少于 5 个结果时需要补充
                ai_terms = generate_synonyms_with_ai(value)
                combined_terms[value] = list(set(mesh_terms + ai_terms))  # 合并并去重
            else:
                combined_terms[value] = mesh_terms
    
    # 显示 JSON 格式的同义词
    st.write(f"获取的 MeSH 主题词和同义词（JSON 格式）：")
    st.json(combined_terms)  # 使用 Streamlit 的 st.json 显示 JSON 数据
    return combined_terms

# 提取关键词
def extract_keywords_with_ai(topic):
    prompt = f"""
    你是一名医学信息检索领域的专家，
    你的任务是根据用户提供的自然语言描述，提取 PICOS 模型中的关键信息，并生成多个英文关键词。
    请严格按照以下 JSON 格式返回结果：
    {{
        "P": ["参与者/患者/人群"],
        "I": ["干预措施"],
        "C": ["对照条件"],
        "O": ["结局指标"],
        "S": ["研究设计"]
    }}
    用户输入：{topic}
    """
    try:
        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "你是一名医学信息检索领域的专家。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},  # 强制返回 JSON 格式
            stream=False
        )
        response = completion.choices[0].message.content
        
        # 打印 AI 原始响应，用于调试
        st.write(f"AI 原始响应: {response}")
        
        if not response:
            raise Exception("AI 没有返回任何内容，请检查输入或 API 配置。")
        
        # 解析 JSON 响应
        keywords = json.loads(response)
        
        # 确保每个部分的关键词是扁平化的字符串列表
        for key, value in keywords.items():
            if isinstance(value, list):  # 如果是列表，则直接转换为字符串列表
                keywords[key] = [str(v) for v in value]
            elif isinstance(value, str):  # 如果是单个字符串，则转换为单元素列表
                keywords[key] = [value]
            else:  # 其他情况（如嵌套列表），需要进一步处理
                keywords[key] = [str(item) for sublist in value for item in sublist]
        
        st.write(f"AI 生成的关键词: {keywords}")
        return keywords
    except Exception as e:
        st.error(f"调用 AI 分析失败，请检查配置。错误信息: {e}")
        return {}

# 生成布尔逻辑检索式
def generate_query(picos, terms):
    query = []
    for key, values in picos.items():
        # 确保 terms.get(key, values) 返回的是一个扁平化的字符串列表
        terms_list = terms.get(key, [])
        if not isinstance(terms_list, list):  # 如果不是列表，则转换为单元素列表
            terms_list = [str(terms_list)]
        else:
            terms_list = [str(term) for term in terms_list]
        
        # 如果 terms_list 为空，则使用原始的 picos 值
        if not terms_list:
            terms_list = values
        
        # 拼接布尔逻辑表达式
        terms_joined = " OR ".join(terms_list)
        query.append(f"({key}: {terms_joined})")
    
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
    
    # 初始化会话状态
    if "step" not in st.session_state:
        st.session_state.step = 0  # 当前步骤：0-未开始，1-提取关键词完成，2-获取同义词完成，3-生成布尔逻辑式完成
    
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
    
    # 步骤 1：提取关键词
    if st.button("提取关键词") and st.session_state.step == 0:
        try:
            keywords = extract_keywords_with_ai(selected_goal.my_topics)
            st.session_state.keywords = keywords
            st.session_state.step = 1  # 更新步骤状态
            st.write("关键词提取完成，您可以选择下一步或重新生成关键词。")
        except Exception as e:
            st.error(f"提取关键词时发生错误: {e}")
    
    # 步骤 2：获取同义词
    if hasattr(st.session_state, 'keywords') and st.session_state.step >= 1:
        if st.button("获取同义词") and st.session_state.step == 1:
            try:
                terms = get_combined_terms(st.session_state.keywords)
                st.session_state.terms = terms
                st.session_state.step = 2  # 更新步骤状态
                st.write("同义词获取完成，您可以生成布尔逻辑检索式。")
            except Exception as e:
                st.error(f"获取同义词时发生错误: {e}")
    
    # 步骤 3：生成布尔逻辑检索式
    if hasattr(st.session_state, 'keywords') and hasattr(st.session_state, 'terms') and st.session_state.step >= 2:
        if st.button("生成布尔逻辑检索式") and st.session_state.step == 2:
            try:
                picos = st.session_state.keywords
                terms = st.session_state.terms
                
                # 将 terms 转换为与 picos 匹配的格式
                matched_terms = {}
                for key, values in picos.items():
                    matched_terms[key] = []
                    for value in values:
                        matched_terms[key].extend(terms.get(value, []))
                
                query = generate_query(picos, matched_terms)
                st.session_state.query = query
                st.session_state.step = 3  # 更新步骤状态
                st.write("生成的布尔逻辑检索式：")
                st.write(query)
                st.write("布尔逻辑检索式生成完成。")
            except Exception as e:
                st.error(f"生成布尔逻辑检索式时发生错误: {e}")
    
    # 步骤 4：PubMed 检索
    if hasattr(st.session_state, 'query') and st.session_state.step >= 3:
        if st.button("在 PubMed 中检索") and st.session_state.step == 3:
            try:
                query = st.session_state.query
                st.write(f"正在使用以下布尔逻辑检索式查询 PubMed 数据库：{query}")
                
                # 显示加载动画
                with st.spinner("正在查询 PubMed 数据库，请稍候..."):
                    pubmed_results = pubmed_search(query)
                
                if not pubmed_results:
                    st.warning("未找到相关文献，请尝试调整布尔逻辑检索式。")
                else:
                    for result in pubmed_results:
                        st.write("标题:", result["title"])
                        st.write("作者:", ", ".join(result["authors"]))
                        st.write("发表年份:", result["year"])
                        st.write("期刊:", result["journal"])
                        st.write("-" * 50)
            except Exception as e:
                st.error(f"PubMed 检索失败: {e}")

if __name__ == "__main__":
    main()