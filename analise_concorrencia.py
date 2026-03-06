"""
Modulo de Analise de Concorrencia
Identifica saturacao de mercado, oportunidades e competicao por setor/bairro
"""

from collections import defaultdict
import math


# Demanda esperada por setor (empresas por 10.000 habitantes)
# Baseado em medias nacionais e estudos do SEBRAE
DEMANDA_SETOR_POR_10K_HAB = {
    # Alimentacao
    "restaurante": 8.0,
    "lanchonete": 6.0,
    "bar": 5.0,
    "padaria": 3.0,
    "acougue": 2.5,
    "pizzaria": 2.0,
    "sorveteria": 1.5,

    # Comercio essencial
    "farmacia": 3.5,
    "supermercado": 2.0,
    "mercado": 4.0,
    "minimercado": 5.0,
    "hortifruti": 2.0,
    "posto de combustivel": 1.5,
    "gas": 2.0,

    # Vestuario
    "vestuario": 6.0,
    "roupa": 6.0,
    "calcados": 3.0,
    "moda": 4.0,
    "bijuteria": 2.0,

    # Servicos
    "salao": 8.0,
    "barbearia": 5.0,
    "estetica": 3.0,
    "otica": 1.5,
    "relojoaria": 0.8,

    # Construcao
    "material de construcao": 2.5,
    "ferragem": 2.0,

    # Veiculos
    "oficina": 4.0,
    "mecanica": 3.0,
    "autopeca": 2.5,
    "borracharia": 2.0,
    "moto": 1.5,

    # Tecnologia
    "celular": 2.5,
    "informatica": 1.5,

    # Educacao
    "escola": 1.0,
    "curso": 2.0,

    # Saude
    "clinica": 2.0,
    "consultorio": 3.0,
    "laboratorio": 0.8,

    # Outros
    "pet": 2.0,
    "papelaria": 1.5,
    "floricultura": 0.8,
    "hotel": 0.5,
    "pousada": 0.5,

    # Default
    "outros": 3.0
}


def classificar_setor(cnae_descricao):
    """
    Classifica o setor baseado na descricao do CNAE
    Retorna a chave do setor para analise
    """
    if not cnae_descricao:
        return "outros"

    texto = cnae_descricao.lower()

    # Ordem importa - mais especifico primeiro
    palavras_chave = [
        ("posto de combustivel", "posto de combustivel"),
        ("combustivel", "posto de combustivel"),
        ("material de construcao", "material de construcao"),
        ("construcao", "material de construcao"),
        ("supermercado", "supermercado"),
        ("minimercado", "minimercado"),
        ("mercado", "mercado"),
        ("mercearia", "mercado"),
        ("hortifruti", "hortifruti"),
        ("restaurante", "restaurante"),
        ("lanchonete", "lanchonete"),
        ("pizzaria", "pizzaria"),
        ("sorveteria", "sorveteria"),
        ("padaria", "padaria"),
        ("acougue", "acougue"),
        ("bar", "bar"),
        ("farmacia", "farmacia"),
        ("drogaria", "farmacia"),
        ("roupa", "vestuario"),
        ("vestuario", "vestuario"),
        ("confeccao", "vestuario"),
        ("moda", "vestuario"),
        ("calcado", "calcados"),
        ("sapato", "calcados"),
        ("bijuteria", "bijuteria"),
        ("joalheria", "bijuteria"),
        ("otica", "otica"),
        ("relojoaria", "relojoaria"),
        ("salao", "salao"),
        ("cabeleireiro", "salao"),
        ("barbearia", "barbearia"),
        ("estetica", "estetica"),
        ("beleza", "estetica"),
        ("cosmetico", "estetica"),
        ("perfumaria", "estetica"),
        ("oficina", "oficina"),
        ("mecanica", "mecanica"),
        ("autopeca", "autopeca"),
        ("peca", "autopeca"),
        ("borracharia", "borracharia"),
        ("pneu", "borracharia"),
        ("moto", "moto"),
        ("celular", "celular"),
        ("telefon", "celular"),
        ("informatica", "informatica"),
        ("computador", "informatica"),
        ("eletronico", "informatica"),
        ("escola", "escola"),
        ("ensino", "escola"),
        ("curso", "curso"),
        ("clinica", "clinica"),
        ("consultorio", "consultorio"),
        ("medic", "consultorio"),
        ("odonto", "consultorio"),
        ("laboratorio", "laboratorio"),
        ("pet", "pet"),
        ("veterinaria", "pet"),
        ("animal", "pet"),
        ("papelaria", "papelaria"),
        ("livraria", "papelaria"),
        ("floricultura", "floricultura"),
        ("hotel", "hotel"),
        ("pousada", "pousada"),
        ("hospedagem", "pousada"),
        ("gas", "gas"),
        ("ferragem", "ferragem"),
        ("ferramenta", "ferragem"),
    ]

    for palavra, categoria in palavras_chave:
        if palavra in texto:
            return categoria

    return "outros"


