from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    
    nursing_topics = relationship("NursingTopic", back_populates="user")
    my_goals = relationship("MyGoals", back_populates="user")
    projects = relationship("Project", back_populates="user")  # 新增关联
    writings = relationship("Writing", back_populates="user")  # 新增关联

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

