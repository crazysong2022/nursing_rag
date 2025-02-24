from openai import OpenAI
import streamlit as st
import os
import json
from sqlalchemy.orm import sessionmaker
from models.database import engine, Base
from models.project_models import User, MyGoals
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 创建数据库会话
Session = sessionmaker(bind=engine)
session = Session()

# 定义系统角色
system_role = """
你是一名医学研究领域的专家，擅长科研方案设计与开题报告撰写。
"""

# 初始化阿里云百炼 API 客户端
try:
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
except Exception as e:
    raise Exception(f"初始化阿里云百炼 API 客户端失败，请检查配置。错误信息: {e}")

def generate_plan_with_ai(my_topic: str):
    """使用 AI 大模型生成方案"""
    prompt = f"""
    根据以下选题内容生成完整且详细的科研设计方案：
    选题内容: {my_topic}
    
    按照下面标准：
    1.研究内容
    2.研究方法及技术路线
      样本选择
        纳入标准
        排除标准
       数据采集工具
       数据分析方法
    3.特色与创新之处
    4.研究基础和条件
    5.预期成果
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

def update_my_goals(db, goal_id: int, my_plan: str):
    """更新 my_goals 表中的 my_plans 字段"""
    try:
        goal = db.query(MyGoals).filter(MyGoals.id == goal_id).first()
        if goal:
            goal.my_plans = my_plan
            db.commit()
            st.write(f"方案已成功更新到数据库，目标 ID: {goal.id}")
        else:
            st.error(f"未找到目标 ID {goal_id}，无法更新方案。")
    except Exception as e:
        db.rollback()  # 回滚事务
        st.error(f"更新方案到数据库时发生错误: {e}")
        raise

def display_my_plans(db, user_id: int):
    """展示已存储的 my_plans"""
    goals = db.query(MyGoals).filter(MyGoals.user_id == user_id).all()
    if not goals:
        st.info("您还没有任何方案。")
        return
    
    st.write("### 我的方案")
    for goal in goals:
        if goal.my_plans:
            with st.expander(goal.my_topics[:30] + "...", expanded=False):
                st.write(goal.my_plans)

def main():
    st.title("我的方案")
    
    # 获取当前用户
    username = st.session_state.get('user')
    user = session.query(User).filter(User.username == username).first()
    if not user:
        st.error("未找到当前用户，请登录后再试。")
        return
    
    # 展示已存储的 my_plans
    display_my_plans(session, user.id)
    
    # 获取当前用户的 my_goals
    my_goals = session.query(MyGoals).filter(MyGoals.user_id == user.id).all()
    if not my_goals:
        st.info("您还没有创建任何选题，请先在选题模块中添加选题。")
        return
    
    # 下拉框：选择 my_topics
    selected_goal = st.selectbox("请选择选题内容", my_goals, format_func=lambda goal: goal.my_topics)
    
    # 生成方案按钮
    if st.button("生成我的方案", key="generate_plan_button"):
        # 调用 AI 生成方案
        try:
            # 创建一个占位符用于逐步更新显示内容
            placeholder = st.empty()
            
            # 调用 AI 生成方案，并逐步显示
            plan = ""
            for chunk in generate_plan_with_ai(selected_goal.my_topics):
                plan += chunk
                placeholder.write(plan)  # 逐步更新显示内容
            st.success("方案生成完成！")
            
            # 更新 my_goals 表中的 my_plans 字段
            update_my_goals(session, selected_goal.id, plan)
        except Exception as e:
            st.error(f"生成方案时发生错误: {e}")

if __name__ == "__main__":
    main()