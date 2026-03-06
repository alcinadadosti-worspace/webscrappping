"""
Analytics CNPJ - FastAPI Backend
Muito mais rapido que Streamlit
"""

from fastapi import FastAPI, Request, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import json
import csv
import io
import os
from datetime import datetime
from typing import List, Optional
import asyncio

# Importa modulos locais
from consulta_cnpj import (
    consultar_cnpj_api, processar_dados_api, gerar_analytics,
    limpar_cnpj, validar_cnpj, salvar_cache, carregar_cache
)
from analise_concorrencia import gerar_relatorio_concorrencia

# =============================================================================
# CONFIGURACAO
# =============================================================================
app = FastAPI(
    title="Analytics CNPJ",
    description="Analise de empresas com dados publicos",
    version="3.0"
)

# Templates
templates = Jinja2Templates(directory="templates")

# Dados em memoria (cache simples)
CACHE_EMPRESAS = []
CACHE_ANALYTICS = {}
CONSULTA_EM_ANDAMENTO = False
PROGRESSO_CONSULTA = {"atual": 0, "total": 0, "cnpj": "", "status": "idle"}

# CNPJs default (Penedo/AL)
CNPJS_DEFAULT = [
    "44.716.179/0001-53", "09.397.499/0005-10", "14.093.245/0001-15",
    "14.407.931/0001-13", "41.190.987/0001-31", "50.484.842/0001-34",
    "31.809.250/0001-09", "19.692.117/0001-01", "02.747.709/0001-80",
    "00.804.030/0001-50", "64.138.749/0001-82", "35.642.768/0004-96",
    "00.360.305/0001-04", "00.000.000/0049-36", "07.237.373/0001-20",
    "60.746.948/0617-66", "41.180.092/0006-20", "48.571.661/0001-01",
    "51.662.502/0001-19", "10.819.605/0001-62", "22.979.541/0001-46",
    "05.740.521/0001-07", "32.860.231/0006-76", "11.857.003/0001-62",
    "54.319.915/0001-93", "26.219.718/0001-67", "52.517.120/0001-64",
    "63.718.970/0001-47", "48.321.599/0001-91", "04.344.950/0001-94",
    "58.257.255/0001-14", "06.017.690/0001-78", "00.416.698/0001-20",
    "21.640.463/0001-98", "09.150.613/0001-80", "17.549.879/0001-28",
    "04.867.949/0001-44", "19.097.309/0001-70", "03.035.253/0001-99",
    "55.494.946/0001-43", "40.188.607/0001-61", "04.281.915/0001-73",
    "01.777.031/0001-16", "60.388.042/0001-73", "05.349.471/0001-23",
    "21.387.751/0001-82", "42.119.864/0001-77", "34.832.249/0001-85",
    "62.838.995/0001-11", "52.799.163/0001-80", "54.226.172/0001-07",
    "48.460.035/0001-30", "15.099.434/0001-68", "25.199.495/0001-50",
    "17.723.320/0001-72", "47.804.779/0001-61", "55.075.878/0001-88",
    "53.445.726/0001-02", "14.750.618/0001-83", "12.711.339/0001-85",
    "00.341.350/0063-14", "00.394.502/0373-07", "00.404.850/0004-06",
    "00.430.642/0004-73", "00.432.229/0006-00", "00.631.670/0001-06",
    "01.140.148/0001-94", "01.207.148/0001-64", "01.234.329/0001-80",
    "01.362.381/0001-11", "01.521.064/0001-09", "01.620.416/0001-75",
    "01.672.001/0001-45", "01.681.228/0006-61", "01.817.989/0001-93",
    "01.877.254/0001-55", "01.900.127/0001-20", "02.056.047/0001-00",
    "02.229.221/0001-61"
]


# =============================================================================
# ROTAS - PAGINAS
# =============================================================================
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Pagina principal"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "cnpjs_default": "\n".join(CNPJS_DEFAULT),
        "total_default": len(CNPJS_DEFAULT)
    })


