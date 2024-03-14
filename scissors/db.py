from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

SQLALCHEMY_DATABASE_URL = 'postgresql://iflfhzuc:ydj_lGGltY42TLKLHqEUZLgSWX9sLy6C@ziggy.db.elephantsql.com/iflfhzuc'


engine = create_engine(SQLALCHEMY_DATABASE_URL)

session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()