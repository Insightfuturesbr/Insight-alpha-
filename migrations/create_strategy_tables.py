"""Migration script to initialize strategy tables."""

from services.repository.strategy_service import Base, engine


def run() -> None:
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    run()
