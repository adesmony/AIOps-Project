import ssl

import asyncpg
from azure.identity.aio import DefaultAzureCredential
from pgvector.asyncpg import register_vector
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.config import Settings


class SqlAlchemyDatabaseProvider:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._sessions = async_sessionmaker(engine, expire_on_commit=False)

    def session(self):
        return self._sessions()

    @property
    def session_factory(self) -> async_sessionmaker:
        return self._sessions

    async def health_check(self) -> bool:
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def close(self) -> None:
        await self._engine.dispose()


class DevelopmentPostgresProvider(SqlAlchemyDatabaseProvider):
    def __init__(self, settings: Settings) -> None:
        if settings.database_url is None:
            raise ValueError("DATABASE_URL is required for Development")
        url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        super().__init__(
            create_async_engine(
                url,
                pool_pre_ping=True,
                connect_args={"command_timeout": settings.database_timeout_seconds},
            )
        )


class ManagedIdentityPostgresProvider(SqlAlchemyDatabaseProvider):
    def __init__(self, settings: Settings) -> None:
        if not all(
            (
                settings.azure_postgres_host,
                settings.azure_postgres_database,
                settings.azure_postgres_user,
            )
        ):
            raise ValueError("Azure PostgreSQL managed identity settings are incomplete")
        self._settings = settings
        self._credential = DefaultAzureCredential()
        super().__init__(
            create_async_engine(
                "postgresql+asyncpg://",
                async_creator=self._connect,
                pool_pre_ping=True,
            )
        )

    async def _connect(self) -> asyncpg.Connection:
        token = await self._credential.get_token(
            "https://ossrdbms-aad.database.windows.net/.default"
        )
        context = ssl.create_default_context()
        connection = await asyncpg.connect(
            host=self._settings.azure_postgres_host,
            database=self._settings.azure_postgres_database,
            user=self._settings.azure_postgres_user,
            password=token.token,
            ssl=context,
            command_timeout=self._settings.database_timeout_seconds,
        )
        await register_vector(connection)
        return connection

    async def close(self) -> None:
        await super().close()
        await self._credential.close()


def create_database_provider(settings: Settings) -> SqlAlchemyDatabaseProvider:
    if settings.is_development:
        return DevelopmentPostgresProvider(settings)
    return ManagedIdentityPostgresProvider(settings)
