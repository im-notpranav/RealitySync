from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

# Naming convention for Alembic auto-generation
POSTGRES_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=POSTGRES_NAMING_CONVENTION)


class Base(AsyncAttrs, DeclarativeBase):
    """Declarative base. Every model sets `__tablename__` explicitly to the name in 05.

    Table names are not derived from class names: naive pluralisation produced names such as
    `entitys` that do not match the schema contract.
    """

    metadata = metadata
