"""资讯模型"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, UniqueConstraint, func
from app.database import Base


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), index=True, comment="股票代码，空为宏观新闻")
    title = Column(String(500), nullable=False, comment="新闻标题")
    url = Column(String(500), comment="新闻链接")
    publish_time = Column(TIMESTAMP, comment="发布时间")
    source_site = Column(String(50), comment="来源站点")
    content_preview = Column(Text, comment="内容摘要")
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("title", "url", name="uq_news_title_url"),
        {"sqlite_autoincrement": True},
    )
