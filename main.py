import streamlit as st
import psycopg2
from dotenv import load_dotenv
import os
import bcrypt
import importlib

# 加载环境变量
load_dotenv()

# 从环境变量获取数据库连接 URL
DATABASE_URL = os.getenv('DATABASE_URL')

# 数据库连接函数
def get_db_connection():
    try:
        connection = psycopg2.connect(DATABASE_URL)
        return connection
    except psycopg2.Error as e:
        st.error(f"数据库连接失败: {e}")
        return None

# 注册函数
def register(username, password):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            # 检查用户名是否已存在
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            existing_user = cursor.fetchone()
            if existing_user:
                st.error("该用户名已被注册，请选择其他用户名。")
            else:
                # 对密码进行哈希加密
                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                # 插入新用户
                cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
                connection.commit()
                st.success("注册成功，请登录。")
                st.session_state['rerun_flag'] = True
        except psycopg2.Error as e:
            st.error(f"注册失败: {e}")
        finally:
            cursor.close()
            connection.close()

# 登录函数
def login(username, password):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            if result:
                # 将 memoryview 转换为 bytes 类型
                hashed_password = bytes(result[0])
                # 验证密码
                if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
                    st.session_state['authentication_status'] = True
                    st.session_state['user'] = username
                    # 设置 URL 参数
                    st.query_params.update(
                        authentication_status='True',
                        user=username
                    )
                    st.session_state['rerun_flag'] = True
                    return True
                else:
                    st.session_state['authentication_status'] = False
                    return False
            else:
                st.session_state['authentication_status'] = False
                return False
        except psycopg2.Error as e:
            st.error(f"登录失败: {e}")
            st.session_state['authentication_status'] = None
            return False
        finally:
            cursor.close()
            connection.close()

# 登出函数
def logout():
    if 'authentication_status' in st.session_state:
        del st.session_state['authentication_status']
    if 'user' in st.session_state:
        del st.session_state['user']
    # 清除 URL 参数
    st.query_params.clear()
    st.success("已成功登出。")
    st.session_state['rerun_flag'] = True

# 初始化会话状态
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None
if 'rerun_flag' not in st.session_state:
    st.session_state['rerun_flag'] = False

# 从 URL 参数恢复会话状态
query_params = st.query_params
if 'authentication_status' in query_params and 'user' in query_params:
    auth_status = query_params['authentication_status'] == 'True'
    user = query_params['user']
    st.session_state['authentication_status'] = auth_status
    st.session_state['user'] = user

# 检查是否需要重新运行
if st.session_state['rerun_flag']:
    st.session_state['rerun_flag'] = False
    st.rerun()

# 处理认证状态
if st.session_state.get('authentication_status'):
    # 用户已登录
    st.write(f'欢迎, *{st.session_state["user"]}*')

    # 侧边栏菜单
    menu = {
        "关于": [],
        "科研选题及设计": ["辅助选题", "凝练问题", "可研方案"],
        "文献处理": ["文献检索", "文献管理", "文献综述"],
        "项目管理": ["数据管理", "数据分析", "结果呈现"],
        "文书书写": ["申报撰写", "报告撰写", "综述撰写", "Meta分析", "文献计量", "原始研究"],
        "润色及投稿": ["语言润色", "投稿格式", "意见修改"]
    }

    selected_menu = st.sidebar.selectbox("菜单", list(menu.keys()))

    if menu[selected_menu]:
        # 创建两个子菜单
        sub_menu = st.sidebar.selectbox("子菜单", menu[selected_menu])
        rag_sub_menu = st.sidebar.selectbox("RAG 子菜单", [f"{item}RAG" for item in menu[selected_menu]])
    else:
        sub_menu = None
        rag_sub_menu = None

    # 侧边栏登出按钮
    if st.sidebar.button('Logout', on_click=logout):
        pass

    if sub_menu or rag_sub_menu:
        # 处理有二级菜单的情况
        menu_mapping = {
            "辅助选题": "direction_assistant",
            "凝练问题": "distill_question",
            "可研方案": "feasibility_question",
            "语言润色": "article_refine",
            "辅助选题RAG": "direction_assistant_rag",
            "凝练问题RAG": "distill_question_rag",
            "可研方案RAG": "feasibility_question_rag",
            "文献检索": "literature_search",
            "文献管理": "literature_management",
            "文献综述": "literature_review",
            "文献检索RAG": "literature_search_rag",
            "文献管理RAG": "literature_management_rag",
            "文献综述RAG": "literature_review_rag",
            "数据管理": "data_management",
            "数据分析": "data_analysis",
            "结果呈现": "result_presentation",
            "数据管理RAG": "data_management_rag",
            "数据分析RAG": "data_analysis_rag",
            "结果呈现RAG": "result_presentation_rag",
            "申报撰写": "application_writing",
            "报告撰写": "report_writing",
            "综述撰写": "review_writing",
            "Meta分析": "meta_analysis",
            "文献计量": "bibliometrics",
            "原始研究": "original_research",
            "申报撰写RAG": "application_writing_rag",
            "报告撰写RAG": "report_writing_rag",
            "综述撰写RAG": "review_writing_rag",
            "Meta分析RAG": "meta_analysis_rag",
            "文献计量RAG": "bibliometrics_rag",
            "原始研究RAG": "original_research_rag",
            "语言润色": "language_refine",
            "投稿格式": "submission_format",
            "意见修改": "review_modification",
            "语言润色RAG": "language_refine_rag",
            "投稿格式RAG": "submission_format_rag",
            "意见修改RAG": "review_modification_rag"
        }
        selected_sub_menu = sub_menu if sub_menu else rag_sub_menu
        module_name = menu_mapping.get(selected_sub_menu)
        if module_name:
            try:
                module = importlib.import_module(f"modules.{module_name}")
                if hasattr(module, 'main'):
                    module.main()
                else:
                    st.error(f"模块 {module_name} 中没有 main 函数")
            except ImportError:
                st.error(f"未找到模块 {module_name}")
            except Exception as e:
                st.error(f"加载模块 {module_name} 时发生错误: {e}")
        else:
            st.error("未找到对应的模块映射")
    else:
        # 处理没有二级菜单的情况
        st.write(f"你选择了 {selected_menu}，暂时没有对应模块实现。")

elif st.session_state.get('authentication_status') is False:
    st.error('用户名或密码错误')
elif st.session_state.get('authentication_status') is None:
    tab1, tab2 = st.tabs(["登录", "注册"])

    with tab1:
        st.title("登录")
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        if st.button('登录', on_click=lambda: login(username, password)):
            pass

    with tab2:
        st.title("注册")
        new_username = st.text_input("新用户名")
        new_password = st.text_input("新密码", type="password")
        if st.button("注册", on_click=lambda: register(new_username, new_password)):
            pass