import streamlit as st
import pandas as pd
import numpy as np
import os
import json
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from models.database import engine, Base
from models.project_models import User, Project, DataFile, CleaningReport
from datetime import datetime
from sklearn.impute import SimpleImputer
import plotly.express as px

# 加载环境变量
load_dotenv()

# 数据库会话管理
Session = sessionmaker(bind=engine)
session = Session()

def create_project(session, user_id, project_name):
    new_project = Project(user_id=user_id, project_name=project_name, created_at=datetime.now())
    session.add(new_project)
    session.commit()
    st.success("项目创建成功！")

def get_user_projects(session, user_id):
    return session.query(Project).filter(Project.user_id == user_id).all()

def upload_data_file(session, project_id, file_name, file_path):
    new_file = DataFile(project_id=project_id, file_name=file_name, file_path=file_path, uploaded_at=datetime.now())
    session.add(new_file)
    session.commit()
    st.success("文件上传成功！")

def get_project_data_files(session, project_id):
    return session.query(DataFile).filter(DataFile.project_id == project_id).all()

def clean_data(file_path):
    try:
        data = pd.read_csv(file_path)
        
        # 分离数值列和非数值列
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        non_numeric_columns = data.select_dtypes(exclude=[np.number]).columns
        
        # 对数值列应用 SimpleImputer 的 mean 策略
        if not numeric_columns.empty:
            imputer = SimpleImputer(strategy='mean')
            data[numeric_columns] = imputer.fit_transform(data[numeric_columns])
        
        # 对非数值列应用 SimpleImputer 的 most_frequent 策略
        if not non_numeric_columns.empty:
            imputer = SimpleImputer(strategy='most_frequent')
            data[non_numeric_columns] = imputer.fit_transform(data[non_numeric_columns])
        
        # 生成清洗报告
        report = {
            "missing_values_before": data.isnull().sum().to_dict(),
            "missing_values_after": data.isnull().sum().to_dict(),
            "summary_statistics": data.describe().to_dict()
        }
        
        return data, report
    except Exception as e:
        st.error(f"数据清洗失败: {e}")
        return None, None

def generate_cleaning_report(data_imputed):
    report = data_imputed.describe().to_json()
    return report

def save_cleaning_report(session, file_id, report_content):
    try:
        new_report = CleaningReport(file_id=file_id, report_content=report_content, created_at=datetime.now())
        session.add(new_report)
        session.commit()
        st.success("清洗报告保存成功！")
    except Exception as e:
        session.rollback()  # 回滚事务
        st.error(f"保存清洗报告失败: {e}")

def display_projects(session, user_id):
    projects = get_user_projects(session, user_id)
    if not projects:
        st.info("您还没有任何项目。")
        return
    
    st.write("### 我的项目")
    for project in projects:
        with st.expander(project.project_name[:30] + "...", expanded=False):
            st.write(project.project_name)

def generate_analysis_code(description):
    # 这里可以扩展为更复杂的逻辑，根据描述生成代码
    python_code = f"""
    import pandas as pd
    import seaborn as sns
    import matplotlib.pyplot as plt

    # Load data
    data = pd.read_csv('data.csv')

    # {description}
    sns.pairplot(data)
    plt.show()
    """
    r_code = f"""
    library(ggplot2)

    # Load data
    data <- read.csv('data.csv')

    # {description}
    ggplot(data, aes(x=variable1, y=variable2)) + geom_point()
    """
    spss_code = f"""
    * Load data.
    GET FILE='data.csv'.

    * {description}.
    GRAPH
      /SCATTERPLOT(BIVAR)=variable1 WITH variable2
      /MISSING=LISTWISE.
    """
    return python_code, r_code, spss_code

