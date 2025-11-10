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

# ---------------- Páginas Principais do Sistema ----------------
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
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        example_data = []
        for i, date in enumerate(dates):
            example_data.append({
                'data_captura': date,
                'valor_compra': np.random.uniform(50, 500),
                'nome_loja': np.random.choice(['Loja A', 'Loja B', 'Loja C', 'Loja D']),
                'tipo_cupom': np.random.choice(['Desconto', 'Cashback', 'Fidelidade'])
            })
        df = pd.DataFrame(example_data)
        get = lambda *names: names[0] if names else None

    # Encontra as colunas de data e valor
    dcol = get("data","data_captura")
    vcol = get("valor_compra","valor")

    # Métricas principais em cards bonitos
    c1, c2, c3, c4 = st.columns(4)
    with c1: 
        kpi_card("Total de Cupons", f"{len(df):,}".replace(",", "."))
    with c2: 
        kpi_card("Conversões", f"{len(df):,}".replace(",", "."))
    with c3:
        avg = df[vcol].mean() if (vcol and (vcol in df.columns)) else 0
        kpi_card("Ticket Médio", f"R$ {avg:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
    with c4:
        total_receita = df[vcol].sum() if (vcol and (vcol in df.columns)) else 0
        kpi_card("Receita Total", f"R$ {total_receita:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

    # Verifica se temos dados suficientes para gráficos
    if not dcol or dcol not in df.columns or not vcol or vcol not in df.columns:
        st.warning("Dados insuficientes para gerar gráficos.")
        return

    # Prepara dados mensais para o gráfico
    df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
    df["Mês"] = df[dcol].dt.to_period("M").astype(str)
    resumo = df.groupby("Mês")[vcol].agg(["sum","mean","count"]).reset_index()
    resumo.columns = ["Mês","Receita","Ticket Médio","Conversões"]

    # Gráfico principal da página inicial
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=resumo["Mês"], y=resumo["Receita"], name="Receita",
        marker_color=PRIMARY,
        hovertemplate="Mês: %{x}<br>Receita: R$ %{y:,.2f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=resumo["Mês"], y=resumo["Ticket Médio"], name="Ticket médio",
        mode="lines+markers", yaxis="y2",
        line=dict(color="darkgray", width=3),
        hovertemplate="Mês: %{x}<br>Ticket: R$ %{y:,.2f}<extra></extra>"
    ))
    fig.update_layout(
        title="Desempenho Mensal - Receita e Ticket Médio",
        xaxis_title="Mês",
        yaxis=dict(title="Receita (R$)"),
        yaxis2=dict(overlaying="y", side="right", title="Ticket médio (R$)"),
        margin=dict(t=80, b=140, l=80, r=80)
    )
    fig = style_fig(fig, y_fmt=",.2f")
    st.plotly_chart(fig, use_container_width=True)

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

