from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'picture': self.picture,
        }


class Genre(Base):
    __tablename__ = 'genre'
    id = Column(Integer, primary_key=True)
    type = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'type': self.type,
        }


class Movies(Base):
    __tablename__ = 'movies'
    id = Column(Integer, primary_key=True)
    title = Column(String(250), nullable=False)
    year = Column(String(4))
    plot = Column(String(1000))
    poster = Column(String(250))
    type = Column(String(80), ForeignKey('genre.type'))
    genre = relationship(Genre)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'title': self.title,
            'year': self.year,
            'plot': self.plot,
            'poster': self.poster,
        }


engine = create_engine(
    'postgresql+psycopg2://postgres@3.82.107.127/moviegenre.db')

Base.metadata.create_all(engine)