def display_analysis_results(data):
    st.write("### 数据分析结果")
    
    # 描述性统计
    st.write("#### 描述性统计")
    st.write(data.describe())
    
    # 相关性分析
    st.write("#### 相关性分析")
    numeric_columns = data.select_dtypes(include=[np.number]).columns
    if not numeric_columns.empty:
        correlation_matrix = data[numeric_columns].corr()
        st.write(correlation_matrix)
        fig = px.imshow(correlation_matrix, text_auto=True, aspect="auto")
        st.plotly_chart(fig)
    else:
        st.info("数据中没有数值列，无法进行相关性分析。")
    
    # 可视化
    st.write("#### 可视化")
    chart_type = st.selectbox("选择图表类型", ["直方图", "箱线图", "散点图"])
    if chart_type == "直方图":
        column = st.selectbox("选择列", data.columns)
        fig = px.histogram(data, x=column)
        st.plotly_chart(fig)
    elif chart_type == "箱线图":
        column = st.selectbox("选择列", data.columns)
        fig = px.box(data, y=column)
        st.plotly_chart(fig)
    elif chart_type == "散点图":
        x_column = st.selectbox("选择X轴列", data.columns)
        y_column = st.selectbox("选择Y轴列", data.columns)
        fig = px.scatter(data, x=x_column, y=y_column)
        st.plotly_chart(fig)

def main():
    st.title("我的项目")
    
    # 获取当前用户
    username = st.session_state.get('user')
    user = session.query(User).filter(User.username == username).first()
    if not user:
        st.error("未找到当前用户，请登录后再试。")
        return
    
    # 确保用户目录存在
    user_dir = os.path.join("data", username)
    os.makedirs(user_dir, exist_ok=True)

    # 展示已存储的项目
    display_projects(session, user.id)
    
    # 创建新项目
    project_name = st.text_input("项目名称")
    if st.button("创建项目"):
        create_project(session, user.id, project_name)

    # 获取当前用户的项目
    projects = get_user_projects(session, user.id)
    if not projects:
        st.info("您还没有创建任何项目，请先创建项目。")
        return
    
    # 下拉框：选择项目
    selected_project = st.selectbox("请选择项目", projects, format_func=lambda project: project.project_name)
    
    # 上传数据文件
    st.write("### 上传数据文件")
    uploaded_file = st.file_uploader("上传文件", type=["csv"])
    if uploaded_file is not None:
        file_name = uploaded_file.name
        file_path = os.path.join(user_dir, file_name)
        uploaded_file.seek(0)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())
        upload_data_file(session, selected_project.id, file_name, file_path)

    # 显示项目数据文件
    st.write("### 数据文件列表")
    data_files = get_project_data_files(session, selected_project.id)
    selected_file = st.selectbox("选择一个数据文件", data_files, format_func=lambda file: file.file_name)

    # 数据清洗
    st.write("### 数据清洗")
    if st.button("开始清洗"):
        file_path = os.path.join(user_dir, selected_file.file_name)
        data_imputed, report = clean_data(file_path)
        if data_imputed is not None:
            st.write("清洗后的数据预览：")
            st.dataframe(data_imputed.head())
            st.write("清洗报告：")
            st.json(report)
            if st.button("确认并保存清洗报告"):
                report_content = json.dumps(report)
                save_cleaning_report(session, selected_file.id, report_content)

    # 数据分析
    st.write("### 数据分析")
    analysis_description = st.text_area("请输入数据分析需求描述")
    if st.button("生成分析代码"):
        python_code, r_code, spss_code = generate_analysis_code(analysis_description)
        st.write("#### Python代码")
        st.code(python_code, language="python")
        st.write("#### R代码")
        st.code(r_code, language="r")
        st.write("#### SPSS代码")
        st.code(spss_code, language="spss")

    # 结果呈现和解读
    st.write("### 结果呈现和解读")
    if st.button("展示分析结果"):
        file_path = os.path.join(user_dir, selected_file.file_name)
        data = pd.read_csv(file_path)
        display_analysis_results(data)

if __name__ == "__main__":
    main()