import streamlit as st
from sqlalchemy.orm import sessionmaker
from models.database import engine, Base
from models.project_models import User, Manuscript, ReferencePaper, ReviewerComment
from dotenv import load_dotenv
import os
import pdfplumber
from openai import OpenAI
from datetime import datetime

# Load environment variables
load_dotenv()

# Create database session
Session = sessionmaker(bind=engine)
session = Session()

# Initialize OpenAI client
try:
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
except Exception as e:
    st.error(f"初始化 OpenAI 客户端失败，请检查配置。错误信息: {e}")
    raise

# Define system role
system_role = """
你是医学研究领域的专家，特别擅长护理方面的科研选题。
"""

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "writing_prompts" not in st.session_state:
    st.session_state.writing_prompts = []

# Helper function: Extract text from PDF
def extract_text_from_pdf(file):
    try:
        with pdfplumber.open(file) as pdf:
            text = ""
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted
        return text
    except Exception as e:
        st.error(f"无法提取 PDF 内容：{e}")
        return None

# Helper function: Call OpenAI model for style analysis or text generation
def call_language_model(prompt, max_tokens=500, temperature=0.7):
    try:
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        full_response = ""
        for chunk in response:
            if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    content = delta.content
                    full_response += content
                    yield content  # Stream content
        st.session_state.full_response = full_response  # Store complete response
    except Exception as e:
        st.error(f"调用 OpenAI 模型失败：{e}")
        raise

# Main program
def main():
    st.title("我的投稿助手")

    # Get current user
    username = st.session_state.get('user')
    user = session.query(User).filter(User.username == username).first()
    if not user:
        st.error("未找到当前用户，请登录后再试。")
        return

    # Function module selection
    st.sidebar.subheader("功能模块")
    module = st.sidebar.selectbox("选择功能模块", [
        "参考文稿风格分析",
        "基于风格创作文稿",
        "审稿意见处理"
    ])

    if module == "参考文稿风格分析":
        analyze_reference_paper(user)
    elif module == "基于风格创作文稿":
        generate_manuscript(user)
    elif module == "审稿意见处理":
        handle_reviewer_feedback(user)

# Function module 1: Reference paper style analysis
def analyze_reference_paper(user):
    st.subheader("参考文稿风格分析")

    uploaded_file = st.file_uploader("上传参考文稿", type=["pdf", "txt"])
    if uploaded_file:
        file_type = uploaded_file.type.split("/")[-1]
        if file_type == "pdf":
            content = extract_text_from_pdf(uploaded_file)
        elif file_type == "txt":
            content = uploaded_file.read().decode("utf-8")
        else:
            st.error("不支持的文件类型")
            return

        st.text_area("参考文稿内容", value=content, height=300)
        analysis_type = st.selectbox("选择分析类型", ["写作风格", "格式规范", "语言特点"])

        # 使用 session_state 存储 AI 生成的结果
        if "analysis_result" not in st.session_state:
            st.session_state.analysis_result = None

        # 开始分析按钮
        if st.button("开始分析", key="analyze_button"):
            prompt = f"请分析以下参考文稿的{analysis_type}：\n{content}"
            placeholder = st.empty()  # 创建一个占位符
            analysis_result = ""
            for chunk in call_language_model(prompt):
                analysis_result += chunk
                placeholder.write(analysis_result)  # 流式输出内容
            st.success("风格分析完成！")

            # 将生成的结果存储到 session_state
            st.session_state.analysis_result = analysis_result

        # 显示生成的结果（如果存在）
        if st.session_state.analysis_result:
            st.write("生成的分析结果：")
            st.write(st.session_state.analysis_result)

        # 确认并保存分析结果按钮
        if st.button("确认并保存分析结果", key="save_analysis_button"):
            if st.session_state.analysis_result:
                # 保存分析结果到数据库
                new_reference = ReferencePaper(
                    title="Reference Paper",
                    content=content,
                    journal_name="Example Journal",
                    style=st.session_state.analysis_result,  # 使用 session_state 中的结果
                    created_at=datetime.now()
                )
                session.add(new_reference)
                session.commit()
                st.success("分析结果已成功保存到数据库。")
                # 清空 session_state 中的结果
                del st.session_state.analysis_result
            else:
                st.warning("请先点击“开始分析”生成结果。")

