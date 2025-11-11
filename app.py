# === CONFIGURAÇÃO DA PÁGINA DEVE SER O PRIMEIRO COMANDO ===
import streamlit as st

# Configuração da página que aparece na aba do navegador - DEVE SER O PRIMEIRO COMANDO
st.set_page_config(
    page_title="CupomGO - Painel Econômico Interativo", 
    page_icon="💳", 
    layout="wide"  # Usa toda a largura da tela
)

# === DEPOIS IMPORTE OS OUTROS MÓDULOS ===
import pandas as pd     # Para trabalhar com tabelas e dados
import numpy as np      # Para cálculos matemáticos
import plotly.express as px  # Para criar gráficos bonitos
import plotly.graph_objects as go  # Para gráficos mais customizados
import datetime, os, hashlib, re  # Utilitários do Python
from PIL import Image, UnidentifiedImageError  # Para trabalhar com imagens
from pathlib import Path

# === Caminhos robustos (Azure/Linux) ===
BASE = Path(__file__).resolve().parent
DATA = (BASE / "data").resolve()

# === Sistema de Filtros Global ===
class SistemaFiltros:
    """
    Sistema centralizado de filtros para todos os gráficos do dashboard
    """
    
    def __init__(self):
        self.filtros_aplicados = {}
        self.drill_down_stack = []  # Pilha para navegação hierárquica
        
    def criar_filtros_sidebar(self, df):
        """
        Cria todos os controles de filtro na sidebar
        """
        st.sidebar.markdown("---")
        st.sidebar.subheader("🎛️ Filtros Globais")
        
        # Filtro por período com slider de datas
        if 'data_captura' in df.columns:
            datas_validas = pd.to_datetime(df['data_captura'], errors='coerce').dropna()
            if not datas_validas.empty:
                min_date = datas_validas.min().date()
                max_date = datas_validas.max().date()
                
                periodo = st.sidebar.date_input(
                    "📅 Período",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                    key="filtro_periodo"
                )
                
                if len(periodo) == 2:
                    self.filtros_aplicados['data_inicio'] = periodo[0]
                    self.filtros_aplicados['data_fim'] = periodo[1]
        
        # Filtro por região (dropdown)
        if 'regiao' in df.columns:
            regioes = ['Todos'] + sorted(df['regiao'].dropna().unique().tolist())
            regiao_selecionada = st.sidebar.selectbox(
                "🌎 Região",
                regioes,
                key="filtro_regiao"
            )
            if regiao_selecionada != 'Todos':
                self.filtros_aplicados['regiao'] = regiao_selecionada
        
        # Filtro por ano (botões)
        if 'data_captura' in df.columns:
            df_copy = df.copy()
            df_copy['data_captura'] = pd.to_datetime(df_copy['data_captura'], errors='coerce')
            df_copy['ano'] = df_copy['data_captura'].dt.year
            anos_disponiveis = sorted(df_copy['ano'].dropna().unique().astype(int).tolist())
            
            if anos_disponiveis:
                st.sidebar.markdown("**📊 Ano:**")
                col1, col2 = st.sidebar.columns(2)
                with col1:
                    if st.button("2023", use_container_width=True, key="btn_2023"):
                        self.filtros_aplicados['ano'] = 2023
                with col2:
                    if st.button("2024", use_container_width=True, key="btn_2024"):
                        self.filtros_aplicados['ano'] = 2024
                
                # Mostra ano atual selecionado
                ano_atual = self.filtros_aplicados.get('ano', 'Todos')
                st.sidebar.info(f"Ano selecionado: **{ano_atual}**")
        
        # Filtro por tipo de cupom
        if 'tipo_cupom' in df.columns:
            tipos = ['Todos'] + sorted(df['tipo_cupom'].dropna().unique().tolist())
            tipo_selecionado = st.sidebar.multiselect(
                "🎯 Tipo de Cupom",
                tipos,
                default=['Todos'],
                key="filtro_tipo"
            )
            if 'Todos' not in tipo_selecionado and tipo_selecionado:
                self.filtros_aplicados['tipo_cupom'] = tipo_selecionado
        
        # Filtro por loja
        if 'nome_loja' in df.columns:
            lojas = ['Todas'] + sorted(df['nome_loja'].dropna().unique().tolist())
            loja_selecionada = st.sidebar.selectbox(
                "🏪 Loja",
                lojas,
                key="filtro_loja"
            )
            if loja_selecionada != 'Todas':
                self.filtros_aplicados['nome_loja'] = loja_selecionada
        
        # Botão para limpar todos os filtros
        if st.sidebar.button("🧹 Limpar Filtros", use_container_width=True):
            self.filtros_aplicados = {}
            self.drill_down_stack = []
            st.rerun()
        
        # Mostra filtros ativos
        if self.filtros_aplicados:
            st.sidebar.markdown("---")
            st.sidebar.markdown("**✅ Filtros Ativos:**")
            for filtro, valor in self.filtros_aplicados.items():
                st.sidebar.write(f"• {filtro}: {valor}")
    
    def aplicar_filtros(self, df):
        """
        Aplica todos os filtros ao dataframe
        """
        df_filtrado = df.copy()
        
        # Filtro de data
        if 'data_inicio' in self.filtros_aplicados and 'data_fim' in self.filtros_aplicados:
            if 'data_captura' in df_filtrado.columns:
                df_filtrado['data_captura'] = pd.to_datetime(df_filtrado['data_captura'], errors='coerce')
                mask = (df_filtrado['data_captura'].dt.date >= self.filtros_aplicados['data_inicio']) & \
                       (df_filtrado['data_captura'].dt.date <= self.filtros_aplicados['data_fim'])
                df_filtrado = df_filtrado[mask]
        
        # Filtro de região
        if 'regiao' in self.filtros_aplicados and 'regiao' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['regiao'] == self.filtros_aplicados['regiao']]
        
        # Filtro de ano
        if 'ano' in self.filtros_aplicados and 'data_captura' in df_filtrado.columns:
            df_filtrado['data_captura'] = pd.to_datetime(df_filtrado['data_captura'], errors='coerce')
            df_filtrado = df_filtrado[df_filtrado['data_captura'].dt.year == self.filtros_aplicados['ano']]
        
        # Filtro de tipo de cupom
        if 'tipo_cupom' in self.filtros_aplicados and 'tipo_cupom' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['tipo_cupom'].isin(self.filtros_aplicados['tipo_cupom'])]
        
        # Filtro de loja
        if 'nome_loja' in self.filtros_aplicados and 'nome_loja' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['nome_loja'] == self.filtros_aplicados['nome_loja']]
        
        return df_filtrado
    
    def adicionar_drill_down(self, nivel, valor):
        """
        Adiciona um nível à pilha de drill-down
        """
        self.drill_down_stack.append((nivel, valor))
    
    def remover_drill_down(self):
        """
        Remove o último nível da pilha de drill-down
        """
        if self.drill_down_stack:
            return self.drill_down_stack.pop()
        return None
    
    def get_nivel_atual(self):
        """
        Retorna o nível atual de drill-down
        """
        return self.drill_down_stack[-1] if self.drill_down_stack else None

# Cria instância global do sistema de filtros
sistema_filtros = SistemaFiltros()

# === Diagnóstico: lista o que o servidor realmente tem em /data ===
@st.cache_data(show_spinner=False)
def _list_data_files():
    items = []
    if DATA.exists():
        for p in sorted(DATA.iterdir()):
            if p.is_file():
                items.append({
                    "arquivo": p.name,
                    "tamanho_kb": round(p.stat().st_size/1024, 1)
                })
    return pd.DataFrame(items)

def _find_file_case_insensitive(filename: str):
    """Procura filename em DATA ignorando maiúsculas/minúsculas."""
    p = DATA / filename
    if p.exists():
        return p
    target = filename.lower()
    for q in DATA.glob("*"):
        if q.is_file() and q.name.lower() == target:
            return q
    return None

