"""
Modulo de integracao com APIs do IBGE
Dados demograficos e economicos por municipio
"""

import requests
import json
import os
from functools import lru_cache

# Cache local para evitar requisicoes repetidas
CACHE_FILE = "cache_ibge.json"


def carregar_cache():
    """Carrega cache do disco"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def salvar_cache(cache):
    """Salva cache no disco"""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except:
        pass


@lru_cache(maxsize=100)
def buscar_municipio_ibge(nome_municipio, uf):
    """
    Busca codigo IBGE do municipio
    """
    try:
        url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            municipios = response.json()
            nome_upper = nome_municipio.upper().strip()

            for mun in municipios:
                if mun['nome'].upper() == nome_upper:
                    return mun['id']

            # Busca parcial
            for mun in municipios:
                if nome_upper in mun['nome'].upper() or mun['nome'].upper() in nome_upper:
                    return mun['id']

        return None
    except Exception as e:
        print(f"Erro ao buscar municipio IBGE: {e}")
        return None


def obter_populacao_municipio(codigo_ibge):
    """
    Obtem populacao estimada do municipio
    Fonte: IBGE Cidades
    """
    cache = carregar_cache()
    cache_key = f"pop_{codigo_ibge}"

    if cache_key in cache:
        return cache[cache_key]

    try:
        # API de populacao estimada
        url = f"https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/-1/variaveis/9324?localidades=N6[{codigo_ibge}]"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                resultados = data[0].get('resultados', [])
                if resultados:
                    series = resultados[0].get('series', [])
                    if series:
                        serie = series[0].get('serie', {})
                        # Pega o valor mais recente
                        for ano in sorted(serie.keys(), reverse=True):
                            valor = serie[ano]
                            if valor and valor != '-':
                                populacao = int(valor)
                                cache[cache_key] = populacao
                                salvar_cache(cache)
                                return populacao

        return None
    except Exception as e:
        print(f"Erro ao obter populacao: {e}")
        return None


def obter_pib_municipio(codigo_ibge):
    """
    Obtem PIB do municipio (ultimo disponivel)
    Fonte: IBGE
    """
    cache = carregar_cache()
    cache_key = f"pib_{codigo_ibge}"

    if cache_key in cache:
        return cache[cache_key]

    try:
        # PIB municipal
        url = f"https://servicodados.ibge.gov.br/api/v3/agregados/5938/periodos/-1/variaveis/37?localidades=N6[{codigo_ibge}]"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                resultados = data[0].get('resultados', [])
                if resultados:
                    series = resultados[0].get('series', [])
                    if series:
                        serie = series[0].get('serie', {})
                        for ano in sorted(serie.keys(), reverse=True):
                            valor = serie[ano]
                            if valor and valor != '-':
                                pib = float(valor) * 1000  # Valor em milhares
                                cache[cache_key] = pib
                                salvar_cache(cache)
                                return pib

        return None
    except Exception as e:
        print(f"Erro ao obter PIB: {e}")
        return None


def obter_pib_per_capita(codigo_ibge):
    """
    Obtem PIB per capita do municipio
    """
    cache = carregar_cache()
    cache_key = f"pib_pc_{codigo_ibge}"

    if cache_key in cache:
        return cache[cache_key]

    try:
        url = f"https://servicodados.ibge.gov.br/api/v3/agregados/5938/periodos/-1/variaveis/543?localidades=N6[{codigo_ibge}]"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                resultados = data[0].get('resultados', [])
                if resultados:
                    series = resultados[0].get('series', [])
                    if series:
                        serie = series[0].get('serie', {})
                        for ano in sorted(serie.keys(), reverse=True):
                            valor = serie[ano]
                            if valor and valor != '-':
                                pib_pc = float(valor)
                                cache[cache_key] = pib_pc
                                salvar_cache(cache)
                                return pib_pc

        return None
    except Exception as e:
        print(f"Erro ao obter PIB per capita: {e}")
        return None


def calcular_fator_economico_ibge(municipio, uf):
    """
    Calcula fator de ajuste economico baseado em dados do IBGE
    Compara com a media nacional
    """
    # PIB per capita medio do Brasil (referencia 2021): ~R$ 41.000
    PIB_PC_REFERENCIA_BRASIL = 41000

    # PIB per capita medio de Sao Paulo capital (referencia): ~R$ 70.000
    PIB_PC_REFERENCIA_SP = 70000

    codigo_ibge = buscar_municipio_ibge(municipio, uf)

    if not codigo_ibge:
        # Fallback para valores default por estado
        fatores_uf = {
            "SP": 0.85, "RJ": 0.75, "MG": 0.65, "PR": 0.70, "RS": 0.70,
            "SC": 0.75, "BA": 0.55, "PE": 0.55, "CE": 0.50, "AL": 0.50,
            "SE": 0.50, "PB": 0.45, "RN": 0.50, "PI": 0.40, "MA": 0.40,
            "GO": 0.65, "DF": 0.95, "MT": 0.70, "MS": 0.65, "ES": 0.65,
            "PA": 0.50, "AM": 0.55, "RO": 0.55, "AC": 0.45, "AP": 0.50,
            "RR": 0.50, "TO": 0.50
        }
        return fatores_uf.get(uf, 0.60)

    pib_pc = obter_pib_per_capita(codigo_ibge)

    if pib_pc:
        # Calcula fator comparando com SP capital (mercado de referencia)
        fator = pib_pc / PIB_PC_REFERENCIA_SP
        # Limita entre 0.3 e 1.5
        fator = max(0.3, min(1.5, fator))
        return round(fator, 3)

    # Fallback
    return 0.60


def obter_dados_completos_municipio(municipio, uf):
    """
    Retorna todos os dados disponiveis do municipio
    """
    codigo_ibge = buscar_municipio_ibge(municipio, uf)

    dados = {
        "municipio": municipio,
        "uf": uf,
        "codigo_ibge": codigo_ibge,
        "populacao": None,
        "pib": None,
        "pib_per_capita": None,
        "fator_economico": None
    }

    if codigo_ibge:
        dados["populacao"] = obter_populacao_municipio(codigo_ibge)
        dados["pib"] = obter_pib_municipio(codigo_ibge)
        dados["pib_per_capita"] = obter_pib_per_capita(codigo_ibge)
        dados["fator_economico"] = calcular_fator_economico_ibge(municipio, uf)
    else:
        dados["fator_economico"] = calcular_fator_economico_ibge(municipio, uf)

    return dados


# Dados pre-carregados de municipios importantes de Alagoas
DADOS_ALAGOAS = {
    "PENEDO": {
        "codigo_ibge": 2706703,
        "populacao_estimada": 65000,
        "pib_per_capita_estimado": 12500,
        "fator_economico": 0.55
    },
    "MACEIO": {
        "codigo_ibge": 2704302,
        "populacao_estimada": 1025000,
        "pib_per_capita_estimado": 22000,
        "fator_economico": 0.75
    },
    "ARAPIRACA": {
        "codigo_ibge": 2700300,
        "populacao_estimada": 235000,
        "pib_per_capita_estimado": 15500,
        "fator_economico": 0.65
    }
}


def obter_dados_alagoas(municipio):
    """
    Retorna dados pre-carregados para municipios de Alagoas
    Mais rapido que consultar API
    """
    mun_upper = municipio.upper().strip()
    return DADOS_ALAGOAS.get(mun_upper, None)


if __name__ == "__main__":
    # Teste
    print("Testando modulo IBGE...")

    dados = obter_dados_completos_municipio("Penedo", "AL")
    print(f"\nDados de Penedo/AL:")
    for k, v in dados.items():
        print(f"  {k}: {v}")

    print(f"\nFator economico calculado: {dados['fator_economico']}")
