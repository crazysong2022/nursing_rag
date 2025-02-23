from sqlalchemy import MetaData
from models.database import engine, Base
import models.project_models as pm
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO)

def create_tables():
    """
    检查并创建数据库表。
    """
    meta = MetaData()
    meta.reflect(bind=engine)
    
    # 列出需要创建的表对应的模型
    tables_to_create = [
        pm.User,
        pm.NursingTopic,
        pm.MyGoals  # 添加 MyGoals 表
    ]

    for table in tables_to_create:
        if table.__tablename__ not in meta.tables:
            try:
                table.__table__.create(bind=engine)
                logging.info(f"成功创建数据表：{table.__tablename__}")
            except Exception as e:
                logging.error(f"创建数据表 {table.__tablename__} 失败：{e}")
        else:
            logging.info(f"数据表 {table.__tablename__} 已存在，跳过创建。")

if __name__ == '__main__':
    create_tables()