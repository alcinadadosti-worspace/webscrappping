# Analytics CNPJ - Dashboard

Dashboard para analise de empresas usando dados publicos da Receita Federal + IBGE.

## Funcionalidades

- Consulta de CNPJs via API publica
- Estimativa de faturamento baseada em:
  - Porte da empresa
  - Setor (CNAE)
  - Regiao (dados IBGE)
  - Idade da empresa
  - Capital social
- Analise de concorrencia por bairro/setor
- Identificacao de oportunidades de mercado
- Graficos interativos
- Exportacao CSV/JSON

## Deploy no Render (Gratuito)

### Passo 1: Criar repositorio no GitHub

```bash
cd dashboard
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/cnpj-analytics.git
git push -u origin main
```

### Passo 2: Deploy no Render

1. Acesse [render.com](https://render.com) e faca login
2. Clique em "New +" > "Web Service"
3. Conecte seu repositorio GitHub
4. Configure:
   - **Name**: cnpj-analytics
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
5. Clique em "Create Web Service"

### Passo 3: Configurar UptimeRobot (manter app acordado)

1. Acesse [uptimerobot.com](https://uptimerobot.com) e crie conta gratuita
2. Adicione novo monitor:
   - **Monitor Type**: HTTP(s)
   - **URL**: `https://sua-app.onrender.com/?health=check`
   - **Monitoring Interval**: 5 minutes
3. Salve o monitor

## Executar Localmente

```bash
# Instalar dependencias
pip install -r requirements.txt

# Executar
streamlit run app.py
```

Acesse: http://localhost:8501

## Estrutura do Projeto

```
dashboard/
├── app.py                 # Dashboard principal (Streamlit)
├── consulta_cnpj.py       # Modulo de consulta de CNPJs
├── dados_ibge.py          # Integracao com API do IBGE
├── analise_concorrencia.py # Analise de mercado e concorrencia
├── requirements.txt       # Dependencias Python
├── render.yaml           # Configuracao do Render
├── .streamlit/
│   └── config.toml       # Configuracao do Streamlit
└── README.md             # Este arquivo
```

## APIs Utilizadas (Gratuitas)

| API | Uso | Limite |
|-----|-----|--------|
| publica.cnpj.ws | Dados cadastrais CNPJ | ~3 req/min |
| IBGE Localidades | Dados de municipios | Sem limite |
| IBGE Agregados | PIB, populacao | Sem limite |

## Metodologia de Estimativa

O faturamento e estimado usando a formula:

```
Faturamento = Base_Porte × Fator_Setor × Fator_Regional × Fator_Idade × Fator_Capital
```

### Fator Regional (IBGE)
- Compara PIB per capita do municipio com Sao Paulo (referencia)
- Penedo/AL: ~0.55 (economia 55% de SP)

### Fator Setor
- Farmacia: 1.6x (alto giro)
- Supermercado: 1.8x (volume)
- Bijuteria: 0.6x (baixo ticket)
- Restaurante: 1.2x (servico)

### Fator Idade
- < 1 ano: 0.5x (empresa nova)
- 5-10 anos: 1.1x (estabelecida)
- > 20 anos: 1.2x (consolidada)

## Licenca

MIT License - Uso livre para fins comerciais e pessoais.
