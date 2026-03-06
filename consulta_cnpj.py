"""
Modulo de Consulta de CNPJ v3
Integra dados da API + IBGE + Analise de Concorrencia
"""

import requests
import time
import json
import os
from datetime import datetime
from collections import defaultdict

# Importa modulos locais
try:
    from dados_ibge import calcular_fator_economico_ibge, obter_dados_completos_municipio
    from analise_concorrencia import classificar_setor, gerar_relatorio_concorrencia
except ImportError:
    # Para rodar standalone
    from dashboard.dados_ibge import calcular_fator_economico_ibge, obter_dados_completos_municipio
    from dashboard.analise_concorrencia import classificar_setor, gerar_relatorio_concorrencia


# =============================================================================
# FATORES DE AJUSTE POR SETOR
# Distribuidoras e atacadistas tem faturamento MUITO maior (alto giro)
# =============================================================================
FATOR_SETOR = {
    # DISTRIBUIDORAS E ATACADO (faturamento alto, mas variavel)
    "distribuidora": 3.0,
    "distribuidor": 3.0,
    "atacado": 2.5,
    "atacadista": 2.5,
    "representacao": 2.5,
    "representante": 2.5,
    "importacao": 3.0,
    "exportacao": 3.0,
    "logistica": 2.5,

    # COMBUSTIVEIS E ENERGIA
    "posto de combustivel": 5.0,
    "combustivel": 5.0,
    "gas": 2.5,
    "energia": 3.0,

    # SUPERMERCADOS E ALIMENTOS
    "supermercado": 3.0,
    "hipermercado": 4.0,
    "mercado": 2.0,
    "mercearia": 0.8,
    "minimercado": 1.0,
    "hortifruti": 1.2,
    "frigorifico": 3.5,
    "acougue": 1.3,

    # ALIMENTACAO
    "restaurante": 1.2, "lanchonete": 0.9, "bar": 0.8, "padaria": 1.3,
    "pizzaria": 1.0, "sorveteria": 0.7, "cafe": 0.6,

    # VESTUARIO
    "vestuario": 0.85, "roupa": 0.85, "calcados": 0.8,
    "moda": 0.85, "confeccao": 1.2, "bijuteria": 0.6, "joalheria": 1.4,
    "otica": 1.1,

    # SAUDE E BELEZA
    "farmacia": 2.0, "drogaria": 2.0,
    "cosmetico": 1.5, "perfumaria": 1.5, "perfume": 1.5,
    "salao": 0.7, "barbearia": 0.5, "estetica": 0.8,
    "clinica": 1.5, "consultorio": 1.2, "hospital": 4.0,
    "odontolog": 1.3, "laboratorio": 2.0,

    # CONSTRUCAO
    "material de construcao": 2.0, "construcao": 2.0,
    "construtora": 3.0, "incorporadora": 4.0,
    "ferragem": 1.2, "cimento": 2.5,

    # VEICULOS
    "concessionaria": 4.0, "automovel": 3.0, "veiculo": 2.5,
    "moto": 1.8, "peca": 1.5, "autopeca": 1.5,
    "oficina": 0.9, "mecanica": 0.9, "borracharia": 0.6,

    # TECNOLOGIA
    "celular": 1.5, "telefon": 1.3, "eletronico": 1.5,
    "informatica": 1.2, "software": 2.0, "tecnologia": 2.0,

    # MOVEIS E ELETRO
    "moveis": 1.5, "eletrodomestico": 1.8, "colchao": 1.2,

    # SERVICOS
    "contabil": 1.0, "advocacia": 1.2, "imobiliaria": 1.5,
    "banco": 5.0, "financeira": 3.0, "credito": 2.5,
    "seguro": 2.5,

    # EDUCACAO
    "escola": 1.5, "faculdade": 3.0, "universidade": 4.0,
    "curso": 0.9, "creche": 0.8,

    # AGRO
    "agropecuaria": 2.0, "agricola": 2.5, "fazenda": 3.0,
    "veterinaria": 0.9, "pet": 0.9,

    # HOTELARIA
    "hotel": 2.0, "pousada": 1.0, "turismo": 1.2,

    # INDUSTRIA
    "industria": 3.0, "fabrica": 3.0, "manufatura": 2.5,
    "metalurgica": 2.5, "siderurgica": 4.0,

    # OUTROS
    "papelaria": 0.7, "grafica": 1.0, "lavanderia": 0.7,
}

