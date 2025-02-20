import streamlit as st
import os
from sqlalchemy.orm import sessionmaker
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

# 主函数
def main():
    st.title("护理科研选题方向助手")

    # 初始化会话状态
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = [{"role": "system", "content": "You are a helpful assistant."}]
    if 'new_nursing_topic' not in st.session_state:
        st.session_state.new_nursing_topic = None
    if 'last_question' not in st.session_state:
        st.session_state.last_question = None
    if 'last_answer' not in st.session_state:
        st.session_state.last_answer = None
    if 'expanded_answers' not in st.session_state:
        st.session_state.expanded_answers = {}
    # 新增一个状态来标记是否有 AI 答案
    if 'has_ai_answer' not in st.session_state:
        st.session_state.has_ai_answer = False

    # 选题模块选择
    topic_types = ["期刊选题", "专刊选题", "现有技术不足分析", "期望目标设定"]
    selected_topic_type = st.selectbox("请选择选题模块", topic_types)

    # 工作区输入框
    journal_topic = ""
    department = ""
    nursing_issue = ""
    technology_deficiency = ""
    expected_goal = ""

    if selected_topic_type == "期刊选题":
        journal_topic = st.text_input("请输入期刊选题")
    elif selected_topic_type == "专刊选题":
        department = st.text_input("请输入科室")
        nursing_issue = st.text_input("请输入护理问题")
    elif selected_topic_type == "现有技术不足分析":
        technology_deficiency = st.text_input("请输入现有技术不足内容")
    elif selected_topic_type == "期望目标设定":
        expected_goal = st.text_input("请输入期望目标内容")

    # 提交按钮
    if st.button("提交"):
        username = st.session_state.get('user')
        user = session.query(User).filter(User.username == username).first()

        # 构建带上下文的 content
        if selected_topic_type == "期刊选题":
            content = f"用户 {username} 在期刊选题栏目中，输入了选题: {journal_topic}"
        elif selected_topic_type == "专刊选题":
            content = f"用户 {username} 在专刊选题栏目中，输入科室: {department}，输入了护理问题: {nursing_issue}"
            if technology_deficiency:
                content += f"，输入了现有技术不足: {technology_deficiency}"
            if expected_goal:
                content += f"，输入了期望目标: {expected_goal}"
        elif selected_topic_type == "现有技术不足分析":
            content = f"用户 {username} 在现有技术不足分析栏目中，输入了内容: {technology_deficiency}"
        elif selected_topic_type == "期望目标设定":
            content = f"用户 {username} 在期望目标设定栏目中，输入了期望目标: {expected_goal}"

        # 保存到数据库
        new_nursing_topic = NursingTopic(
            topic_type=selected_topic_type,
            content=content,
            user=user
        )
        session.add(new_nursing_topic)
        session.commit()
        st.success("选题信息已成功保存到数据库。")
        st.session_state.new_nursing_topic = new_nursing_topic

        # 构建用户输入
        user_input = content

        if st.session_state.last_question != user_input:
            # 调用大模型
            answer = call_llm(user_input, st.session_state.conversation_history)
            st.session_state.conversation_history.append({"role": "user", "content": user_input})
            st.session_state.conversation_history.append({"role": "assistant", "content": answer})
            st.session_state.last_question = user_input
            st.session_state.last_answer = answer
            # 有 AI 答案了，更新状态
            st.session_state.has_ai_answer = True

    # 显示对话历史
    for i, message in enumerate(st.session_state.conversation_history):
        if message["role"] == "user":
            st.markdown(f'<div style="border: 1px solid lightgray; border-radius: 5px; padding: 10px; background-color: #2D2D2D; color: white;">**用户**: {message["content"]}</div>', unsafe_allow_html=True)
        elif message["role"] == "assistant":
            answer = message['content']
            lines = answer.split('\n')
            short_answer = '\n'.join(lines[:2])  # 截取前两行

            is_expanded = st.session_state.expanded_answers.get(i, False)

            if not is_expanded:
                st.markdown(f'<div style="border: 1px solid lightgray; border-radius: 5px; padding: 10px; background-color: #2D2D2D; color: white;">**AI**: {short_answer}</div>', unsafe_allow_html=True)
                if len(lines) > 2:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"展开", key=f"expand_{i}"):
                            st.session_state.expanded_answers[i] = True
                            st.rerun()
                    with col2:
                        if st.button(f"➕", key=f"rag_{i}"):
                            st.write("添加到 RAG 知识库功能暂未实现，敬请期待！")
            else:
                st.markdown(f'<div style="border: 1px solid lightgray; border-radius: 5px; padding: 10px; background-color: #2D2D2D; color: white;">**AI**: {answer}</div>', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"收起", key=f"collapse_{i}"):
                        st.session_state.expanded_answers[i] = False
                        st.rerun()
                with col2:
                    if st.button(f"➕", key=f"rag_{i}"):
                        st.write("添加到 RAG 知识库功能暂未实现，敬请期待！")

    # 只有在有 AI 答案后才显示新的提问框和提交按钮
    if st.session_state.has_ai_answer:
        new_question = st.text_input("继续提问", "")
        if st.button("提交新问题"):
            # 使用不同的 system role
            new_system_role = "You are an expert in providing in - depth analysis based on previous conversations."
            new_conversation_history = [{"role": "system", "content": new_system_role}] + st.session_state.conversation_history[1:]

            if st.session_state.last_question != new_question:
                new_answer = call_llm(new_question, new_conversation_history)
                st.session_state.conversation_history.append({"role": "user", "content": new_question})
                st.session_state.conversation_history.append({"role": "assistant", "content": new_answer})
                st.session_state.last_question = new_question
                st.session_state.last_answer = new_answer
                st.rerun()

    session.close()

if __name__ == "__main__":
    main()