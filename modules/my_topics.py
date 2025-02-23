from openai import OpenAI
import streamlit as st
import os
import json
from sqlalchemy.orm import sessionmaker
from models.database import engine, Base
from models.project_models import User, NursingTopic, MyGoals
from datetime import datetime

# 创建数据库会话
Session = sessionmaker(bind=engine)
session = Session()

# 定义系统角色
system_role = """
你是医学研究领域的专家，特别擅长护理方面的科研选题。
"""

# 初始化OpenAI客户端
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"  # OpenAI 的 endpoint
)

# 初始化会话状态
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "qwen-plus"
if "messages" not in st.session_state:
    st.session_state.messages = []

# 主函数
def main():
    st.title("我的选题")
    
    # 获取当前用户
    username = st.session_state.get('user')
    user = session.query(User).filter(User.username == username).first()
    if not user:
        st.error("未找到当前用户，请登录后再试。")
        return
    
    # 获取当前用户的 nursing_topics
    nursing_topics = session.query(NursingTopic).filter(NursingTopic.user_id == user.id).all()
    if not nursing_topics:
        st.info("您还没有创建任何选题，请先在选题模块中添加选题。")
        return
    
    # 第一个下拉框：选择 content
    selected_content = st.selectbox("请选择选题内容", [nt.content for nt in nursing_topics])
    selected_topic = next(nt for nt in nursing_topics if nt.content == selected_content)
    
    # 第二个下拉框：选择 sub_content
    selected_sub_content = st.selectbox("请选择子内容", selected_topic.sub_content.split("\n"))
    
    # 用户输入框
    user_input = st.text_area("请输入您的选择或需求", value="")
    
    # 显示 conversation_history
    st.write("### 对话历史")
    conversation_history = json.loads(selected_topic.conversation_history)
    for message in conversation_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 生成选题按钮
    if st.button("生成我的选题", key="generate_button"):
        # 构建输入文本
        input_text = f"基于选题内容：{selected_content} 和子内容：{selected_sub_content}，以及用户的需求：{user_input}，生成一个基于上面内容的PICOS精炼研究选题。"
        
        # 将用户输入添加到会话状态的消息列表中
        st.session_state.messages.append({"role": "user", "content": input_text})
        
        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(input_text)
        
        # 调用OpenAI模型生成回答
        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model=st.session_state["openai_model"],
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True,
            )
            response = st.write_stream(stream)
        
        # 将AI的回答添加到会话状态的消息列表中
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # 存储和重复按钮
        col1, col2 = st.columns(2)
        with col1:
            if st.button("存储", key="store_button"):
                # 存储到 my_goals 表的 my_topics 字段
                new_goal = MyGoals(
                    user_id=user.id,
                    my_topics=response,
                    created_at=datetime.now()
                )
                session.add(new_goal)
                session.commit()
                st.success("选题已成功存储到我的目标中。")
        with col2:
            if st.button("重复", key="rerun_button"):
                # 重新生成答案
                st.rerun()

if __name__ == "__main__":
    main()