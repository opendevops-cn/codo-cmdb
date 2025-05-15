from sqlalchemy import Column, Integer, String, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

from models.base import TimeBaseModel

Base = declarative_base()


class CBBBigAreaModels(TimeBaseModel, Base):
    __tablename__ = "t_cbb_big_area"

    id = Column("id", Integer, primary_key=True, autoincrement=True)
    biz_id = Column("biz_id", String(15), index=True, comment="业务ID")
    env_id = Column("env_id", String(15), index=True, comment="环境ID")
    big_area = Column("big_area", String(255), index=True, comment="大区")
    idip = Column("idip", String(255), comment="idip")
    app_secret = Column("app_secret", Text, comment="app_secret")
    description = Column("description", String(255), default="", comment="备注")

    __table_args__ = (UniqueConstraint("biz_id", "env_id", "big_area", name="biz_env_big_area_unique"),)
