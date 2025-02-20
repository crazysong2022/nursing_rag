from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from models.database import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True)
    password = Column(String(255))

    # 关联护理选题信息
    nursing_topics = relationship("NursingTopic", back_populates="user")


class NursingTopic(Base):
    __tablename__ = 'nursing_topics'
    id = Column(Integer, primary_key=True, index=True)
    topic_type = Column(String(255))
    content = Column(Text)

    # 关联用户
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="nursing_topics")