# =============================================================================
# FAIXA BASE POR PORTE (ajustado para ser mais realista)
# =============================================================================
FAIXA_PORTE = {
    "MEI": {"min": 0, "max": 81000, "tipico": 50000},
    "Micro Empresa": {"min": 81000, "max": 360000, "tipico": 200000},
    "ME": {"min": 81000, "max": 360000, "tipico": 200000},
    "Empresa de Pequeno Porte": {"min": 360000, "max": 4800000, "tipico": 2000000},
    "EPP": {"min": 360000, "max": 4800000, "tipico": 2000000},
    "Demais": {"min": 4800000, "max": 500000000, "tipico": 25000000},
    "DESCONHECIDO": {"min": 81000, "max": 360000, "tipico": 180000}
}


def limpar_cnpj(cnpj):
    """Remove caracteres especiais do CNPJ"""
    return ''.join(filter(str.isdigit, cnpj))


def validar_cnpj(cnpj):
    """Valida formato do CNPJ"""
    cnpj_limpo = limpar_cnpj(cnpj)
    return len(cnpj_limpo) == 14


def consultar_cnpj_api(cnpj, tentativas=3):
    """
    Consulta CNPJ usando API publica
    Com retry automatico
    """
    cnpj_limpo = limpar_cnpj(cnpj)

    if not validar_cnpj(cnpj):
        return {"erro": "CNPJ invalido"}

    url = f"https://publica.cnpj.ws/cnpj/{cnpj_limpo}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    for tentativa in range(tentativas):
        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # Rate limit - aguarda e tenta novamente
                wait_time = 60 * (tentativa + 1)
                time.sleep(wait_time)
                continue
            elif response.status_code == 404:
                return {"erro": "CNPJ nao encontrado"}
            else:
                return {"erro": f"Erro HTTP {response.status_code}"}

        except requests.exceptions.Timeout:
            if tentativa < tentativas - 1:
                time.sleep(5)
                continue
            return {"erro": "Timeout na requisicao"}
        except Exception as e:
            return {"erro": str(e)}

    return {"erro": "Limite de tentativas excedido"}


def identificar_setor_chave(cnae_descricao):
    """Identifica palavra-chave do setor"""
    if not cnae_descricao:
        return None

    texto = cnae_descricao.lower()

    for chave in FATOR_SETOR.keys():
        if chave in texto:
            return chave

    return None


def calcular_fator_idade(data_abertura):
    """
    Calcula fator de ajuste baseado na idade da empresa
    Empresas mais antigas tendem a ter faturamento mais consolidado
    """
    if not data_abertura or data_abertura == "N/A":
        return 1.0

    try:
        for fmt in ["%Y-%m-%d", "%d/%m/%Y"]:
            try:
                data = datetime.strptime(str(data_abertura)[:10], fmt)
                break
            except:
                continue
        else:
            return 1.0

        anos = (datetime.now() - data).days / 365

        if anos < 1:
            return 0.4   # Empresa nova, ainda estabilizando
        elif anos < 2:
            return 0.6
        elif anos < 3:
            return 0.8
        elif anos < 5:
            return 1.0
        elif anos < 10:
            return 1.3   # Empresa estabelecida
        elif anos < 15:
            return 1.5   # Empresa consolidada
        elif anos < 20:
            return 1.7   # Empresa madura
        else:
            return 2.0   # Empresa muito consolidada (20+ anos)

    except:
        return 1.0


def calcular_fator_capital(capital_social, porte):
    """Calcula fator de ajuste baseado no capital social"""
    if not capital_social:
        return 1.0

    try:
        capital = float(capital_social)
    except:
        return 1.0

    referencias = {
        "MEI": 15000,
        "Micro Empresa": 50000,
        "ME": 50000,
        "Empresa de Pequeno Porte": 200000,
        "EPP": 200000,
        "Demais": 1000000
    }

    ref = referencias.get(porte, 50000)

    if capital < ref * 0.3:
        return 0.85
    elif capital < ref:
        return 1.0
    elif capital < ref * 3:
        return 1.15
    else:
        return 1.3