# Function module 2: Manuscript generation based on style
def generate_manuscript(user):
    st.subheader("基于风格创作文稿")

    references = session.query(ReferencePaper).all()
    if not references:
        st.warning("请先上传并分析参考文稿以获取风格数据。")
        return

    reference_options = {f"{ref.id}: {ref.title}" for ref in references}
    selected_reference = st.selectbox("选择参考文稿风格", list(reference_options))
    selected_ref_id = int(selected_reference.split(":")[0])
    guidelines = st.text_area("输入创作规范（可选）", height=100)

    # Use session_state to track button clicks
    if "generate_clicked" not in st.session_state:
        st.session_state.generate_clicked = False

    if st.button("生成文稿", key="generate_button"):
        st.session_state.generate_clicked = True

    if st.session_state.generate_clicked:
        reference = session.query(ReferencePaper).filter(ReferencePaper.id == selected_ref_id).first()
        if not reference:
            st.error("未找到对应的参考文稿。")
            return

        prompt = f"根据以下参考文稿的风格和创作规范生成文稿：\n\n参考文稿风格：{reference.style}\n\n创作规范：{guidelines}"
        placeholder = st.empty()  # Create a placeholder
        generated_content = ""
        for chunk in call_language_model(prompt):
            generated_content += chunk
            placeholder.write(generated_content)  # Stream content
        st.success("文稿生成完成！")

        # Save generated manuscript to database
        if st.button("保存文稿", key="save_manuscript_button"):
            if "full_response" in st.session_state:
                new_manuscript = Manuscript(
                    user_id=user.id,
                    title="Generated Manuscript",
                    content=st.session_state.full_response,
                    polished_content=None,
                    journal_style=reference.style,  # Associate with reference paper style
                    created_at=datetime.now()
                )
                session.add(new_manuscript)
                session.commit()
                st.success("文稿已成功保存到数据库。")
                del st.session_state.full_response  # Clear session_state content
                st.session_state.generate_clicked = False  # Reset button state

# Function module 3: Reviewer feedback handling
def handle_reviewer_feedback(user):
    st.subheader("审稿意见处理")

    manuscripts = session.query(Manuscript).all()
    if not manuscripts:
        st.warning("请先上传或生成文稿以处理审稿意见。")
        return

    manuscript_options = {f"{man.id}: {man.title}" for man in manuscripts}
    selected_manuscript = st.selectbox("选择文稿", list(manuscript_options))
    selected_man_id = int(selected_manuscript.split(":")[0])
    reviewer_comment = st.text_area("输入审稿人意见", height=200)
    action = st.radio("选择操作", ["修改原文", "撰写回复信"])

    # Use session_state to track button clicks
    if "handle_feedback_clicked" not in st.session_state:
        st.session_state.handle_feedback_clicked = False

    if st.button("处理审稿意见", key="handle_feedback_button"):
        st.session_state.handle_feedback_clicked = True

    if st.session_state.handle_feedback_clicked:
        manuscript = session.query(Manuscript).filter(Manuscript.id == selected_man_id).first()
        if not manuscript:
            st.error("未找到对应的文稿。")
            return

        if action == "修改原文":
            prompt = f"根据以下审稿意见修改原文：\n\n原文：{manuscript.content}\n\n审稿意见：{reviewer_comment}"
            placeholder = st.empty()  # Create a placeholder
            revised_content = ""
            for chunk in call_language_model(prompt):
                revised_content += chunk
                placeholder.write(revised_content)  # Stream content
            st.success("原文修改完成！")

            # Save revised content to database
            if st.button("保存修改结果", key="save_revision_button"):
                if "full_response" in st.session_state:
                    new_review = ReviewerComment(
                        manuscript_id=manuscript.id,
                        comment=reviewer_comment,
                        reply_letter=None,
                        revised_content=st.session_state.full_response,
                        created_at=datetime.now()
                    )
                    session.add(new_review)
                    session.commit()
                    st.success("修改结果已成功保存到数据库。")
                    del st.session_state.full_response  # Clear session_state content
                    st.session_state.handle_feedback_clicked = False  # Reset button state

        elif action == "撰写回复信":
            prompt = f"根据以下审稿意见撰写回复信：\n\n审稿意见：{reviewer_comment}"
            placeholder = st.empty()  # Create a placeholder
            reply_letter = ""
            for chunk in call_language_model(prompt):
                reply_letter += chunk
                placeholder.write(reply_letter)  # Stream content
            st.success("回复信生成完成！")

            # Save reply letter to database
            if st.button("保存回复信", key="save_reply_button"):
                if "full_response" in st.session_state:
                    new_review = ReviewerComment(
                        manuscript_id=manuscript.id,
                        comment=reviewer_comment,
                        reply_letter=st.session_state.full_response,
                        revised_content=None,
                        created_at=datetime.now()
                    )
                    session.add(new_review)
                    session.commit()
                    st.success("回复信已成功保存到数据库。")
                    del st.session_state.full_response  # Clear session_state content
                    st.session_state.handle_feedback_clicked = False  # Reset button state

if __name__ == "__main__":
    main()