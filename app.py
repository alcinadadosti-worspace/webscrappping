"""
Dashboard de Analytics de CNPJs - Penedo/AL
Streamlit App para Render Web Service
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import time

# Importa modulos locais
from consulta_cnpj import (
    consultar_cnpj_api, processar_dados_api, gerar_analytics,
    consultar_lote, salvar_cache, carregar_cache, limpar_cnpj, validar_cnpj
)
from analise_concorrencia import gerar_relatorio_concorrencia, classificar_setor
from dados_ibge import obter_dados_completos_municipio

# =============================================================================
# CONFIGURACAO DA PAGINA
# =============================================================================
st.set_page_config(
    page_title="Analytics CNPJ - Penedo/AL",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .stProgress > div > div > div > div {
        background-color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# FUNCOES AUXILIARES
# =============================================================================
def formatar_moeda(valor):
    """Formata valor como moeda brasileira"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def criar_grafico_barras(dados, x, y, titulo, cor="#1f77b4"):
    """Cria grafico de barras com Plotly"""
    fig = px.bar(
        dados, x=x, y=y,
        title=titulo,
        color_discrete_sequence=[cor]
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=False,
        height=400
    )
    return fig


def criar_grafico_pizza(dados, valores, nomes, titulo):
    """Cria grafico de pizza com Plotly"""
    fig = px.pie(
        values=valores, names=nomes,
        title=titulo,
        hole=0.4
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    return fig


# =============================================================================
# SIDEBAR - ENTRADA DE DADOS
# =============================================================================
st.sidebar.markdown("## 📋 Entrada de CNPJs")

# Lista completa de CNPJs (Penedo/AL)
CNPJS_DEFAULT = """44.716.179/0001-53
09.397.499/0005-10
14.093.245/0001-15
14.407.931/0001-13
41.190.987/0001-31
50.484.842/0001-34
31.809.250/0001-09
19.692.117/0001-01
02.747.709/0001-80
00.804.030/0001-50
64.138.749/0001-82
35.642.768/0004-96
00.360.305/0001-04
00.000.000/0049-36
07.237.373/0001-20
60.746.948/0617-66
41.180.092/0006-20
48.571.661/0001-01
51.662.502/0001-19
10.819.605/0001-62
22.979.541/0001-46
05.740.521/0001-07
32.860.231/0006-76
11.857.003/0001-62
54.319.915/0001-93
26.219.718/0001-67
52.517.120/0001-64
63.718.970/0001-47
48.321.599/0001-91
04.344.950/0001-94
58.257.255/0001-14
06.017.690/0001-78
00.416.698/0001-20
21.640.463/0001-98
09.150.613/0001-80
17.549.879/0001-28
04.867.949/0001-44
19.097.309/0001-70
03.035.253/0001-99
55.494.946/0001-43
40.188.607/0001-61
04.281.915/0001-73
01.777.031/0001-16
60.388.042/0001-73
05.349.471/0001-23
21.387.751/0001-82
42.119.864/0001-77
34.832.249/0001-85
62.838.995/0001-11
52.799.163/0001-80
54.226.172/0001-07
48.460.035/0001-30
15.099.434/0001-68
25.199.495/0001-50
17.723.320/0001-72
47.804.779/0001-61
55.075.878/0001-88
53.445.726/0001-02
14.750.618/0001-83
12.711.339/0001-85
00.341.350/0063-14
00.394.502/0373-07
00.404.850/0004-06
00.430.642/0004-73
00.432.229/0006-00
00.631.670/0001-06
01.140.148/0001-94
01.207.148/0001-64
01.234.329/0001-80
01.362.381/0001-11
01.521.064/0001-09
01.620.416/0001-75
01.672.001/0001-45
01.681.228/0006-61
01.817.989/0001-93
01.877.254/0001-55
01.900.127/0001-20
02.056.047/0001-00
02.229.221/0001-61"""

# Opcao de entrada
st.sidebar.markdown("### Escolha como inserir os CNPJs:")
metodo_entrada = st.sidebar.radio(
    "Metodo de entrada:",
    ["📝 Colar/Digitar", "📁 Upload de Arquivo"],
    label_visibility="collapsed"
)

cnpjs_input = ""

if metodo_entrada == "📁 Upload de Arquivo":
    st.sidebar.markdown("**Formatos aceitos:** CSV, TXT, Excel")
    arquivo = st.sidebar.file_uploader(
        "Selecione o arquivo:",
        type=["csv", "txt", "xlsx", "xls"],
        label_visibility="collapsed"
    )

    if arquivo:
        try:
            if arquivo.name.endswith(('.xlsx', '.xls')):
                # Excel
                df_upload = pd.read_excel(arquivo)
                # Procura coluna com CNPJ
                col_cnpj = None
                for col in df_upload.columns:
                    if 'cnpj' in col.lower():
                        col_cnpj = col
                        break
                if col_cnpj:
                    cnpjs_input = '\n'.join(df_upload[col_cnpj].astype(str).tolist())
                else:
                    # Usa primeira coluna
                    cnpjs_input = '\n'.join(df_upload.iloc[:, 0].astype(str).tolist())
                st.sidebar.success(f"✅ {len(cnpjs_input.split(chr(10)))} CNPJs carregados")
            else:
                # CSV ou TXT
                conteudo = arquivo.read().decode('utf-8')
                # Tenta detectar se e CSV
                if ',' in conteudo or ';' in conteudo:
                    import io
                    df_upload = pd.read_csv(io.StringIO(conteudo), sep=None, engine='python')
                    col_cnpj = None
                    for col in df_upload.columns:
                        if 'cnpj' in col.lower():
                            col_cnpj = col
                            break
                    if col_cnpj:
                        cnpjs_input = '\n'.join(df_upload[col_cnpj].astype(str).tolist())
                    else:
                        cnpjs_input = '\n'.join(df_upload.iloc[:, 0].astype(str).tolist())
                else:
                    # Texto simples, um CNPJ por linha
                    cnpjs_input = conteudo
                st.sidebar.success(f"✅ Arquivo carregado")
        except Exception as e:
            st.sidebar.error(f"Erro ao ler arquivo: {e}")
            cnpjs_input = CNPJS_DEFAULT
    else:
        st.sidebar.info("👆 Selecione um arquivo")
        cnpjs_input = ""
else:
    # Area de texto para CNPJs
    cnpjs_input = st.sidebar.text_area(
        "Cole os CNPJs (um por linha):",
        value=CNPJS_DEFAULT,
        height=300
    )

# Configuracoes
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Configuracoes")

delay_requisicao = st.sidebar.slider(
    "Delay entre requisicoes (segundos):",
    min_value=1, max_value=10, value=3
)

populacao_municipio = st.sidebar.number_input(
    "Populacao do municipio:",
    min_value=1000, max_value=10000000, value=65000
)

# Botao de consulta
consultar = st.sidebar.button("🔍 Consultar CNPJs", type="primary", use_container_width=True)

# Carregar cache
st.sidebar.markdown("---")
if st.sidebar.button("📂 Carregar ultima consulta"):
    cache = carregar_cache()
    if cache:
        st.session_state['empresas'] = cache.get('empresas', [])
        st.session_state['data_consulta'] = cache.get('data', '')
        st.sidebar.success("Cache carregado!")
    else:
        st.sidebar.warning("Nenhum cache encontrado")


# =============================================================================
# PAGINA PRINCIPAL
# =============================================================================
st.markdown('<h1 class="main-header">📊 Analytics de CNPJs</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: gray;">Analise de empresas com dados publicos + IBGE</p>', unsafe_allow_html=True)

# Inicializa session state
if 'empresas' not in st.session_state:
    st.session_state['empresas'] = []

# =============================================================================
# PROCESSAMENTO DE CNPJs
# =============================================================================
if consultar:
    # Parse dos CNPJs
    linhas = cnpjs_input.strip().split('\n')
    cnpjs = [linha.strip() for linha in linhas if linha.strip()]

    # Valida CNPJs
    cnpjs_validos = [c for c in cnpjs if validar_cnpj(c)]
    cnpjs_invalidos = [c for c in cnpjs if not validar_cnpj(c)]

    if cnpjs_invalidos:
        st.warning(f"⚠️ {len(cnpjs_invalidos)} CNPJs invalidos serao ignorados")

    if not cnpjs_validos:
        st.error("❌ Nenhum CNPJ valido encontrado")
    else:
        st.info(f"🔄 Consultando {len(cnpjs_validos)} CNPJs... (isso pode levar alguns minutos)")

        # Barra de progresso
        progress_bar = st.progress(0)
        status_text = st.empty()

        empresas = []
        for i, cnpj in enumerate(cnpjs_validos, 1):
            status_text.text(f"Consultando: {cnpj} ({i}/{len(cnpjs_validos)})")
            progress_bar.progress(i / len(cnpjs_validos))

            dados_api = consultar_cnpj_api(cnpj)
            empresa = processar_dados_api(dados_api, cnpj)
            empresas.append(empresa)

            if i < len(cnpjs_validos):
                time.sleep(delay_requisicao)

        st.session_state['empresas'] = empresas
        st.session_state['data_consulta'] = datetime.now().isoformat()

        # Salva cache
        salvar_cache(empresas)

        progress_bar.empty()
        status_text.empty()
        st.success(f"✅ Consulta concluida! {len([e for e in empresas if e.get('status') == 'ok'])} empresas encontradas")


# =============================================================================
# EXIBICAO DOS RESULTADOS
# =============================================================================
if st.session_state['empresas']:
    empresas = st.session_state['empresas']
    empresas_validas = [e for e in empresas if e.get('status') == 'ok']

    if not empresas_validas:
        st.warning("Nenhuma empresa valida para exibir")
    else:
        # Gera analytics
        analytics = gerar_analytics(empresas)
        relatorio_concorrencia = gerar_relatorio_concorrencia(empresas_validas, populacao_municipio)

        # =================================================================
        # METRICAS PRINCIPAIS
        # =================================================================
        st.markdown("---")
        st.subheader("📈 Resumo Geral")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total de Empresas",
                analytics['resumo']['total_encontrados'],
                delta=f"{analytics['resumo']['total_erros']} erros" if analytics['resumo']['total_erros'] > 0 else None,
                delta_color="inverse"
            )

        with col2:
            st.metric(
                "Faturamento Total Estimado",
                formatar_moeda(analytics['resumo']['faturamento_anual_total']),
                delta="anual"
            )

        with col3:
            st.metric(
                "Faturamento Medio",
                formatar_moeda(analytics['resumo']['faturamento_medio']),
                delta="por empresa"
            )

        with col4:
            st.metric(
                "Setores Identificados",
                len(analytics['por_setor']),
                delta=f"{len(analytics['por_bairro'])} bairros"
            )

        # =================================================================
        # GRAFICOS
        # =================================================================
        st.markdown("---")
        st.subheader("📊 Visualizacoes")

        tab1, tab2, tab3, tab4 = st.tabs(["Por Setor", "Por Bairro", "Por Porte", "Top Empresas"])

        with tab1:
            # Grafico por setor
            df_setor = pd.DataFrame([
                {"Setor": k.title(), "Quantidade": v['quantidade'], "Faturamento": v['faturamento']}
                for k, v in analytics['por_setor'].items()
            ]).sort_values('Faturamento', ascending=False)

            col1, col2 = st.columns(2)

            with col1:
                fig = px.bar(
                    df_setor.head(10), x='Setor', y='Quantidade',
                    title='Quantidade de Empresas por Setor',
                    color='Quantidade',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(xaxis_tickangle=-45, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.pie(
                    df_setor.head(8), values='Faturamento', names='Setor',
                    title='Faturamento por Setor',
                    hole=0.4
                )
                st.plotly_chart(fig, use_container_width=True)

        with tab2:
            # Grafico por bairro
            df_bairro = pd.DataFrame([
                {"Bairro": k, "Quantidade": v['quantidade'], "Faturamento": v['faturamento']}
                for k, v in analytics['por_bairro'].items()
            ]).sort_values('Faturamento', ascending=False)

            col1, col2 = st.columns(2)

            with col1:
                fig = px.bar(
                    df_bairro, x='Bairro', y='Quantidade',
                    title='Empresas por Bairro',
                    color='Faturamento',
                    color_continuous_scale='Greens'
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.treemap(
                    df_bairro, path=['Bairro'], values='Faturamento',
                    title='Faturamento por Bairro (Treemap)',
                    color='Faturamento',
                    color_continuous_scale='Greens'
                )
                st.plotly_chart(fig, use_container_width=True)

        with tab3:
            # Grafico por porte
            df_porte = pd.DataFrame([
                {"Porte": k, "Quantidade": v['quantidade'], "Faturamento": v['faturamento']}
                for k, v in analytics['por_porte'].items()
            ])

            col1, col2 = st.columns(2)

            with col1:
                fig = px.pie(
                    df_porte, values='Quantidade', names='Porte',
                    title='Distribuicao por Porte',
                    hole=0.3
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.bar(
                    df_porte, x='Porte', y='Faturamento',
                    title='Faturamento por Porte',
                    color='Porte'
                )
                st.plotly_chart(fig, use_container_width=True)

        with tab4:
            # Top empresas
            df_top = pd.DataFrame(analytics['top_empresas'])
            df_top['Faturamento Formatado'] = df_top['faturamento'].apply(formatar_moeda)

            fig = px.bar(
                df_top, x='razao_social', y='faturamento',
                title='Top 10 Empresas por Faturamento Estimado',
                color='setor',
                text='Faturamento Formatado'
            )
            fig.update_layout(xaxis_tickangle=-45, showlegend=True)
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

        # =================================================================
        # ANALISE DE CONCORRENCIA
        # =================================================================
        st.markdown("---")
        st.subheader("🎯 Analise de Concorrencia")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Oportunidades de Mercado")
            oportunidades = relatorio_concorrencia.get('oportunidades', [])

            if oportunidades:
                for op in oportunidades[:5]:
                    potencial_emoji = "🟢" if op['potencial'] == 'alto' else "🟡"
                    st.markdown(f"""
                    {potencial_emoji} **{op['setor'].title()}**
                    - Empresas existentes: {op['empresas_existentes']}
                    - Demanda esperada: {op['demanda_esperada']:.0f}
                    - Cobertura: {op['taxa_cobertura']:.1f}%
                    """)
            else:
                st.info("Nenhuma oportunidade identificada com os dados atuais")

        with col2:
            st.markdown("### Setores mais Competitivos")
            setores_comp = relatorio_concorrencia.get('setores_competitividade', {})

            df_comp = pd.DataFrame([
                {"Setor": k.title(), "Empresas": v['empresas'], "Faturamento": v['faturamento']}
                for k, v in setores_comp.items()
            ]).sort_values('Empresas', ascending=False).head(8)

            fig = px.bar(
                df_comp, x='Setor', y='Empresas',
                title='Concentracao por Setor',
                color='Faturamento',
                color_continuous_scale='Reds'
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

        # =================================================================
        # TABELA DE DADOS
        # =================================================================
        st.markdown("---")
        st.subheader("📋 Dados Detalhados")

        # Prepara DataFrame
        df_empresas = pd.DataFrame(empresas_validas)

        # Seleciona colunas para exibir
        colunas_exibir = [
            'razao_social', 'nome_fantasia', 'bairro', 'municipio',
            'setor_classificado', 'porte', 'faturamento_anual_estimado',
            'fator_setor', 'fator_regional', 'fator_idade'
        ]

        df_display = df_empresas[colunas_exibir].copy()
        df_display.columns = [
            'Razao Social', 'Nome Fantasia', 'Bairro', 'Municipio',
            'Setor', 'Porte', 'Fat. Anual Est.', 'Fator Setor', 'Fator Regional', 'Fator Idade'
        ]

        # Formata valores
        df_display['Fat. Anual Est.'] = df_display['Fat. Anual Est.'].apply(formatar_moeda)

        st.dataframe(df_display, use_container_width=True, height=400)

        # =================================================================
        # EXPORTACAO
        # =================================================================
        st.markdown("---")
        st.subheader("📥 Exportar Dados")

        col1, col2, col3 = st.columns(3)

        with col1:
            # CSV
            csv = df_empresas.to_csv(index=False, sep=';', encoding='utf-8-sig')
            st.download_button(
                "📄 Baixar CSV",
                csv,
                "empresas_analytics.csv",
                "text/csv",
                use_container_width=True
            )

        with col2:
            # JSON
            json_data = json.dumps({
                "empresas": empresas_validas,
                "analytics": analytics,
                "data_consulta": st.session_state.get('data_consulta', '')
            }, ensure_ascii=False, indent=2)
            st.download_button(
                "📋 Baixar JSON",
                json_data,
                "empresas_analytics.json",
                "application/json",
                use_container_width=True
            )

        with col3:
            # Relatorio
            relatorio = f"""
RELATORIO DE ANALYTICS - CNPJS
==============================
Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}

RESUMO GERAL
------------
Total de empresas: {analytics['resumo']['total_encontrados']}
Faturamento total: {formatar_moeda(analytics['resumo']['faturamento_anual_total'])}
Faturamento medio: {formatar_moeda(analytics['resumo']['faturamento_medio'])}

SETORES
-------
{chr(10).join([f"- {k}: {v['quantidade']} empresas, {formatar_moeda(v['faturamento'])}" for k, v in sorted(analytics['por_setor'].items(), key=lambda x: x[1]['faturamento'], reverse=True)[:10]])}

BAIRROS
-------
{chr(10).join([f"- {k}: {v['quantidade']} empresas, {formatar_moeda(v['faturamento'])}" for k, v in sorted(analytics['por_bairro'].items(), key=lambda x: x[1]['faturamento'], reverse=True)])}
            """
            st.download_button(
                "📝 Baixar Relatorio TXT",
                relatorio,
                "relatorio_analytics.txt",
                "text/plain",
                use_container_width=True
            )

else:
    # Mensagem inicial
    st.info("👈 Insira os CNPJs na barra lateral e clique em 'Consultar CNPJs' para iniciar a analise")

    # Informacoes sobre a ferramenta
    st.markdown("""
    ### Como funciona:

    1. **Cole os CNPJs** na barra lateral (um por linha)
    2. **Clique em Consultar** para buscar os dados
    3. **Analise os resultados** com graficos interativos

    ### Dados coletados:
    - Razao social e nome fantasia
    - Endereco completo
    - CNAE (atividade economica)
    - Porte da empresa
    - **Faturamento estimado** (baseado em porte + setor + regiao + idade)

    ### Fontes de dados:
    - **API publica.cnpj.ws** - Dados cadastrais da Receita Federal
    - **API IBGE** - Dados economicos regionais
    - **Estudos SEBRAE** - Faturamento medio por setor
    """)


# =============================================================================
# FOOTER
# =============================================================================
st.markdown("---")
st.markdown("""
<p style="text-align: center; color: gray; font-size: 0.8rem;">
    Analytics CNPJ v3.0 | Dados publicos da Receita Federal + IBGE<br>
    Faturamento e ESTIMATIVA baseada em porte, setor, regiao e idade da empresa
</p>
""", unsafe_allow_html=True)


# =============================================================================
# HEALTH CHECK (para UptimeRobot)
# =============================================================================
# O Streamlit nao suporta rotas customizadas diretamente,
# mas podemos usar query params para health check
if st.query_params.get("health") == "check":
    st.write("OK")
