
import os,sys
from datetime import datetime
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

DBPath = 'sqlite:///LinkedInJobSkillsDB.db'
Base = declarative_base()

# DEFINE THE TABLES
class CompanySkill( Base ):
    __tablename__ = 'companies'
    id = Column( Integer, primary_key=True )
    timestamp = Column(DateTime, default=datetime.utcnow)
    skill = Column( String( 500 ), nullable=True )
    company = Column( String( 400 ), nullable=True )
    relation_count = Column( Integer, nullable=True )

class RelatedSkill(Base):
    __tablename__ = 'related_skills'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    skill = Column( String(500), nullable=True)
    related_skill = Column( String(500), nullable=True)
    relation_count = Column(Integer, nullable=True)

class RootSkill( Base ):
    __tablename__ = 'root_skills'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    skill = Column(String(500), nullable=True)
    link = Column(String(2083), nullable=True)              # this is max length of url

Engine = create_engine( DBPath )
Base.metadata.create_all( Engine )