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
    st.session_state['authentication_status'] = auth_status
    st.session_state['user'] = user

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
    
    # 定义菜单结构
    menu = {
        "关于": [],
        "科研选题及设计": ["辅助选题", "凝练问题", "可研方案"],
        "文献处理": ["文献检索", "文献管理", "文献综述"],
        "项目管理": ["数据管理", "数据分析", "结果呈现"],
        "文书书写": ["申报撰写", "报告撰写", "综述撰写", "Meta分析", "文献计量", "原始研究"],
        "润色及投稿": ["语言润色", "投稿格式", "意见修改"]
    }
    
    selected_menu = st.sidebar.selectbox("菜单", list(menu.keys()))
    
    # 显示子菜单（如果存在）
    if menu[selected_menu]:
        sub_menu = st.sidebar.selectbox("子菜单", menu[selected_menu])
        
        if sub_menu:
            module_name = menu_mapping.get(sub_menu)
            if module_name:
                try:
                    module = importlib.import_module(f"{MODULE_PATH}.{module_name}")
                    if hasattr(module, 'main'):
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
    if st.sidebar.button('Logout', on_click=logout):
        pass
    
    # 显示历史记录（固定在 Logout 按钮下方）
    # 显示历史记录（固定在 Logout 按钮下方）
st.sidebar.markdown("---")  # 分隔线
st.sidebar.subheader("历史记录")

connection = get_db_connection()
if connection:
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT topic_type, content, created_at FROM nursing_topics ORDER BY created_at DESC")
        results = cursor.fetchall()
        
        # 调试：打印查询结果
        st.write("查询结果:", results)
        
        # 分组显示历史记录
        now = datetime.now()
        today = now.date()
        yesterday = (now - timedelta(days=1)).date()
        three_days_ago = (now - timedelta(days=3)).date()
        seven_days_ago = (now - timedelta(days=7)).date()
        
        time_groups = {
            "今天": [],
            "昨天": [],
            "三天前": [],
            "七天前": []
        }
        
        for row in results:
            topic_type, content, created_at = row
            created_date = created_at.date()
            
            # 提取“输入了选题:”后面的内容
            if "输入了选题:" in content:
                topic_content = content.split("输入了选题:")[1].strip()
            else:
                topic_content = content
            
            # 分组逻辑
            if created_date == today:
                time_groups["今天"].append((topic_type, topic_content))
            elif created_date == yesterday:
                time_groups["昨天"].append((topic_type, topic_content))
            elif three_days_ago <= created_date < yesterday:
                time_groups["三天前"].append((topic_type, topic_content))
            elif seven_days_ago <= created_date < three_days_ago:
                time_groups["七天前"].append((topic_type, topic_content))
        
        # 渲染分组内容
        for group_name, items in time_groups.items():
            if items:
                st.sidebar.write(f"**{group_name}:**")
                for topic_type, topic_content in items:
                    st.sidebar.write(f"- **{topic_type}**: {topic_content}")
            else:
                st.sidebar.write(f"{group_name}: 暂无记录")
    
    except psycopg2.Error as e:
        st.error(f"加载历史记录失败: {e}")
    finally:
        connection.close()
else:
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