def calcular_indice_saturacao(qtd_empresas_setor, populacao, setor):
    """
    Calcula indice de saturacao do mercado

    Retorna:
    - < 0.5: Mercado com oportunidade (poucas empresas para demanda)
    - 0.5 a 1.5: Mercado equilibrado
    - > 1.5: Mercado saturado (muita concorrencia)
    """
    if not populacao or populacao == 0:
        return None

    demanda_esperada = DEMANDA_SETOR_POR_10K_HAB.get(setor, 3.0)

    # Empresas esperadas para a populacao
    empresas_esperadas = (populacao / 10000) * demanda_esperada

    if empresas_esperadas == 0:
        return None

    # Indice: empresas reais / empresas esperadas
    indice = qtd_empresas_setor / empresas_esperadas

    return round(indice, 2)


def analisar_concorrencia_bairro(empresas, populacao_municipio=65000):
    """
    Analisa concorrencia por bairro

    Retorna analise detalhada de cada bairro com:
    - Setores presentes
    - Indice de saturacao por setor
    - Oportunidades identificadas
    """
    # Estima populacao por bairro (distribuicao simplificada)
    bairros = defaultdict(list)

    for emp in empresas:
        if emp.get("razao_social") != "NAO ENCONTRADO":
            bairro = emp.get("bairro", "NAO INFORMADO")
            if bairro == "N/A":
                bairro = "NAO INFORMADO"
            bairros[bairro].append(emp)

    # Estima populacao por bairro baseado em quantidade de empresas
    total_empresas = sum(len(emps) for emps in bairros.values())

    analise_bairros = {}

    for bairro, emps in bairros.items():
        # Estima populacao proporcional ao numero de empresas
        # Bairros com mais empresas tendem a ter mais populacao/movimento
        if total_empresas > 0:
            fator_bairro = len(emps) / total_empresas
            pop_estimada_bairro = populacao_municipio * fator_bairro * 1.5  # Ajuste
        else:
            pop_estimada_bairro = 5000

        # Agrupa por setor
        setores_bairro = defaultdict(list)
        for emp in emps:
            setor = classificar_setor(emp.get("setor", ""))
            setores_bairro[setor].append(emp)

        # Analisa cada setor no bairro
        analise_setores = {}
        for setor, emps_setor in setores_bairro.items():
            saturacao = calcular_indice_saturacao(
                len(emps_setor),
                pop_estimada_bairro,
                setor
            )

            analise_setores[setor] = {
                "quantidade": len(emps_setor),
                "empresas": [e["razao_social"] for e in emps_setor],
                "indice_saturacao": saturacao,
                "status": classificar_status_saturacao(saturacao),
                "faturamento_total": sum(e.get("faturamento_anual_estimado", 0) for e in emps_setor)
            }

        analise_bairros[bairro] = {
            "total_empresas": len(emps),
            "populacao_estimada": int(pop_estimada_bairro),
            "setores": analise_setores,
            "faturamento_total": sum(e.get("faturamento_anual_estimado", 0) for e in emps)
        }

    return analise_bairros


def classificar_status_saturacao(indice):
    """
    Classifica o status do mercado baseado no indice de saturacao
    """
    if indice is None:
        return "indefinido"
    elif indice < 0.3:
        return "grande_oportunidade"
    elif indice < 0.7:
        return "oportunidade"
    elif indice < 1.3:
        return "equilibrado"
    elif indice < 2.0:
        return "competitivo"
    else:
        return "saturado"


def identificar_oportunidades(analise_bairros, populacao_municipio=65000):
    """
    Identifica oportunidades de mercado (setores com demanda nao atendida)
    """
    oportunidades = []

    # Analisa setores que deveriam existir mas nao existem ou sao escassos
    setores_presentes = defaultdict(int)

    for bairro, dados in analise_bairros.items():
        for setor, info in dados["setores"].items():
            setores_presentes[setor] += info["quantidade"]

    # Verifica setores com demanda esperada
    for setor, demanda in DEMANDA_SETOR_POR_10K_HAB.items():
        empresas_esperadas = (populacao_municipio / 10000) * demanda
        empresas_existentes = setores_presentes.get(setor, 0)

        if empresas_esperadas > 0:
            taxa_cobertura = empresas_existentes / empresas_esperadas

            if taxa_cobertura < 0.5:
                gap = int(empresas_esperadas - empresas_existentes)
                oportunidades.append({
                    "setor": setor,
                    "empresas_existentes": empresas_existentes,
                    "demanda_esperada": round(empresas_esperadas, 1),
                    "gap": gap,
                    "taxa_cobertura": round(taxa_cobertura * 100, 1),
                    "potencial": "alto" if taxa_cobertura < 0.3 else "medio",
                    "descricao": f"Faltam aproximadamente {gap} empresas de {setor} para atender a demanda"
                })

    # Ordena por potencial
    oportunidades.sort(key=lambda x: x["taxa_cobertura"])

    return oportunidades


