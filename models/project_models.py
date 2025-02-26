from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP,LargeBinary
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(LargeBinary, nullable=False)
    
    nursing_topics = relationship("NursingTopic", back_populates="user")
    my_goals = relationship("MyGoals", back_populates="user")
    projects = relationship("Project", back_populates="user")  # 新增关联
    writings = relationship("Writing", back_populates="user")  # 新增关联
    manuscripts = relationship("Manuscript", back_populates="user")  # 新增关联

class NursingTopic(Base):
    __tablename__ = 'nursing_topics'
    
    id = Column(Integer, primary_key=True, index=True)
    topic_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    sub_content = Column(Text, nullable=False)
    conversation_history = Column(Text, default="")  # 使用 TEXT 类型，默认值为空字符串
    user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(TIMESTAMP, default=text('CURRENT_TIMESTAMP'))
    
    user = relationship("User", back_populates="nursing_topics")

class MyGoals(Base):
    __tablename__ = 'my_goals'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    my_topics = Column(Text, nullable=True)
    my_plans = Column(Text, nullable=True)
    my_articles = Column(Text, nullable=True)
    my_projects = Column(Text, nullable=True)
    my_writings = Column(Text, nullable=True)
    my_manuscripts = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=text('CURRENT_TIMESTAMP'))
    
    user = relationship("User", back_populates="my_goals")

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    project_name = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, default=text('CURRENT_TIMESTAMP'))
    
    user = relationship("User", back_populates="projects")
    data_files = relationship("DataFile", back_populates="project")  # 新增关联

class DataFile(Base):
    __tablename__ = 'data_files'
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    uploaded_at = Column(TIMESTAMP, default=text('CURRENT_TIMESTAMP'))
    
    project = relationship("Project", back_populates="data_files")
    cleaning_reports = relationship("CleaningReport", back_populates="data_file")  # 新增关联

class CleaningReport(Base):
    __tablename__ = 'cleaning_reports'
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey('data_files.id'), nullable=False)
    report_content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=text('CURRENT_TIMESTAMP'))
    
    data_file = relationship("DataFile", back_populates="cleaning_reports")

class Writing(Base):
    __tablename__ = 'writings'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    type = Column(String, nullable=False)  # 撰写类型
    user_input = Column(Text, nullable=False)  # 用户输入的内容
    generated_content = Column(Text, nullable=False)  # 生成的内容
    created_at = Column(TIMESTAMP, default=text('CURRENT_TIMESTAMP'))
    
    user = relationship("User", back_populates="writings")

class Manuscript(Base):
    __tablename__ = 'manuscripts'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # 关联用户
    title = Column(String, nullable=False)  # 文稿标题
    content = Column(Text, nullable=False)  # 文稿内容
    polished_content = Column(Text, nullable=True)  # 润色后的内容
    journal_style = Column(String, nullable=True)  # 目标期刊风格（可选）
    created_at = Column(TIMESTAMP, default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(TIMESTAMP, default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP'))

    user = relationship("User", back_populates="manuscripts")
    reviews = relationship("ReviewerComment", back_populates="manuscript")  # 关联审稿人意见

class ReferencePaper(Base):
    __tablename__ = 'reference_papers'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)  # 参考文稿标题
    content = Column(Text, nullable=False)  # 参考文稿内容
    journal_name = Column(String, nullable=False)  # 期刊名称
    style = Column(Text, nullable=True)  # 新增字段：风格分析结果
    created_at = Column(TIMESTAMP, default=text('CURRENT_TIMESTAMP'))

class ReviewerComment(Base):
    __tablename__ = 'reviewer_comments'

    id = Column(Integer, primary_key=True, index=True)
    manuscript_id = Column(Integer, ForeignKey('manuscripts.id'), nullable=False)  # 关联用户文稿
    comment = Column(Text, nullable=False)  # 审稿人意见
    reply_letter = Column(Text, nullable=True)  # 回复信内容
    revised_content = Column(Text, nullable=True)  # 修改后的文稿内容
    created_at = Column(TIMESTAMP, default=text('CURRENT_TIMESTAMP'))

    manuscript = relationship("Manuscript", back_populates="reviews")