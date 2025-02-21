from sqlalchemy import Column, Integer, String, Text, ForeignKey,TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    
    nursing_topics = relationship("NursingTopic", back_populates="user")

class NursingTopic(Base):
    __tablename__ = 'nursing_topics'
    
    id = Column(Integer, primary_key=True, index=True)
    topic_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    conversation_history = Column(Text, default="")  # 使用 TEXT 类型，默认值为空字符串
    user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(TIMESTAMP, default=text('CURRENT_TIMESTAMP'))
    
    user = relationship("User", back_populates="nursing_topics")

