import streamlit as st
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import seaborn as sns
import altair as alt # Altair é excelente para gráficos interativos no Streamlit

# --- Configurações de Conexão com o Banco de Dados (Mantidas do exemplo anterior) ---

DB_HOST = "rds-prod.cmt2mu288c4s.us-east-1.rds.amazonaws.com"
DB_PORT = "5432"
DB_NAME = "iesb"
DB_USER = "data_iesb"
DB_PASSWORD = "wjDfqcUxfjtYXp04tr0S"

@st.cache_data # Armazena em cache os resultados da função
def carregar_dados_pib():
    """
    Tenta conectar ao banco de dados e carregar os dados da tabela
    'pib_municipios_brasil' em um DataFrame Pandas.
    """
    conn = None
    df = pd.DataFrame()

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        query = "SELECT * FROM pib_municipios_brasil;"
        df = pd.read_sql(query, conn)
        # st.success(f"🎉 Dados da tabela 'pib_municipios_brasil' carregados: {len(df)} linhas.") # Remover após depuração
    except psycopg2.Error as e:
        st.error(f"❌ Erro ao carregar dados do banco de dados:")
        st.error(f"Detalhes: {e}")
        st.warning("Verifique suas credenciais, conexão de rede e permissões da tabela.")
    finally:
        if conn:
            conn.close()
    return df

# Carregar os dados uma vez para todo o aplicativo
dados_pib_bruto = carregar_dados_pib()

# --- Funções para as Páginas do Aplicativo ---

def pagina_inicial(dados_pib):
    st.title('Análise do Valor do PIB por Ano') # Título principal da página

    if dados_pib.empty:
        st.warning("❌ Dados não carregados. Não é possível exibir a análise do PIB por ano.")
        return

    # Certificar-se de que as colunas necessárias existem
    required_cols = ['ano_pib', 'vl_pib']
    if not all(col in dados_pib.columns for col in required_cols):
        st.error(f"Colunas necessárias {required_cols} não encontradas no DataFrame. Verifique o esquema do seu banco de dados.")
        return

    # Preparação dos dados para o PIB total por ano
    pib = dados_pib.groupby('ano_pib')['vl_pib'].sum().reset_index().sort_values(by='ano_pib', ascending=True)
    pib.rename(columns={'ano_pib': 'Ano', 'vl_pib': 'Valor do PIB'}, inplace=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader('Dados do PIB por Ano')
        st.dataframe(pib, use_container_width=True, hide_index=True, height=460)
    with col2:
        st.subheader('Evolução do Valor do PIB por Ano')
        # Verifica se há dados para o gráfico antes de tentar criar
        if not pib.empty:
            fig = px.line(
                pib,
                x='Ano',
                y='Valor do PIB',
                title='Evolução do Valor do PIB Total por Ano'
            )
            st.plotly_chart(fig, use_container_width=True) # Adicionado use_container_width
        else:
            st.info("Não há dados de PIB para exibir o gráfico de evolução.")

def pagina_analise_interativa(dados_pib):
    st.title("📊 Página 2 - Interatividade por Município e Ano")

    if dados_pib.empty:
        st.warning("❌ Dados não carregados.")
        return

    # --- Preparação dos dados ---
    df = dados_pib.copy()
    try:
        df['Ano'] = pd.to_numeric(df['ano_pib'], errors='coerce')
        df['Valor_PIB'] = df['vl_pib']
        df['Município'] = df['nome_municipio']
        df.dropna(subset=['Ano', 'Valor_PIB', 'Município'], inplace=True)
        df['Ano'] = df['Ano'].astype(int)
    except Exception as e:
        st.error(f"Erro no preparo dos dados: {e}")
        return

    # --- MENU LATERAL INTERATIVO ---
    st.sidebar.header("🎛️ Filtros")

    municipios = sorted(df['Município'].unique().tolist())
    municipio_sel = st.sidebar.selectbox("Selecione o Município:", municipios)

    anos_disp = sorted(df[df['Município'] == municipio_sel]['Ano'].unique().tolist())
    ano_sel = st.sidebar.selectbox("Selecione o Ano:", anos_disp)

    df_municipio = df[df['Município'] == municipio_sel]
    df_ano = df_municipio[df_municipio['Ano'] == ano_sel]

    # --- GRÁFICOS LADO A LADO ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(" Evolução do PIB")
        linha_df = df_municipio.groupby('Ano')['Valor_PIB'].sum().reset_index()
        fig_line, ax = plt.subplots(figsize=(6, 4))
        sns.lineplot(data=linha_df, x='Ano', y='Valor_PIB', marker='o', ax=ax)
        ax.set_title(f"Evolução do PIB - {municipio_sel}")
        ax.set_xlabel("Ano")
        ax.set_ylabel("Valor do PIB")
        st.pyplot(fig_line)

    with col2:
        st.subheader(" Distribuição do PIB por Setor")
        if not df_ano.empty:
            setores = {
                'Agropecuária': 'vl_agropecuaria',
                'Indústria': 'vl_industria',
                'Serviços': 'vl_servicos',
                'Administração Pública': 'vl_administracao'
            }

            setor_data = {
                setor: float(df_ano[col].sum())
                for setor, col in setores.items()
                if col in df_ano.columns
            }

            donut_df = pd.DataFrame({
                'Setor': list(setor_data.keys()),
                'Valor': list(setor_data.values())
            })

            fig_donut, ax2 = plt.subplots(figsize=(5, 5))
            wedges, texts, autotexts = ax2.pie(
                donut_df['Valor'],
                labels=donut_df['Setor'],
                autopct='%1.1f%%',
                startangle=90,
                wedgeprops=dict(width=0.4)
            )
            ax2.set_title(f"Distribuição por Setor - {ano_sel}")
            st.pyplot(fig_donut)
        else:
            st.info("Sem dados para o ano selecionado.")



# --- Menu lateral ---
st.sidebar.title("Navegação")
page_selection = st.sidebar.radio("Ir para:", ["Página Inicial", "Página 2 - Interatividade"])

if page_selection == "Página Inicial":
    pagina_inicial(dados_pib_bruto)
elif page_selection == "Página 2 - Interatividade":
    pagina_analise_interativa(dados_pib_bruto)

# Status de conexão
if not dados_pib_bruto.empty:
    st.sidebar.success("Dados carregados do DB.")
else:
    st.sidebar.error("Falha ao carregar dados do DB.")
