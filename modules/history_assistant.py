import streamlit as st
import os
import json
from sqlalchemy.orm import sessionmaker, joinedload
from models.database import engine, Base
from models.project_models import User, NursingTopic
from openai import OpenAI

# 创建数据库会话
Session = sessionmaker(bind=engine)
session = Session()

# 调用大模型
def call_llm(user_input, messages):
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    new_messages = messages + [{"role": "user", "content": user_input}]
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=new_messages,
        stream=True,
        stream_options={"include_usage": True}
    )
    result = ""
    placeholder = st.empty()
    for chunk in completion:
        try:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                result += chunk.choices[0].delta.content
                placeholder.write(result)
        except IndexError as e:
            st.error(f"发生索引错误: {e}")
    return result

# 显示对话历史
def display_conversation_history():
    """显示当前会话的对话历史"""
    for i, message in enumerate(st.session_state.conversation_history):
        if message["role"] == "user":
            st.markdown(f'<div style="border: 1px solid lightgray; border-radius: 5px; padding: 10px; background-color: #2D2D2D; color: white;">**用户**: {message["content"]}</div>', unsafe_allow_html=True)
        elif message["role"] == "assistant":
            answer = message['content']
            lines = answer.split('\n')
            short_answer = '\n'.join(lines[:2])
            is_expanded = st.session_state.expanded_answers.get(i, False)
            if not is_expanded:
                st.markdown(f'<div style="border: 1px solid lightgray; border-radius: 5px; padding: 10px; background-color: #2D2D2D; color: white;">**AI**: {short_answer}</div>', unsafe_allow_html=True)
                if len(lines) > 2:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"展开", key=f"expand_{i}"):
                            st.session_state.expanded_answers[i] = True
                            st.rerun()
            else:
                st.markdown(f'<div style="border: 1px solid lightgray; border-radius: 5px; padding: 10px; background-color: #2D2D2D; color: white;">**AI**: {answer}</div>', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"收起", key=f"collapse_{i}"):
                        st.session_state.expanded_answers[i] = False
                        st.rerun()

# 主函数
def main():
    st.title("历史记录助手")
    
    # 初始化会话状态
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    if 'new_nursing_topic' not in st.session_state:
        st.session_state.new_nursing_topic = None
    if 'last_question' not in st.session_state:
        st.session_state.last_question = None
    if 'last_answer' not in st.session_state:
        st.session_state.last_answer = None
    if 'expanded_answers' not in st.session_state:
        st.session_state.expanded_answers = {}
    if 'has_ai_answer' not in st.session_state:
        st.session_state.has_ai_answer = False
    
    # 获取锁定的 topic_type 和 content
    selected_topic_type = st.session_state.get('selected_topic_type')
    selected_content = st.session_state.get('selected_content')
    
    if not selected_topic_type or not selected_content:
        st.error("未选择有效的选题内容或类型，请先从历史记录中加载。")
        return
    
    # 显示锁定的选题内容
    st.text_input("选题类型", value=selected_topic_type, disabled=True, key="topic_type_display")  # 锁定 topic_type
    st.text_input("选题内容", value=selected_content, disabled=True, key="content_display")  # 锁定 content
    
    # 加载已存储的对话历史
    connection = session
    try:
        results = connection.query(NursingTopic).filter_by(content=selected_content).order_by(NursingTopic.created_at).all()
        
        # 如果有对话历史，则加载到会话状态
        if results:
            conversation_history = []
            for row in results:
                history = json.loads(row.conversation_history) if row.conversation_history else []
                conversation_history.extend(history)
            st.session_state.conversation_history = conversation_history
        
        # 显示对话历史
        if st.session_state.conversation_history:
            display_conversation_history()
    except Exception as e:
        st.error(f"加载历史记录失败: {e}")

    # 提交新问题
    new_question = st.text_input("继续提问", key="new_question_input")
    if st.button("提交新问题", key="submit_new_question_button"):
        username = st.session_state.get('user')
        user = session.query(User).filter(User.username == username).first()
        
        # 构建用户输入
        if st.session_state.last_question != new_question:
            # 调用 LLM 并获取 AI 回答
            new_system_role = "You are an expert in providing in - depth analysis based on previous conversations."
            new_conversation_history = [{"role": "system", "content": new_system_role}] + st.session_state.conversation_history
            new_answer = call_llm(new_question, new_conversation_history)
            
            # 更新会话状态
            st.session_state.conversation_history.append({"role": "user", "content": new_question})
            st.session_state.conversation_history.append({"role": "assistant", "content": new_answer})
            st.session_state.last_question = new_question
            st.session_state.last_answer = new_answer
            
            # 保存到数据库
            try:
                # 确保用户对象存在
                if not user:
                    st.error("用户信息未找到，请重新登录。")
                    return
                
                # 创建新的 NursingTopic 记录
                new_nursing_topic = NursingTopic(
                    topic_type=selected_topic_type,
                    content=selected_content,
                    sub_content=new_question,
                    user=user,
                    conversation_history=json.dumps([
                        {"role": "user", "content": new_question},
                        {"role": "assistant", "content": new_answer}
                    ], ensure_ascii=False)
                )
                session.add(new_nursing_topic)
                session.commit()
                
                st.success("新问题已成功存储到数据库！")
                
                # 更新 st.session_state.new_nursing_topic
                st.session_state.new_nursing_topic = new_nursing_topic
            except Exception as e:
                session.rollback()
                st.error(f"存储到数据库失败: {e}")
            
            st.rerun()
    
    session.close()