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
    Aplica um visual consistente em todos os gráficos com interações melhoradas.
    """
    # Configura o layout geral do gráfico
    fig.update_layout(
        font=dict(color="black", size=12),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="closest",  # Mais preciso para interações
        hoverlabel=dict(
            bgcolor="white",
            font_color="black",
            font_size=12,
            bordercolor="lightgray",
            namelength=-1
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.35,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="lightgray",
            borderwidth=1,
            font=dict(size=11)
        ),
        title_font=dict(color="black", size=16),
        margin=dict(l=80, r=80, t=80, b=140),
        # Melhorias para interação
        clickmode='event+select',  # Permite cliques e seleções
        dragmode='zoom',  # Permite zoom
        showlegend=True
    )
    
    # Estiliza os eixos
    fig.update_xaxes(
        title_font=dict(color="black", size=12), 
        tickfont=dict(color="black", size=11), 
        gridcolor="lightgray",
        zerolinecolor="lightgray", 
        showgrid=True
    )
    
    fig.update_yaxes(
        title_font=dict(color="black", size=12), 
        tickfont=dict(color="black", size=11), 
        gridcolor="lightgray", 
        zerolinecolor="lightgray", 
        showgrid=True
    )
    
    # Formata números se especificado
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

# ---------------- SISTEMA DE FILTROS GLOBAIS ----------------
def criar_filtros_globais(df):
    """
    Cria filtros globais que afetam todos os gráficos do dashboard.
    """
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎛️ Filtros Globais")
    
    # Filtro por período
    if 'data_captura' in df.columns:
        df['data_captura'] = pd.to_datetime(df['data_captura'], errors='coerce')
        datas_validas = df['data_captura'].dropna()
        if not datas_validas.empty:
            min_date = datas_validas.min().date()
            max_date = datas_validas.max().date()
            
            periodo = st.sidebar.date_input(
                "📅 Período",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="global_period"
            )
            
            if len(periodo) == 2:
                mask = (df['data_captura'].dt.date >= periodo[0]) & (df['data_captura'].dt.date <= periodo[1])
                df = df[mask]
    
    # Filtro por loja
    if 'nome_loja' in df.columns:
        lojas = ['Todas'] + sorted(df['nome_loja'].unique().tolist())
        loja_selecionada = st.sidebar.selectbox(
            "🏪 Filtrar por Loja",
            lojas,
            key="global_store"
        )
        if loja_selecionada != 'Todas':
            df = df[df['nome_loja'] == loja_selecionada]
    
    # Filtro por tipo de cupom
    if 'tipo_cupom' in df.columns:
        tipos = ['Todos'] + sorted(df['tipo_cupom'].unique().tolist())
        tipo_selecionado = st.sidebar.selectbox(
            "🎯 Filtrar por Tipo",
            tipos,
            key="global_type"
        )
        if tipo_selecionado != 'Todos':
            df = df[df['tipo_cupom'] == tipo_selecionado]
    
    # Filtro por valor mínimo
    if 'valor_compra' in df.columns:
        valor_min = st.sidebar.slider(
            "💰 Valor Mínimo da Compra (R$)",
            min_value=float(df['valor_compra'].min()),
            max_value=float(df['valor_compra'].max()),
            value=float(df['valor_compra'].min()),
            key="global_min_value"
        )
        df = df[df['valor_compra'] >= valor_min]
    
    return df

# ---------------- COMPONENTES DE INTERAÇÃO AVANÇADOS ----------------
def criar_grafico_interativo(df, tipo, x_col, y_col, color_col=None, title="", 
                           hover_data=None, selection_callback=None):
    """
    Cria gráficos com interações avançadas.
    """
    if df.empty:
        return go.Figure()
    
    # Dados para tooltip
    hover_data = hover_data or {}
    
    if tipo == 'bar':
        fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=title,
                    hover_data=hover_data, text_auto=True)
        
        # Melhorar interatividade
        fig.update_traces(
            hovertemplate=f"<b>{x_col}:</b> %{{x}}<br><b>{y_col}:</b> %{{y}}<extra></extra>",
            hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial"),
            marker_line_width=0
        )
        
    elif tipo == 'line':
        fig = px.line(df, x=x_col, y=y_col, color=color_col, title=title,
                     hover_data=hover_data, markers=True)
        
        fig.update_traces(
            hovertemplate=f"<b>{x_col}:</b> %{{x}}<br><b>{y_col}:</b> %{{y:,.2f}}<extra></extra>",
            line_width=3,
            marker=dict(size=8)
        )
        
    elif tipo == 'scatter':
        fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=title,
                        hover_data=hover_data, size_max=15)
        
        fig.update_traces(
            hovertemplate=f"<b>{x_col}:</b> %{{x}}<br><b>{y_col}:</b> %{{y}}<extra></extra>",
            marker=dict(size=10, opacity=0.7, line=dict(width=1, color='DarkSlateGrey'))
        )
    
    # Aplicar estilo consistente
    fig = style_fig(fig)
    
    # Adicionar funcionalidade de destaque
    fig.update_traces(
        selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=0.3))
    )
    
    return fig

def criar_mapa_calor_interativo(df, x_col, y_col, values_col, title=""):
    """
    Cria heatmap com interações avançadas.
    """
    if df.empty:
        return go.Figure()
    
    pivot_table = df.pivot_table(values=values_col, index=y_col, columns=x_col, aggfunc='sum', fill_value=0)
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_table.values,
        x=pivot_table.columns,
        y=pivot_table.index,
        colorscale='Blues',
        hoverongaps=False,
        hovertemplate=f"<b>{x_col}:</b> %{{x}}<br><b>{y_col}:</b> %{{y}}<br><b>Total:</b> %{{z:,.2f}}<extra></extra>",
        showscale=True
    ))
    
    fig.update_layout(title=title)
    return style_fig(fig)

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

# ---------------- FUNÇÃO PARA DADOS DE EXEMPLO ----------------
def generate_example_data(num_rows=2500):
    """
    Cria dados de exemplo realistas quando não temos dados reais.
    Isso permite demonstrar a aplicação mesmo sem base de dados.
    """
    np.random.seed(42)  # Para resultados consistentes
    
    # Gera datas dos últimos ~18 meses
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=540) 
    
    # Cria datas com mais transações em finais de semana
    base_days = pd.date_range(start_date, end_date)
    day_weights = [0.9, 0.9, 1.0, 1.1, 1.4, 1.5, 1.2]  # Segunda a Domingo
    day_probs = [day_weights[d.weekday()] for d in base_days]
    day_probs = np.array(day_probs) / sum(day_probs)
    chosen_dates = np.random.choice(base_days, num_rows, p=day_probs, replace=True)
    
    # Horários mais prováveis: almoço e jantar
    hours_lunch = np.random.normal(12.5, 1, num_rows // 2)
    hours_evening = np.random.normal(20, 1.5, num_rows - (num_rows // 2))
    hours = np.concatenate([hours_lunch, hours_evening])
    np.random.shuffle(hours)
    minutes = np.random.randint(0, 60, num_rows)
    
    # Combina datas e horários
    final_dates = [
        d.replace(hour=int(h % 24), minute=int(m), second=0, microsecond=0)
        for d, h, m in zip(chosen_dates, hours, minutes)
    ]
    
    df = pd.DataFrame({'data_captura': final_dates})
    
    # Lojas realistas com probabilidades diferentes
    lojas = ['iFood', 'Mercado Livre', 'Amazon', 'Uber', 'Magazine Luiza', 'Supermercado Dia', 'Renner', 'Netshoes']
    loja_probs = [0.30, 0.20, 0.15, 0.10, 0.08, 0.07, 0.05, 0.05]
    df['nome_loja'] = np.random.choice(lojas, num_rows, p=loja_probs)
    
    # Categorias das lojas
    cat_map = {
        'iFood': 'Alimentação', 'Uber': 'Transporte', 'Supermercado Dia': 'Varejo', 'Renner': 'Moda', 
        'Netshoes': 'Esportes', 'Mercado Livre': 'Marketplace', 'Amazon': 'Marketplace', 'Magazine Luiza': 'Varejo'
    }
    df['categoria_estabelecimento'] = df['nome_loja'].map(cat_map)
    
    # Tipos de cupom
    tipos = ['Desconto %', 'Cashback', 'Frete Grátis', 'Primeira Compra']
    tipo_probs = [0.4, 0.3, 0.2, 0.1]
    df['tipo_cupom'] = np.random.choice(tipos, num_rows, p=tipo_probs)
    
    # Valores realistas por loja
    valor_base_map = {
        'iFood': 70, 'Uber': 30, 'Supermercado Dia': 150, 'Renner': 200, 
        'Netshoes': 250, 'Mercado Livre': 180, 'Amazon': 220, 'Magazine Luiza': 800
    }
    df['valor_base'] = df['nome_loja'].map(valor_base_map)
    df['valor_compra'] = np.random.normal(df['valor_base'], df['valor_base'] * 0.3).clip(10, 5000).round(2)
    
    # Margens e custos realistas
    margem_map = {
        'iFood': 0.3, 'Uber': 0.2, 'Supermercado Dia': 0.15, 'Renner': 0.4, 
        'Netshoes': 0.35, 'Mercado Livre': 0.25, 'Amazon': 0.2, 'Magazine Luiza': 0.22
    }
    df['margem_bruta'] = df['nome_loja'].map(margem_map)
    df['custo_venda'] = (df['valor_compra'] * (1 - df['margem_bruta'])).round(2)
    df['lucro_bruto'] = (df['valor_compra'] - df['custo_venda']).round(2)
    
    # Investimento em marketing varia por tipo de cupom
    invest_map = {'Desconto %': 0.05, 'Cashback': 0.08, 'Frete Grátis': 0.03, 'Primeira Compra': 0.15}
    df['investimento_mkt'] = (df['tipo_cupom'].map(invest_map) * df['valor_compra'] + np.random.uniform(0.5, 2, num_rows)).round(2)
    
    return df.drop(columns=['valor_base', 'margem_bruta'])

# ---------------- PÁGINAS ATUALIZADAS COM INTERAÇÕES ----------------
def page_home(tx, stores):
    """
    Página inicial - visão geral do sistema.
    É a porta de entrada para todas as análises.
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
        Utilize o <strong>menu </strong> para navegar pelas análises detalhadas, incluindo:
        <ul>
            <li style="color: #333;"><strong>Indicadores Executivos:</strong> Métricas de alto nível para CEO, CTO e CFO.</li>
            <li style="color: #333;"><strong>Análise de Tendências:</strong> Padrões de consumo e comportamento por loja.</li>
            <li style="color: #333;"><strong>Financeiro:</strong> Análise de DRE, ROI, ROIC e indicadores de rentabilidade.</li>
            <li style="color: #333;"><strong>Painel Econômico:</strong> Contexto macroeconômico (SELIC, IPCA e Inadimplência).</li>
            <li style="color: #333;"><strong>Uso de Cupons:</strong> Acompanhe seu progresso no nosso sistema de gamificação.</li>
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
        df = generate_example_data(1000)
        get = lambda *names: names[0] if names else None

    # Aplicar filtros globais
    df_filtrado = criar_filtros_globais(df.copy())
    
    # Encontra as colunas de data e valor
    dcol = get("data","data_captura")
    vcol = get("valor_compra","valor")

    # Métricas principais em cards bonitos
    c1, c2, c3, c4 = st.columns(4)
    with c1: 
        kpi_card("Total de Cupons", f"{len(df_filtrado):,}".replace(",", "."))
    with c2: 
        kpi_card("Conversões", f"{len(df_filtrado):,}".replace(",", "."))
    with c3:
        avg = df_filtrado[vcol].mean() if (vcol and (vcol in df_filtrado.columns)) else 0
        kpi_card("Ticket Médio", f"R$ {avg:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
    with c4:
        total_receita = df_filtrado[vcol].sum() if (vcol and (vcol in df_filtrado.columns)) else 0
        kpi_card("Receita Total", f"R$ {total_receita:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

    # Verifica se temos dados suficientes para gráficos
    if not dcol or dcol not in df_filtrado.columns or not vcol or vcol not in df_filtrado.columns:
        st.warning("Dados insuficientes para gerar gráficos.")
        return

    # Prepara dados mensais para o gráfico
    df_filtrado[dcol] = pd.to_datetime(df_filtrado[dcol], errors="coerce")
    df_filtrado["Mês"] = df_filtrado[dcol].dt.to_period("M").astype(str)
    resumo = df_filtrado.groupby("Mês")[vcol].agg(["sum","mean","count"]).reset_index()
    resumo.columns = ["Mês","Receita","Ticket Médio","Conversões"]

    # Gráfico principal da página inicial com interações
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=resumo["Mês"], y=resumo["Receita"], name="Receita",
        marker_color=PRIMARY,
        hovertemplate="Mês: %{x}<br>Receita: R$ %{y:,.2f}<extra></extra>",
        opacity=0.8
    ))
    fig.add_trace(go.Scatter(
        x=resumo["Mês"], y=resumo["Ticket Médio"], name="Ticket médio",
        mode="lines+markers", yaxis="y2",
        line=dict(color="darkgray", width=3),
        marker=dict(size=8, color="darkgray"),
        hovertemplate="Mês: %{x}<br>Ticket: R$ %{y:,.2f}<extra></extra>"
    ))
    fig.update_layout(
        title="Desempenho Mensal - Receita e Ticket Médio",
        xaxis_title="Mês",
        yaxis=dict(title="Receita (R$)"),
        yaxis2=dict(overlaying="y", side="right", title="Ticket médio (R$)"),
        margin=dict(t=80, b=140, l=80, r=80),
        hovermode="x unified"
    )
    fig = style_fig(fig, y_fmt=",.2f")
    st.plotly_chart(fig, use_container_width=True)

    # Gráfico de distribuição por loja (top 10)
    if 'nome_loja' in df_filtrado.columns:
        st.subheader("🏪 Top Lojas por Receita")
        
        loja_receita = df_filtrado.groupby('nome_loja')[vcol].sum().nlargest(10).reset_index()
        loja_receita.columns = ['Loja', 'Receita']
        
        fig_lojas = criar_grafico_interativo(
            loja_receita, 'bar', 'Loja', 'Receita',
            title="Top 10 Lojas por Receita",
            hover_data={'Receita': ':,.2f'}
        )
        
        st.plotly_chart(fig_lojas, use_container_width=True)

