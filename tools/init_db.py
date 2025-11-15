# tools/init_db.py
from services.repository.strategy_service import Base, engine  # ajuste se seus nomes forem outros
# Se o engine/Base ficarem noutro arquivo (ex.: api_strategies.py), importe de lá.
Base.metadata.create_all(bind=engine)
print("OK: tabelas criadas/confirmadas.")