def page_kpis(tx):
    """
    Página de Indicadores Executivos - métricas para tomada de decisão.
    Focada em CEO, CTO e CFO com visões diferentes.
    """
    top_header()
    hero("📊 Painel Executivo", "Métricas estratégicas por perfil de liderança")

    # Explicação da página
    st.markdown("""
    <div style="background-color: #f0f2f6; border-radius: 10px; padding: 20px; margin-bottom: 20px; border: 1px solid #e0e0e0;">
        <p style="color: #333; font-size: 16px;">
        Esta página consolida os indicadores-chave de performance (KPIs) segmentados 
        pelos principais pilares de gestão:
        </p>
        <ul style="color: #333; font-size: 16px;">
            <li><strong>CEO:</strong> Foco em crescimento, conversões e taxa de adesão.</li>
            <li><strong>CTO:</strong> Foco em volume operacional, estabilidade e tráfego diário.</li>
            <li><strong>CFO:</strong> Foco em receita, rentabilidade (ROI) e eficiência financeira.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Carrega dados
    df, get = normcols(tx)
    
    # Dados de exemplo se não houver dados reais
    if df.empty:
        st.info("Aguardando dados... Gerando dados de exemplo mais realistas para demonstração.")
        df = generate_example_data(num_rows=2500)
        df, get = normcols(df)

    # Encontra colunas importantes
    dcol = get("data","data_captura")
    vcol = get("valor_compra","valor")
    scol = get("nome_loja","loja","tipo_loja")
    tcol = get("tipo_cupom","tipo")

    # Abas para diferentes perfis executivos
    tab1, tab2, tab3 = st.tabs(["📈 Performance CEO - Conversões e Taxas", "🔧 Performance CTO - Operações", "💰 Performance CFO - Financeiro"])

    with tab1:
        st.subheader("📈 Performance CEO - Conversões e Taxas")
        
        if not dcol:
            st.warning("Coluna de data não encontrada.")
            return
            
        # Prepara dados mensais
        df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
        bym = df[dcol].dt.to_period("M").astype(str)
        conv = bym.value_counts().sort_index()
        
        if len(conv) == 0:
            st.info("Sem dados de conversões para exibir.")
            return
            
        # Calcula taxa de adesão (percentual do mês com maior volume)
        taxa_adesao = (conv.values / conv.values.max() * 100) if len(conv) > 0 else np.array([])

        # Gráfico para CEO
        fig_ceo = go.Figure()
        fig_ceo.add_trace(go.Bar(
            x=conv.index, y=conv.values, name="Conversões",
            marker_color=PRIMARY,
            hovertemplate="Mês: %{x}<br>Conversões: %{y:,}<extra></extra>"
        ))
        
        if len(taxa_adesao) > 0:
            fig_ceo.add_trace(go.Scatter(
                x=conv.index, y=taxa_adesao, name="Taxa de Adesão (%)",
                mode="lines+markers", yaxis="y2",
                line=dict(color="orange", width=3),
                hovertemplate="Mês: %{x}<br>Taxa: %{y:.1f}%<extra></extra>"
            ))

        fig_ceo.update_layout(
            title="Conversões e Taxa de Adesão Mensal",
            xaxis_title="Mês",
            yaxis=dict(title="Conversões"),
            yaxis2=dict(overlaying="y", side="right", title="Taxa de Adesão (%)") if len(taxa_adesao) > 0 else None,
            margin=dict(t=80, b=140, l=80, r=80)
        )
        fig_ceo = style_fig(fig_ceo)
        st.plotly_chart(fig_ceo, use_container_width=True)

        # KPIs para CEO
        col1, col2, col3 = st.columns(3)
        with col1:
            kpi_card("Total Conversões", f"{len(df):,}".replace(",", "."))
        with col2:
            kpi_card("Meses Ativos", f"{len(conv)}")
        with col3:
            max_conv = conv.max() if len(conv) > 0 else 0
            kpi_card("Pico Mensal", f"{max_conv:,}".replace(",", "."))

    with tab2:
        st.subheader("🔧 Performance CTO - Volume Operacional")
        
        if not dcol:
            st.warning("Coluna de data não encontrada.")
            return
            
        # Volume diário de transações
        volume_diario = df[dcol].dt.date
        volume_contagem = volume_diario.value_counts().sort_index()

        if len(volume_contagem) == 0:
            st.info("Sem dados de volume operacional para exibir.")
            return

        # Gráfico de volume diário
        fig_cto = px.bar(
            x=volume_contagem.index.astype(str), y=volume_contagem.values,
            title="Volume Diário de Transações",
            labels={"x":"Data", "y":"Transações"},
            color_discrete_sequence=[PRIMARY]
        )
        fig_cto.update_traces(hovertemplate="Data: %{x}<br>Transações: %{y:,}<extra></extra>")
        fig_cto = style_fig(fig_cto, y_fmt=",.0f")
        st.plotly_chart(fig_cto, use_container_width=True)

        # KPIs para CTO
        col1, col2, col3 = st.columns(3)
        with col1: 
            kpi_card("Transações/Dia", f"{volume_contagem.mean():.0f}")
        with col2: 
            kpi_card("Pico Diário", f"{volume_contagem.max():,}".replace(",", "."))
        with col3: 
            kpi_card("Dias Ativos", f"{len(volume_contagem)}")

        # Gráfico por dia da semana
        if dcol in df.columns:
            df_copy = df.copy()
            df_copy['Dia_Semana'] = df_copy[dcol].dt.day_name()
            dias_ordem = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            dias_portugues = {
                'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta', 
                'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
            }
            
            volume_semanal = df_copy['Dia_Semana'].value_counts().reindex(dias_ordem).fillna(0)
            volume_semanal.index = volume_semanal.index.map(dias_portugues)
            
            fig_semanal = px.bar(
                x=volume_semanal.index, y=volume_semanal.values,
                title="Distribuição de Transações por Dia da Semana",
                labels={"x":"Dia da Semana", "y":"Transações"},
                color_discrete_sequence=["#3b82f6"]
            )
            fig_semanal = style_fig(fig_semanal)
            st.plotly_chart(fig_semanal, use_container_width=True)

    with tab3:
        st.subheader("💰 Performance CFO - Receita e ROI")
        
        if df.empty:
            st.warning("Não há dados disponíveis para análise financeira.")
            return

        # Gráfico de evolução da receita
        if dcol and vcol:
            df_copy = df.copy()
            df_copy[dcol] = pd.to_datetime(df_copy[dcol]) 
            df_copy['Mês'] = df_copy[dcol].dt.to_period('M').astype(str)
            
            receita_mensal = df_copy.groupby('Mês')[vcol].sum().reset_index()
            
            fig_receita = px.line(
                receita_mensal, x='Mês', y=vcol,
                title="📈 Evolução da Receita Mensal",
                labels={vcol: "Receita (R$)", "Mês": "Mês"},
                color_discrete_sequence=[PRIMARY]
            )
            fig_receita.update_traces(mode='lines+markers', line=dict(width=3))
            fig_receita = style_fig(fig_receita, y_fmt=",.2f")
            st.plotly_chart(fig_receita, use_container_width=True)

        # Gráfico de ROI por loja
        if scol and vcol and scol in df.columns:
            
            if 'investimento_mkt' in df.columns and 'lucro_bruto' in df.columns:
                # Cálculo realista de ROI se temos os dados
                agg = df.groupby(scol).agg(
                    Receita=('valor_compra', 'sum'), 
                    Transacoes=('valor_compra', 'count'), 
                    Investimento=('investimento_mkt', 'sum'),
                    Lucro=('lucro_bruto', 'sum')
                ).reset_index()
                agg['ROI'] = ((agg['Lucro'] - agg['Investimento']) / agg['Investimento'] * 100).round(2)
            else:
                # Cálculo simplificado para dados de exemplo
                agg = df.groupby(scol)[vcol].agg(['sum', 'count']).reset_index()
                agg.columns = [scol, 'Receita', 'Transacoes']
                agg['Investimento'] = agg['Receita'] * 0.35 
                agg['ROI'] = ((agg['Receita'] - agg['Investimento']) / agg['Investimento'] * 100).round(2)
            
            agg = agg.nlargest(10, 'Receita')

            fig_cfo = go.Figure()
            fig_cfo.add_trace(go.Bar(
                x=agg[scol].astype(str), y=agg['Receita'], name="Receita",
                marker_color=PRIMARY,
                hovertemplate="Loja: %{x}<br>Receita: R$ %{y:,.2f}<extra></extra>"
            ))
            fig_cfo.add_trace(go.Scatter(
                x=agg[scol].astype(str), y=agg['ROI'], name="ROI",
                yaxis="y2", mode="lines+markers",
                line=dict(color="red", width=3),
                hovertemplate="Loja: %{x}<br>ROI: %{y:.2f}%<extra></extra>"
            ))
            fig_cfo.update_layout(
                title="🏪 Receita e ROI por Loja (Top 10)",
                xaxis_title="Lojas",
                yaxis=dict(title="Receita (R$)"),
                yaxis2=dict(overlaying="y", side="right", title="ROI (%)"),
                margin=dict(t=80, b=140, l=80, r=80)
            )
            fig_cfo = style_fig(fig_cfo, y_fmt=",.2f")
            st.plotly_chart(fig_cfo, use_container_width=True)

            # KPIs financeiros
            col1, col2, col3 = st.columns(3)
            with col1: 
                kpi_card("Receita Total", f"R$ {agg['Receita'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
            with col2: 
                kpi_card("ROI Médio", f"{agg['ROI'].mean():.1f}%")
            with col3: 
                kpi_card("Melhor ROI", f"{agg['ROI'].max():.1f}%")

        # Gráfico de pizza por tipo de cupom
        if tcol and vcol and tcol in df.columns:
            tipo_agg = df.groupby(tcol)[vcol].agg(['sum', 'count']).reset_index()
            tipo_agg.columns = [tcol, 'Receita', 'Transacoes']
            
            fig_tipo = px.pie(
                tipo_agg, values='Receita', names=tcol,
                title="🥧 Distribuição da Receita por Tipo de Cupom",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_tipo = style_fig(fig_tipo)
            st.plotly_chart(fig_tipo, use_container_width=True)

        # Evolução do ticket médio
        if dcol and vcol:
            df_copy = df.copy()
            if 'Mês' not in df_copy.columns:
                    df_copy[dcol] = pd.to_datetime(df_copy[dcol])
                    df_copy['Mês'] = df_copy[dcol].dt.to_period('M').astype(str)
                    
            ticket_mensal = df_copy.groupby('Mês')[vcol].mean().reset_index()
            
            fig_ticket = px.line(
                ticket_mensal, x='Mês', y=vcol,
                title="💰 Evolução do Ticket Médio Mensal",
                labels={vcol: "Ticket Médio (R$)", "Mês": "Mês"},
                color_discrete_sequence=["#10b981"]
            )
            fig_ticket.update_traces(mode='lines+markers', line=dict(width=3))
            fig_ticket = style_fig(fig_ticket, y_fmt=",.2f")
            st.plotly_chart(fig_ticket, use_container_width=True)

        # Evolução da margem de lucro
        if dcol and vcol:
            df_copy = df.copy()
            if 'Mês' not in df_copy.columns:
                df_copy[dcol] = pd.to_datetime(df_copy[dcol])
                df_copy['Mês'] = df_copy[dcol].dt.to_period('M').astype(str)
            
            if 'lucro_bruto' in df_copy.columns:
                # Cálculo real se temos dados de lucro
                lucro_mensal = df_copy.groupby('Mês').agg(
                    Receita_Total=(vcol, 'sum'),
                    Lucro_Total=('lucro_bruto', 'sum')
                ).reset_index()
                lucro_mensal['Margem_Lucro'] = (lucro_mensal['Lucro_Total'] / lucro_mensal['Receita_Total'] * 100).round(2)
            else:
                # Margens simuladas para dados de exemplo
                lucro_mensal = df_copy.groupby('Mês')[vcol].sum().reset_index()
                np.random.seed(123)
                lucro_mensal['Margem_Lucro'] = np.random.uniform(30, 45, len(lucro_mensal))
            
            fig_margem = px.area(
                lucro_mensal, x='Mês', y='Margem_Lucro',
                title="📊 Evolução da Margem de Lucro (%)",
                labels={"Margem_Lucro": "Margem de Lucro (%)", "Mês": "Mês"},
                color_discrete_sequence=["#8b5cf6"]
            )
            fig_margem.update_traces(line=dict(width=3))
            fig_margem = style_fig(fig_margem)
            st.plotly_chart(fig_margem, use_container_width=True)

def page_tendencias(tx):
    """
    Página de análise de tendências - entenda o comportamento dos usuários.
    Mostra padrões de uso, lojas preferidas, horários de pico, etc.
    """
    top_header()
    hero("📈 Análise de Tendências", "Comportamento do consumidor e padrões de uso de cupons")

    st.markdown("""
    <div style="background-color: #f0f2f6; border-radius: 10px; padding: 20px; margin-bottom: 20px; border: 1px solid #e0e0e0;">
        <p style="color: #333; font-size: 16px;">
        Explore os padrões por detrás dos números. Esta página permite-lhe analisar quando os seus clientes 
        usam cupons (por hora, dia da semana) e quais as lojas e tipos de cupom que geram maior 
        envolvimento e receita.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Carrega dados
    df, get = normcols(tx)
    
    if df.empty:
        st.info("Aguardando dados... Gerando dados de exemplo realistas para demonstração.")
        df = generate_example_data(num_rows=2500)
        df, get = normcols(df)

    # Encontra colunas importantes
    dcol = get("data", "data_captura")
    vcol = get("valor_cupom", "valor_compra", "valor")
    scol = get("nome_estabelecimento", "nome_loja", "loja")
    tcol = get("tipo_cupom", "tipo")
    cat_col = get("categoria_estabelecimento", "categoria_loja")

    # Verifica se temos dados mínimos
    if not dcol or not vcol or not scol or not tcol:
        st.warning("Dados insuficientes para a análise de tendências. Colunas-chave (data, valor, loja, tipo) estão faltando.")
        st.info(f"Colunas encontradas: data='{dcol}', valor='{vcol}', loja='{scol}', tipo='{tcol}'")
        return

    try:
        # Prepara dados para análise
        df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
        df = df.dropna(subset=[dcol, vcol, scol, tcol]) 
        
        # Cria colunas derivadas para análise
        df['Mês'] = df[dcol].dt.to_period('M').astype(str)
        df['Dia_Semana_Num'] = df[dcol].dt.weekday 
        df['Dia_Semana'] = df[dcol].dt.day_name()
        df['Hora'] = df[dcol].dt.hour
        
        # Traduz dias da semana para português
        dias_portugues = {
            'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',   
            'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        df['Dia_Semana'] = df['Dia_Semana'].map(dias_portugues)
        
    except Exception as e:
        st.error(f"Erro ao processar os dados: {e}")
        return

    # Abas para diferentes tipos de análise
    tab1, tab2, tab3 = st.tabs(["📊 Tendências Temporais", "🏪 Comportamento por Loja", "🎯 Padrões de Consumo"])

    with tab1:
        st.subheader("Tendências Temporais de Uso")
        
        # Agrupa dados por mês
        uso_mensal = df.groupby('Mês').agg(
            Receita=(vcol, 'sum'),
            Cupons=(vcol, 'count')
        ).reset_index()
        
        # Gráfico de receita vs volume
        fig_mensal = go.Figure()
        fig_mensal.add_trace(go.Bar(
            x=uso_mensal['Mês'], y=uso_mensal['Receita'], name='Receita (R$)',
            marker_color=PRIMARY, yaxis='y1'
        ))
        fig_mensal.add_trace(go.Scatter(
            x=uso_mensal['Mês'], y=uso_mensal['Cupons'], name='Volume (Cupons)',
            mode='lines+markers', line=dict(color='#f59e0b', width=3), yaxis='y2'
        ))
        
        fig_mensal.update_layout(
            title="Evolução Mensal: Receita (Barras) e Volume (Linha)",
            xaxis_title="Mês",
            yaxis=dict(title='Receita (R$)'),
            yaxis2=dict(title='Volume de Cupons', overlaying='y', side='right'),
            legend=dict(orientation="h", yanchor="bottom", y=-0.4)
        )
        st.plotly_chart(style_fig(fig_mensal, y_fmt=",.2f"), use_container_width=True)

        # Gráficos de dia da semana e hora
        col1, col2 = st.columns(2)
        with col1:
            uso_diario = df.groupby(['Dia_Semana_Num', 'Dia_Semana']).size().reset_index(name='Cupons').sort_values('Dia_Semana_Num')
            fig_diario = px.bar(
                uso_diario, x='Dia_Semana', y='Cupons',
                title="Volume de Cupons por Dia da Semana",
                labels={'Dia_Semana': 'Dia da Semana', 'Cupons': 'Total de Cupons'},
                color_discrete_sequence=["#3b82f6"]
            )
            fig_diario = style_fig(fig_diario)
            st.plotly_chart(fig_diario, use_container_width=True)
        
        with col2:
            uso_hora = df.groupby('Hora').size().reset_index(name='Cupons')
            fig_hora = px.bar(
                uso_hora, x='Hora', y='Cupons',
                title="Volume de Cupons por Hora do Dia",
                labels={'Hora': 'Hora (0-23)', 'Cupons': 'Total de Cupons'},
                color_discrete_sequence=["#10b981"]
            )
            fig_hora = style_fig(fig_hora)
            st.plotly_chart(fig_hora, use_container_width=True)

    with tab2:
        st.subheader("Comportamento por Estabelecimento")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Top 10 lojas por receita
            receita_lojas = df.groupby(scol)[vcol].sum().nlargest(10).sort_values(ascending=True)
            fig_lojas_receita = px.bar(
                receita_lojas, y=receita_lojas.index, x=receita_lojas.values,
                title="Top 10 Lojas por Receita Total",
                labels={'y': 'Loja', 'x': 'Receita (R$)'},
                orientation='h', text_auto=',.2s',
                color_discrete_sequence=[PRIMARY]
            )
            fig_lojas_receita = style_fig(fig_lojas_receita, x_fmt=",.2f")
            st.plotly_chart(fig_lojas_receita, use_container_width=True)
        
        with col2:
            # Top 10 lojas por volume
            volume_lojas = df[scol].value_counts().nlargest(10).sort_values(ascending=True)
            fig_lojas_volume = px.bar(
                volume_lojas, y=volume_lojas.index, x=volume_lojas.values,
                title="Top 10 Lojas por Volume de Cupons",
                labels={'y': 'Loja', 'x': 'Quantidade de Cupons'},
                orientation='h', text_auto=True,
                color_discrete_sequence=["#f59e0b"]
            )
            fig_lojas_volume = style_fig(fig_lojas_volume)
            st.plotly_chart(fig_lojas_volume, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            # Ticket médio por loja
            ticket_lojas = df.groupby(scol)[vcol].mean().nlargest(10).sort_values(ascending=True)
            fig_ticket = px.bar(
                ticket_lojas, y=ticket_lojas.index, x=ticket_lojas.values,
                title="Ticket Médio por Loja (Top 10)",
                labels={'y': 'Loja', 'x': 'Ticket Médio (R$)'},
                orientation='h', text_auto=',.2f',
                color_discrete_sequence=['#00CC96']
            )
            fig_ticket = style_fig(fig_ticket, x_fmt=",.2f")
            st.plotly_chart(fig_ticket, use_container_width=True)
        
        with col2:
            # Distribuição por categoria (se disponível)
            if cat_col in df.columns:
                receita_categoria = df.groupby(cat_col)[vcol].sum()
                fig_cat_pie = px.pie(
                    receita_categoria, values=receita_categoria.values, names=receita_categoria.index,
                    title="Distribuição da Receita por Categoria de Loja",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                    hole=0.3  # Donut chart
                )
                fig_cat_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_cat_pie = style_fig(fig_cat_pie)
                st.plotly_chart(fig_cat_pie, use_container_width=True)
            else:
                st.info("Coluna 'categoria_estabelecimento' não encontrada. Pulando gráfico de categorias.")

    with tab3:
        st.subheader("Padrões de Consumo e Eficiência")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Volume por tipo de cupom
            tipos_cupom_vol = df[tcol].value_counts()
            fig_tipos_vol = px.pie(
                tipos_cupom_vol, values=tipos_cupom_vol.values, names=tipos_cupom_vol.index,
                title="Volume por Tipo de Cupom (Contagem)",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_tipos_vol = style_fig(fig_tipos_vol)
            st.plotly_chart(fig_tipos_vol, use_container_width=True)
        
        with col2:
            # Receita por tipo de cupom
            tipos_cupom_rec = df.groupby(tcol)[vcol].sum()
            fig_tipos_rec = px.pie(
                tipos_cupom_rec, values=tipos_cupom_rec.values, names=tipos_cupom_rec.index,
                title="Receita Gerada por Tipo de Cupom (R$)", 
                hole=0.3,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_tipos_rec = style_fig(fig_tipos_rec)
            st.plotly_chart(fig_tipos_rec, use_container_width=True)
            
        
        # Box plot de distribuição de valores
        df_sample = df.sample(n=min(2000, len(df)))  # Amostra para performance
        top_10_lojas = df[scol].value_counts().nlargest(10).index
        df_sample_top10 = df_sample[df_sample[scol].isin(top_10_lojas)]

        fig_dist = px.box(
            df_sample_top10, 
            x=scol,
            y=vcol,
            color=tcol,
            title="Distribuição do Valor da Compra por Loja (Top 10) e Tipo de Cupom",
            labels={vcol: "Valor da Compra (R$)", scol: "Loja", tcol: "Tipo de Cupom"}
        )
        
        fig_dist = style_fig(fig_dist, y_fmt=",.2f")
        st.plotly_chart(fig_dist, use_container_width=True)

def page_financeiro(tx):
    """
    Página de análise financeira detalhada - DRE, ROI, balanço, etc.
    Para profissionais de finanças entenderem a saúde do negócio.
    """
    top_header()
    hero("💰 Painel Financeiro", "Análise detalhada de receita, despesas, lucro e métricas financeiras")
    
    st.markdown("""
    <div style="background-color: #f0f2f6; border-radius: 10px; padding: 20px; margin-bottom: 20px; border: 1px solid #e0e0e0;">
        <p style="color: #333; font-size: 16px;">
        Esta secção oferece uma visão aprofundada da saúde financeira da sua operação de cupons. 
        Analise o fluxo de caixa, demonstrações de resultados, e indicadores-chave de rentabilidade 
        como <strong>ROI (Retorno sobre o Investimento)</strong> e <strong>ROIC (Retorno sobre o Capital Investido)</strong>.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Carrega dados
    df, get = normcols(tx)
    dcol = get("data","data_captura")
    vcol = get("valor_compra","valor")

    # Dados de exemplo se necessário
    if df.empty or not dcol or not vcol or dcol not in df.columns or vcol not in df.columns:
        st.info("Sem dados financeiros suficientes em assets/transacoes.xlsx. A carregar dados de exemplo.")
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='M')
        example_data = []
        for i, date in enumerate(dates):
            example_data.append({
                'data_captura': date,
                'valor_compra': np.random.uniform(10000, 50000)
            })
        df = pd.DataFrame(example_data)
        dcol = 'data_captura'
        vcol = 'valor_compra'

    # Prepara dados mensais
    df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
    df["Mês"] = df[dcol].dt.to_period("M").astype(str)

    mensal = df.groupby("Mês")[vcol].agg(['sum', 'mean', 'count']).reset_index()
    mensal.columns = ["Mês", "Receita", "Ticket_Médio", "Conversões"]

    # Simula dados financeiros (em uma aplicação real, viriam de base de dados)
    rng = np.random.default_rng(42)
    base_despesas = rng.uniform(0.6, 0.8, len(mensal))
    for i in range(1, len(base_despesas)):
        base_despesas[i] = 0.3 * base_despesas[i] + 0.7 * base_despesas[i-1]

    # Cálculos financeiros realistas
    mensal["Despesas"] = (mensal["Receita"] * base_despesas).round(2)
    mensal["Lucro"] = (mensal["Receita"] - mensal["Despesas"]).round(2)
    mensal["Margem_Lucro"] = (mensal["Lucro"] / mensal["Receita"] * 100).round(2)
    mensal["CAC"] = (mensal["Despesas"] / mensal["Conversões"]).round(2)  # Custo de Aquisição por Cliente
    
    mensal["ROI"] = (mensal["Lucro"] / mensal["Despesas"] * 100).round(2)
    mensal["ROIC"] = ((mensal["Lucro"] - (mensal["Despesas"] * 0.1)) / (mensal["Despesas"] * 0.6) * 100).round(2)
    mensal["EBITDA"] = (mensal["Lucro"] * 1.2).round(2)  # Lucro antes de juros, impostos, depreciação e amortização
    mensal["EBIT"] = (mensal["Lucro"] * 1.1).round(2)    # Lucro antes de juros e impostos
    mensal["Faturamento_Liquido"] = (mensal["Receita"] * 0.85).round(2)  # Receita menos impostos
    mensal["Custo_Variavel"] = (mensal["Receita"] * 0.45).round(2)
    mensal["Custo_Fixo"] = (mensal["Despesas"] - mensal["Custo_Variavel"]).round(2)
    mensal["Margem_Contribuicao"] = ((mensal["Receita"] - mensal["Custo_Variavel"]) / mensal["Receita"] * 100).round(2)
    mensal["Ponto_Equilibrio"] = (mensal["Custo_Fixo"] / (mensal["Margem_Contribuicao"] / 100)).round(2)

    # Demonstrações contábeis
    mensal["Ativo_Total"] = (mensal["Receita"] * 2.5).round(2)
    mensal["Passivo_Total"] = (mensal["Ativo_Total"] * 0.6).round(2)
    mensal["Patrimonio_Liquido"] = (mensal["Ativo_Total"] - mensal["Passivo_Total"]).round(2)
    mensal["Endividamento"] = (mensal["Passivo_Total"] / mensal["Ativo_Total"] * 100).round(2)
    mensal["Liquidez_Corrente"] = (mensal["Ativo_Total"] * 0.4 / mensal["Passivo_Total"] * 0.7).round(2)
    mensal["Margem_EBITDA"] = (mensal["EBITDA"] / mensal["Receita"] * 100).round(2)
    mensal["Margem_EBIT"] = (mensal["EBIT"] / mensal["Receita"] * 100).round(2)

    # Abas para diferentes análises financeiras
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Fluxo Financeiro", "📊 Demonstrações Contábeis", "💰 Análise de Rentabilidade", "📋 Balanço Patrimonial"])

    with tab1:
        st.subheader("Fluxo Financeiro Mensal")

        # Gráfico de receita, despesas e lucro
        fig_fluxo = go.Figure()
        fig_fluxo.add_trace(go.Bar(x=mensal["Mês"], y=mensal["Receita"], name="Receita", marker_color=PRIMARY, opacity=0.8))
        fig_fluxo.add_trace(go.Bar(x=mensal["Mês"], y=mensal["Despesas"], name="Despesas", marker_color="#f59e0b", opacity=0.8))
        fig_fluxo.add_trace(go.Scatter(x=mensal["Mês"], y=mensal["Lucro"], name="Lucro", mode="lines+markers", line=dict(color="#000000", width=3), marker=dict(size=8)))
        fig_fluxo.update_layout(
            title="Evolução da Receita, Despesas e Lucro", 
            xaxis_title="Mês", 
            yaxis_title="Valor (R$)", 
            barmode="group", 
            hovermode="x unified",
            margin=dict(t=80, b=140, l=80, r=80)
        )
        st.plotly_chart(style_fig(fig_fluxo, y_fmt=",.2f"), use_container_width=True)

        # KPIs financeiros
        col1, col2, col3, col4 = st.columns(4)
        with col1: 
            kpi_card("Receita Total", f"R$ {mensal['Receita'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
        with col2: 
            kpi_card("Lucro Total", f"R$ {mensal['Lucro'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X","."))
        with col3: 
            kpi_card("Margem Média", f"{mensal['Margem_Lucro'].mean():.1f}%")
        with col4: 
            kpi_card("CAC Médio", f"R$ {mensal['CAC'].mean():.2f}")

    with tab2:
        st.subheader("Demonstração do Resultado do Exercício (DRE)")
        
        ultimo_mes = mensal.iloc[-1] if len(mensal) > 0 else None
        
        if ultimo_mes is not None:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**DRE do Último Mês**")
                # Estrutura de uma DRE típica
                dre_data = {
                    'Descrição': [
                        'Receita Bruta',
                        '(-) Impostos (15%)',
                        'Receita Líquida',
                        '(-) Custo Variável',
                        'Margem de Contribuição',
                        '(-) Custo Fixo',
                        'EBITDA',
                        '(-) Depreciação/Amortização',
                        'EBIT',
                        '(-) Juros e Tributos',
                        'Lucro Líquido'
                    ],
                    'Valor (R$)': [
                        ultimo_mes['Receita'],
                        ultimo_mes['Receita'] * 0.15,
                        ultimo_mes['Faturamento_Liquido'],
                        ultimo_mes['Custo_Variavel'],
                        ultimo_mes['Receita'] - ultimo_mes['Custo_Variavel'],
                        ultimo_mes['Custo_Fixo'],
                        ultimo_mes['EBITDA'],
                        ultimo_mes['EBITDA'] - ultimo_mes['EBIT'],
                        ultimo_mes['EBIT'],
                        ultimo_mes['EBIT'] - ultimo_mes['Lucro'],
                        ultimo_mes['Lucro']
                    ]
                }
                
                dre_df = pd.DataFrame(dre_data)
                dre_df['% Receita'] = (dre_df['Valor (R$)'] / ultimo_mes['Receita'] * 100).round(1)
                st.dataframe(dre_df.style.format({
                    'Valor (R$)': 'R$ {:.2f}',
                    '% Receita': '{:.1f}%'
                }), use_container_width=True)
            
            with col2:
                # Gráfico sunburst da composição da DRE
                fig_dre = px.sunburst(
                    names=[
                        'Receita Líquida', 'Custo Variável', 'Custo Fixo', 
                        'EBITDA', 'EBIT', 'Lucro Líquido'
                    ],
                    parents=[
                        '', 'Receita Líquida', 'Margem de Contribuição',
                        'Margem de Contribuição', 'EBITDA', 'EBIT'
                    ],
                    values=[
                        ultimo_mes['Faturamento_Liquido'],
                        ultimo_mes['Custo_Variavel'],
                        ultimo_mes['Custo_Fixo'],
                        ultimo_mes['EBITDA'],
                        ultimo_mes['EBITDA'] - ultimo_mes['EBIT'],
                        ultimo_mes['Lucro']
                    ],
                    title="Composição da DRE - Último Mês"
                )
                fig_dre = style_fig(fig_dre)
                st.plotly_chart(fig_dre, use_container_width=True)

        # Evolução das margens
        fig_margens = go.Figure()
        fig_margens.add_trace(go.Scatter(x=mensal["Mês"], y=mensal["Margem_Lucro"], name="Margem Líquida", mode="lines+markers", line=dict(width=3)))
        fig_margens.add_trace(go.Scatter(x=mensal["Mês"], y=mensal["Margem_EBITDA"], name="Margem EBITDA", mode="lines+markers", line=dict(width=3)))
        fig_margens.add_trace(go.Scatter(x=mensal["Mês"], y=mensal["Margem_EBIT"], name="Margem EBIT", mode="lines+markers", line=dict(width=3)))
        fig_margens.update_layout(
            title="Evolução das Margens (%)",
            xaxis_title="Mês",
            yaxis_title="Margem (%)",
            margin=dict(t=80, b=140, l=80, r=80)
        )
        st.plotly_chart(style_fig(fig_margens), use_container_width=True)

    with tab3:
        st.subheader("Análise de Rentabilidade e Retorno")
        
        # ROIC vs ROI
        fig_roic = go.Figure()
        fig_roic.add_trace(go.Scatter(x=mensal["Mês"], y=mensal["ROIC"], name="ROIC", mode="lines+markers", 
                                    line=dict(color="#10b981", width=3)))
        fig_roic.add_trace(go.Scatter(x=mensal["Mês"], y=mensal["ROI"], name="ROI", mode="lines+markers", 
                                    line=dict(color="#3b82f6", width=3)))
        fig_roic.add_hline(y=15, line_dash="dash", line_color="green", annotation_text="Meta ROIC 15%")
        fig_roic.update_layout(
            title="ROIC vs ROI - Comparativo de Retorno",
            xaxis_title="Mês",
            yaxis_title="Retorno (%)",
            margin=dict(t=80, b=140, l=80, r=80)
        )
        st.plotly_chart(style_fig(fig_roic), use_container_width=True)

        # KPIs de rentabilidade
        col1, col2, col3, col4 = st.columns(4)
        with col1: 
            kpi_card("ROIC Médio", f"{mensal['ROIC'].mean():.1f}%")
        with col2: 
            kpi_card("ROI Médio", f"{mensal['ROI'].mean():.1f}%")
        with col3: 
            kpi_card("Melhor ROIC", f"{mensal['ROIC'].max():.1f}%")
        with col4: 
            kpi_card("Meta ROIC", "15.0%")

        # Ponto de equilíbrio
        fig_equilibrio = go.Figure()
        fig_equilibrio.add_trace(go.Bar(x=mensal["Mês"], y=mensal["Receita"], name="Receita", marker_color=PRIMARY))
        fig_equilibrio.add_trace(go.Scatter(x=mensal["Mês"], y=mensal["Ponto_Equilibrio"], name="Ponto de Equilíbrio", 
                                        mode="lines+markers", line=dict(color="#ef4444", width=3, dash="dash")))
        fig_equilibrio.update_layout(
            title="Receita vs Ponto de Equilíbrio",
            xaxis_title="Mês",
            yaxis_title="Valor (R$)",
            margin=dict(t=80, b=140, l=80, r=80)
        )
        st.plotly_chart(style_fig(fig_equilibrio, y_fmt=",.2f"), use_container_width=True)

        # Tabela detalhada de rentabilidade
        st.subheader("Indicadores de Rentabilidade Detalhados")
        rentabilidade = mensal[["Mês", "Receita", "Lucro", "EBITDA", "EBIT", "ROI", "ROIC", "Margem_Lucro", "Margem_EBITDA"]].round(2)
        st.dataframe(rentabilidade.style.format({
            "Receita": "R$ {:.2f}", "Lucro": "R$ {:.2f}", "EBITDA": "R$ {:.2f}", 
            "EBIT": "R$ {:.2f}", "ROI": "{:.1f}%", "ROIC": "{:.1f}%",
            "Margem_Lucro": "{:.1f}%", "Margem_EBITDA": "{:.1f}%"
        }), use_container_width=True)

    with tab4:
        st.subheader("Balanço Patrimonial e Indicadores de Solidez")
        
        if len(mensal) > 0:
            ultimo_mes = mensal.iloc[-1]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Balanço Patrimonial - Último Mês**")
                balanco_data = {
                    'Ativo': [
                        'Ativo Circulante',
                        'Ativo Não Circulante',
                        'Total do Ativo'
                    ],
                    'Valor (R$)': [
                        ultimo_mes['Ativo_Total'] * 0.4,
                        ultimo_mes['Ativo_Total'] * 0.6,
                        ultimo_mes['Ativo_Total']
                    ]
                }
                
                balanco_df = pd.DataFrame(balanco_data)
                st.dataframe(balanco_df.style.format({
                    'Valor (R$)': 'R$ {:.2f}'
                }), use_container_width=True)
            
            with col2:
                st.markdown("**Passivo e Patrimônio Líquido**")
                passivo_data = {
                    'Passivo': [
                        'Passivo Circulante',
                        'Passivo Não Circulante',
                        'Patrimônio Líquido',
                        'Total do Passivo + PL'
                    ],
                    'Valor (R$)': [
                        ultimo_mes['Passivo_Total'] * 0.7,
                        ultimo_mes['Passivo_Total'] * 0.3,
                        ultimo_mes['Patrimonio_Liquido'],
                        ultimo_mes['Passivo_Total'] + ultimo_mes['Patrimonio_Liquido']
                    ]
                }
                
                passivo_df = pd.DataFrame(passivo_data)
                st.dataframe(passivo_df.style.format({
                    'Valor (R$)': 'R$ {:.2f}'
                }), use_container_width=True)

            # Indicadores de solidez
            st.markdown("**Indicadores de Solidez Financeira**")
            indicadores_data = {
                'Indicador': [
                    'Grau de Endividamento',
                    'Liquidez Corrente',
                    'ROIC',
                    'Margem Líquida'
                ],
                'Valor': [
                    f"{ultimo_mes['Endividamento']:.1f}%",
                    f"{ultimo_mes['Liquidez_Corrente']:.2f}",
                    f"{ultimo_mes['ROIC']:.1f}%",
                    f"{ultimo_mes['Margem_Lucro']:.1f}%"
                ],
                'Interpretação': [
                    'Aceitável (<60%)' if ultimo_mes['Endividamento'] < 60 else 'Alto',
                    'Boa (>1.0)' if ultimo_mes['Liquidez_Corrente'] > 1.0 else 'Atenção',
                    'Bom (>15%)' if ultimo_mes['ROIC'] > 15 else 'Regular',
                    'Boa (>10%)' if ultimo_mes['Margem_Lucro'] > 10 else 'Regular'
                ]
            }
            
            indicadores_df = pd.DataFrame(indicadores_data)
            st.dataframe(indicadores_df, use_container_width=True)

        # Evolução do balanço
        fig_balanco = go.Figure()
        fig_balanco.add_trace(go.Scatter(x=mensal["Mês"], y=mensal["Ativo_Total"], name="Ativo Total", mode="lines+markers", line=dict(width=3)))
        fig_balanco.add_trace(go.Scatter(x=mensal["Mês"], y=mensal["Passivo_Total"], name="Passivo Total", mode="lines+markers", line=dict(width=3)))
        fig_balanco.add_trace(go.Scatter(x=mensal["Mês"], y=mensal["Patrimonio_Liquido"], name="Patrimônio Líquido", mode="lines+markers", line=dict(width=3)))
        fig_balanco.update_layout(
            title="Evolução do Balanço Patrimonial",
            xaxis_title="Mês",
            yaxis_title="Valor (R$)",
            margin=dict(t=80, b=140, l=80, r=80)
        )
        st.plotly_chart(style_fig(fig_balanco, y_fmt=",.2f"), use_container_width=True)

        # Indicadores de estrutura
        fig_estrutura = go.Figure()
        fig_estrutura.add_trace(go.Scatter(x=mensal["Mês"], y=mensal["Endividamento"], name="Grau de Endividamento", mode="lines+markers", line=dict(width=3)))
        fig_estrutura.add_trace(go.Scatter(x=mensal["Mês"], y=mensal["Liquidez_Corrente"], name="Liquidez Corrente", mode="lines+markers", line=dict(width=3), yaxis="y2"))
        fig_estrutura.update_layout(
            title="Indicadores de Estrutura Financeira",
            xaxis_title="Mês",
            yaxis=dict(title="Endividamento (%)"),
            yaxis2=dict(overlaying="y", side="right", title="Liquidez Corrente"),
            margin=dict(t=80, b=140, l=80, r=80)
        )
        st.plotly_chart(style_fig(fig_estrutura), use_container_width=True)

def page_eco():
    """
    Página de contexto econômico - mostra indicadores macroeconômicos.
    Ajuda a entender o ambiente externo que afeta o negócio.
    """
    top_header()
    hero("📈 Painel Econômico", "Indicadores macroeconômicos e tendências do mercado")

    st.markdown("""
    <div style="background-color: #f0f2f6; border-radius: 10px; padding: 20px; margin-bottom: 20px; border: 1px solid #e0e0e0;">
        <p style="color: #333; font-size: 16px;">
        Nenhum negócio opera isoladamente. Esta página contextualiza o desempenho dos seus cupons 
        com o cenário macroeconômico.
        </p>
        <p style="color: #333; font-size: 16px;">
        Acompanhe a evolução de indicadores cruciais como a <strong>Taxa SELIC</strong>, 
        <strong>IPCA (Inflação)</strong> e <strong>Níveis de Inadimplência</strong>, 
        e entenda como fatores externos podem estar a influenciar o poder de compra dos seus clientes.
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

    def _normalize_cols(df):
        """
        Normaliza nomes de colunas para dados econômicos.
        """
        df = df.copy()
        df.columns = [str(c).strip() for c in df.columns]
        lower = {c.lower(): c for c in df.columns}
        
        def pick(*names):
            for n in names:
                if n.lower() in lower:
                    return lower[n.lower()]
            for n in names:
                for lc, orig in lower.items():
                    if n.lower() in lc:
                        return orig
            return None
            
        return df, pick

    def _as_numeric(s):
        """
        Converte strings para números, tratando porcentagens e vírgulas decimais.
        """
        return pd.to_numeric(
            s.astype(str).str.replace("%","", regex=False).str.replace(",", ".", regex=False).str.replace(" ", "", regex=False),
            errors="coerce"
        )

    # Dados de exemplo se não houver dados reais
    if eco.empty:
        st.info("Ficheiro 'economia.csv' não encontrado. A carregar dados de exemplo.")
        eco = pd.DataFrame({
            "Ano": list(range(2019, 2026)),
            "PIB_Variacao":     [1.4, -3.9, 4.6, 2.9, 2.3, 2.1, 2.2],
            "Inflacao_IPCA":    [4.3,  4.5,10.1, 5.8, 4.6, 3.9, 4.2],
            "Selic":            [5.0,  2.0, 9.25,13.75,11.75,10.5,10.0],
            "Inadimplencia":    [3.7,  4.2, 4.8, 5.3, 4.9, 4.6, 4.4],
            "Desemprego":       [11.0,13.5,13.2, 9.9, 8.5, 8.1, 7.8],
            "Cambio_USD":       [4.0,  5.2, 5.4, 5.1, 4.9, 4.8, 4.7],
            "Consumo_Familias": [1.8, -5.2, 3.9, 3.2, 2.8, 2.5, 2.3]
        })

    eco, pick = _normalize_cols(eco)
    col_ano   = pick("ano","year")
    col_date  = pick("date","data")
    col_selic = pick("selic","taxa_selic","juros")
    col_ipca  = pick("ipca","inflacao_ipca","inflação","inflacao")
    col_inad  = pick("inadimpl","default")

    eco_anual = pd.DataFrame()
    eco_mensal = pd.DataFrame()

    # Prepara dados anuais e mensais
    if col_date is not None:
        # Dados com datas específicas
        eco[col_date] = pd.to_datetime(eco[col_date], errors="coerce")
        eco = eco.dropna(subset=[col_date]).sort_values(col_date)
        
        # Converte para numérico
        for c in [col_selic, col_ipca, col_inad]:
            if c is not None and c in eco.columns:
                eco[c] = _as_numeric(eco[c])

        eco_mensal = eco.rename(columns={col_date: "Data"}).copy()
        rename_map = {}
        if col_selic and col_selic in eco_mensal.columns: 
            rename_map[col_selic] = "Selic"
        if col_ipca  and col_ipca  in eco_mensal.columns: 
            rename_map[col_ipca]  = "IPCA"
        if col_inad  and col_inad  in eco_mensal.columns: 
            rename_map[col_inad]  = "Inadimplencia"
        eco_mensal.rename(columns=rename_map, inplace=True)
        eco_mensal["Ano"] = eco_mensal["Data"].dt.year

        # Agrupa por ano
        grp = eco_mensal.groupby("Ano")
        d = {"Ano": grp.size().index}
        if "Selic" in eco_mensal.columns: 
            d["Selic"] = grp["Selic"].mean().values
        if "IPCA"  in eco_mensal.columns: 
            d["IPCA"]  = grp["IPCA"].mean().values
        if "Inadimplencia" in eco_mensal.columns: 
            d["Inadimplencia"] = grp["Inadimplencia"].mean().values
        eco_anual = pd.DataFrame(d)

    elif col_ano is not None:
        # Dados anuais
        eco = eco.sort_values(col_ano)
        eco_anual = eco.rename(columns={col_ano: "Ano"}).copy()
        
        # Renomeia colunas para nomes padrão
        if col_selic and col_selic in eco_anual.columns and col_selic != "Selic": 
            eco_anual.rename(columns={col_selic: "Selic"}, inplace=True)
        if col_ipca  and col_ipca  in eco_anual.columns and col_ipca  != "IPCA": 
            eco_anual.rename(columns={col_ipca: "IPCA"}, inplace=True)
        if col_inad  and col_inad  in eco_anual.columns and col_inad  != "Inadimplencia": 
            eco_anual.rename(columns={col_inad: "Inadimplencia"}, inplace=True)
            
        # Converte para numérico
        for c in ["Selic","IPCA","Inadimplencia"]:
            if c in eco_anual.columns:
                eco_anual[c] = _as_numeric(eco_anual[c])

        # Cria dados mensais interpolados a partir dos anuais
        meses = pd.date_range(start="2024-01-01", end="2025-12-31", freq="M")
        eco_mensal = pd.DataFrame({"Data": meses})
        
        def interp(col):
            """Interpola dados anuais para mensais com um pouco de ruído."""
            if col not in eco_anual.columns or eco_anual[col].dropna().empty:
                return pd.Series([pd.NA]*len(meses))
            v24 = eco_anual.loc[eco_anual["Ano"]==2024, col].iloc[0] if (eco_anual["Ano"]==2024).any() else eco_anual[col].iloc[-1]
            v25 = eco_anual.loc[eco_anual["Ano"]==2025, col].iloc[0] if (eco_anual["Ano"]==2025).any() else v24
            lin = np.linspace(v24, v25, len(meses))
            rng = np.random.default_rng(7)
            noise = rng.normal(0, max(0.02, 0.005*abs(v25)), len(meses))
            return pd.Series(lin + noise).round(2)
            
        if "Selic" in eco_anual.columns: 
            eco_mensal["Selic"] = interp("Selic")
        if "IPCA"  in eco_mensal.columns: 
            eco_mensal["IPCA"]  = interp("IPCA")
        if "Inadimplencia" in eco_anual.columns: 
            eco_mensal["Inadimplencia"] = interp("Inadimplencia")

    else:
        st.warning("Não foi possível identificar colunas de 'Ano' ou 'Data' nos dados econômicos.")
        return

    # Abas para visualização anual e mensal
    tab1, tab2 = st.tabs(["📊 Evolução Anual", "📈 Evolução Mensal"])

    with tab1:
        st.subheader("Evolução Anual — SELIC, IPCA e Inadimplência")

        if "Selic" in eco_anual.columns and eco_anual["Selic"].notna().any():
            fig_selic_y = go.Figure()
            fig_selic_y.add_trace(go.Scatter(x=eco_anual["Ano"], y=eco_anual["Selic"], mode="lines+markers", name="SELIC (%)", line=dict(width=3)))
            fig_selic_y.update_layout(
                title="Evolução SELIC (%) — Anual", 
                xaxis_title="Ano", 
                yaxis_title="SELIC (%)",
                margin=dict(t=80, b=140, l=80, r=80)
            )
            st.plotly_chart(style_fig(fig_selic_y), use_container_width=True)

        if "IPCA" in eco_anual.columns and eco_anual["IPCA"].notna().any():
            fig_ipca_y = go.Figure()
            fig_ipca_y.add_trace(go.Bar(x=eco_anual["Ano"], y=eco_anual["IPCA"], name="IPCA (%)", marker_color=PRIMARY, opacity=0.85))
            fig_ipca_y.update_layout(
                title="Evolução IPCA (%) — Anual", 
                xaxis_title="Ano", 
                yaxis_title="IPCA (%)",
                margin=dict(t=80, b=140, l=80, r=80)
            )
            st.plotly_chart(style_fig(fig_ipca_y), use_container_width=True)

        if "Inadimplencia" in eco_anual.columns and eco_anual["Inadimplencia"].notna().any():
            fig_inad_y = go.Figure()
            fig_inad_y.add_trace(go.Scatter(x=eco_anual["Ano"], y=eco_anual["Inadimplencia"], mode="lines+markers", name="Inadimplência (%)", line=dict(width=3)))
            fig_inad_y.update_layout(
                title="Evolução da Inadimplência (%) — Anual", 
                xaxis_title="Ano", 
                yaxis_title="Inadimplência (%)",
                margin=dict(t=80, b=140, l=80, r=80)
            )
            st.plotly_chart(style_fig(fig_inad_y), use_container_width=True)

    with tab2:
        st.subheader("Evolução Mensal — SELIC, IPCA e Inadimplência")

        if "Selic" in eco_mensal.columns and eco_mensal["Selic"].notna().any():
            fig = px.line(eco_mensal, x="Data", y="Selic", title="Evolução SELIC (%) — Mensal")
            fig.update_layout(margin=dict(t=80, b=140, l=80, r=80))
            st.plotly_chart(style_fig(fig), use_container_width=True)

        if "IPCA" in eco_mensal.columns and eco_mensal["IPCA"].notna().any():
            fig = px.line(eco_mensal, x="Data", y="IPCA", title="Evolução IPCA (%) — Mensal")
            fig.update_layout(margin=dict(t=80, b=140, l=80, r=80))
            st.plotly_chart(style_fig(fig), use_container_width=True)

        if "Inadimplencia" in eco_mensal.columns and eco_mensal["Inadimplencia"].notna().any():
            fig = px.area(eco_mensal, x="Data", y="Inadimplencia", title="Evolução da Inadimplência (%) — Mensal")
            fig.update_layout(margin=dict(t=80, b=140, l=80, r=80))
            st.plotly_chart(style_fig(fig), use_container_width=True)

def page_simulacaologin():
    """
    Página de gamificação - onde usuários acompanham seu progresso.
    A parte mais divertida do sistema!
    """
    top_header()
    hero("🎯 Simulação de Uso de Cupons", "Sistema de gamificação e progressão por níveis")

    st.markdown("""
    <div style="background-color: #f0f2f6; border-radius: 10px; padding: 20px; margin-bottom: 20px; border: 1px solid #e0e0e0;">
        <p style="color: #333; font-size: 16px;">
        Esta é a sua área pessoal de gamificação! <strong>Registe os cupons</strong> que você usa para 
        subir de nível, ganhar <strong>XP</strong> e desbloquear <strong>conquistas</strong>.
        </p>
        <p style="color: #333; font-size: 16px;">
        Use o simulador para planear o seu progresso e veja o seu histórico de economia a crescer.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # CSS personalizado para garantir que as métricas fiquem com texto preto
    metric_style = """
        <style>
            [data-testid="stTabsBar"] button p {
                color: #000000 !important;
            }
            [data-testid="stTabsBar"] button[aria-selected="true"] p {
                font-weight: bold;
                color: #000000 !important;
            }
            .black-metric-label {
                font-size: 0.875rem; 
                color: #000000 !important;
                margin-bottom: 0.25rem;
                line-height: 1.5;
            }
            .black-metric-value {
                font-size: 1.5rem; 
                font-weight: 500;
                color: #000000;
            }
            .metric-box {
                background-color: #f9f9f9;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 16px;
                text-align: center;
                height: 100%; 
            }
        </style>
    """
    st.markdown(metric_style, unsafe_allow_html=True)

    # Cria arquivo de usos de cupom se não existir
    if not os.path.exists(CUPOM_USOS_PATH):
        pd.DataFrame(columns=["email","data","loja","tipo","valor","local"]).to_csv(CUPOM_USOS_PATH, index=False)

    # Verifica se usuário está logado
    email = st.session_state.get("user_email")
    if not email:
        st.info("Faça login para acessar a simulação.")
        return

    # Carrega dados do usuário
    df_users = load_users()
    user_data = df_users[df_users["email"] == email]
    
    if user_data.empty:
        st.error("Usuário não encontrado.")
        return
        
    # Extrai dados do usuário
    cupons_usados = int(user_data["cupons_usados"].iloc[0]) if not pd.isna(user_data["cupons_usados"].iloc[0]) else 0
    total_economizado = float(user_data["total_economizado"].iloc[0]) if not pd.isna(user_data["total_economizado"].iloc[0]) else 0.0
    xp = int(user_data["xp"].iloc[0]) if not pd.isna(user_data["xp"].iloc[0]) else 0
    nivel_id = int(user_data["nivel"].iloc[0]) if not pd.isna(user_data["nivel"].iloc[0]) else 1
    
    if nivel_id not in gamificacao.niveis:
        nivel_id = 1
        
    nivel_info = gamificacao.niveis.get(nivel_id, gamificacao.niveis[1])
    progresso, proximo_nivel_info = gamificacao.calcular_progresso(cupons_usados, nivel_id)

    # Sistema de abas organizado
    tab1, tab2, tab3, tab4 = st.tabs(["🎮 Progresso", "📊 Desempenho", "🎯 Simulação", "🏆 Conquistas"])

    with tab1:
        # Layout principal do progresso
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Card de Nível Atual - mostra nível atual e progresso
            st.markdown(f"""
                <div style="background: linear-gradient(135deg, {nivel_info['cor']}20, {nivel_info['cor']}40); 
                            padding: 20px; border-radius: 15px; border-left: 5px solid {nivel_info['cor']};
                            margin-bottom: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 14px; color: #666;">Seu Nível Atual</div>
                            <div style="font-size: 24px; font-weight: bold; color: {nivel_info['cor']};">{nivel_info['nome']}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 14px; color: #666;">Cashback</div>
                            <div style="font-size: 20px; font-weight: bold; color: {nivel_info['cor']};">{nivel_info['cashback']}%</div>
                        </div>
                    </div>
                    <div style="margin-top: 15px;">
                        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #666;">
                            <span>{cupons_usados} cupons usados</span>
                            <span>{proximo_nivel_info['cupons_necessarios'] if proximo_nivel_info else 'Máximo'}</span>
                        </div>
                        <div style="background: #e0e0e0; height: 8px; border-radius: 4px; margin-top: 5px;">
                            <div style="background: {nivel_info['cor']}; height: 100%; width: {progresso * 100}%; border-radius: 4px;"></div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Estatísticas Rápidas
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            
            with col_stat1:
                st.markdown(f'''
                    <div class="metric-box">
                        <div class="black-metric-label">💰 Total Economizado</div>
                        <div class="black-metric-value">R$ {total_economizado:.2f}</div>
                    </div>
                ''', unsafe_allow_html=True)
                
            with col_stat2:
                st.markdown(f'''
                    <div class="metric-box">
                        <div class="black-metric-label">⭐ XP Acumulado</div>
                        <div class="black-metric-value">{xp}</div>
                    </div>
                ''', unsafe_allow_html=True)
                
            with col_stat3:
                if proximo_nivel_info:
                    st.markdown(f'''
                        <div class="metric-box">
                            <div class="black-metric-label">🏆 Próximo Nível</div>
                            <div class="black-metric-value">{proximo_nivel_info["nome"]}</div>
                        </div>
                    ''', unsafe_allow_html=True)
                else:
                    st.markdown(f'''
                        <div class="metric-box">
                            <div class="black-metric-label">🏆 Nível Máximo</div>
                            <div class="black-metric-value">Alcançado!</div>
                        </div>
                    ''', unsafe_allow_html=True)

        with col2:
            # Conquistas Rápidas - mostra as 3 conquistas mais recentes
            st.markdown("**🏅 Conquistas Recentes**")
            conquistas_desbloqueadas = []
            for key, conquista in gamificacao.conquistas.items():
                if user_data[f"conquista_{key}"].iloc[0] if f"conquista_{key}" in user_data.columns else False:
                    conquistas_desbloqueadas.append(conquista)
            
            if conquistas_desbloqueadas:
                for conquista in conquistas_desbloqueadas[:3]:  # Mostra apenas as 3 mais recentes
                    st.markdown(f"<div style='color: #000000;'>{conquista['icone']} <strong>{conquista['nome']}</strong></div>", unsafe_allow_html=True)
                    st.caption(conquista['descricao'])
            else:
                st.info("Nenhuma conquista desbloqueada ainda.")

        # Sistema de Níveis - mostra todos os níveis disponíveis
        st.subheader("💎 Jornada de Níveis")
        niveis_cols = st.columns(len(gamificacao.niveis))
        
        for idx, (nivel_key, info) in enumerate(gamificacao.niveis.items()):
            with niveis_cols[idx]:
                is_current = nivel_key == nivel_id
                is_unlocked = cupons_usados >= info["cupons_necessarios"]
                
                border_color = info["cor"] if is_current or is_unlocked else "#e0e0e0"
                bg_color = f"{info['cor']}20" if is_current else "#f8f9fa" if is_unlocked else "#f8f9fa"
                text_color = info["cor"] if is_current or is_unlocked else "#999"
                
                nivel_html = f"""
                <div style="background: {bg_color}; padding: 15px; border-radius: 10px; border: 2px solid {border_color}; text-align: center; height: 120px;">
                    <div style="font-size: 20px; color: {text_color};">{info['nome'].split(' ')[0]}</div>
                    <div style="font-size: 12px; color: {text_color}; margin: 5px 0;">{info['cupons_necessarios']}+ cupons</div>
                    <div style="font-size: 14px; font-weight: bold; color: {info['cor']};">{info['cashback']}% cashback</div>
                """
                
                if is_unlocked:
                    nivel_html += '<div style="font-size: 10px; color: green; margin-top: 5px;">✓ Desbloqueado</div>'
                if is_current:
                    nivel_html += '<div style="font-size: 10px; color: blue; margin-top: 5px;">● Atual</div>'
                
                nivel_html += "</div>"
                
                st.markdown(nivel_html, unsafe_allow_html=True)

        # Registro de Cupom - formulário para registrar novo cupom
        st.markdown("---")
        st.subheader("🎁 Registrar Uso de Cupom")
        
        with st.form("form_cupom", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                loja = st.text_input("🏪 Loja", placeholder="Ex: Supermercado São João")
                tipo = st.selectbox("🎯 Tipo de Cupom", ["Desconto", "Cashback", "Fidelidade", "Primeira Compra", "Frete Grátis"])
            with col2:
                valor = st.number_input("💰 Valor do Cupom (R$)", min_value=0.0, step=1.0, format="%.2f")
                local = st.text_input("📍 Local", placeholder="Ex: São Paulo - SP")
            
            submit = st.form_submit_button("🎊 Registrar Cupom", use_container_width=True)

        if submit:
            if not loja:
                st.warning("Por favor, informe o nome da loja.")
            else:
                cupom_data = {
                    "loja": loja,
                    "tipo": tipo,
                    "valor": valor,
                    "local": local
                }
                
                # Atualiza gamificação e verifica conquistas
                conquistas_desbloqueadas = atualizar_usuario_gamificacao(email, cupom_data)
                
                # Salva no histórico
                usos = pd.read_csv(CUPOM_USOS_PATH) if os.path.exists(CUPOM_USOS_PATH) else pd.DataFrame(columns=["email","data","loja","tipo","valor","local"])
                usos = pd.concat([usos, pd.DataFrame([{
                    "email": email, 
                    "data": datetime.datetime.now().isoformat(),
                    "loja": loja, 
                    "tipo": tipo, 
                    "valor": float(valor), 
                    "local": local
                }])], ignore_index=True)
                usos.to_csv(CUPOM_USOS_PATH, index=False)

                st.success("🎉 Cupom registrado com sucesso!")
                
                # Mostra conquistas desbloqueadas com animação
                if conquistas_desbloqueadas:
                    st.balloons()
                    for conquista_id in conquistas_desbloqueadas:
                        conquista = gamificacao.conquistas[conquista_id]
                        st.markdown(f"""
                            <div style="background: linear-gradient(135deg, #FFD700, #FFA500); 
                                        padding: 15px; border-radius: 10px; text-align: center; 
                                        margin: 10px 0; border: 2px solid #FF6B00;">
                                <div style="font-size: 24px;">{conquista['icone']}</div>
                                <div style="font-size: 18px; font-weight: bold; color: #000;">Conquista Desbloqueada!</div>
                                <div style="font-size: 16px; color: #000;">{conquista['nome']}</div>
                                <div style="font-size: 14px; color: #333;">{conquista['descricao']}</div>
                                <div style="font-size: 12px; color: #666; margin-top: 5px;">+{conquista['xp']} XP ganhos!</div>
                            </div>
                        """, unsafe_allow_html=True)
                
                st.rerun()

    with tab2:
        st.subheader("📊 Análise de Desempenho")
        
        # Gráfico de progresso mensal (simulado)
        fig_progresso = go.Figure()
        
        meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun']
        cupons_mensais = [max(1, cupons_usados // len(meses)) for _ in range(len(meses))]
        if cupons_mensais:
            cupons_mensais[-1] = cupons_usados - sum(cupons_mensais[:-1])
        
        fig_progresso.add_trace(go.Bar(
            x=meses,
            y=cupons_mensais,
            name="Cupons Usados",
            marker_color=PRIMARY
        ))
        
        fig_progresso.update_layout(
            title="Evolução Mensal de Cupons Usados",
            xaxis_title="Mês",
            yaxis_title="Quantidade de Cupons",
            showlegend=True
        )
        
        fig_progresso = style_fig(fig_progresso) 
        st.plotly_chart(fig_progresso, use_container_width=True)
        
        # Métricas de diversificação
        col1, col2, col3 = st.columns(3)
        with col1:
            lojas_val = user_data["lojas_visitadas"].iloc[0].count(",") + 1 if user_data["lojas_visitadas"].iloc[0] != "[]" else 0
            st.markdown(f'<div class="black-metric-label">🏪 Lojas Diferentes</div><div class="black-metric-value">{lojas_val}</div>', unsafe_allow_html=True)
        with col2:
            tipos_val = user_data["tipos_usados"].iloc[0].count(",") + 1 if user_data["tipos_usados"].iloc[0] != "[]" else 0
            st.markdown(f'<div class="black-metric-label">🎯 Tipos de Cupom</div><div class="black-metric-value">{tipos_val}</div>', unsafe_allow_html=True)
        with col3:
            economia_media = total_economizado / cupons_usados if cupons_usados > 0 else 0
            st.markdown(f'<div class="black-metric-label">💰 Economia Média por Cupom</div><div class="black-metric-value">R$ {economia_media:.2f}</div>', unsafe_allow_html=True)

    with tab3:
        st.subheader("🎯 Simulação Avançada")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Simulação Rápida**")
            num_cupons_simular = st.slider("Número de cupons para simular", 1, 50, 10)
            valor_medio_simular = st.slider("Valor médio por cupom (R$)", 10.0, 500.0, 100.0)
            
            if st.button("🚀 Executar Simulação", use_container_width=True):
                # Simula vários cupons de uma vez
                for i in range(num_cupons_simular):
                    cupom_simulado = {
                        "loja": f"Loja Simulada {i+1}",
                        "tipo": np.random.choice(["Desconto", "Cashback", "Fidelidade"]),
                        "valor": valor_medio_simular * np.random.uniform(0.5, 1.5),
                        "local": "Simulação"
                    }
                    atualizar_usuario_gamificacao(email, cupom_simulado)
                
                st.success(f"✅ {num_cupons_simular} cupons simulados com sucesso!")
                st.rerun()
        
        with col2:
            st.markdown("**Calculadora de Progresso**")
            cupons_desejados = st.number_input("Cupons para próximo nível", 
                                             min_value=cupons_usados+1, 
                                             max_value=100, 
                                             value=min(cupons_usados+10, 100))
            
            if proximo_nivel_info:
                cupons_necessarios = proximo_nivel_info["cupons_necessarios"] - cupons_usados
                st.info(f"📊 Para **{proximo_nivel_info['nome']}**: mais **{cupons_necessarios}** cupons")
                
                cupons_por_semana = st.slider("Cupons por semana", 1, 20, 5)
                semanas_necessarias = max(1, cupons_necessarios // cupons_por_semana) if cupons_por_semana > 0 else 0
                st.markdown(f'<div class="black-metric-label">⏱️ Tempo estimado</div><div class="black-metric-value">{semanas_necessarias} semanas</div>', unsafe_allow_html=True)

    with tab4:
        st.subheader("🏆 Todas as Conquistas")
        
        conquistas_cols = st.columns(2)
        
        # Mostra todas as conquistas disponíveis
        for idx, (conquista_id, conquista) in enumerate(gamificacao.conquistas.items()):
            col_idx = idx % 2
            desbloqueada = user_data[f"conquista_{conquista_id}"].iloc[0] if f"conquista_{conquista_id}" in user_data.columns else False
            
            with conquistas_cols[col_idx]:
                bg_color = "#f0f8f0" if desbloqueada else "#f5f5f5"
                border_color = "#4CAF50" if desbloqueada else "#e0e0e0"
                icon_color = "#4CAF50" if desbloqueada else "#999"
                
                st.markdown(f"""
                    <div style="background: {bg_color}; padding: 15px; border-radius: 10px; border: 2px solid {border_color}; margin-bottom: 10px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 24px; color: {icon_color};">{conquista['icone']}</span>
                            <div>
                                <div style="font-weight: bold; color: {'#000' if desbloqueada else '#666'};">{conquista['nome']}</div>
                                <div style="font-size: 12px; color: {'#666' if desbloqueada else '#999'};">{conquista['descricao']}</div>
                                <div style="font-size: 11px; color: #888; margin-top: 5px;">+{conquista['xp']} XP</div>
                            </div>
                        </div>
                        {'<div style="text-align: right; color: #4CAF50; font-size: 12px;">✓ Desbloqueada</div>' if desbloqueada else '<div style="text-align: right; color: #999; font-size: 12px;">🔒 Bloqueada</div>'}
                    </div>
                """, unsafe_allow_html=True)

    # Histórico de Usos
    st.markdown("---")
    st.subheader("📋 Histórico de Cupons")
    if os.path.exists(CUPOM_USOS_PATH):
        hist = pd.read_csv(CUPOM_USOS_PATH)
        hist = hist[hist["email"] == email]
        if not hist.empty:
            hist["data"] = pd.to_datetime(hist["data"]).dt.strftime("%d/%m/%Y %H:%M")
            hist["economia_estimada"] = hist["valor"] * 0.1  # 10% de economia
            st.dataframe(
                hist.sort_values("data", ascending=False).style.format({
                    "valor": "R$ {:.2f}",
                    "economia_estimada": "R$ {:.2f}"
                }), 
                use_container_width=True
            )
            
            # Métricas resumidas do histórico
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f'''
                    <div class="metric-box">
                        <div class="black-metric-label">Total de Cupons</div>
                        <div class="black-metric-value">{len(hist)}</div>
                    </div>
                ''', unsafe_allow_html=True)
            with col2:
                st.markdown(f'''
                    <div class="metric-box">
                        <div class="black-metric-label">Economia Total</div>
                        <div class="black-metric-value">R$ {hist["economia_estimada"].sum():.2f}</div>
                    </div>
                ''', unsafe_allow_html=True)
            with col3:
                lojas_unicas = hist["loja"].nunique()
                st.markdown(f'''
                    <div class="metric-box">
                        <div class="black-metric-label">Lojas Diferentes</div>
                        <div class="black-metric-value">{lojas_unicas}</div>
                    </div>
                ''', unsafe_allow_html=True)
        else:
            st.info("Nenhum cupom registrado ainda.")

def page_sobre():
    """
    Página Sobre - mostra informações sobre a equipe do projeto e sobre o CupomGO
    """
    top_header()
    hero("👥 Sobre o CupomGO", "Conheça nossa plataforma, equipe e professores orientadores")

    # Sobre o CupomGO
    st.markdown("""
    <div style="background-color: #f8f9fa; border-radius: 15px; padding: 30px; margin-bottom: 30px; 
                border-left: 5px solid #0C2D6B; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="color: #0C2D6B; margin-top: 0;">💳 Sobre o CupomGO</h2>
        <p style="color: #333; font-size: 16px; line-height: 1.6;">
        O <strong>CupomGO</strong> é uma plataforma inovadora de gestão e gamificação de cupons de desconto, 
        desenvolvida para transformar a experiência de economia em uma jornada interativa e recompensadora. 
        Nosso objetivo é conectar usuários a descontos exclusivos, enquanto oferecemos às empresas insights 
        valiosos sobre o comportamento de consumo.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Tecnologia
    st.markdown("---")
    st.subheader("🛠️ Tecnologia")
    
    tech_col1, tech_col2, tech_col3, tech_col4 = st.columns(4)
    
    with tech_col1:
        st.markdown("""
        <div style="text-align: center; padding: 15px;">
            <div style="font-size: 36px; margin-bottom: 10px;">🎨</div>
            <h5 style="color: #0C2D6B; margin: 0;">Streamlit</h5>
            <p style="color: #666; font-size: 12px; margin: 5px 0 0 0;">
            Interface Web
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with tech_col2:
        st.markdown("""
        <div style="text-align: center; padding: 15px;">
            <div style="font-size: 36px; margin-bottom: 10px;">📊</div>
            <h5 style="color: #0C2D6B; margin: 0;">Plotly</h5>
            <p style="color: #666; font-size: 12px; margin: 5px 0 0 0;">
            Visualizações
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with tech_col3:
        st.markdown("""
        <div style="text-align: center; padding: 15px;">
            <div style="font-size: 36px; margin-bottom: 10px;">🐼</div>
            <h5 style="color: #0C2D6B; margin: 0;">Pandas</h5>
            <p style="color: #666; font-size: 12px; margin: 5px 0 0 0;">
            Dados
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with tech_col4:
        st.markdown("""
        <div style="text-align: center; padding: 15px;">
            <div style="font-size: 36px; margin-bottom: 10px;">🎯</div>
            <h5 style="color: #0C2D6B; margin: 0;">Gamificação</h5>
            <p style="color: #666; font-size: 12px; margin: 5px 0 0 0;">
            Sistema Proprietário
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Integrantes do grupo
    st.markdown("---")
    st.subheader("🎓 Integrantes do Grupo")
    
    integrantes = [
        "Carlos Roberto Santos Latorre",
        "Felipe Lin", 
        "Felipe Wakasa Klabunde",
        "Stephany Aliyah Guimarães Eurípedes de Paula"
    ]
    
    col1, col2 = st.columns(2)
    
    with col1:
        for i in range(0, len(integrantes), 2):
            st.markdown(f"""
                <div style="background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; 
                            border-left: 4px solid #0C2D6B; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="font-weight: bold; color: #0C2D6B;">👤 {integrantes[i]}</div>
                </div>
            """, unsafe_allow_html=True)
    
    with col2:
        for i in range(1, len(integrantes), 2):
            if i < len(integrantes):
                st.markdown(f"""
                    <div style="background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; 
                                border-left: 4px solid #0C2D6B; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="font-weight: bold; color: #0C2D6B;">👤 {integrantes[i]}</div>
                    </div>
                """, unsafe_allow_html=True)

    # Professores orientadores
    st.markdown("---")
    st.subheader("🏫 Professores Orientadores")
    
    professores = [
        "Eduardo Savino Gomes",
        "Lucy Mari Tabuti", 
        "Mauricio Lopes Da Cunha",
        "Rodnil da Silva Moreira Lisboa"
    ]
    
    prof_col1, prof_col2 = st.columns(2)
    
    with prof_col1:
        for i in range(0, len(professores), 2):
            st.markdown(f"""
                <div style="background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; 
                            border-left: 4px solid #10b981; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="font-weight: bold; color: #10b981;">🎓 {professores[i]}</div>
                </div>
            """, unsafe_allow_html=True)
    
    with prof_col2:
        for i in range(1, len(professores), 2):
            if i < len(professores):
                st.markdown(f"""
                    <div style="background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; 
                                border-left: 4px solid #10b981; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="font-weight: bold; color: #10b981;">🎓 {professores[i]}</div>
                    </div>
                """, unsafe_allow_html=True)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p>💡 <strong>CupomGO</strong> - Transformando economia em experiência 🎮</p>
      
    </div>
    """, unsafe_allow_html=True)

# ---------------- Estado da Aplicação ----------------
# Inicializa o estado da aplicação se não existir
# Think of this as the app's memory - it remembers things between interactions
if "auth" not in st.session_state: 
    st.session_state.auth = False  # Whether user is logged in
if "auth_mode" not in st.session_state: 
    st.session_state.auth_mode = "login"  # Current auth screen (login/signup)
if "user_email" not in st.session_state: 
    st.session_state.user_email = None  # Email of logged in user
if "page" not in st.session_state: 
    st.session_state.page = "home"  # Current page being displayed

# ---------------- Roteamento Principal ----------------
def main():
    """
    Função principal que controla toda a aplicação.
    Decide o que mostrar baseado no estado do usuário (logado ou não).
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
        # Think of this as a TV remote - each button goes to a different channel
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
