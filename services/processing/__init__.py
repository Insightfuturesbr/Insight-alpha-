
"""
Módulo: preprocessing
Responsabilidade: Realiza o pré-processamento dos dados brutos da planilha de operações.
Inclui limpeza de colunas, tratamento de tipos, cálculo do resultado bruto e líquido original,
formatação de datas e geração de campos necessários para análise futura.

Pré-requisitos:
- DataFrame contendo colunas do Profit ou MetaTrader (com nomes como 'Resultado', 'Taxa', 'Abertura', etc.)

Gera:
- Colunas padronizadas de valores (resultado bruto, líquido, taxas)
- Datas no formato datetime
- Colunas auxiliares como 'Caixa Líquido', 'Resultado Líquido Acumulado', etc.

---

Module: preprocessing
Responsibility: Handles initial preprocessing of raw operation data from trading platforms.
Includes column renaming, type parsing, calculation of original gross and net results,
date formatting, and generation of derived fields for later analysis.

Prerequisites:
- DataFrame with columns from Profit or MetaTrader (e.g., 'Resultado', 'Taxa', 'Abertura', etc.)

Outputs:
- Standardized numeric columns (gross/net result, fees)
- Datetime-formatted dates
- Helper columns such as 'Caixa Líquido', 'Resultado Líquido Acumulado', etc.
"""