@app.get("/health")
async def health_check():
    """Health check para UptimeRobot"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# =============================================================================
# ROTAS - API
# =============================================================================
@app.post("/api/consultar")
async def consultar_cnpjs(request: Request, background_tasks: BackgroundTasks):
    """Inicia consulta de CNPJs em background"""
    global CONSULTA_EM_ANDAMENTO, PROGRESSO_CONSULTA, CACHE_EMPRESAS, CACHE_ANALYTICS

    if CONSULTA_EM_ANDAMENTO:
        return JSONResponse({"error": "Consulta ja em andamento"}, status_code=400)

    data = await request.json()
    cnpjs_texto = data.get("cnpjs", "")
    delay = data.get("delay", 3)

    # Parse dos CNPJs
    linhas = cnpjs_texto.strip().split('\n')
    cnpjs = [linha.strip() for linha in linhas if linha.strip()]
    cnpjs = list(dict.fromkeys(cnpjs))  # Remove duplicatas
    cnpjs_validos = [c for c in cnpjs if validar_cnpj(c)]

    if not cnpjs_validos:
        return JSONResponse({"error": "Nenhum CNPJ valido"}, status_code=400)

    # Inicia consulta em background
    CONSULTA_EM_ANDAMENTO = True
    PROGRESSO_CONSULTA = {"atual": 0, "total": len(cnpjs_validos), "cnpj": "", "status": "running"}
    CACHE_EMPRESAS = []

    background_tasks.add_task(processar_cnpjs_background, cnpjs_validos, delay)

    return {"message": "Consulta iniciada", "total": len(cnpjs_validos)}


async def processar_cnpjs_background(cnpjs: List[str], delay: int):
    """Processa CNPJs em background"""
    global CONSULTA_EM_ANDAMENTO, PROGRESSO_CONSULTA, CACHE_EMPRESAS, CACHE_ANALYTICS

    empresas = []

    for i, cnpj in enumerate(cnpjs, 1):
        PROGRESSO_CONSULTA = {
            "atual": i,
            "total": len(cnpjs),
            "cnpj": cnpj,
            "status": "running"
        }

        # Consulta API
        dados_api = consultar_cnpj_api(cnpj)
        empresa = processar_dados_api(dados_api, cnpj)
        empresas.append(empresa)

        # Delay entre requisicoes
        if i < len(cnpjs):
            await asyncio.sleep(delay)

    # Gera analytics
    CACHE_EMPRESAS = empresas
    CACHE_ANALYTICS = gerar_analytics(empresas)

    # Salva cache
    salvar_cache(empresas)

    PROGRESSO_CONSULTA["status"] = "completed"
    CONSULTA_EM_ANDAMENTO = False


@app.get("/api/progresso")
async def get_progresso():
    """Retorna progresso da consulta"""
    return PROGRESSO_CONSULTA


@app.get("/api/resultados")
async def get_resultados():
    """Retorna resultados da consulta"""
    if not CACHE_EMPRESAS:
        # Tenta carregar do cache
        cache = carregar_cache()
        if cache:
            return {
                "empresas": cache.get("empresas", []),
                "analytics": gerar_analytics(cache.get("empresas", [])),
                "from_cache": True
            }
        return {"empresas": [], "analytics": {}, "from_cache": False}

    return {
        "empresas": CACHE_EMPRESAS,
        "analytics": CACHE_ANALYTICS,
        "from_cache": False
    }


@app.get("/api/concorrencia")
async def get_concorrencia(populacao: int = 65000):
    """Retorna analise de concorrencia"""
    if not CACHE_EMPRESAS:
        return {"error": "Nenhum dado disponivel"}

    empresas_validas = [e for e in CACHE_EMPRESAS if e.get("status") == "ok"]
    relatorio = gerar_relatorio_concorrencia(empresas_validas, populacao)

    return relatorio


@app.post("/api/upload")
async def upload_arquivo(file: UploadFile = File(...)):
    """Processa upload de arquivo com CNPJs"""
    conteudo = await file.read()

    try:
        if file.filename.endswith(('.xlsx', '.xls')):
            # Excel - precisa pandas
            import pandas as pd
            df = pd.read_excel(io.BytesIO(conteudo))
            col_cnpj = None
            for col in df.columns:
                if 'cnpj' in col.lower():
                    col_cnpj = col
                    break
            if col_cnpj:
                cnpjs = df[col_cnpj].astype(str).tolist()
            else:
                cnpjs = df.iloc[:, 0].astype(str).tolist()
        else:
            # CSV ou TXT
            texto = conteudo.decode('utf-8')
            if ',' in texto or ';' in texto:
                # CSV
                import pandas as pd
                df = pd.read_csv(io.StringIO(texto), sep=None, engine='python')
                col_cnpj = None
                for col in df.columns:
                    if 'cnpj' in col.lower():
                        col_cnpj = col
                        break
                if col_cnpj:
                    cnpjs = df[col_cnpj].astype(str).tolist()
                else:
                    cnpjs = df.iloc[:, 0].astype(str).tolist()
            else:
                # TXT simples
                cnpjs = [linha.strip() for linha in texto.split('\n') if linha.strip()]

        # Remove duplicatas e invalidos
        cnpjs = list(dict.fromkeys(cnpjs))
        cnpjs_validos = [c for c in cnpjs if validar_cnpj(c)]

        return {
            "cnpjs": cnpjs_validos,
            "total": len(cnpjs_validos),
            "texto": "\n".join(cnpjs_validos)
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/api/exportar/csv")
async def exportar_csv():
    """Exporta dados em CSV"""
    if not CACHE_EMPRESAS:
        return JSONResponse({"error": "Nenhum dado"}, status_code=400)

    output = io.StringIO()
    empresas_validas = [e for e in CACHE_EMPRESAS if e.get("status") == "ok"]

    if empresas_validas:
        writer = csv.DictWriter(output, fieldnames=empresas_validas[0].keys(), delimiter=';')
        writer.writeheader()
        writer.writerows(empresas_validas)

    return HTMLResponse(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=empresas.csv"}
    )


@app.get("/api/exportar/json")
async def exportar_json():
    """Exporta dados em JSON"""
    if not CACHE_EMPRESAS:
        return JSONResponse({"error": "Nenhum dado"}, status_code=400)

    return JSONResponse(
        content={
            "empresas": CACHE_EMPRESAS,
            "analytics": CACHE_ANALYTICS,
            "data_exportacao": datetime.now().isoformat()
        },
        headers={"Content-Disposition": "attachment; filename=empresas.json"}
    )


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    # Cria pasta templates se nao existir
    os.makedirs("templates", exist_ok=True)

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