@st.cache_data(show_spinner=False)
def load_csv(name, **kwargs):
    """
    Carrega arquivos CSV da pasta data com tratamento de erros e cache
    """
    p = _find_file_case_insensitive(name)
    if p is None:
        st.error(f"❌ Arquivo **{name}** não encontrado em **{DATA}**.\n"
                 f"Coloque o arquivo na pasta **data/** (mesmo nível do app.py).")
        return pd.DataFrame()

    try:
        return pd.read_csv(p, **kwargs)
    except Exception as e:
        st.error(f"❌ Erro ao ler **{p.name}**: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_xlsx(name, sheet_name=0, **kwargs):
    """
    Carrega arquivos Excel da pasta data com tratamento de erros e cache
    """
    p = _find_file_case_insensitive(name)
    if p is None:
        st.error(f"❌ Arquivo **{name}** não encontrado em **{DATA}**.\n"
                 f"Coloque o arquivo na pasta **data/** (mesmo nível do app.py).")
        return pd.DataFrame()

    try:
        # engine explícita para ambientes server
        return pd.read_excel(p, sheet_name=sheet_name, engine="openpyxl", **kwargs)
    except Exception as e:
        st.error(f"❌ Erro ao ler **{p.name}**: {e}")
        return pd.DataFrame()

def read_table(filename: str, sheet_name=0, **kwargs):
    """
    Lê .xlsx/.xls com openpyxl; .csv com pandas. Para execução se não achar.
    kwargs: passam para read_excel/read_csv (ex.: dtype, parse_dates, sep, encoding)
    """
    p = _find_file_case_insensitive(filename)
    if p is None:
        st.error(f"❌ Arquivo **{filename}** não encontrado em **{DATA}**.\n"
                 f"Coloque o arquivo na pasta **data/** (mesmo nível do app.py).")
        # Em vez de parar, retorna DataFrame vazio para permitir continuar
        return pd.DataFrame()

    ext = p.suffix.lower()
    try:
        if ext in (".xlsx", ".xls"):
            # engine explícita para ambientes server
            return pd.read_excel(p, sheet_name=sheet_name, engine="openpyxl", **kwargs)
        elif ext == ".csv":
            return pd.read_csv(p, **kwargs)
        else:
            st.error(f"❌ Extensão não suportada: **{ext}** ({p.name}). "
                     f"Use .xlsx/.xls/.csv.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Erro ao ler **{p.name}**: {e}")
        return pd.DataFrame()

# === (Opcional) Leitor com múltiplos candidatos de nome ===
def read_any(candidates, **kwargs):
    """
    Tenta ler na ordem. Exemplo:
    read_any(['transacoes.xlsx','transações.xlsx','transacoes.csv'])
    """
    for name in candidates:
        p = _find_file_case_insensitive(name)
        if p is not None:
            return read_table(p.name, **kwargs)
    st.error("❌ Nenhum dos arquivos foi encontrado: " + ", ".join(candidates))
    return pd.DataFrame()

# ---------------- Carregamento dos Dados ----------------
# Carrega todos os arquivos usando o sistema robusto
# CORREÇÃO: Tenta diferentes variações de nome para conquista.csv
try:
    conquista = read_any(["conquista.csv", "conquistas.csv", "achievements.csv"])
except:
    conquista = pd.DataFrame()

try:
    cupom_usos = load_csv("cupom_usos.csv")
except:
    cupom_usos = pd.DataFrame()

try:
    economia = load_csv("economia.csv")
except:
    economia = pd.DataFrame()

try:
    usuarios = load_csv("usuarios.csv")
except:
    usuarios = pd.DataFrame()

try:
    lojas = load_xlsx("lojas.xlsx")
except:
    lojas = pd.DataFrame()

try:
    pedestres = load_xlsx("pedestres.xlsx")
except:
    pedestres = pd.DataFrame()

try:
    players = load_xlsx("players.xlsx")
except:
    players = pd.DataFrame()

try:
    transacoes = load_xlsx("transacoes.xlsx")
except:
    transacoes = pd.DataFrame()

# ---------------- Carregamento dos Dados ----------------
# Atualiza as variáveis principais com os dados carregados
df_transacoes = transacoes if not transacoes.empty else pd.DataFrame()
df_lojas = lojas if not lojas.empty else pd.DataFrame()
df_players = players if not players.empty else pd.DataFrame()
df_pedestres = pedestres if not pedestres.empty else pd.DataFrame()
df_economia = economia if not economia.empty else pd.DataFrame()

# Adiciona colunas de hierarquia temporal para drill-down se não existirem
if not df_transacoes.empty and 'data_captura' in df_transacoes.columns:
    df_transacoes['data_captura'] = pd.to_datetime(df_transacoes['data_captura'], errors='coerce')
    df_transacoes['ano'] = df_transacoes['data_captura'].dt.year
    df_transacoes['trimestre'] = df_transacoes['data_captura'].dt.quarter
    df_transacoes['mes'] = df_transacoes['data_captura'].dt.month
    df_transacoes['mes_nome'] = df_transacoes['data_captura'].dt.strftime('%B')

# Antes de plotar, cheque se veio
if not df_transacoes.empty:
    # ... seus gráficos aqui
    pass

# Cor principal da nossa marca - usada em botões, títulos e gráficos
PRIMARY = "#0C2D6B"

# ---------------- CSS Externo ----------------
def inject_css_file(path="assets/styles.css"):
    """
    Carrega nosso arquivo de estilos personalizado.
    Pense nisso como as roupas da nossa aplicação - deixa tudo mais bonito!
    """
    try:
        # Lê o arquivo CSS como se fosse um texto normal
        css = Path(path).read_text(encoding="utf-8")
        # Aplica os estilos na página
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except Exception as e:
        # Se o arquivo não existir, a aplicação funciona mesmo assim, só fica menos bonita
        st.warning(f"Não foi possível carregar o CSS ({e}).")

# Chama a função para aplicar os estilos
inject_css_file()

# ---------------- Onde Guardamos Nossos Dados ----------------
# São como as gavetas onde guardamos informações importantes
def get_data_path(filename):
    """Obtém caminho seguro para arquivos de dados"""
    data_file = _find_file_case_insensitive(filename)
    if data_file and data_file.exists():
        return data_file
    # Fallback para assets se existir
    assets_file = BASE / "assets" / filename
    return assets_file if assets_file.exists() else None

PATH_TX = get_data_path("transacoes.xlsx")
PATH_STORES = get_data_path("lojas.xlsx")
USERS_PATH = get_data_path("usuarios.csv")
ECON_PATH = get_data_path("economia.csv")
CUPOM_USOS_PATH = get_data_path("cupom_usos.csv")
CONQUISTAS_PATH = get_data_path("conquistas.csv")

# ---------------- Sistema de Gamificação ----------------
class SistemaGamificacao:
    """
    Transforma o uso de cupons em um jogo divertido!
    Usuários sobem de nível, ganham recompensas e desbloqueiam conquistas.
    Isso motiva todo mundo a economizar mais!
    """
    
    def __init__(self):
        # Níveis que os usuários podem alcançar - como em um videogame
        # Cada nível dá mais cashback e requer mais cupons
        self.niveis = {
            1: {"nome": "🥉 Iniciante", "cupons_necessarios": 0, "cashback": 1, "cor": "#CD7F32"},
            2: {"nome": "🥉 Bronze", "cupons_necessarios": 5, "cashback": 2, "cor": "#CD7F32"},
            3: {"nome": "🥈 Prata", "cupons_necessarios": 10, "cashback": 3, "cor": "#C0C0C0"},
            4: {"nome": "🥇 Ouro", "cupons_necessarios": 20, "cashback": 5, "cor": "#FFD700"},
            5: {"nome": "💎 Diamante", "cupons_necessarios": 35, "cashback": 8, "cor": "#B9F2FF"},
            6: {"nome": "👑 Mestre", "cupons_necessarios": 50, "cashback": 10, "cor": "#FF69B4"}
        }
        
        # Conquistas especiais - como "medalhas" que usuários podem ganhar
        self.conquistas = {
            "primeiro_passo": {"nome": "Primeiros Passos", "descricao": "Use seu primeiro cupom", "icone": "🎯", "xp": 50},
            "economizador": {"nome": "Economizador", "descricao": "Economize R$ 100+ com cupons", "icone": "💰", "xp": 100},
            "colecionador": {"nome": "Colecionador", "descricao": "Use 10 cupons diferentes", "icone": "📚", "xp": 150},
            "explorador": {"nome": "Explorador", "descricao": "Use cupons em 5 lojas diferentes", "icone": "🧭", "xp": 120},
            "fiel": {"nome": "Cliente Fiel", "descricao": "Use 5 cupons na mesma loja", "icone": "❤️", "xp": 80},
            "estrategista": {"nome": "Estrategista", "descricao": "Use 3 tipos diferentes de cupom", "icone": "🎯", "xp": 130},
            "vip": {"nome": "Cliente VIP", "descricao": "Alcance nível Ouro", "icone": "⭐", "xp": 200},
            "lenda": {"nome": "Lenda", "descricao": "Alcance nível Mestre", "icone": "🏆", "xp": 500}
        }
    
    def calcular_nivel(self, cupons_usados):
        """
        Descobre em qual nível o usuário está baseado em quantos cupons ele já usou.
        É como subir de nível em um RPG - quanto mais cupons, mais alto o nível!
        """
        # Começa do nível mais alto e vai descendo até achar o nível certo
        for nivel_id, info in sorted(self.niveis.items(), reverse=True):
            if cupons_usados >= info["cupons_necessarios"]:
                return nivel_id, info
        # Se não encontrou nenhum, fica no nível 1 (básico)
        return 1, self.niveis[1]
    
    def calcular_progresso(self, cupons_usados, nivel_atual):
        """
        Calcula quanto falta para o próximo nível.
        Retorna uma porcentagem (0 a 100%) mostrando o progresso.
        """
        if nivel_atual not in self.niveis:
            nivel_atual = 1  # Segurança - se o nível for inválido, volta para 1
            
        nivel_proximo = nivel_atual + 1  # Próximo nível que queremos alcançar
        
        # Verifica se existe um próximo nível
        if nivel_proximo in self.niveis:
            cupons_atual = self.niveis[nivel_atual]["cupons_necessarios"]
            cupons_proximo = self.niveis[nivel_proximo]["cupons_necessarios"]
            
            if cupons_proximo > cupons_atual:
                # Calcula quanto já caminhamos em direção ao próximo nível
                progresso = (cupons_usados - cupons_atual) / (cupons_proximo - cupons_atual)
                progresso = max(0.0, min(1.0, progresso))  # Garante que fique entre 0% e 100%
            else:
                progresso = 1.0  # Já alcançou
                
            return progresso, self.niveis[nivel_proximo]
        
        # Se não há próximo nível, chegamos ao topo!
        return 1.0, None
    
    def verificar_conquistas(self, usuario_data, cupom_data):
        """
        Verifica se o usuário ganhou alguma conquista depois de usar um cupom.
        É como ganhar um troféu por alcançar certos marcos!
        """
        conquistas_desbloqueadas = []  # Lista de conquistas novas
        
        # Pega os dados atualizados do usuário
        cupons_usados = usuario_data.get("cupons_usados", 0)
        total_economizado = usuario_data.get("total_economizado", 0)
        lojas_visitadas = eval(usuario_data.get("lojas_visitadas", "[]"))
        tipos_usados = eval(usuario_data.get("tipos_usados", "[]"))
        
        # Verifica cada tipo de conquista possível:
        
        # Primeiro cupom usado
        if cupons_usados == 1 and not usuario_data.get("conquista_primeiro_passo", False):
            conquistas_desbloqueadas.append("primeiro_passo")
        
        # Economizou bastante dinheiro
        if total_economizado >= 100 and not usuario_data.get("conquista_economizador", False):
            conquistas_desbloqueadas.append("economizador")
        
        # Usou muitos cupons
        if cupons_usados >= 10 and not usuario_data.get("conquista_colecionador", False):
            conquistas_desbloqueadas.append("colecionador")
        
        # Explorou várias lojas diferentes
        if len(set(lojas_visitadas)) >= 5 and not usuario_data.get("conquista_explorador", False):
            conquistas_desbloqueadas.append("explorador")
        
        # Fiel a uma loja específica
        if lojas_visitadas and max([lojas_visitadas.count(loja) for loja in set(lojas_visitadas)]) >= 5 and not usuario_data.get("conquista_fiel", False):
            conquistas_desbloqueadas.append("fiel")
        
        # Usou diferentes tipos de cupom
        if len(set(tipos_usados)) >= 3 and not usuario_data.get("conquista_estrategista", False):
            conquistas_desbloqueadas.append("estrategista")
        
        # Alcançou nível alto
        nivel_atual, _ = self.calcular_nivel(cupons_usados)
        if nivel_atual >= 4 and not usuario_data.get("conquista_vip", False):
            conquistas_desbloqueadas.append("vip")
        
        # Alcançou o nível máximo
        if nivel_atual >= 6 and not usuario_data.get("conquista_lenda", False):
            conquistas_desbloqueadas.append("lenda")
        
        return conquistas_desbloqueadas

# Cria o sistema de gamificação para usarmos em toda a aplicação
gamificacao = SistemaGamificacao()

# ---------------- Funções Utilitárias ----------------
def safe_logo(width=150):
    """
    Tenta carregar o logo da empresa de forma segura.
    Se não conseguir (arquivo não existe ou é inválido), mostra o nome escrito.
    """
    logo_path = "assets/Logo - PicMoney.png"
    
    # Cria 3 colunas: esquerda (vazia), centro (logo), direita (vazia)
    # Isso centraliza o logo no menu lateral
    col1, col2, col3 = st.sidebar.columns([1, 2, 1]) 
    
    with col2:  # Coluna do meio - onde fica o logo
        try:
            if os.path.exists(logo_path):
                # Tenta abrir a imagem
                img = Image.open(logo_path)
                st.image(img, width=width)
            else:
                # Se o arquivo não existe, mostra o nome
                st.markdown(
                    '<div style="text-align: center; font-size: 22px; font-weight: bold; color: #0C2D6B;">CupomGO</div>', 
                    unsafe_allow_html=True
                )
        except (UnidentifiedImageError, OSError):
            # Se a imagem está corrompida, mostra o nome
            st.markdown(
                '<div style="text-align: center; font-size: 22px; font-weight: bold; color: #0C2D6B;">CupomGO</div>', 
                unsafe_allow_html=True
            )

def style_fig(fig, y_fmt=None, x_fmt=None):
    """
    Aplica um visual consistente em todos os gráficos.
    Pense nisso como o 'tema' dos nossos gráficos - deixa tudo com a mesma cara.
    """
    # Configura o layout geral do gráfico
    fig.update_layout(
        font=dict(color="black", size=12),  # Fonte preta e legível
        paper_bgcolor="white",     # Fundo branco ao redor do gráfico
        plot_bgcolor="white",      # Fundo blanco dentro do gráfico
        hovermode="x unified",     # Mostra dados de todas as linhas ao passar o mouse
        hoverlabel=dict(
            bgcolor="white",       # Fundo branco nas dicas
            font_color="black",    # Texto preto nas dicas
            font_size=12,
            bordercolor="lightgray",
            namelength=-1
        ),
        legend=dict(
            orientation="h",       # Legenda na horizontal
            yanchor="bottom",      # Ancora embaixo
            y=-0.35,              # Posição abaixo do gráfico
            xanchor="center",      # Centralizada
            x=0.5,
            bgcolor="rgba(255,255,255,0.9)",  # Fundo semi-transparente
            bordercolor="lightgray",
            borderwidth=1,
            font=dict(size=11)
        ),
        title_font=dict(color="black", size=16),  # Título em preto
        margin=dict(l=80, r=80, t=80, b=140)  # Espaço ao redor do gráfico
    )
    
    # Estiliza o eixo X (horizontal)
    fig.update_xaxes(
        title_font=dict(color="black", size=12), 
        tickfont=dict(color="black", size=11), 
        gridcolor="lightgray",     # Grades cinza claras
        zerolinecolor="lightgray", 
        showgrid=True              # Mostra as grades
    )
    
    # Estiliza o eixo Y (vertical)
    fig.update_yaxes(
        title_font=dict(color="black", size=12), 
        tickfont=dict(color="black", size=11), 
        gridcolor="lightgray", 
        zerolinecolor="lightgray", 
        showgrid=True
    )
    
    # Formata números se especificado (ex: 1000 vira 1.000)
    if y_fmt is not None: 
        fig.update_yaxes(tickformat=y_fmt)
    if x_fmt is not None: 
        fig.update_xaxes(tickformat=x_fmt)
        
    return fig

# ---------------- Sistema de Login e Cadastro ----------------
def hash_password(pwd: str) -> str:
    """
    Transforma a senha em um código secreto (hash).
    Isso é importante para segurança - nunca guardamos senhas reais!
    """
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()

@st.cache_data(show_spinner=False)
def load_users() -> pd.DataFrame:
    """
    Carrega a lista de usuários do arquivo CSV com cache.
    Se o arquivo não existe, cria uma estrutura vazia.
    """
    if not os.path.exists(USERS_PATH):
        # Define todas as colunas que vamos precisar
        colunas_base = ["nome","email","senha_hash","criado_em","cupons_usados"]
        colunas_gamificacao = [
            "total_economizado", "xp", "nivel", "lojas_visitadas", 
            "tipos_usados", "ultimo_cupom", "melhor_sequencia"
        ]
        conquistas_cols = [f"conquista_{key}" for key in gamificacao.conquistas.keys()]
        return pd.DataFrame(columns=colunas_base + colunas_gamificacao + conquistas_cols)
    
    try:
        # Tenta carregar o arquivo existente
        df = pd.read_csv(USERS_PATH)
        
        # Garante que todas as colunas de gamificação existam
        colunas_gamificacao = [
            "total_economizado", "xp", "nivel", "lojas_visitadas", 
            "tipos_usados", "ultimo_cupom", "melhor_sequencia"
        ]
        for col in colunas_gamificacao:
            if col not in df.columns:
                if col in ["lojas_visitadas", "tipos_usados"]:
                    df[col] = "[]"  # Lista vazia
                else:
                    df[col] = 0     # Zero como valor padrão
        
        # Garante que todas as colunas de conquistas existam
        conquistas_cols = [f"conquista_{key}" for key in gamificacao.conquistas.keys()]
        for col in conquistas_cols:
            if col not in df.columns:
                df[col] = False  # Ainda não conquistou
                
        return df
    except Exception:
        # Em caso de erro, retorna estrutura básica
        return pd.DataFrame(columns=["nome","email","senha_hash","criado_em","cupons_usados"])

def email_exists(df: pd.DataFrame, email: str) -> bool:
    """
    Verifica se um email já está cadastrado.
    Evita que duas pessoas usem o mesmo email.
    """
    return email.lower() in (df["email"].astype(str).str.lower().tolist() if not df.empty else [])

def save_user(nome: str, email: str, pwd: str):
    """
    Salva um novo usuário no sistema.
    Como adicionar uma nova ficha no nosso cadastro.
    """
    df = load_users()
    
    # Prepara todos os dados do novo usuário
    new_data = {
        "nome": (nome or "").strip(),
        "email": (email or "").strip(),
        "senha_hash": hash_password(pwd or ""),
        "criado_em": datetime.datetime.utcnow().isoformat(),
        "cupons_usados": 0,
        "total_economizado": 0.0,
        "xp": 0,
        "nivel": 1,
        "lojas_visitadas": "[]",
        "tipos_usados": "[]",
        "ultimo_cupom": None,
        "melhor_sequencia": 0
    }
    
    # Inicializa todas as conquistas como "não desbloqueadas"
    for key in gamificacao.conquistas.keys():
        new_data[f"conquista_{key}"] = False
        
    # Adiciona o novo usuário à tabela
    new = pd.DataFrame([new_data])
    df = pd.concat([df, new], ignore_index=True)
    df.to_csv(USERS_PATH, index=False, encoding="utf-8")
    st.cache_data.clear()  # Limpa o cache para refletir as mudanças

def check_login(email: str, pwd: str) -> bool:
    """
    Verifica se o email e senha estão corretos.
    Como um porteiro que verifica sua identidade.
    """
    df = load_users()
    if df.empty: 
        return False  # Não há usuários cadastrados
    
    # Procura o usuário pelo email
    row = df[df["email"].astype(str).str.lower() == (email or "").lower()]
    if row.empty: 
        return False  # Email não encontrado
    
    # Verifica se a senha hasheada confere
    return row.iloc[0]["senha_hash"] == hash_password(pwd or "")

def atualizar_usuario_gamificacao(email: str, cupom_data: dict):
    """
    Atualiza os dados do usuário depois que ele usa um cupom.
    Atualiza nível, conquistas, economia total, etc.
    """
    df = load_users()
    if df.empty: 
        return []  # Não há usuários
    
    # Encontra o usuário pelo email
    user_idx = df[df["email"] == email].index
    if len(user_idx) == 0: 
        return []  # Usuário não encontrado
    
    idx = user_idx[0]
    usuario = df.loc[idx].to_dict()
    
    # Atualiza contador de cupons usados
    df.at[idx, "cupons_usados"] = usuario.get("cupons_usados", 0) + 1
    
    # Calcula economia (10% do valor do cupom) e soma ao total
    economia = cupom_data.get("valor", 0) * 0.1
    df.at[idx, "total_economizado"] = usuario.get("total_economizado", 0) + economia
    
    # Adiciona a loja à lista de lojas visitadas (se for nova)
    loja = cupom_data.get("loja", "")
    lojas_visitadas = eval(usuario.get("lojas_visitadas", "[]"))
    if loja and loja not in lojas_visitadas:
        lojas_visitadas.append(loja)
        df.at[idx, "lojas_visitadas"] = str(lojas_visitadas)
    
    # Adiciona o tipo de cupom à lista de tipos usados (se for novo)
    tipo = cupom_data.get("tipo", "")
    tipos_usados = eval(usuario.get("tipos_usados", "[]"))
    if tipo and tipo not in tipos_usados:
        tipos_usados.append(tipo)
        df.at[idx, "tipos_usados"] = str(tipos_usados)
    
    # Recalcula o nível atual
    cupons_usados = df.at[idx, "cupons_usados"]
    nivel_id, nivel_info = gamificacao.calcular_nivel(cupons_usados)
    df.at[idx, "nivel"] = nivel_id
    
    # Verifica se desbloqueou alguma conquista
    usuario_atualizado = df.loc[idx].to_dict()
    conquistas = gamificacao.verificar_conquistas(usuario_atualizado, cupom_data)
    
    # Marca as conquistas desbloqueadas e adiciona XP
    for conquista_id in conquistas:
        df.at[idx, f"conquista_{conquista_id}"] = True
        xp_conquista = gamificacao.conquistas[conquista_id]["xp"]
        df.at[idx, "xp"] = usuario_atualizado.get("xp", 0) + xp_conquista
    
    # Salva todas as mudanças
    df.to_csv(USERS_PATH, index=False, encoding="utf-8")
    st.cache_data.clear()  # Limpa o cache para refletir as mudanças
    return conquistas

# ---------------- Carregamento de Dados com Cache ---------------
@st.cache_data(show_spinner=False)
def load_xlsx_cached(path):
    """
    Carrega arquivos Excel com cache.
    Cache significa que não precisa ler o arquivo toda vez - fica mais rápido!
    """
    try:
        return pd.read_excel(path) if os.path.exists(path) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_csv_cached(path):
    """
    Carrega arquivos CSV com cache.
    """
    try:
        return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def normcols(df: pd.DataFrame):
    """
    Normaliza os nomes das colunas para facilitar nosso trabalho.
    Assim não importa se a coluna se chama "Data", "data" ou "DATA" - encontramos ela!
    """
    df = df.copy()
    # Remove espaços extras dos nomes das colunas
    df.columns = [str(c).strip() for c in df.columns]
    
    # Cria um dicionário com versões minúsculas para facilitar busca
    lower = {c.lower(): c for c in df.columns}
    
    def get(*names):
        """
        Procura uma coluna por vários nomes possíveis.
        Exemplo: get("data", "date", "data_captura") - acha qualquer um desses
        """
        for n in names:
            if n in lower: 
                return lower[n]  # Encontrou exato
        for want in names:
            for lc, orig in lower.items():
                if want in lc: 
                    return orig  # Encontrou parecido
        return None  # Não encontrou
        
    return df, get

# ---------------- Componentes Visuais da Interface ----------------
def top_header():
    """
    Cabeçalho que aparece no topo de todas as páginas depois do login.
    Mostra logo, informações do usuário e botão de sair.
    """
    col1, col2, col3 = st.columns([5,3,1])
    
    with col1:
        # Nome da aplicação
        st.markdown('<div style="font-size: 24px; font-weight: bold; color: #0C2D6B;">CupomGO</div>', unsafe_allow_html=True)
    
    with col2:
        # Informações do usuário logado
        user = st.session_state.get("user_email") or "Usuário"
        df_users = load_users()
        user_data = df_users[df_users["email"] == user]
        
        if not user_data.empty:
            nivel_id = user_data["nivel"].iloc[0]
            if nivel_id not in gamificacao.niveis:
                nivel_id = 1  # Segurança
            nivel_info = gamificacao.niveis.get(nivel_id, gamificacao.niveis[1])
            st.markdown(
                f'<div style="text-align:right;color:#000000;padding-top:6px;">👤 {user} <span style="color:{nivel_info["cor"]}">{nivel_info["nome"]}</span></div>', 
                unsafe_allow_html=True
            )
        else:
            st.markdown(f'<div style="text-align:right;color:#000000;padding-top:6px;">👤 {user}</div>', unsafe_allow_html=True)
    
    with col3:
        # Botão de sair
        if st.button("🚪 Sair", key="logout_btn_top"):
            # Limpa toda a sessão e volta para o login
            st.session_state.clear()
            st.session_state.auth = False
            st.session_state.page = "home"
            st.rerun()

def hero(title, sub=""):
    """
    Cria um título grande e bonito para as páginas.
    Chamamos de "hero" porque é a primeira coisa que o usuário vê.
    """
    st.markdown(
        f'<div class="pm-hero"><div class="pm-title">{title}</div><div class="pm-sub">{sub}</div></div>', 
        unsafe_allow_html=True
    )

def kpi_card(title, value):
    """
    Cria um cartão bonito para mostrar números importantes (KPIs).
    KPI = Key Performance Indicator (Indicador-chave de Performance)
    """
    st.markdown(f"""
        <div class="pm-card">
            <div class="pm-metric-title">{title}</div>
            <div class="pm-metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# ---------------- Menu Lateral de Navegação --------------
# Lista de todas as páginas disponíveis no menu
NAV_ITEMS = [
    ("Home", "home"),
    ("Indicadores Executivos", "kpis"),
    ("Análise de Tendências", "tendencias"),
    ("Financeiro", "fin"),
    ("Painel Econômico", "eco"),
    ("Uso de Cupons", "sim"),
    ("Sobre", "sobre"),
]

def sidebar_nav():
    """
    Cria o menu lateral de navegação.
    É como o mapa que ajuda usuários a navegar na aplicação.
    """
    # Logo centralizado
    safe_logo(width=150) 
    
    # Título do menu
    st.sidebar.markdown(
        '<div style="text-align: center; font-size: 20px; font-weight: bold; color: #0C2D6B; margin-bottom: 20px;">CupomGO</div>', 
        unsafe_allow_html=True
    )
    
    # Mostra informações do usuário logado
    email = st.session_state.get("user_email")
    if email:
        df_users = load_users()
        user_data = df_users[df_users["email"] == email]
        
        if not user_data.empty:
            cupons_usados = user_data["cupons_usados"].iloc[0]
            nivel_id = user_data["nivel"].iloc[0]
            
            if nivel_id not in gamificacao.niveis:
                nivel_id = 1
            nivel_info = gamificacao.niveis.get(nivel_id, gamificacao.niveis[1])
            
            # Card bonito mostrando o nível do usuário
            st.sidebar.markdown(f"""
                <div style="background: linear-gradient(135deg, {nivel_info['cor']}20, {nivel_info['cor']}40); 
                            padding: 15px; border-radius: 10px; margin-bottom: 15px; border-left: 4px solid {nivel_info['cor']};">
                    <div style="font-size: 14px; color: #666;">Seu Nível</div>
                    <div style="font-size: 18px; font-weight: bold; color: {nivel_info['cor']};">{nivel_info['nome']}</div>
                    <div style="font-size: 12px; color: #666;">{cupons_usados} cupons usados</div>
                </div>
            """, unsafe_allow_html=True)
    
    # Linha divisória
    st.sidebar.markdown("---")
    
    # Botões de navegação
    active = st.session_state.get("page", "home")
    for label, slug in NAV_ITEMS:
        if st.sidebar.button(label, key=f"nav_{slug}", use_container_width=True):
            st.session_state.page = slug  # Muda a página
            st.rerun()  # Recarrega a aplicação
    
    st.sidebar.markdown("---")
    
    # Sistema de Filtros Globais
    if not df_transacoes.empty:
        sistema_filtros.criar_filtros_sidebar(df_transacoes)

# ---------------- Gráficos Interativos com Drill-Down ----------------
def criar_grafico_vendas_temporais(df, nivel_drill_down=None):
    """
    Cria gráfico de vendas com funcionalidade de drill-down temporal
    """
    df_filtrado = sistema_filtros.aplicar_filtros(df)
    
    # Define a hierarquia de drill-down
    if nivel_drill_down is None:
        nivel_drill_down = sistema_filtros.get_nivel_atual()
    
    if nivel_drill_down:
        nivel, valor = nivel_drill_down
        if nivel == 'ano':
            df_filtrado = df_filtrado[df_filtrado['ano'] == valor]
            agrupamento = 'trimestre'
            titulo = f"Vendas por Trimestre - {valor}"
            eixo_x = 'Trimestre'
        elif nivel == 'trimestre':
            df_filtrado = df_filtrado[df_filtrado['trimestre'] == valor]
            agrupamento = 'mes'
            titulo = f"Vendas por Mês - {valor}º Trimestre"
            eixo_x = 'Mês'
        else:
            agrupamento = 'ano'
            titulo = "Vendas por Ano"
            eixo_x = 'Ano'
    else:
        agrupamento = 'ano'
        titulo = "Vendas por Ano"
        eixo_x = 'Ano'
    
    # Agrupa os dados
    if agrupamento == 'ano':
        dados_agrupados = df_filtrado.groupby('ano')['valor_compra'].sum().reset_index()
        dados_agrupados.columns = [eixo_x, 'Receita']
    elif agrupamento == 'trimestre':
        dados_agrupados = df_filtrado.groupby('trimestre')['valor_compra'].sum().reset_index()
        dados_agrupados.columns = [eixo_x, 'Receita']
        dados_agrupados[eixo_x] = 'T' + dados_agrupados[eixo_x].astype(str)
    else:  # mês
        dados_agrupados = df_filtrado.groupby('mes')['valor_compra'].sum().reset_index()
        dados_agrupados.columns = [eixo_x, 'Receita']
        # Converte número do mês para nome
        meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        dados_agrupados[eixo_x] = dados_agrupados[eixo_x].apply(lambda x: meses[x-1] if 1 <= x <= 12 else str(x))
    
    # Cria o gráfico
    fig = px.bar(
        dados_agrupados, 
        x=eixo_x, 
        y='Receita',
        title=titulo,
        color_discrete_sequence=[PRIMARY]
    )
    
    # Adiciona interatividade de drill-down
    if agrupamento == 'ano' and not dados_agrupados.empty:
        fig.update_traces(
            hovertemplate="<b>%{x}</b><br>Receita: R$ %{y:,.2f}<extra></extra>",
            customdata=dados_agrupados[eixo_x].values
        )
    elif agrupamento == 'trimestre' and not dados_agrupados.empty:
        fig.update_traces(
            hovertemplate="<b>%{x}</b><br>Receita: R$ %{y:,.2f}<extra></extra>",
            customdata=dados_agrupados[eixo_x].values
        )
    
    fig = style_fig(fig, y_fmt=",.2f")
    
    # Botão de voltar se estiver em drill-down
    if nivel_drill_down:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            if st.button("⬅️ Voltar", use_container_width=True):
                sistema_filtros.remover_drill_down()
                st.rerun()
    else:
        st.plotly_chart(fig, use_container_width=True)
    
    return fig

def criar_grafico_vendas_lojas(df):
    """
    Cria gráfico de vendas por loja com interatividade
    """
    df_filtrado = sistema_filtros.aplicar_filtros(df)
    
    if 'nome_loja' not in df_filtrado.columns or 'valor_compra' not in df_filtrado.columns:
        st.warning("Dados insuficientes para gráfico de vendas por loja.")
        return
    
    # Agrupa por loja
    vendas_lojas = df_filtrado.groupby('nome_loja')['valor_compra'].agg(['sum', 'count']).reset_index()
    vendas_lojas.columns = ['Loja', 'Receita', 'Transações']
    vendas_lojas = vendas_lojas.nlargest(10, 'Receita')
    
    # Cria gráfico duplo
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=vendas_lojas['Loja'],
        y=vendas_lojas['Receita'],
        name='Receita',
        marker_color=PRIMARY,
        hovertemplate="<b>%{x}</b><br>Receita: R$ %{y:,.2f}<extra></extra>"
    ))
    
    fig.add_trace(go.Scatter(
        x=vendas_lojas['Loja'],
        y=vendas_lojas['Transações'],
        name='Transações',
        yaxis='y2',
        mode='lines+markers',
        line=dict(color='#FF6B6B', width=3),
        hovertemplate="<b>%{x}</b><br>Transações: %{y}<extra></extra>"
    ))
    
    fig.update_layout(
        title="Top 10 Lojas por Receita e Volume",
        xaxis_title="Lojas",
        yaxis=dict(title="Receita (R$)"),
        yaxis2=dict(title="Número de Transações", overlaying='y', side='right'),
        showlegend=True
    )
    
    fig = style_fig(fig, y_fmt=",.2f")
    st.plotly_chart(fig, use_container_width=True)
    
    return fig

def criar_grafico_tipo_cupom(df):
    """
    Cria gráfico de distribuição por tipo de cupom
    """
    df_filtrado = sistema_filtros.aplicar_filtros(df)
    
    if 'tipo_cupom' not in df_filtrado.columns:
        st.warning("Dados insuficientes para gráfico de tipos de cupom.")
        return
    
    # Gráfico de pizza
    distribuicao_tipo = df_filtrado['tipo_cupom'].value_counts()
    
    fig = px.pie(
        values=distribuicao_tipo.values,
        names=distribuicao_tipo.index,
        title="Distribuição por Tipo de Cupom",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Quantidade: %{value}<br>Percentual: %{percent}<extra></extra>"
    )
    
    fig = style_fig(fig)
    st.plotly_chart(fig, use_container_width=True)
    
    return fig

def criar_grafico_evolucao_mensal(df):
    """
    Cria gráfico de evolução mensal com linha temporal
    """
    df_filtrado = sistema_filtros.aplicar_filtros(df)
    
    if 'data_captura' not in df_filtrado.columns or 'valor_compra' not in df_filtrado.columns:
        st.warning("Dados insuficientes para gráfico de evolução mensal.")
        return
    
    # Prepara dados mensais
    df_filtrado['data_captura'] = pd.to_datetime(df_filtrado['data_captura'])
    df_filtrado['mes_ano'] = df_filtrado['data_captura'].dt.to_period('M').astype(str)
    
    evolucao_mensal = df_filtrado.groupby('mes_ano').agg({
        'valor_compra': ['sum', 'count'],
        'nome_loja': 'nunique'
    }).reset_index()
    
    evolucao_mensal.columns = ['Mês', 'Receita', 'Transações', 'Lojas_Únicas']
    
    # Gráfico de evolução
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=evolucao_mensal['Mês'],
        y=evolucao_mensal['Receita'],
        name='Receita',
        mode='lines+markers',
        line=dict(color=PRIMARY, width=3),
        hovertemplate="<b>%{x}</b><br>Receita: R$ %{y:,.2f}<extra></extra>"
    ))
    
    fig.add_trace(go.Bar(
        x=evolucao_mensal['Mês'],
        y=evolucao_mensal['Transações'],
        name='Transações',
        yaxis='y2',
        marker_color='rgba(255, 107, 107, 0.7)',
        hovertemplate="<b>%{x}</b><br>Transações: %{y}<extra></extra>"
    ))
    
    fig.update_layout(
        title="Evolução Mensal - Receita e Volume",
        xaxis_title="Mês",
        yaxis=dict(title="Receita (R$)"),
        yaxis2=dict(title="Número de Transações", overlaying='y', side='right'),
        showlegend=True
    )
    
    fig = style_fig(fig, y_fmt=",.2f")
    st.plotly_chart(fig, use_container_width=True)
    
    return fig

# ---------------- Páginas Principais do Sistema ----------------
def page_home(tx, stores):
    """
    Página inicial - visão geral do sistema com gráficos interativos.
    """
    top_header()
    hero("🏠 Página Inicial", "Visão geral das operações e métricas principais")

    # Introdução amigável
    st.markdown("""
    <div style="background-color: #f0f2f6; border-radius: 10px; padding: 20px; margin-bottom: 20px; border: 1px solid #e0e0e0;">
        <h3 style="color: #0C2D6B; margin-top: 0;">Bem-vindo ao CupomGO!</h3>
        <p style="color: #333; font-size: 16px;">
        Esta é a sua central de inteligência para monitorar o desempenho das suas campanhas de cupons. 
        Aqui na Página Inicial, você tem uma visão geral das métricas mais importantes.
        </p>
        <p style="color: #333; font-size: 16px;">
        <strong>🎛️ Funcionalidades Interativas:</strong>
        <ul>
            <li style="color: #333;"><strong>Filtros Globais:</strong> Use a sidebar para filtrar dados por período, região, tipo de cupom e loja.</li>
            <li style="color: #333;"><strong>Drill-Down:</strong> Clique nas barras dos gráficos para navegar hierarquicamente (Ano → Trimestre → Mês).</li>
            <li style="color: #333;"><strong>Gráficos Interativos:</strong> Passe o mouse sobre os gráficos para ver detalhes.</li>
        </ul>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    # Carrega e prepara os dados
    df, get = normcols(tx)
    
    # Se não há dados reais, cria dados de exemplo para demonstração
    if df.empty:
        st.info("Nenhum dado encontrado. A carregar dados de exemplo.")
        df = generate_example_data(num_rows=1000)
        get = lambda *names: names[0] if names else None

    # Aplica filtros globais
    df_filtrado = sistema_filtros.aplicar_filtros(df)
    
    # Métricas principais em cards bonitos
    c1, c2, c3, c4 = st.columns(4)
    with c1: 
        kpi_card("Total de Cupons", f"{len(df_filtrado):,}".replace(",", "."))
    with c2: 
        kpi_card("Conversões", f"{len(df_filtrado):,}".replace(",", "."))
    with c3:
        avg = df_filtrado['valor_compra'].mean() if 'valor_compra' in df_filtrado.columns else 0
        kpi_card("Ticket Médio", f"R$ {avg:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
    with c4:
        total_receita = df_filtrado['valor_compra'].sum() if 'valor_compra' in df_filtrado.columns else 0
        kpi_card("Receita Total", f"R$ {total_receita:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

    # Gráficos Interativos
    st.markdown("## 📊 Visualizações Interativas")
    
    # Gráfico de vendas temporal com drill-down
    st.markdown("### 📈 Evolução Temporal")
    criar_grafico_vendas_temporais(df)
    
    # Gráficos em colunas
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏪 Top Lojas")
        criar_grafico_vendas_lojas(df)
    
    with col2:
        st.markdown("### 🎯 Tipos de Cupom")
        criar_grafico_tipo_cupom(df)
    
    # Gráfico de evolução mensal
    st.markdown("### 📅 Evolução Mensal Detalhada")
    criar_grafico_evolucao_mensal(df)

def generate_example_data(num_rows=1000):
    """
    Cria dados de exemplo realistas quando não temos dados reais.
    """
    np.random.seed(42)
    
    # Gera datas dos últimos 2 anos
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=730)
    dates = pd.date_range(start_date, end_date, num=num_rows)
    
    # Lojas realistas
    lojas = ['iFood', 'Mercado Livre', 'Amazon', 'Uber', 'Magazine Luiza', 
             'Supermercado Dia', 'Renner', 'Netshoes', 'Americanas', 'Submarino']
    
    # Tipos de cupom
    tipos_cupom = ['Desconto %', 'Cashback', 'Frete Grátis', 'Primeira Compra', 'Black Friday']
    
    # Regiões
    regioes = ['Sudeste', 'Sul', 'Nordeste', 'Centro-Oeste', 'Norte']
    
    df = pd.DataFrame({
        'data_captura': np.random.choice(dates, num_rows),
        'nome_loja': np.random.choice(lojas, num_rows, p=[0.2, 0.15, 0.1, 0.1, 0.1, 0.08, 0.08, 0.07, 0.06, 0.06]),
        'tipo_cupom': np.random.choice(tipos_cupom, num_rows, p=[0.4, 0.3, 0.15, 0.1, 0.05]),
        'valor_compra': np.random.exponential(100, num_rows).round(2),
        'regiao': np.random.choice(regioes, num_rows)
    })
    
    # Adiciona hierarquia temporal
    df['data_captura'] = pd.to_datetime(df['data_captura'])
    df['ano'] = df['data_captura'].dt.year
    df['trimestre'] = df['data_captura'].dt.quarter
    df['mes'] = df['data_captura'].dt.month
    
    return df

def page_kpis(tx):
    """
    Página de Indicadores Executivos - métricas para tomada de decisão.
    Agora com gráficos interativos.
    """
    top_header()
    hero("📊 Painel Executivo", "Métricas estratégicas por perfil de liderança")

    st.markdown("""
    <div style="background-color: #f0f2f6; border-radius: 10px; padding: 20px; margin-bottom: 20px; border: 1px solid #e0e0e0;">
        <p style="color: #333; font-size: 16px;">
        Esta página consolida os indicadores-chave de performance (KPIs) segmentados 
        pelos principais pilares de gestão. <strong>Use os filtros na sidebar</strong> para analisar 
        perfis específicos de dados.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Carrega dados
    df, get = normcols(tx)
    
    if df.empty:
        st.info("Aguardando dados... Gerando dados de exemplo mais realistas para demonstração.")
        df = generate_example_data(num_rows=2500)
        df, get = normcols(df)

    # Aplica filtros
    df_filtrado = sistema_filtros.aplicar_filtros(df)

    # Abas para diferentes perfis executivos
    tab1, tab2, tab3 = st.tabs(["📈 Performance CEO", "🔧 Performance CTO", "💰 Performance CFO"])

    with tab1:
        st.subheader("📈 Performance CEO - Conversões e Taxas")
        criar_grafico_vendas_temporais(df)
        criar_grafico_evolucao_mensal(df)

    with tab2:
        st.subheader("🔧 Performance CTO - Volume Operacional")
        criar_grafico_vendas_lojas(df)
        
        # Gráfico adicional para CTO - Distribuição por horário
        if 'data_captura' in df_filtrado.columns:
            df_filtrado['hora'] = pd.to_datetime(df_filtrado['data_captura']).dt.hour
            distribuicao_hora = df_filtrado['hora'].value_counts().sort_index()
            
            fig_hora = px.bar(
                x=distribuicao_hora.index,
                y=distribuicao_hora.values,
                title="Distribuição de Transações por Hora do Dia",
                labels={'x': 'Hora do Dia', 'y': 'Transações'},
                color_discrete_sequence=['#00CC96']
            )
            fig_hora = style_fig(fig_hora)
            st.plotly_chart(fig_hora, use_container_width=True)

    with tab3:
        st.subheader("💰 Performance CFO - Receita e ROI")
        criar_grafico_tipo_cupom(df)
        criar_grafico_evolucao_mensal(df)

def page_tendencias(tx):
    """
    Página de análise de tendências - entenda o comportamento dos usuários.
    Agora com gráficos interativos e filtros.
    """
    top_header()
    hero("📈 Análise de Tendências", "Comportamento do consumidor e padrões de uso de cupons")

    st.markdown("""
    <div style="background-color: #f0f2f6; border-radius: 10px; padding: 20px; margin-bottom: 20px; border: 1px solid #e0e0e0;">
        <p style="color: #333; font-size: 16px;">
        Explore os padrões por detrás dos números. <strong>Use os filtros na sidebar</strong> para analisar 
        perfis específicos de comportamento dos seus clientes.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Carrega dados
    df, get = normcols(tx)
    
    if df.empty:
        st.info("Aguardando dados... Gerando dados de exemplo mais realistas para demonstração.")
        df = generate_example_data(num_rows=2500)
        df, get = normcols(df)

    # Aplica filtros
    df_filtrado = sistema_filtros.aplicar_filtros(df)

    # Abas para diferentes tipos de análise
    tab1, tab2, tab3 = st.tabs(["📊 Tendências Temporais", "🏪 Comportamento por Loja", "🎯 Padrões de Consumo"])

    with tab1:
        st.subheader("Tendências Temporais de Uso")
        criar_grafico_vendas_temporais(df)
        criar_grafico_evolucao_mensal(df)

    with tab2:
        st.subheader("Comportamento por Estabelecimento")
        criar_grafico_vendas_lojas(df)
        
        # Gráfico adicional - Ticket médio por loja
        if 'nome_loja' in df_filtrado.columns and 'valor_compra' in df_filtrado.columns:
            ticket_lojas = df_filtrado.groupby('nome_loja')['valor_compra'].mean().nlargest(10).sort_values(ascending=True)
            fig_ticket = px.bar(
                y=ticket_lojas.index,
                x=ticket_lojas.values,
                title="Ticket Médio por Loja (Top 10)",
                labels={'x': 'Ticket Médio (R$)', 'y': 'Loja'},
                orientation='h',
                color_discrete_sequence=['#00CC96']
            )
            fig_ticket = style_fig(fig_ticket, x_fmt=",.2f")
            st.plotly_chart(fig_ticket, use_container_width=True)

    with tab3:
        st.subheader("Padrões de Consumo e Eficiência")
        criar_grafico_tipo_cupom(df)
        
        # Gráfico adicional - Distribuição por valor
        if 'valor_compra' in df_filtrado.columns:
            fig_distribuicao = px.histogram(
                df_filtrado,
                x='valor_compra',
                title="Distribuição dos Valores das Compras",
                labels={'valor_compra': 'Valor da Compra (R$)'},
                color_discrete_sequence=[PRIMARY]
            )
            fig_distribuicao = style_fig(fig_distribuicao, x_fmt=",.2f")
            st.plotly_chart(fig_distribuicao, use_container_width=True)

def page_financeiro(tx):
    """
    Página de análise financeira detalhada - DRE, ROI, balanço, etc.
    Agora com gráficos interativos e filtros.
    """
    top_header()
    hero("💰 Painel Financeiro", "Análise detalhada de receita, despesas, lucro e métricas financeiras")
    
    st.markdown("""
    <div style="background-color: #f0f2f6; border-radius: 10px; padding: 20px; margin-bottom: 20px; border: 1px solid #e0e0e0;">
        <p style="color: #333; font-size: 16px;">
        Esta secção oferece uma visão aprofundada da saúde financeira da sua operação de cupons. 
        <strong>Use os filtros na sidebar</strong> para analisar períodos específicos.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Carrega dados
    df, get = normcols(tx)
    
    if df.empty:
        st.info("Aguardando dados... Gerando dados de exemplo mais realistas para demonstração.")
        df = generate_example_data(num_rows=2500)
        df, get = normcols(df)

    # Aplica filtros
    df_filtrado = sistema_filtros.aplicar_filtros(df)

    # Abas para diferentes análises financeiras
    tab1, tab2, tab3 = st.tabs(["📈 Fluxo Financeiro", "📊 Rentabilidade", "🎯 Eficiência"])

    with tab1:
        st.subheader("Fluxo Financeiro")
        criar_grafico_vendas_temporais(df)
        criar_grafico_evolucao_mensal(df)

    with tab2:
        st.subheader("Análise de Rentabilidade")
        criar_grafico_tipo_cupom(df)
        criar_grafico_vendas_lojas(df)

    with tab3:
        st.subheader("Indicadores de Eficiência")
        
        # KPIs financeiros
        col1, col2, col3, col4 = st.columns(4)
        
        total_receita = df_filtrado['valor_compra'].sum() if 'valor_compra' in df_filtrado.columns else 0
        total_transacoes = len(df_filtrado)
        ticket_medio = total_receita / total_transacoes if total_transacoes > 0 else 0
        lojas_unicas = df_filtrado['nome_loja'].nunique() if 'nome_loja' in df_filtrado.columns else 0
        
        with col1:
            kpi_card("Receita Total", f"R$ {total_receita:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
        with col2:
            kpi_card("Transações", f"{total_transacoes:,}".replace(",", "."))
        with col3:
            kpi_card("Ticket Médio", f"R$ {ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
        with col4:
            kpi_card("Lojas Únicas", f"{lojas_unicas}")

def page_eco():
    """
    Página de contexto econômico - mostra indicadores macroeconômicos.
    Agora com filtros interativos.
    """
    top_header()
    hero("📈 Painel Econômico", "Indicadores macroeconômicos e tendências do mercado")

    st.markdown("""
    <div style="background-color: #f0f2f6; border-radius: 10px; padding: 20px; margin-bottom: 20px; border: 1px solid #e0e0e0;">
        <p style="color: #333; font-size: 16px;">
        Nenhum negócio opera isoladamente. Esta página contextualiza o desempenho dos seus cupons 
        com o cenário macroeconômico. <strong>Use os filtros na sidebar</strong> para analisar períodos específicos.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Carrega dados econômicos
    if os.path.exists(ECON_PATH):
        try:
            eco = pd.read_csv(ECON_PATH)
        except Exception:
            eco = pd.DataFrame()
    else:
        eco = pd.DataFrame()

    # Dados de exemplo se não houver dados reais
    if eco.empty:
        st.info("Ficheiro 'economia.csv' não encontrado. A carregar dados de exemplo.")
        eco = pd.DataFrame({
            "Data": pd.date_range(start='2023-01-01', end='2024-12-31', freq='M'),
            "Selic": np.random.uniform(10, 14, 24),
            "IPCA": np.random.uniform(3, 8, 24),
            "Inadimplencia": np.random.uniform(4, 7, 24),
            "PIB_Variacao": np.random.uniform(0.5, 3.0, 24)
        })

    # Aplica filtros aos dados econômicos
    eco_filtrado = eco.copy()
    if 'Data' in eco_filtrado.columns:
        eco_filtrado['Data'] = pd.to_datetime(eco_filtrado['Data'])
        if sistema_filtros.filtros_aplicados.get('data_inicio') and sistema_filtros.filtros_aplicados.get('data_fim'):
            mask = (eco_filtrado['Data'].dt.date >= sistema_filtros.filtros_aplicados['data_inicio']) & \
                   (eco_filtrado['Data'].dt.date <= sistema_filtros.filtros_aplicados['data_fim'])
            eco_filtrado = eco_filtrado[mask]

    # Gráficos econômicos
    col1, col2 = st.columns(2)
    
    with col1:
        if 'Selic' in eco_filtrado.columns:
            fig_selic = px.line(
                eco_filtrado, 
                x='Data', 
                y='Selic',
                title="Evolução da Taxa SELIC (%)",
                labels={'Selic': 'SELIC (%)', 'Data': 'Data'},
                color_discrete_sequence=[PRIMARY]
            )
            fig_selic = style_fig(fig_selic)
            st.plotly_chart(fig_selic, use_container_width=True)
    
    with col2:
        if 'IPCA' in eco_filtrado.columns:
            fig_ipca = px.line(
                eco_filtrado, 
                x='Data', 
                y='IPCA',
                title="Evolução do IPCA (%)",
                labels={'IPCA': 'IPCA (%)', 'Data': 'Data'},
                color_discrete_sequence=['#FF6B6B']
            )
            fig_ipca = style_fig(fig_ipca)
            st.plotly_chart(fig_ipca, use_container_width=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        if 'Inadimplencia' in eco_filtrado.columns:
            fig_inad = px.area(
                eco_filtrado, 
                x='Data', 
                y='Inadimplencia',
                title="Evolução da Inadimplência (%)",
                labels={'Inadimplencia': 'Inadimplência (%)', 'Data': 'Data'},
                color_discrete_sequence=['#00CC96']
            )
            fig_inad = style_fig(fig_inad)
            st.plotly_chart(fig_inad, use_container_width=True)
    
    with col4:
        if 'PIB_Variacao' in eco_filtrado.columns:
            fig_pib = px.bar(
                eco_filtrado, 
                x='Data', 
                y='PIB_Variacao',
                title="Variação do PIB Trimestral (%)",
                labels={'PIB_Variacao': 'Variação do PIB (%)', 'Data': 'Data'},
                color_discrete_sequence=['#FFA500']
            )
            fig_pib = style_fig(fig_pib)
            st.plotly_chart(fig_pib, use_container_width=True)

# [As funções page_simulacaologin e page_sobre permanecem exatamente como estavam no código original]

# ---------------- Telas de Login e Cadastro ----------------
def login_screen():
    """
    Tela de login para usuários que já têm conta.
    """
    # Centraliza o formulário na tela
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(
            """
            <div class="pm-auth">
            <div style="text-align: center; margin-bottom: 2rem;">
                <h2 style="color: #000000; margin-bottom: 0.5rem;">Entrar no CupomGO</h2>
                <p style="color: #000000;">Use seu e-mail e senha para acessar o dashboard</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Formulário de login
        with st.form("login", clear_on_submit=False):
            email = st.text_input("E-mail", placeholder="Digite seu e-mail", label_visibility="visible")
            pwd = st.text_input("Senha", type="password", placeholder="Digite sua senha", label_visibility="visible")
            
            colA, colB = st.columns([1,1])
            ok = colA.form_submit_button("Entrar", use_container_width=True)
            to_signup = colB.form_submit_button("Criar conta", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # Navegação para cadastro
        if to_signup:
            st.session_state.auth_mode = "signup"
            st.rerun()

        # Tentativa de login
        if ok:
            if email and pwd and check_login(email, pwd):
                # Login bem-sucedido!
                st.session_state.auth = True
                st.session_state.user_email = email
                st.session_state.page = "home"
                st.success("✅ Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("❌ E-mail ou senha inválidos.")

def signup_screen():
    """
    Tela de cadastro para novos usuários.
    """
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(
            """
            <div class="pm-auth">
            <div style="text-align: center; margin-bottom: 2rem;">
                <h2 style="color: #000000; margin-bottom: 0.5rem;">Criar conta</h2>
                <p style="color: #000000;">Cadastre-se para começar a visualizar seus indicadores</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Formulário de cadastro
        with st.form("signup"):
            nome = st.text_input("Nome completo", placeholder="Seu nome e sobrenome", label_visibility="visible")
            email = st.text_input("E-mail", placeholder="Digite seu e-mail", label_visibility="visible")
            pwd = st.text_input("Senha", type="password", placeholder="Crie uma senha", label_visibility="visible")
            pwd2 = st.text_input("Confirmar senha", type="password", placeholder="Repita a senha", label_visibility="visible")
            ok = st.form_submit_button("Cadastrar", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # Link para voltar ao login
        if st.button("Já tem conta? Ir para Login", use_container_width=True):
            st.session_state.auth_mode = "login"
            st.rerun()

        # Processamento do cadastro
        if ok:
            # Validações passo a passo
            if not (nome and email and pwd and pwd2):
                st.warning("Preencha todos os campos.")
            elif len(pwd) < 6:
                st.warning("A senha deve ter pelo menos 6 caracteres.")
            elif pwd != pwd2:
                st.warning("As senhas não conferem.")
            elif email_exists(load_users(), email):
                st.error("Este e-mail já está cadastrado.")
            else:
                # Tudo certo! Cria o usuário
                save_user(nome, email, pwd)
                st.success("✅ Cadastro realizado! Agora faça login.")
                st.session_state.auth_mode = "login"
                st.rerun()

# ---------------- Estado da Aplicação ----------------
# Inicializa o estado da aplicação se não existir
if "auth" not in st.session_state: 
    st.session_state.auth = False
if "auth_mode" not in st.session_state: 
    st.session_state.auth_mode = "login"
if "user_email" not in st.session_state: 
    st.session_state.user_email = None
if "page" not in st.session_state: 
    st.session_state.page = "home"

# ---------------- Roteamento Principal ----------------
def main():
    """
    Função principal que controla toda a aplicação.
    """
    if not st.session_state.auth:
        # Usuário não está logado - mostra telas de autenticação
        if st.session_state.auth_mode == "login":
            login_screen()
        else:
            signup_screen()
    else:
        # Usuário está logado - carrega dados e mostra o dashboard
        tx = transacoes if not transacoes.empty else pd.DataFrame()
        stores = lojas if not lojas.empty else pd.DataFrame()
        sidebar_nav()
        page = st.session_state.get("page", "home")
        
        # Roteamento para as diferentes páginas
        if page == "home": 
            page_home(tx, stores)
        elif page == "kpis": 
            page_kpis(tx)
        elif page == "tendencias":
            page_tendencias(tx)
        elif page == "fin": 
            page_financeiro(tx)
        elif page == "eco": 
            page_eco()
        elif page == "sim":
            page_simulacaologin()
        elif page == "sobre":
            page_sobre()

# Ponto de entrada da aplicação
if __name__ == "__main__":
    main()
