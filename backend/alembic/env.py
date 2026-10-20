from logging.config import fileConfig

from alembic import context

import app.auth.models  # noqa: F401  Imported so each domain's tables register themselves on Base.metadata.
import app.kyc.models  # noqa: F401
from app.core.database import Base, engine

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