def calcular_score_competitivo(empresa, todas_empresas):
    """
    Calcula score competitivo da empresa em relacao aos concorrentes

    Fatores:
    - Tempo de mercado (idade)
    - Localizacao (bairro com mais ou menos concorrencia)
    - Porte relativo
    - Setor (mais ou menos saturado)
    """
    setor = classificar_setor(empresa.get("setor", ""))
    bairro = empresa.get("bairro", "")

    # Conta concorrentes diretos (mesmo setor, mesmo bairro)
    concorrentes_diretos = sum(
        1 for e in todas_empresas
        if classificar_setor(e.get("setor", "")) == setor
        and e.get("bairro") == bairro
        and e.get("cnpj") != empresa.get("cnpj")
    )

    # Concorrentes no municipio (mesmo setor)
    concorrentes_municipio = sum(
        1 for e in todas_empresas
        if classificar_setor(e.get("setor", "")) == setor
        and e.get("cnpj") != empresa.get("cnpj")
    )

    # Score base
    score = 50

    # Ajuste por idade (empresas mais antigas = mais estabelecidas)
    fator_idade = empresa.get("fator_idade", 1.0)
    score += (fator_idade - 1) * 20  # -10 a +4 pontos

    # Ajuste por concorrencia local
    if concorrentes_diretos == 0:
        score += 15  # Monopolio local
    elif concorrentes_diretos <= 2:
        score += 5
    elif concorrentes_diretos > 5:
        score -= 10

    # Ajuste por porte
    porte = empresa.get("porte", "")
    if "Pequeno Porte" in porte or "EPP" in porte:
        score += 10
    elif "Demais" in porte:
        score += 15

    # Normaliza entre 0 e 100
    score = max(0, min(100, score))

    return {
        "score": round(score),
        "concorrentes_bairro": concorrentes_diretos,
        "concorrentes_municipio": concorrentes_municipio,
        "classificacao": classificar_score(score)
    }


def classificar_score(score):
    """Classifica o score competitivo"""
    if score >= 80:
        return "excelente"
    elif score >= 60:
        return "bom"
    elif score >= 40:
        return "regular"
    elif score >= 20:
        return "desafiador"
    else:
        return "critico"


def gerar_relatorio_concorrencia(empresas, populacao_municipio=65000):
    """
    Gera relatorio completo de analise de concorrencia
    """
    empresas_validas = [e for e in empresas if e.get("razao_social") != "NAO ENCONTRADO"]

    # Analise por bairro
    analise_bairros = analisar_concorrencia_bairro(empresas_validas, populacao_municipio)

    # Identificar oportunidades
    oportunidades = identificar_oportunidades(analise_bairros, populacao_municipio)

    # Score competitivo de cada empresa
    for emp in empresas_validas:
        emp["score_competitivo"] = calcular_score_competitivo(emp, empresas_validas)

    # Ranking de setores mais competitivos
    setores_competitividade = defaultdict(lambda: {"empresas": 0, "faturamento": 0})
    for emp in empresas_validas:
        setor = classificar_setor(emp.get("setor", ""))
        setores_competitividade[setor]["empresas"] += 1
        setores_competitividade[setor]["faturamento"] += emp.get("faturamento_anual_estimado", 0)

    return {
        "analise_bairros": analise_bairros,
        "oportunidades": oportunidades,
        "setores_competitividade": dict(setores_competitividade),
        "empresas_com_score": empresas_validas,
        "resumo": {
            "total_bairros": len(analise_bairros),
            "total_setores": len(setores_competitividade),
            "total_oportunidades": len(oportunidades),
            "bairro_mais_empresas": max(analise_bairros.items(), key=lambda x: x[1]["total_empresas"])[0] if analise_bairros else None,
            "setor_mais_presente": max(setores_competitividade.items(), key=lambda x: x[1]["empresas"])[0] if setores_competitividade else None
        }
    }


if __name__ == "__main__":
    # Teste com dados de exemplo
    empresas_teste = [
        {"razao_social": "Farmacia A", "setor": "Comercio varejista de medicamentos", "bairro": "CENTRO", "faturamento_anual_estimado": 200000, "fator_idade": 1.2},
        {"razao_social": "Farmacia B", "setor": "Comercio varejista de medicamentos", "bairro": "CENTRO", "faturamento_anual_estimado": 180000, "fator_idade": 1.0},
        {"razao_social": "Restaurante X", "setor": "Restaurantes e similares", "bairro": "CENTRO", "faturamento_anual_estimado": 150000, "fator_idade": 0.8},
        {"razao_social": "Loja Roupas", "setor": "Comercio varejista de vestuario", "bairro": "CENTRO HISTORICO", "faturamento_anual_estimado": 100000, "fator_idade": 1.1},
    ]

    relatorio = gerar_relatorio_concorrencia(empresas_teste, 65000)

    print("=== RELATORIO DE CONCORRENCIA ===\n")
    print(f"Resumo: {relatorio['resumo']}")
    print(f"\nOportunidades identificadas: {len(relatorio['oportunidades'])}")
    for op in relatorio['oportunidades'][:5]:
        print(f"  - {op['setor']}: {op['descricao']}")