def estimar_faturamento(porte, cnae_descricao, municipio, uf, data_abertura, capital_social):
    """
    Estimativa de faturamento v4 - melhorada para distribuidoras e empresas grandes
    """
    # Faixa base pelo porte
    faixa = FAIXA_PORTE.get(porte, FAIXA_PORTE["DESCONHECIDO"])
    base = faixa["tipico"]

    # Fator do setor
    setor_chave = identificar_setor_chave(cnae_descricao)
    fator_setor = FATOR_SETOR.get(setor_chave, 1.0) if setor_chave else 1.0

    # Fator regional (IBGE)
    # Distribuidoras/atacadistas vendem para outras regioes, menor penalizacao
    setores_nao_locais = ["distribuidora", "distribuidor", "atacado", "atacadista",
                          "importacao", "exportacao", "representacao", "industria",
                          "fabrica", "logistica"]

    if setor_chave in setores_nao_locais:
        # Empresas que vendem para fora nao sao tao afetadas pela economia local
        fator_regional = 0.85  # Penalizacao menor
    else:
        fator_regional = calcular_fator_economico_ibge(municipio, uf) if municipio else 0.6

    # Fator idade
    fator_idade = calcular_fator_idade(data_abertura)

    # Fator capital (menos peso para empresas grandes, capital declarado nem sempre reflete realidade)
    if porte == "Demais":
        fator_capital = 1.0  # Ignora capital para empresas grandes
    else:
        fator_capital = calcular_fator_capital(capital_social, porte)

    # Calculo final
    faturamento = base * fator_setor * fator_regional * fator_idade * fator_capital

    # Limita dentro da faixa (mais flexivel para cima)
    faturamento_min = faixa["min"] * 0.3
    faturamento_max = faixa["max"] * 2.0  # Permite ir acima do max para empresas excepcionais
    faturamento = max(faturamento_min, min(faturamento, faturamento_max))

    return {
        "anual": round(faturamento, 2),
        "mensal": round(faturamento / 12, 2),
        "faixa_min": faixa["min"],
        "faixa_max": faixa["max"],
        "fatores": {
            "base": base,
            "setor": setor_chave or "generico",
            "fator_setor": round(fator_setor, 3),
            "fator_regional": round(fator_regional, 3),
            "fator_idade": round(fator_idade, 3),
            "fator_capital": round(fator_capital, 3)
        }
    }


def processar_dados_api(dados_api, cnpj_original):
    """
    Processa dados retornados pela API e enriquece com estimativas
    """
    if not dados_api or "erro" in dados_api:
        return {
            "cnpj": cnpj_original,
            "status": "erro",
            "erro": dados_api.get("erro", "Erro desconhecido") if dados_api else "Sem dados",
            "razao_social": "NAO ENCONTRADO"
        }

    estab = dados_api.get('estabelecimento', {})
    porte_info = dados_api.get('porte', {})

    # Extrai dados basicos
    porte = porte_info.get('descricao', 'DESCONHECIDO') if isinstance(porte_info, dict) else str(porte_info)

    cnae_principal = estab.get('atividade_principal', {})
    cnae_descricao = cnae_principal.get('descricao', 'N/A') if isinstance(cnae_principal, dict) else 'N/A'
    cnae_codigo = cnae_principal.get('id', 'N/A') if isinstance(cnae_principal, dict) else 'N/A'

    cidade_info = estab.get('cidade', {})
    municipio = cidade_info.get('nome', 'N/A') if isinstance(cidade_info, dict) else 'N/A'

    estado_info = estab.get('estado', {})
    uf = estado_info.get('sigla', 'N/A') if isinstance(estado_info, dict) else 'N/A'

    data_abertura = estab.get('data_inicio_atividade', 'N/A')
    capital_social = dados_api.get('capital_social', 0)

    # Calcula estimativa de faturamento
    faturamento = estimar_faturamento(
        porte, cnae_descricao, municipio, uf, data_abertura, capital_social
    )

    # Classifica setor
    setor_classificado = classificar_setor(cnae_descricao)

    # Monta objeto final
    empresa = {
        "cnpj": cnpj_original,
        "cnpj_limpo": limpar_cnpj(cnpj_original),
        "status": "ok",
        "razao_social": dados_api.get('razao_social', 'N/A'),
        "nome_fantasia": estab.get('nome_fantasia', '') or 'N/A',
        "situacao_cadastral": estab.get('situacao_cadastral', 'N/A'),
        "logradouro": estab.get('logradouro', 'N/A'),
        "numero": estab.get('numero', 'N/A'),
        "complemento": estab.get('complemento', ''),
        "bairro": estab.get('bairro', 'N/A'),
        "municipio": municipio,
        "uf": uf,
        "cep": estab.get('cep', 'N/A'),
        "cnae_codigo": cnae_codigo,
        "cnae_descricao": cnae_descricao,
        "setor_classificado": setor_classificado,
        "porte": porte,
        "capital_social": capital_social,
        "data_abertura": data_abertura,
        "natureza_juridica": dados_api.get('natureza_juridica', {}).get('descricao', 'N/A') if isinstance(dados_api.get('natureza_juridica'), dict) else 'N/A',
        "telefone": (estab.get('ddd1', '') or '') + (estab.get('telefone1', '') or ''),
        "email": estab.get('email', 'N/A'),

        # Faturamento estimado
        "faturamento_anual_estimado": faturamento["anual"],
        "faturamento_mensal_estimado": faturamento["mensal"],
        "faturamento_faixa_min": faturamento["faixa_min"],
        "faturamento_faixa_max": faturamento["faixa_max"],

        # Fatores usados no calculo
        "fator_setor": faturamento["fatores"]["fator_setor"],
        "fator_regional": faturamento["fatores"]["fator_regional"],
        "fator_idade": faturamento["fatores"]["fator_idade"],
        "fator_capital": faturamento["fatores"]["fator_capital"],

        # Metadados
        "data_consulta": datetime.now().isoformat(),
        "fonte": "publica.cnpj.ws"
    }

    return empresa


