from openai import OpenAI
import streamlit as st
import os
from sqlalchemy.orm import sessionmaker
from models.database import engine, Base
from models.project_models import User, Writing
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create database session
Session = sessionmaker(bind=engine)
session = Session()

# Initialize Aliyun BaiLian API client
try:
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
except Exception as e:
    raise Exception(f"初始化阿里云百炼 API 客户端失败，请检查配置。错误信息: {e}")

# Define system role
system_role = """
你是医学研究领域的专家，特别擅长护理方面的科研选题。
"""

# Initialize conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize writing prompts
if "writing_prompts" not in st.session_state:
    st.session_state.writing_prompts = []

def main():
    st.title("撰写助手")

    # Get current user
    username = st.session_state.get('user')
    user = session.query(User).filter(User.username == username).first()
    if not user:
        st.error("未找到当前用户，请登录后再试。")
        return

    # Conversation mode
    st.subheader("对话模式：探讨如何撰写文章")

    # Display conversation history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if len(message["content"]) > 300:
                with st.expander("展开详细内容", expanded=False):
                    st.markdown(message["content"])
            else:
                st.markdown(message["content"])

    # User input
    prompt = st.chat_input("请输入您的问题或想法")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Call Qwen to generate response
        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": system_role},
                    *st.session_state.messages
                ],
                stream=True,
            )
            full_response = ""
            response_container = st.empty()  # Create an empty container to update
            for chunk in response:
                if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "content") and delta.content:
                        full_response += delta.content
                        response_container.markdown(full_response)  # Update the container
            st.session_state.messages.append({"role": "assistant", "content": full_response})

    # Writing prompt generation
    st.subheader("生成写作提示")

    # User selects writing type
    writing_type = st.selectbox("选择撰写类型", [
        "项目申报书撰写",
        "项目报告撰写",
        "综述撰写",
        "Meta分析撰写",
        "计量文献学论文撰写",
        "原始研究的科学论文撰写"
    ])

    # User input box
    user_input = st.text_area("请输入相关内容", value="")

    # Generate writing prompts button
    if st.button("生成写作提示", key="generate_prompts_button"):
        # Build input text
        input_text = f"基于撰写类型：{writing_type}，用户输入的内容：{user_input}，以及对话历史，生成写作提示。"
        
        # Call Qwen to generate writing prompts
        try:
            response = client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": system_role},
                    *st.session_state.messages,
                    {"role": "user", "content": input_text}
                ],
                stream=True,
            )
            prompts_text = ""
            response_container = st.empty()  # Create an empty container to update
            for chunk in response:
                if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "content") and delta.content:
                        prompts_text += delta.content
                        response_container.markdown(prompts_text)  # Update the container
            st.session_state.writing_prompts = prompts_text.split("\n")
            st.success("写作提示生成完成！")
        except Exception as e:
            st.error(f"生成写作提示时发生错误: {e}")

    # Display writing prompts
    st.subheader("写作提示")
    for i, prompt in enumerate(st.session_state.writing_prompts):
        st.write(f"{i + 1}. {prompt}")

    # Save writing prompts
    if st.button("保存写作提示", key="save_prompts_button"):
        try:
            for prompt in st.session_state.writing_prompts:
                new_writing = Writing(
                    user_id=user.id,
                    type=writing_type,
                    user_input=user_input,
                    generated_content=prompt,
                    created_at=datetime.now()
                )
                session.add(new_writing)
            session.commit()
            st.success("写作提示已成功保存到数据库。")
        except Exception as e:
            session.rollback()
            st.error(f"保存写作提示时发生错误: {e}")

if __name__ == "__main__":
    main()