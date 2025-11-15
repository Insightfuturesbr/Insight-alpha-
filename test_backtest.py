
import os
import logging
from app.core.orchestrator import InsightFutures
import pandas as pd

# Configure logging to display INFO level messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_test():
    """
    Runs a test of the backtesting process.
    """
    logging.info("Starting backtest test...")

    # Path to the input file
    file_path = "/home/hector/Documents/repo/insight-futures-project/insight-Futures-Py/dataset/operacoes.xlsx"

    # Check if the file exists
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return

    # --- User Parameters ---
    # These parameters will be passed to the backtest process, simulating user input.
    parametros_usuario = {
        # Activation rule
        'ativar_automacao': True,
        'ativacao_percentual': 20,
        'ativacao_base': 'media_drawdowns',
        'comparador_ativacao': 'mais_severo',

        # Pause rule
        'pausar_automacao': True,
        'pausa_percentual': 20,
        'pausa_base': 'media_lucros',
        'comparador_pausa': 'maior_que',

        # Deactivation rule
        'desativar_automacao': True,
        'desativacao_percentual': 80,
        'desativacao_base': 'maior_drawdown_historico',
        'comparador_desativacao': 'mais_severo',
    }

    try:
        # 1. Initialize the InsightFutures class
        # This will process the input file and prepare the data for the backtest.
        insight_futures = InsightFutures(file_path=file_path)
        
        # 2. Run the complete backtest
        logging.info("Running complete backtest...")
        insight_futures.rodar_backtest_completo(parametros_usuario)

        # 3. Log the results
        logging.info("Backtest finished. Logging results...")
        
        # Check if the results are available
        if hasattr(insight_futures, 'df_backtest') and insight_futures.df_backtest is not None:
            logging.info("Backtest DataFrame (first 5 rows):")
            print(insight_futures.df_backtest.head())
        else:
            logging.warning("df_backtest not found or is None.")

        if hasattr(insight_futures, 'metricas_backtest'):
            logging.info("Backtest Metrics:")
            print(insight_futures.metricas_backtest)
        else:
            logging.warning("metricas_backtest not found.")

        if hasattr(insight_futures, 'metricas_original'):
            logging.info("Original Metrics:")
            print(insight_futures.metricas_original)
        else:
            logging.warning("metricas_original not found.")

    except Exception as e:
        logging.error(f"An error occurred during the backtest: {e}", exc_info=True)

if __name__ == "__main__":
    run_test()
