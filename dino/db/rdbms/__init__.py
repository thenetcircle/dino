from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Integer, Column, ForeignKey, UniqueConstraint


DeclarativeBase = declarative_base()

rooms_users_association_table = Table(
        'rooms_users_association_table',
        DeclarativeBase.metadata,
        Column('room_id', Integer, ForeignKey('rooms.id')),
        Column('user_id', Integer, ForeignKey('users.id')),
        UniqueConstraint('room_id', 'user_id', name='UC_room_id_user_id')
)
