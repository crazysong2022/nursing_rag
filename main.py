import streamlit as st
import psycopg2
from dotenv import load_dotenv
import os
import bcrypt
import importlib
import json
from datetime import datetime, timedelta

# 加载环境变量
load_dotenv()

# 从环境变量获取数据库连接 URL
DATABASE_URL = os.getenv('DATABASE_URL')

# 数据库连接函数
def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except psycopg2.Error as e:
        st.error(f"数据库连接失败: {e}")
        return None

# 注册函数
def register(username, password):
    if not username or not password:
        st.error("用户名和密码不能为空")
        return
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            existing_user = cursor.fetchone()
            if existing_user:
                st.error("该用户名已被注册，请选择其他用户名。")
            else:
                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
                connection.commit()
                st.success("注册成功，请登录。")
                st.session_state['rerun_flag'] = True
        except psycopg2.Error as e:
            st.error(f"注册失败: {e}")
        finally:
            connection.close()

# 登录函数
def login(username, password):
    if not username or not password:
        st.error("用户名和密码不能为空")
        return False
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            if result:
                hashed_password = bytes(result[0])
                if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
                    st.session_state['authentication_status'] = True
                    st.session_state['user'] = username
                    st.query_params.update(authentication_status='True', user=username)
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
            connection.close()

# 登出函数
def logout():
    if 'authentication_status' in st.session_state:
        del st.session_state['authentication_status']
    if 'user' in st.session_state:
        del st.session_state['user']
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
    # 验证用户是否存在于数据库中
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s", (user,))
            existing_user = cursor.fetchone()
            if existing_user:
                st.session_state['authentication_status'] = auth_status
                st.session_state['user'] = user
            else:
                st.session_state['authentication_status'] = False
        except psycopg2.Error as e:
            st.error(f"验证用户失败: {e}")
            st.session_state['authentication_status'] = False
        finally:
            connection.close()

# 检查是否需要重新运行
if st.session_state['rerun_flag']:
    st.session_state['rerun_flag'] = False
    st.rerun()

# 加载配置文件
def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

config = load_config()
MODULE_PATH = config.get("module_path", "modules")
menu_mapping = config.get("menu_mapping", {})

# 处理认证状态
if st.session_state.get('authentication_status'):
    st.write(f'欢迎, *{st.session_state["user"]}*')
    
    # 定义合并后的菜单
    combined_menu = {
        "辅助选题": "direction_assistant",
        "我的选题": "my_topics",
        "我的方案": "my_plans",
        "我的文献": "my_references",
        "我的项目": "my_projects",
        "我的文章": "my_articles",
        "我要投稿": "my_submissions"
    }
    
    # 选择菜单项
    selected_menu = st.sidebar.selectbox("菜单", list(combined_menu.keys()))
    
    # 创建一个容器用于动态加载模块内容
    module_container = st.empty()
    
    # 加载对应的模块内容
    if selected_menu:
        module_name = combined_menu.get(selected_menu)
        if module_name:
            try:
                module = importlib.import_module(f"{MODULE_PATH}.{module_name}")
                if hasattr(module, 'main'):
                    with module_container.container():  # 在容器中加载模块内容
                        module.main()
                else:
                    st.error(f"模块 {module_name} 中没有 main 函数")
            except ModuleNotFoundError:
                st.error(f"未找到模块 {module_name}，请检查模块路径是否正确。")
            except AttributeError:
                st.error(f"模块 {module_name} 缺少 main 函数，请检查模块实现。")
            except Exception as e:
                st.error(f"加载模块 {module_name} 时发生未知错误: {e}")
        else:
            st.error("未找到对应的模块映射")
    
    # 添加 Logout 按钮
    if st.sidebar.button('Logout', on_click=logout, key="logout_button"):
        pass
    
    # 显示历史记录（固定在 Logout 按钮下方）
    st.sidebar.markdown("---")  # 分隔线
    with st.sidebar.expander("历史记录", expanded=False):  # 默认折叠
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                
                # 查询总记录数
                cursor.execute("""
                    SELECT COUNT(DISTINCT content)
                    FROM nursing_topics
                """)
                total_records = cursor.fetchone()[0]
                
                # 分页参数
                records_per_page = 5  # 每页显示的记录数
                page_number = st.number_input("页码", min_value=1, max_value=(total_records // records_per_page) + 1, value=1, key="history_page_number")
                offset = (page_number - 1) * records_per_page
                
                # 查询分页数据（去重并排序）
                cursor.execute("""
                    SELECT content, topic_type, MAX(created_at) AS latest_created_at
                    FROM nursing_topics
                    GROUP BY content, topic_type
                    ORDER BY latest_created_at DESC
                    LIMIT %s OFFSET %s
                """, (records_per_page, offset))
                results = cursor.fetchall()
                
                # 渲染分页数据
                for row in results:
                    content, topic_type, _ = row
                    
                    # 提取“输入了选题:”后面的内容
                    if "输入了选题:" in content:
                        topic_content = content.split("输入了选题:")[1].strip()
                    else:
                        topic_content = content
                    
                    # 为每个 content 添加按钮
                    if st.button(f"加载: {topic_content}", key=f"load_{content}"):
                        # 更新会话状态
                        st.session_state['selected_topic_type'] = topic_type  # 锁定 topic_type
                        st.session_state['selected_content'] = content  # 锁定 content
                        
                        # 强制刷新界面
                        st.rerun()
        
            except psycopg2.Error as e:
                st.error(f"加载历史记录失败: {e}")
            finally:
                connection.close()

    # 如果选中了某个 content，则加载其所有记录
    if 'selected_content' in st.session_state:
        # 创建一个容器用于动态加载模块内容
        history_container = st.empty()
        with history_container.container():  # 在容器中加载 history_assistant 内容
            from modules.history_assistant import main as history_main
            history_main()
else:
    tab1, tab2 = st.tabs(["登录", "注册"])
    with tab1:
        st.title("登录")
        username = st.text_input("用户名", key="login_username")
        password = st.text_input("密码", type="password", key="login_password")
        if st.button('登录', on_click=lambda: login(username, password), key="login_button"):
            pass
    with tab2:
        st.title("注册")
        new_username = st.text_input("新用户名", key="register_username")
        new_password = st.text_input("新密码", type="password", key="register_password")
        if st.button("注册", on_click=lambda: register(new_username, new_password), key="register_button"):
            pass