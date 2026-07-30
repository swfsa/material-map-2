from sqlmodel import create_engine, Session
from config import require_database_url


engine = create_engine(
    require_database_url(),
    echo=False,#把 SQL 打印到终端，方便学习和排错；

    pool_pre_ping=True,#使用连接前先确认连接仍有效；

    pool_recycle=3600#定期回收旧连接，减少 MySQL 主动断开连接带来的问题。
)

def get_session():

    return Session(engine)