"""Valida DDL do migrador dentro de uma transação sempre revertida."""

from sqlalchemy import create_engine, text

from argos.config import Settings
from argos.infrastructure.database.config import build_migration_database_url


def main() -> None:
    settings = Settings()
    engine = create_engine(build_migration_database_url(settings))

    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text("SET ROLE argos_migrator"))
                active_role = connection.scalar(text("SELECT current_user"))
                if active_role != "argos_migrator":
                    raise RuntimeError("Não foi possível assumir argos_migrator.")

                connection.execute(
                    text(
                        "CREATE TABLE public.argos_migrator_validation "
                        "(id bigint PRIMARY KEY)"
                    )
                )
                connection.execute(
                    text("DROP TABLE public.argos_migrator_validation")
                )
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
