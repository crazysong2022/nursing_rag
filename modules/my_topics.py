from openai import OpenAI
import streamlit as st
import os
import json
from sqlalchemy.orm import sessionmaker
from models.database import engine, Base
from models.project_models import User, NursingTopic, MyGoals
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 创建数据库会话
Session = sessionmaker(bind=engine)
session = Session()

# 定义系统角色
system_role = """
你是医学研究领域的专家，特别擅长护理方面的科研选题。
"""

# 初始化阿里云百炼 API 客户端
try:
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
except Exception as e:
    raise Exception(f"初始化阿里云百炼 API 客户端失败，请检查配置。错误信息: {e}")

def generate_plan_with_ai(conversation_history: str, user_input: str):
    """使用 AI 大模型生成方案"""
    prompt = f"""
    {conversation_history}\n{user_input}
    """
    try:
        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt}
            ],
            stream=True,
            stream_options={"include_usage": True}
        )
        for chunk in completion:
            if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    content = delta.content
                    yield content  # 逐步返回内容
    except Exception as e:
        raise Exception(f"调用阿里云百炼 API 失败，请检查配置。错误信息: {e}")

def add_process_design(db, user_id: int, plan: str):
    """向 my_goals 表中添加记录"""
    try:
        new_goal = MyGoals(
            user_id=user_id,
            my_topics=plan,
            created_at=datetime.now()
        )
        db.add(new_goal)
        db.commit()
        db.refresh(new_goal)
        st.write(f"选题已成功保存到数据库，ID: {new_goal.id}")
        return new_goal
    except Exception as e:
        db.rollback()  # 回滚事务
        st.error(f"保存选题到数据库时发生错误: {e}")
        raise

def display_my_topics(db, user_id: int):
    """展示已存储的 my_topics"""
    goals = db.query(MyGoals).filter(MyGoals.user_id == user_id).all()
    if not goals:
        st.info("您还没有任何选题。")
        return
    
    st.write("### 我的选题")
    for goal in goals:
        if goal.my_topics:
            with st.expander(goal.my_topics[:30] + "...", expanded=False):
                st.write(goal.my_topics)

def main():
    st.title("我的选题")
    
    # 获取当前用户
    username = st.session_state.get('user')
    user = session.query(User).filter(User.username == username).first()
    if not user:
        st.error("未找到当前用户，请登录后再试。")
        return
    
    # 展示已存储的 my_topics
    display_my_topics(session, user.id)
    
    # 获取当前用户的 nursing_topics
    nursing_topics = session.query(NursingTopic).filter(NursingTopic.user_id == user.id).all()
    if not nursing_topics:
        st.info("您还没有创建任何选题，请先在选题模块中添加选题。")
        return
    
    # 第一个下拉框：选择 content
    selected_content = st.selectbox("请选择选题内容", [nt.content for nt in nursing_topics])
    selected_topic = next(nt for nt in nursing_topics if nt.content == selected_content)
    
    # 第二个下拉框：选择 sub_content
    sub_content_list = selected_topic.sub_content.split("\n") if selected_topic.sub_content else []
    selected_sub_content = st.selectbox("请选择子内容", sub_content_list)
    
    # 显示 conversation_history
    st.write("### 对话历史")
    conversation_history = json.loads(selected_topic.conversation_history)
    for message in conversation_history:
        if message["role"] == "assistant":
            st.markdown(message["content"])
    
    # 用户输入框
    user_input = st.text_area("请输入您的选择或需求", value="")
    
    # 生成选题按钮
    if st.button("生成我的选题", key="generate_button"):
        # 构建输入文本
        input_text = f"基于选题内容：{selected_content} 和子内容：{selected_sub_content}，以及用户的需求：{user_input}，生成一个基于上面内容的一两句话精炼研究选题，提供与选题相关的最新文献链接及摘要。。"
        
        # 将对话历史和用户输入合并为 AI 的输入
        ai_input = "\n".join([msg["content"] for msg in conversation_history if msg["role"] == "assistant"]) + "\n" + user_input
        
        # 调用OpenAI模型生成回答
        try:
            # 创建一个占位符用于逐步更新显示内容
            placeholder = st.empty()
            
            # 调用 AI 生成方案，并逐步显示
            plan = ""
            for chunk in generate_plan_with_ai(ai_input, user_input):
                plan += chunk
                placeholder.write(plan)  # 逐步更新显示内容
            st.success("方案生成完成！")
            
            # 设置保存按钮状态
            st.session_state.plan = plan
            st.session_state.plan_generated = True
        except Exception as e:
            st.error(f"生成方案时发生错误: {e}")
        
    # 保存方案
    if st.session_state.get("plan_generated"):
        if st.button("确定保存", key="save_button"):
            try:
                add_process_design(session, user.id, st.session_state.plan)
                st.success("选题已成功存储到我的目标中。")
            except Exception as e:
                st.error(f"保存选题时发生错误: {e}")

if __name__ == "__main__":
    main()