def consultar_lote(cnpjs, callback_progresso=None, delay=3):
    """
    Consulta lista de CNPJs com callback de progresso
    Ideal para uso em interfaces (Streamlit, etc)
    """
    resultados = []
    total = len(cnpjs)
    cnpjs_unicos = list(dict.fromkeys(cnpjs))  # Remove duplicatas

    for i, cnpj in enumerate(cnpjs_unicos, 1):
        if callback_progresso:
            callback_progresso(i, total, cnpj)

        # Consulta API
        dados_api = consultar_cnpj_api(cnpj)

        # Processa dados
        empresa = processar_dados_api(dados_api, cnpj)
        resultados.append(empresa)

        # Delay entre requisicoes
        if i < len(cnpjs_unicos):
            time.sleep(delay)

    return resultados


def gerar_analytics(empresas):
    """
    Gera analytics completo das empresas
    """
    empresas_validas = [e for e in empresas if e.get("status") == "ok"]

    if not empresas_validas:
        return {"erro": "Nenhuma empresa valida encontrada"}

    # Por bairro
    por_bairro = defaultdict(lambda: {"quantidade": 0, "faturamento": 0, "empresas": []})
    for emp in empresas_validas:
        bairro = emp.get("bairro", "N/A")
        por_bairro[bairro]["quantidade"] += 1
        por_bairro[bairro]["faturamento"] += emp.get("faturamento_anual_estimado", 0)
        por_bairro[bairro]["empresas"].append(emp["razao_social"])

    # Por setor
    por_setor = defaultdict(lambda: {"quantidade": 0, "faturamento": 0, "empresas": []})
    for emp in empresas_validas:
        setor = emp.get("setor_classificado", "outros")
        por_setor[setor]["quantidade"] += 1
        por_setor[setor]["faturamento"] += emp.get("faturamento_anual_estimado", 0)
        por_setor[setor]["empresas"].append(emp["razao_social"])

    # Por porte
    por_porte = defaultdict(lambda: {"quantidade": 0, "faturamento": 0})
    for emp in empresas_validas:
        porte = emp.get("porte", "DESCONHECIDO")
        por_porte[porte]["quantidade"] += 1
        por_porte[porte]["faturamento"] += emp.get("faturamento_anual_estimado", 0)

    # Totais
    faturamento_total = sum(e.get("faturamento_anual_estimado", 0) for e in empresas_validas)

    # Top empresas
    top_empresas = sorted(empresas_validas, key=lambda x: x.get("faturamento_anual_estimado", 0), reverse=True)[:10]

    return {
        "resumo": {
            "total_consultados": len(empresas),
            "total_encontrados": len(empresas_validas),
            "total_erros": len(empresas) - len(empresas_validas),
            "faturamento_anual_total": faturamento_total,
            "faturamento_mensal_total": faturamento_total / 12,
            "faturamento_medio": faturamento_total / len(empresas_validas) if empresas_validas else 0,
        },
        "por_bairro": dict(por_bairro),
        "por_setor": dict(por_setor),
        "por_porte": dict(por_porte),
        "top_empresas": [
            {"razao_social": e["razao_social"], "setor": e["setor_classificado"], "faturamento": e["faturamento_anual_estimado"]}
            for e in top_empresas
        ]
    }


# Cache de resultados
CACHE_RESULTADOS = {}


def salvar_cache(empresas, nome="cache_empresas"):
    """Salva resultados em cache local"""
    arquivo = f"{nome}.json"
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump({
            "data": datetime.now().isoformat(),
            "empresas": empresas
        }, f, ensure_ascii=False, indent=2)
    return arquivo


def carregar_cache(nome="cache_empresas"):
    """Carrega resultados do cache"""
    arquivo = f"{nome}.json"
    if os.path.exists(arquivo):
        with open(arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


if __name__ == "__main__":
    # Teste
    print("Testando consulta de CNPJ...")

    cnpj_teste = "44.716.179/0001-53"
    dados = consultar_cnpj_api(cnpj_teste)

    if dados and "erro" not in dados:
        empresa = processar_dados_api(dados, cnpj_teste)
        print(f"\nEmpresa: {empresa['razao_social']}")
        print(f"Setor: {empresa['setor_classificado']}")
        print(f"Faturamento estimado: R$ {empresa['faturamento_anual_estimado']:,.2f}/ano")
        print(f"Fatores: setor={empresa['fator_setor']}, regional={empresa['fator_regional']}, idade={empresa['fator_idade']}")
    else:
        print(f"Erro: {dados}")