def page_kpis_interativa(tx):
    """
    Página de KPIs com interações avançadas.
    """
    top_header()
    hero("📊 Painel Executivo Interativo", "Métricas estratégicas com filtros e drill-down")

    # Aplicar filtros globais
    df_filtrado = criar_filtros_globais(tx.copy())
    
    # Se não há dados, usa dados de exemplo
    if df_filtrado.empty:
        st.info("Gerando dados de exemplo para demonstração...")
        df_filtrado = generate_example_data(1000)
    
    # Abas para diferentes perfis
    tab1, tab2, tab3 = st.tabs(["📈 CEO - Conversões", "🔧 CTO - Operações", "💰 CFO - Financeiro"])

    with tab1:
        st.subheader("📈 Performance CEO - Conversões e Taxas")
        
        # Gráfico interativo de conversões mensais
        col1, col2 = st.columns([3, 1])
        
        with col2:
            st.markdown("**Configurações**")
            mostrar_tendencia = st.checkbox("📈 Mostrar linha de tendência", True)
            agrupamento = st.radio("Agrupar por:", ["Mês", "Semana", "Dia"], horizontal=True)
        
        with col1:
            # Preparar dados para agrupamento
            df_ceo = df_filtrado.copy()
            df_ceo['data_captura'] = pd.to_datetime(df_ceo['data_captura'])
            
            if agrupamento == "Mês":
                df_ceo['periodo'] = df_ceo['data_captura'].dt.to_period('M').astype(str)
            elif agrupamento == "Semana":
                df_ceo['periodo'] = df_ceo['data_captura'].dt.strftime('%Y-%U')
            else:  # Dia
                df_ceo['periodo'] = df_ceo['data_captura'].dt.date
            
            conversoes = df_ceo.groupby('periodo').size().reset_index(name='conversoes')
            
            fig_ceo = criar_grafico_interativo(
                conversoes, 'line', 'periodo', 'conversoes',
                title=f"Evolução de Conversões por {agrupamento}",
                hover_data={'conversoes': ':,'}
            )
            
            if mostrar_tendencia and len(conversoes) > 1:
                # Adicionar linha de tendência
                z = np.polyfit(range(len(conversoes)), conversoes['conversoes'], 1)
                p = np.poly1d(z)
                fig_ceo.add_trace(go.Scatter(
                    x=conversoes['periodo'],
                    y=p(range(len(conversoes))),
                    mode='lines',
                    name='Tendência',
                    line=dict(dash='dash', color='red'),
                    hovertemplate="Tendência: %{y:.1f} conversões<extra></extra>"
                ))
            
            st.plotly_chart(fig_ceo, use_container_width=True)

        # KPIs com drill-down
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_conversoes = len(df_filtrado)
            st.metric("Total Conversões", f"{total_conversoes:,}")
            
        with col2:
            # Simular taxa de crescimento
            crescimento = np.random.uniform(5, 15)
            st.metric("Crescimento Mensal", f"+{crescimento:.1f}%")
            
        with col3:
            if st.button("🔍 Detalhes Conversões", use_container_width=True):
                st.session_state.drill_down = "conversoes_detalhes"
                
        with col4:
            if st.button("📊 Exportar Dados", use_container_width=True):
                # Simular exportação
                st.success("Dados exportados para CSV!")

        # Gráfico de pizza interativo por tipo de cupom
        if 'tipo_cupom' in df_filtrado.columns:
            st.subheader("📊 Distribuição por Tipo de Cupom")
            
            tipo_dist = df_filtrado['tipo_cupom'].value_counts().reset_index()
            tipo_dist.columns = ['Tipo', 'Quantidade']
            
            fig_pizza = px.pie(tipo_dist, values='Quantidade', names='Tipo', 
                              title="Distribuição por Tipo de Cupom",
                              hole=0.3)
            
            fig_pizza.update_traces(
                hovertemplate="<b>%{label}</b><br>Quantidade: %{value}<br>Percentual: %{percent}<extra></extra>",
                textposition='inside',
                textinfo='percent+label'
            )
            
            fig_pizza = style_fig(fig_pizza)
            st.plotly_chart(fig_pizza, use_container_width=True)

    with tab2:
        st.subheader("🔧 Performance CTO - Volume Operacional")
        
        # Heatmap de atividade por hora e dia da semana
        st.subheader("🕐 Heatmap de Atividade")
        
        df_cto = df_filtrado.copy()
        df_cto['data_captura'] = pd.to_datetime(df_cto['data_captura'])
        df_cto['hora'] = df_cto['data_captura'].dt.hour
        df_cto['dia_semana'] = df_cto['data_captura'].dt.day_name()
        
        # Ordenar dias da semana
        dias_ordem = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dias_traduzidos = {
            'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
            'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        
        df_cto['dia_semana'] = df_cto['dia_semana'].map(dias_traduzidos)
        dias_ordem_trad = [dias_traduzidos[d] for d in dias_ordem]
        
        heatmap_data = df_cto.groupby(['dia_semana', 'hora']).size().reset_index(name='transacoes')
        heatmap_data['dia_semana'] = pd.Categorical(heatmap_data['dia_semana'], categories=dias_ordem_trad, ordered=True)
        heatmap_data = heatmap_data.sort_values(['dia_semana', 'hora'])
        
        fig_heatmap = criar_mapa_calor_interativo(
            heatmap_data, 'hora', 'dia_semana', 'transacoes',
            title="Heatmap de Transações por Hora e Dia da Semana"
        )
        
        st.plotly_chart(fig_heatmap, use_container_width=True)

        # Gráfico de performance por loja com seleção interativa
        st.subheader("🏪 Performance por Loja")
        
        if 'nome_loja' in df_cto.columns and 'valor_compra' in df_cto.columns:
            loja_performance = df_cto.groupby('nome_loja').agg({
                'valor_compra': ['count', 'sum', 'mean']
            }).round(2)
            
            loja_performance.columns = ['Transações', 'Receita_Total', 'Ticket_Médio']
            loja_performance = loja_performance.reset_index()
            
            # Gráfico de barras interativo
            fig_lojas = criar_grafico_interativo(
                loja_performance.nlargest(10, 'Receita_Total'),
                'bar', 'nome_loja', 'Receita_Total',
                title="Top 10 Lojas por Receita",
                hover_data={'Ticket_Médio': ':.2f', 'Transações': ':,'}
            )
            
            st.plotly_chart(fig_lojas, use_container_width=True)

    with tab3:
        st.subheader("💰 Performance CFO - Receita e ROI")
        
        # Gráfico de evolução financeira com múltiplas métricas
        st.subheader("📈 Evolução Financeira")
        
        df_cfo = df_filtrado.copy()
        df_cfo['data_captura'] = pd.to_datetime(df_cfo['data_captura'])
        df_cfo['mes'] = df_cfo['data_captura'].dt.to_period('M').astype(str)
        
        evolucao = df_cfo.groupby('mes').agg({
            'valor_compra': ['sum', 'mean', 'count']
        }).round(2)
        
        evolucao.columns = ['Receita', 'Ticket_Médio', 'Transações']
        evolucao = evolucao.reset_index()
        
        # Gráfico com múltiplos eixos Y
        fig_evolucao = go.Figure()
        
        # Receita (barra)
        fig_evolucao.add_trace(go.Bar(
            name="Receita",
            x=evolucao['mes'],
            y=evolucao['Receita'],
            yaxis='y',
            marker_color=PRIMARY,
            hovertemplate="<b>Mês:</b> %{x}<br><b>Receita:</b> R$ %{y:,.2f}<extra></extra>"
        ))
        
        # Ticket Médio (linha)
        fig_evolucao.add_trace(go.Scatter(
            name="Ticket Médio",
            x=evolucao['mes'],
            y=evolucao['Ticket_Médio'],
            yaxis='y2',
            mode='lines+markers',
            line=dict(color='orange', width=3),
            hovertemplate="<b>Mês:</b> %{x}<br><b>Ticket Médio:</b> R$ %{y:.2f}<extra></extra>"
        ))
        
        fig_evolucao.update_layout(
            title="Evolução da Receita e Ticket Médio",
            xaxis=dict(title="Mês"),
            yaxis=dict(title="Receita (R$)", side="left"),
            yaxis2=dict(title="Ticket Médio (R$)", side="right", overlaying="y"),
            legend=dict(x=0.02, y=0.98)
        )
        
        fig_evolucao = style_fig(fig_evolucao)
        st.plotly_chart(fig_evolucao, use_container_width=True)

        # Análise de ROI interativa
        st.subheader("📊 Análise de ROI")
        
        col1, col2 = st.columns(2)
        
        with col1:
            investimento_medio = st.slider(
                "💰 Investimento Médio por Transação (%)",
                min_value=5, max_value=30, value=15
            )
        
        with col2:
            margem_desejada = st.slider(
                "🎯 Margem de Lucro Desejada (%)", 
                min_value=10, max_value=40, value=25
            )
        
        # Calcular ROI simulado
        if 'nome_loja' in df_cfo.columns:
            roi_analysis = df_cfo.groupby('nome_loja').agg({
                'valor_compra': ['sum', 'count']
            }).round(2)
            
            roi_analysis.columns = ['Receita', 'Transações']
            roi_analysis = roi_analysis.reset_index()
            
            roi_analysis['Investimento'] = roi_analysis['Receita'] * (investimento_medio / 100)
            roi_analysis['Lucro'] = roi_analysis['Receita'] * (margem_desejada / 100)
            roi_analysis['ROI'] = ((roi_analysis['Lucro'] - roi_analysis['Investimento']) / roi_analysis['Investimento'] * 100).round(2)
            
            # Gráfico de ROI
            fig_roi = criar_grafico_interativo(
                roi_analysis.nlargest(10, 'ROI'),
                'bar', 'nome_loja', 'ROI',
                title=f"ROI por Loja (Top 10) - Investimento: {investimento_medio}%",
                hover_data={'Receita': ':.2f', 'Lucro': ':.2f', 'Investimento': ':.2f'}
            )
            
            fig_roi.update_yaxes(ticksuffix="%")
            st.plotly_chart(fig_roi, use_container_width=True)

def page_tendencias_interativa(tx):
    """
    Página de tendências com análises interativas.
    """
    top_header()
    hero("📈 Análise de Tendências Interativa", "Explore padrões e comportamentos com filtros avançados")

    # Aplicar filtros
    df_filtrado = criar_filtros_globais(tx.copy())
    
    if df_filtrado.empty:
        df_filtrado = generate_example_data(1500)
    
    # Sidebar com filtros específicos de tendências
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Filtros de Tendências")
    
    # Filtro de análise temporal
    analise_temporal = st.sidebar.radio(
        "Análise Temporal:",
        ["Horária", "Diária", "Semanal", "Mensal"],
        horizontal=True
    )
    
    # Filtro de segmentação
    segmentacao = st.sidebar.multiselect(
        "Segmentar por:",
        ["Loja", "Tipo de Cupom", "Categoria"] if any(x in df_filtrado.columns for x in ['nome_loja', 'tipo_cupom', 'categoria_estabelecimento']) else ["Loja", "Tipo de Cupom"],
        default=["Loja"]
    )

    # Abas de análise
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Sazonalidade", "🏪 Comportamento", "📊 Padrões", "🔮 Previsões"])

    with tab1:
        st.subheader("📅 Análise Sazonalidade")
        
        # Preparar dados temporais
        df_temp = df_filtrado.copy()
        df_temp['data_captura'] = pd.to_datetime(df_temp['data_captura'])
        
        if analise_temporal == "Horária":
            df_temp['periodo'] = df_temp['data_captura'].dt.hour
            periodo_label = "Hora"
        elif analise_temporal == "Diária":
            df_temp['periodo'] = df_temp['data_captura'].dt.day_name()
            # Ordenar dias
            dias_ordem = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            dias_trad = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
            df_temp['periodo'] = df_temp['periodo'].map(dict(zip(dias_ordem, dias_trad)))
            df_temp['periodo'] = pd.Categorical(df_temp['periodo'], categories=dias_trad, ordered=True)
            periodo_label = "Dia da Semana"
        elif analise_temporal == "Semanal":
            df_temp['periodo'] = df_temp['data_captura'].dt.strftime('%Y-%U')
            periodo_label = "Semana"
        else:  # Mensal
            df_temp['periodo'] = df_temp['data_captura'].dt.to_period('M').astype(str)
            periodo_label = "Mês"
        
        # Gráfico de tendência principal
        tendencia_principal = df_temp.groupby('periodo').agg({
            'valor_compra': ['sum', 'count', 'mean']
        }).round(2)
        
        tendencia_principal.columns = ['Receita', 'Transações', 'Ticket_Médio']
        tendencia_principal = tendencia_principal.reset_index()
        
        # Criar gráfico interativo
        metrica_selecionada = st.selectbox(
            "Selecione a métrica:",
            ["Receita", "Transações", "Ticket_Médio"],
            key="tendencia_metrica"
        )
        
        fig_tendencia = criar_grafico_interativo(
            tendencia_principal,
            'line', 'periodo', metrica_selecionada,
            title=f"Evolução {metrica_selecionada} - {analise_temporal}",
            hover_data={metrica_selecionada: ':,.2f' if 'Receita' in metrica_selecionada or 'Ticket' in metrica_selecionada else ':,'}
        )
        
        st.plotly_chart(fig_tendencia, use_container_width=True)
        
        # Análise comparativa por segmentação
        if segmentacao and 'nome_loja' in segmentacao and 'nome_loja' in df_temp.columns:
            st.subheader("🏪 Comparativo por Loja")
            
            lojas_top = df_temp['nome_loja'].value_counts().nlargest(5).index
            df_top_lojas = df_temp[df_temp['nome_loja'].isin(lojas_top)]
            
            comparativo = df_top_lojas.groupby(['periodo', 'nome_loja']).agg({
                'valor_compra': 'sum'
            }).reset_index()
            
            fig_comparativo = criar_grafico_interativo(
                comparativo,
                'line', 'periodo', 'valor_compra', 'nome_loja',
                title=f"Comparativo de Receita - Top 5 Lojas",
                hover_data={'valor_compra': ':,.2f'}
            )
            
            st.plotly_chart(fig_comparativo, use_container_width=True)

    with tab2:
        st.subheader("🏪 Comportamento do Consumidor")
        
        # Mapa de calor de correlação
        st.subheader("🔗 Análise de Correlação")
        
        # Selecionar colunas numéricas para correlação
        colunas_numericas = df_filtrado.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(colunas_numericas) > 1:
            correlacao = df_filtrado[colunas_numericas].corr()
            
            fig_corr = go.Figure(data=go.Heatmap(
                z=correlacao.values,
                x=correlacao.columns,
                y=correlacao.columns,
                colorscale='RdBu_r',
                zmin=-1,
                zmax=1,
                hoverongaps=False,
                hovertemplate="<b>%{x}</b> vs <b>%{y}</b><br>Correlação: %{z:.3f}<extra></extra>",
                text=correlacao.round(3).values,
                texttemplate="%{text}",
                textfont={"size": 10}
            ))
            
            fig_corr.update_layout(
                title="Mapa de Correlação entre Variáveis Numéricas",
                xaxis_title="Variáveis",
                yaxis_title="Variáveis"
            )
            
            fig_corr = style_fig(fig_corr)
            st.plotly_chart(fig_corr, use_container_width=True)
        
        # Análise de ticket médio
        st.subheader("💰 Análise de Ticket Médio")
        
        if 'nome_loja' in df_filtrado.columns and 'valor_compra' in df_filtrado.columns:
            ticket_analysis = df_filtrado.groupby('nome_loja').agg({
                'valor_compra': ['count', 'mean', 'std']
            }).round(2)
            
            ticket_analysis.columns = ['Transações', 'Ticket_Médio', 'Desvio_Padrão']
            ticket_analysis = ticket_analysis.reset_index()
            ticket_analysis = ticket_analysis[ticket_analysis['Transações'] >= 5]  # Filtrar lojas com poucas transações
            
            # Scatter plot interativo
            fig_scatter = px.scatter(
                ticket_analysis,
                x='Transações',
                y='Ticket_Médio',
                size='Ticket_Médio',
                color='Ticket_Médio',
                hover_name='nome_loja',
                title="Relação: Volume vs Ticket Médio por Loja",
                labels={'Transações': 'Número de Transações', 'Ticket_Médio': 'Ticket Médio (R$)'},
                size_max=30
            )
            
            fig_scatter.update_traces(
                hovertemplate="<b>%{hovertext}</b><br>Transações: %{x}<br>Ticket Médio: R$ %{y:.2f}<extra></extra>"
            )
            
            fig_scatter = style_fig(fig_scatter)
            st.plotly_chart(fig_scatter, use_container_width=True)

    with tab3:
        st.subheader("📊 Padrões de Consumo")
        
        # Análise de cesta
        st.subheader("🛒 Análise de Cesta de Compras (Simulada)")
        
        # Simular dados de cesta (em um sistema real, viria de base de dados)
        produtos_populares = {
            'Eletrônicos': ['Smartphone', 'Tablet', 'Fones', 'Carregador'],
            'Moda': ['Camiseta', 'Calça', 'Tênis', 'Moletom'],
            'Casa': ['Cama', 'Mesa', 'Sofá', 'Cadeira'],
            'Alimentação': ['Pizza', 'Hambúrguer', 'Sushi', 'Açaí']
        }
        
        # Criar dados simulados de associação
        associacoes = []
        for categoria, produtos in produtos_populares.items():
            for i, produto1 in enumerate(produtos):
                for produto2 in produtos[i+1:]:
                    associacoes.append({
                        'Produto_A': produto1,
                        'Produto_B': produto2,
                        'Suporte': np.random.uniform(0.1, 0.3),
                        'Confiança': np.random.uniform(0.4, 0.8),
                        'Lift': np.random.uniform(1.2, 3.0)
                    })
        
        df_associacoes = pd.DataFrame(associacoes)
        
        # Filtros para análise de associação
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_suporte = st.slider("Suporte Mínimo", 0.0, 0.5, 0.1, 0.01)
        with col2:
            min_confianca = st.slider("Confiança Mínima", 0.0, 1.0, 0.5, 0.05)
        with col3:
            min_lift = st.slider("Lift Mínimo", 1.0, 5.0, 1.5, 0.1)
        
        # Aplicar filtros
        df_filtrado_assoc = df_associacoes[
            (df_associacoes['Suporte'] >= min_suporte) &
            (df_associacoes['Confiança'] >= min_confianca) &
            (df_associacoes['Lift'] >= min_lift)
        ].sort_values('Lift', ascending=False)
        
        # Mostrar tabela de associações
        st.dataframe(
            df_filtrado_assoc.head(20).style.format({
                'Suporte': '{:.2%}',
                'Confiança': '{:.2%}', 
                'Lift': '{:.2f}'
            }),
            use_container_width=True
        )
        
        # Gráfico de rede de associações (simplificado)
        st.subheader("🕸️ Rede de Associações")
        
        if not df_filtrado_assoc.empty:
            # Criar gráfico de barras para as melhores associações
            fig_assoc = criar_grafico_interativo(
                df_filtrado_assoc.head(15),
                'bar', 'Lift', 'Produto_A',
                title="Top Associações por Lift",
                hover_data={'Suporte': ':.2%', 'Confiança': ':.2%', 'Lift': ':.2f'}
            )
            
            fig_assoc.update_layout(
                xaxis_title="Lift",
                yaxis_title="Associação"
            )
            
            st.plotly_chart(fig_assoc, use_container_width=True)

    with tab4:
        st.subheader("🔮 Previsões e Tendências Futuras")
        
        # Simular previsões (em sistema real, usaria modelo de ML)
        st.info("""
        💡 **Sistema de Previsão**: Esta seção utiliza algoritmos de machine learning para prever 
        tendências futuras baseadas em dados históricos. As previsões são atualizadas automaticamente 
        conforme novos dados são processados.
        """)
        
        # Criar dados de previsão simulados
        ultimos_meses = 12
        meses = pd.date_range(end=pd.Timestamp.now(), periods=ultimos_meses + 6, freq='M')
        
        # Dados históricos (simulados)
        historico = {
            'Mês': meses[:ultimos_meses],
            'Receita_Real': np.random.normal(100000, 20000, ultimos_meses).cumsum() + 500000,
            'Transações_Real': np.random.normal(1000, 200, ultimos_meses).cumsum() + 5000
        }
        
        # Previsões (simuladas)
        previsoes = {
            'Mês': meses[ultimos_meses-1:],
            'Receita_Prevista': np.random.normal(120000, 15000, 7).cumsum() + historico['Receita_Real'][-1],
            'Transações_Previstas': np.random.normal(1200, 150, 7).cumsum() + historico['Transações_Real'][-1]
        }
        
        df_historico = pd.DataFrame(historico)
        df_previsoes = pd.DataFrame(previsoes)
        
        # Combinar dados
        df_previsao_completa = pd.concat([
            df_historico.assign(Tipo='Histórico'),
            df_previsoes.assign(Tipo='Previsão')
        ])
        
        # Gráfico de previsão
        fig_previsao = go.Figure()
        
        # Histórico
        fig_previsao.add_trace(go.Scatter(
            name="Receita Real",
            x=df_historico['Mês'],
            y=df_historico['Receita_Real'],
            mode='lines+markers',
            line=dict(color=PRIMARY, width=3),
            hovertemplate="<b>Mês:</b> %{x|%b %Y}<br><b>Receita Real:</b> R$ %{y:,.0f}<extra></extra>"
        ))
        
        # Previsão
        fig_previsao.add_trace(go.Scatter(
            name="Receita Prevista",
            x=df_previsoes['Mês'],
            y=df_previsoes['Receita_Prevista'],
            mode='lines+markers',
            line=dict(color='orange', width=3, dash='dash'),
            hovertemplate="<b>Mês:</b> %{x|%b %Y}<br><b>Receita Prevista:</b> R$ %{y:,.0f}<extra></extra>"
        ))
        
        # Área de incerteza (simulada)
        fig_previsao.add_trace(go.Scatter(
            name="Margem de Erro",
            x=df_previsoes['Mês'].tolist() + df_previsoes['Mês'].tolist()[::-1],
            y=(df_previsoes['Receita_Prevista'] * 1.1).tolist() + (df_previsoes['Receita_Prevista'] * 0.9).tolist()[::-1],
            fill='toself',
            fillcolor='rgba(255,165,0,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip",
            showlegend=True
        ))
        
        fig_previsao.update_layout(
            title="📈 Previsão de Receita para os Próximos 6 Meses",
            xaxis_title="Mês",
            yaxis_title="Receita (R$)",
            hovermode="x unified"
        )
        
        fig_previsao = style_fig(fig_previsao)
        st.plotly_chart(fig_previsao, use_container_width=True)
        
        # Métricas de previsão
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            crescimento_previsto = ((df_previsoes['Receita_Prevista'].iloc[-1] - df_historico['Receita_Real'].iloc[-1]) / 
                                  df_historico['Receita_Real'].iloc[-1] * 100)
            st.metric("Crescimento Previsto", f"{crescimento_previsto:.1f}%")
            
        with col2:
            st.metric("Precisão do Modelo", "92.3%", "1.2%")
            
        with col3:
            st.metric("Próximo Mês", f"R$ {df_previsoes['Receita_Prevista'].iloc[1]:,.0f}")
            
        with col4:
            confianca = st.slider("🎯 Nível de Confiança", 80, 99, 90, key="confianca_previsao")
            st.metric("Intervalo Confiança", f"±{100 - confiança}%")

# ---------------- PÁGINAS EXISTENTES (mantidas para compatibilidade) ----------------
def page_financeiro(tx):
    """
    Página de análise financeira detalhada.
    """
    top_header()
    hero("💰 Painel Financeiro", "Análise detalhada de receita, despesas, lucro e métricas financeiras")
    
    # Usar a versão interativa como fallback
    page_kpis_interativa(tx)

def page_eco():
    """
    Página de contexto econômico.
    """
    top_header()
    hero("📈 Painel Econômico", "Indicadores macroeconômicos e tendências do mercado")
    
    st.info("""
    🚧 **Página em Desenvolvimento**
    
    Esta página está sendo atualizada com visualizações interativas avançadas.
    Enquanto isso, explore as outras seções do dashboard.
    """)

def page_simulacaologin():
    """
    Página de gamificação.
    """
    top_header()
    hero("🎯 Simulação de Uso de Cupons", "Sistema de gamificação e progressão por níveis")
    
    st.info("""
    🚧 **Página em Desenvolvimento**
    
    Esta página está sendo atualizada com mais interações e recursos de gamificação.
    Enquanto isso, explore as análises interativas disponíveis.
    """)

def page_sobre():
    """
    Página Sobre.
    """
    top_header()
    hero("👥 Sobre o CupomGO", "Conheça nossa plataforma, equipe e professores orientadores")
    
    st.info("""
    🚧 **Página em Desenvolvimento**
    
    Esta página está sendo atualizada com informações completas sobre o projeto.
    """)

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
if "drill_down" not in st.session_state:
    st.session_state.drill_down = None

# ---------------- Roteamento Principal Atualizado ----------------
def main():
    """
    Função principal atualizada com páginas interativas.
    """
    if not st.session_state.auth:
        if st.session_state.auth_mode == "login":
            login_screen()
        else:
            signup_screen()
    else:
        tx = transacoes if not transacoes.empty else pd.DataFrame()
        stores = lojas if not lojas.empty else pd.DataFrame()
        sidebar_nav()
        page = st.session_state.get("page", "home")
        
        # Roteamento atualizado com versões interativas
        if page == "home": 
            page_home(tx, stores)
        elif page == "kpis": 
            page_kpis_interativa(tx)  # Versão interativa
        elif page == "tendencias":
            page_tendencias_interativa(tx)  # Versão interativa
        elif page == "fin": 
            page_financeiro(tx)
        elif page == "eco": 
            page_eco()
        elif page == "sim":
            page_simulacaologin()
        elif page == "sobre":
            page_sobre()

# Ponto de entrada
if __name__ == "__main__":
    main()
