
"""
This module contains helper functions and data for header detection and normalization.
"""
import re
import unicodedata
from typing import List, Dict, Union, Tuple

CANONICAL_HEADERS = [
    'Ativo',
    'Abertura',
    'Fechamento',
    'Tempo Operação',
    'Qtd Compra',
    'Qtd Venda',
    'Lado',
    'Preço Compra',
    'Preço Venda',
    'Preço de Mercado',
    'Médio',
    'Res. Intervalo Bruto',
    'Res. Intervalo (%)',
    'Número Operação',
    'Res. Operação (%)',
    'Res. Operação',
    'Drawdown',
    'Ganho Max.',
    'Perda Max.',
    'TET',
    'Total',
]

VARIATIONS: Dict[str, List[Union[str, re.Pattern]]] = {
    'Ativo': ['ativo', 'ticker', 'simbolo', 'symbol', 'papel'],
    'Abertura': [
        'abertura',
        'data',
        'data entrada',
        'data hora entrada',
        'entrada',
        'open time',
    ],
    'Fechamento': [
        'fechamento',
        'data saida',
        'saida',
        'data hora saida',
        'close time',
    ],
    'Tempo Operação': [
        'tempo operacao',
        'duracao',
        'tempo',
        'tempo trade',
        'tempo execucao',
    ],
    'Qtd Compra': [
        'quantidade compra',
        'qtd compra',
        'qtde compra',
        'qtdcompras',
        'qtdcompra',
    ],
    'Qtd Venda': [
        'quantidade venda',
        'qtd venda',
        'qtde venda',
        'qtdvendas',
        'qtdvenda',
    ],
    'Lado': ['lado', 'direcao', 'side', 'compra venda', 'c v', 'long short'],
    'Preço Compra': [
        'preco compra',
        'preco de compra',
        'precoentrada',
        'preco entrada',
        'preco buy',
    ],
    'Preço Venda': [
        'preco venda',
        'preco de venda',
        'preco saida',
        'preco saida venda',
        'preco sell',
    ],
    'Preço de Mercado': [
        'preco de mercado',
        'preco mercado',
        'market price',
        'preco mark',
        'preco ref',
        'mark',
    ],
    'Médio': ['medio', 'preco medio', 'preco medio ponderado', 'pm', 'media preco'],
    'Res. Intervalo Bruto': [
        'res intervalo bruto',
        'resultado intervalo bruto',
        'resultado bruto',
        'pnl bruto',
        'p l bruto',
    ],
    'Res. Intervalo (%)': [
        'res intervalo',
        'res intervalo pct',
        'resultado intervalo pct',
        'resultado intervalo %',
    ],
    'Número Operação': [
        'numero operacao',
        'n operacao',
        'num operacao',
        'id trade',
        'trade #',
    ],
    'Res. Operação': [
        'res operacao',
        'resultado operacao',
        'pnl',
        'p l',
        'resultado',
    ],
    'Res. Operação (%)': [
        'res operacao pct',
        'resultado operacao pct',
        'pnl pct',
        'retorno pct',
    ],
    'Drawdown': ['drawdown', 'dd', 'max drawdown', 'queda', 'rebaixamento'],
    'Ganho Max.': [
        'ganho max',
        'max gain',
        'melhor ganho',
        'melhor trade',
        'max profit',
    ],
    'Perda Max.': [
        'perda max',
        'max loss',
        'pior trade',
        'worst trade',
        'max draw',
    ],
    'TET': [
        'tet',
        'tempo entre trades',
        'tempo entre operacoes',
        'elapsed',
        'cooldown',
    ],
    'Total': [
        'total',
        'total acumulado',
        'resultado total',
        'saldo',
        'equity delta',
    ],
}

def norm(s: object) -> str:
    if s is None:
        return ''
    s = str(s)
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = s.lower()
    s = re.sub(r'[().]', ' ', s)
    s = re.sub(r'[^a-z0-9% ]+', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def normalize_tokens(s: str) -> str:
    s = re.sub(r'\bqtde?\b', 'quantidade', s)
    s = re.sub(r'\bqtd\b', 'quantidade', s)
    s = re.sub(r'\bcompra(s)?\b', 'compra', s)
    s = re.sub(r'\bvenda(s)?\b', 'venda', s)
    s = re.sub(r'\bpreco\b', 'preco', s)
    s = re.sub(r'\boperacao(oes|es)?\b', 'operacao', s)
    
    s = re.sub(r'\bintervalo\b', 'intervalo', s)
    s = re.sub(r'\bmax\b', 'max', s)
    s = re.sub(r'\bmedio\b', 'medio', s)
    s = re.sub(r'\bporcentagem\b', 'pct', s)
    s = re.sub(r'\bpercentual\b', 'pct', s)
    return s

def levenshtein(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[m][n]

def similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    dist = levenshtein(a, b)
    return 1 - dist / max(len(a), len(b), 1)

CANON_NORM: List[Tuple[str, str]] = [(c, normalize_tokens(norm(c))) for c in CANONICAL_HEADERS]

VARIATIONS_NORM: Dict[str, List[Union[str, re.Pattern]]] = {
    c: [v if isinstance(v, re.Pattern) else normalize_tokens(norm(v)) for v in VARIATIONS[c]]
    for c in CANONICAL_HEADERS
}
