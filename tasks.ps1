param(
    [string]$Task
)

# Descobre o Python no venv
if (Test-Path .\.venv\Scripts\python.exe) {
    $py = ".\.venv\Scripts\python.exe"
    $pip = ".\.venv\Scripts\pip.exe"
} else {
    $py = "python"
    $pip = "pip"
}

switch ($Task) {
    "run" {
        Write-Host "Rodando aplicacao..."
        & $py main.py
    }
    "lint" {
        Write-Host "Rodando linter..."
        & $py -m flake8 app/
    }
    "test" {
        Write-Host "Rodando testes (sem integracao)..."
        & $py -m pytest -q -m "not integration"
    }
    "cov" {
        Write-Host "Cobertura (tudo)..."
        & $py -m pytest --cov=app --cov-report=term-missing
    }
    "clean" {
        Write-Host "Limpando arquivos temporarios..."
        Remove-Item -Recurse -Force .pytest_cache, __pycache__, outputs -ErrorAction SilentlyContinue
    }
    default {
        Write-Host "Tarefa nao reconhecida. Use: run, lint, test, clean"
    }
}
