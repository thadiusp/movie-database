from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class Editor(Base):
    __tablename__ = 'editor'

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
    editor_id = Column(Integer, ForeignKey('editor.id'))
    editor = relationship(Editor)

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
    genre_id = Column(Integer, ForeignKey('genre.id'))
    genre = relationship(Genre)
    editor_id = Column(Integer, ForeignKey('editor.id'))
    editor = relationship(Editor)

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
    'postgresql://catalog:password@localhost/moviegenre')

Base.metadata.create_all(engine)
print('The tables have been built.')
