# ============================================================
# PicMoney Dashboard v19 — Streamlit + Plotly + Folium
# Tema claro; textos pretos; Login/Cadastro claros
# Interações: filtros cruzados (sidebar), período (Dia/Semana/Mês),
# range selector/slider, cumulativo, média móvel, picos anotados,
# normalização 0–100%, Top-N/ordenação (CFO), download CSV por gráfico
# Páginas: Home, Indicadores Executivos, Mapa, Financeiro, Painel Econômico, Login
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import hashlib, os, datetime, re
from PIL import Image, UnidentifiedImageError

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
st.set_page_config(page_title="PicMoney Dashboard", page_icon="💳", layout="wide")
PRIMARY = "#62C370"

# ------------------------------------------------------------
# CSS (arquivo + fallback mínimo)
# ------------------------------------------------------------
def inject_css():
    try:
        with open("assets/styles.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception:
        st.markdown("""
        <style>
        :root{
          --pm-bg:#FFFFFF; --pm-surface:#FFFFFF; --pm-surface-2:#FAFAFA; --pm-primary:#62C370;
          --pm-accent:#EEDC82; --pm-text:#1C1C1C; --pm-muted:#6B7280; --pm-border:#E5E7EB;
        }
        html, body, .block-container{ background:var(--pm-bg)!important; color:var(--pm-text)!important; }
        [data-testid="stSidebar"]{
          background:var(--pm-surface); border-right:1px solid var(--pm-border);
          padding:12px 8px;
        }
        .pm-hero{border:1px solid var(--pm-border); background:linear-gradient(120deg, rgba(98,195,112,.08), rgba(238,220,130,.08));
          padding:14px 16px; border-radius:16px; box-shadow:0 8px 24px rgba(0,0,0,.06); margin: 8px 0 16px 0;}
        .pm-hero .pm-title{font-weight:700; color:var(--pm-text); font-size:20px;}
        .pm-hero .pm-sub{color:var(--pm-muted); font-size:13px;}
        .pm-card{background:var(--pm-surface); border:1px solid var(--pm-border); border-radius:14px;
          padding:12px 14px; box-shadow:0 6px 18px rgba(0,0,0,.06); text-align:center;}
        .pm-metric-title{font-weight:600; color:var(--pm-muted); margin-bottom:6px;}
        .pm-metric-value{font-size:22px; font-weight:800; color:var(--pm-text);}
        .pm-filter{background:var(--pm-surface); border:1px solid var(--pm-border); border-radius:14px;
          padding:10px 12px; margin-bottom:12px; box-shadow:0 6px 18px rgba(0,0,0,.06);}
        .auth-card{margin-top:8px; margin-bottom:8px;}
        .auth-title{font-weight:700; font-size:20px;}
        .auth-sub{font-size:13px; color:var(--pm-muted);}
        .logo-fallback{font-weight:800; font-size:18px;}
        .stTextInput>div>div>input, .stPassword>div>div>input{
          background:#FFFFFF !important; color:#000 !important; border:1px solid var(--pm-border) !important;
        }
        .stButton>button{
          background:#FFFFFF !important; color:#000 !important; border:1px solid var(--pm-border) !important;
          border-radius:10px !important;
        }
        </style>
        """, unsafe_allow_html=True)

inject_css()

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------
PATH_PLAYERS     = "assets/players.xlsx"
PATH_TX          = "assets/transacoes.xlsx"
PATH_STORES      = "assets/lojas.xlsx"
PATH_PEDESTRIANS = "assets/pedestres.xlsx"
USERS_PATH       = "assets/usuarios.csv"
ECON_PATH        = "assets/economia.csv"

# ------------------------------------------------------------
# UTILS
# ------------------------------------------------------------
def safe_logo(width=64):
    logo_path = "assets/Logo(PicMoney).png"
    try:
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            st.image(img, width=width)
        else:
            st.markdown('<div class="logo-fallback">PicMoney</div>', unsafe_allow_html=True)
    except (UnidentifiedImageError, OSError):
        st.markdown('<div class="logo-fallback">PicMoney</div>', unsafe_allow_html=True)

def style_fig(fig):
    """Tema claro + textos pretos + grades leves + barra de ferramentas útil."""
    fig.update_layout(
        font=dict(color="#000"),
        paper_bgcolor="white", plot_bgcolor="white",
        legend=dict(font=dict(color="#000"), bgcolor="rgba(255,255,255,0.6)", bordercolor="#E5E7EB", borderwidth=1),
        hovermode="x unified",
        margin=dict(l=8, r=8, t=36, b=8),
        modebar_add=["v1hovermode","toggleSpikelines","toImage"]
    )
    fig.update_xaxes(title_font=dict(color="#000"), tickfont=dict(color="#000"), gridcolor="#E5E7EB", zerolinecolor="#E5E7EB")
    fig.update_yaxes(title_font=dict(color="#000"), tickfont=dict(color="#000"), gridcolor="#E5E7EB", zerolinecolor="#E5E7EB")
    return fig

def add_time_controls(fig):
    """Adiciona range selector/slider no eixo X (temporal)."""
    fig.update_xaxes(
        rangeselector=dict(
            buttons=[
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=3, label="3m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(step="all", label="Tudo")
            ]
        ),
        rangeslider=dict(visible=True),
        type="date",
        showspikes=True, spikemode="across", spikesnap="cursor", spikethickness=1
    )
    return fig

def df_download_button(df, label="⬇️ Baixar CSV", fname="dados.csv"):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label, csv, file_name=fname, mime="text/csv")

# ------------------------------------------------------------
# AUTH
# ------------------------------------------------------------
def hash_password(pwd: str) -> str:
    return hashlib.sha256((pwd or "").encode("utf-8")).hexdigest()

def load_users() -> pd.DataFrame:
    if not os.path.exists(USERS_PATH):
        return pd.DataFrame(columns=["nome","email","senha_hash","criado_em"])
    try:
        return pd.read_csv(USERS_PATH)
    except Exception:
        return pd.DataFrame(columns=["nome","email","senha_hash","criado_em"])

def email_exists(df: pd.DataFrame, email: str) -> bool:
    return (email or "").lower() in (df["email"].astype(str).str.lower().tolist() if not df.empty else [])

def save_user(nome: str, email: str, pwd: str):
    df = load_users()
    new = pd.DataFrame([{
        "nome": (nome or "").strip(),
        "email": (email or "").strip(),
        "senha_hash": hash_password(pwd or ""),
        "criado_em": datetime.datetime.utcnow().isoformat()
    }])
    df = pd.concat([df,new], ignore_index=True)
    df.to_csv(USERS_PATH, index=False, encoding="utf-8")

def check_login(email: str, pwd: str) -> bool:
    df = load_users()
    if df.empty: return False
    row = df[df["email"].astype(str).str.lower()==(email or "").lower()]
    if row.empty: return False
    return row.iloc[0]["senha_hash"] == hash_password(pwd or "")

# ------------------------------------------------------------
# LOADERS
# ------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_xlsx(path):
    try:
        return pd.read_excel(path) if os.path.exists(path) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_csv(path):
    try:
        return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def normcols(df: pd.DataFrame):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    lower = {c.lower(): c for c in df.columns}
    def get(*names):
        for n in names:
            if n in lower: return lower[n]
        # contém substring
        for want in names:
            for lc, orig in lower.items():
                if want in lc: return orig
        return None
    return df, get

def ensure_lat_lon(df: pd.DataFrame, get):
    lat_col = get("latitude","lat")
    lon_col = get("longitude","lng","long","lon")
    if lat_col and lon_col:
        return df, lat_col, lon_col
    lc = get("local_captura","local","captura")
    if not lc: return df, None, None

    def parse_lat(s):
        if pd.isna(s): return np.nan
        m = re.findall(r"-?\d{1,3}\.\d+", str(s))
        if len(m) >= 2:
            try: return float(m[0])
            except: return np.nan
        return np.nan

    def parse_lon(s):
        if pd.isna(s): return np.nan
        m = re.findall(r"-?\d{1,3}\.\d+", str(s))
        if len(m) >= 2:
            try: return float(m[1])
            except: return np.nan
        return np.nan

    df = df.copy()
    try:
        df["__latitude__"]  = df[lc].apply(parse_lat)
        df["__longitude__"] = df[lc].apply(parse_lon)
        return df, "__latitude__", "__longitude__"
    except Exception:
        return df, None, None

# ------------------------------------------------------------
# CROSS-FILTERS (sidebar)
# ------------------------------------------------------------
def ui_global_filters(df, get, title="🎛️ Filtros (página)"):
    df = df.copy()
    scol = get("nome_loja","loja","merchant","estabelecimento")
    tcol = get("tipo_cupom","tipo","categoria","segmento","classe")
    vcol = get("valor_compra","valor","amount","preco")
    txtcol = get("cupom","codigo","id_cupom","cupom_id")

    with st.sidebar.expander(title, expanded=False):
        if scol and scol in df.columns:
            lojas = sorted(df[scol].dropna().astype(str).unique().tolist())[:3000]
            pick_lojas = st.multiselect("Lojas", lojas, default=[])
            if pick_lojas:
                df = df[df[scol].astype(str).isin(pick_lojas)]

        if tcol and tcol in df.columns:
            tipos = sorted(df[tcol].dropna().astype(str).unique().tolist())[:3000]
            pick_tipos = st.multiselect("Tipos de cupom", tipos, default=[])
            if pick_tipos:
                df = df[df[tcol].astype(str).isin(pick_tipos)]

        if vcol and vcol in df.columns:
            try:
                vmin, vmax = float(df[vcol].min()), float(df[vcol].max())
                smin, smax = st.slider("Faixa de valores", min_value=float(round(vmin,2)),
                                       max_value=float(round(vmax,2)),
                                       value=(float(round(vmin,2)), float(round(vmax,2))))
                df = df[(df[vcol] >= smin) & (df[vcol] <= smax)]
            except Exception:
                pass

        if txtcol and txtcol in df.columns:
            q = st.text_input("Buscar código de cupom (contém)")
            if q:
                df = df[df[txtcol].astype(str).str.contains(q, case=False, na=False)]
    return df

def add_time_widgets(df, dcol):
    df = df.copy()
    df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
    min_d = pd.to_datetime(df[dcol].min())
    max_d = pd.to_datetime(df[dcol].max())
    if pd.isna(min_d) or pd.isna(max_d):
        return df, "M"

    with st.expander("⏱️ Filtros de tempo", expanded=False):
        c1, c2 = st.columns(2)
        start = c1.date_input("De", value=min_d.date())
        end   = c2.date_input("Até", value=max_d.date())
        freq = st.radio("Agregação", ["Mês", "Semana", "Dia"], horizontal=True, index=0)
    if start and end:
        mask = (df[dcol] >= pd.to_datetime(start)) & (df[dcol] <= pd.to_datetime(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))
        df = df.loc[mask]

    return df, {"Mês":"M", "Semana":"W-MON", "Dia":"D"}[freq]

# ------------------------------------------------------------
# UI helpers
# ------------------------------------------------------------
def top_header():
    col1, col2, col3 = st.columns([5,3,1])
    with col1:
        safe_logo(48)
    with col2:
        user = st.session_state.get("user_email") or "Usuário"
        st.markdown(f'<div style="text-align:right;color:#1C1C1C;padding-top:6px;">👤 {user}</div>', unsafe_allow_html=True)
    with col3:
        if st.button("🚪 Sair", key="logout_btn_top"):
            st.session_state.clear()
            st.session_state.auth = False
            st.session_state.page = "home"
            st.rerun()

def hero(title, sub=""):
    st.markdown(f'<div class="pm-hero"><div class="pm-title">{title}</div><div class="pm-sub">{sub}</div></div>', unsafe_allow_html=True)

def kpi_card(title, value):
    st.markdown(f"""
        <div class="pm-card">
            <div class="pm-metric-title">{title}</div>
            <div class="pm-metric-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------
# NAV
# ------------------------------------------------------------
NAV_ITEMS = [
    ("Home", "home"),
    ("Indicadores Executivos", "kpis"),
    ("Mapa", "mapa"),
    ("Financeiro", "fin"),
    ("Painel Econômico", "eco"),
    ("Login", "login")
]

def sidebar_nav():
    try:
        st.sidebar.image("assets/Logo(PicMoney).png", width=56)
    except Exception:
        st.sidebar.markdown("**PicMoney**")
    st.sidebar.markdown("---")
    active = st.session_state.get("page", "home")
    for label, slug in NAV_ITEMS:
        btn_label = f"▶ {label}" if slug == active else label
        if st.sidebar.button(btn_label, key=f"nav_{slug}", use_container_width=True):
            st.session_state.page = slug
            st.rerun()
    st.sidebar.markdown("---")

# ------------------------------------------------------------
# PAGES
# ------------------------------------------------------------
def page_home(tx, stores):
    top_header()
    hero("🏠 Home", "Resumo geral com métricas e evolução")

    if tx.empty:
        st.info("Sem dados de transações."); return

    df, get = normcols(tx)
    dcol = get("data","data_captura")
    vcol = get("valor_compra","valor")

    # KPIs do ano corrente
    if dcol and vcol and dcol in df.columns and vcol in df.columns:
        df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
        y = datetime.datetime.now().year
        dfa = df[df[dcol].dt.year==y]
        conv = len(dfa)
        avg  = dfa[vcol].mean() if not dfa.empty else 0
        c1, c2, c3 = st.columns(3)
        with c1: kpi_card("Cupons Ativos (ano)", f"{len(dfa):,}".replace(",", "."))
        with c2: kpi_card("Conversões (ano)", f"{conv:,}".replace(",", "."))
        with c3: kpi_card("Ticket Médio (ano)", f"R$ {avg:,.2f}".replace(",", "X").replace(".", ",").replace("X","."))

    # Filtros + tempo
    df = ui_global_filters(df, get)
    if not dcol or not vcol or dcol not in df.columns or vcol not in df.columns:
        st.warning("Dados insuficientes para gráficos."); return

    df, freq = add_time_widgets(df, dcol)
    df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
    df["Periodo"] = df[dcol].dt.to_period(freq).dt.to_timestamp()

    resumo = df.groupby("Periodo")[vcol].agg(Receita="sum", Ticket_Médio="mean", Conversões="count").reset_index()

    c1, c2, c3 = st.columns(3)
    show_cum = c1.checkbox("📈 Mostrar cumulativo", value=False)
    show_pts = c2.checkbox("● Marcadores", value=True)
    smooth   = c3.slider("Suavização (média móvel)", 1, 6, 1)

    if smooth > 1:
        for col in ["Receita","Ticket_Médio","Conversões"]:
            resumo[col] = resumo[col].rolling(smooth, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=resumo["Periodo"], y=resumo["Receita"],
        name="Receita (R$)", marker_color=PRIMARY,
        hovertemplate="Período: %{x|%Y-%m}<br>Receita: R$ %{y:,.2f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=resumo["Periodo"], y=resumo["Ticket_Médio"],
        name="Ticket Médio (R$)", mode="lines+markers" if show_pts else "lines",
        yaxis="y2", line=dict(width=3),
        hovertemplate="Período: %{x|%Y-%m}<br>Ticket: R$ %{y:,.2f}<extra></extra>"
    ))
    if show_cum:
        fig.add_trace(go.Scatter(
            x=resumo["Periodo"], y=resumo["Receita"].cumsum(),
            name="Receita (Acumulada)", mode="lines", line=dict(dash="dash"),
            hovertemplate="Período: %{x|%Y-%m}<br>Receita Acum.: R$ %{y:,.2f}<extra></extra>"
        ))
    fig.update_layout(
        title="Receita, Ticket Médio e Conversões por período",
        xaxis_title="Período",
        yaxis=dict(title="Receita (R$)"),
        yaxis2=dict(overlaying="y", side="right", title="Ticket Médio (R$)")
    )
    fig = style_fig(fig)
    fig = add_time_controls(fig)
    st.plotly_chart(fig, use_container_width=True)

    df_download_button(resumo.rename(columns={"Periodo":"periodo","Ticket_Médio":"ticket_medio"}),
                       "⬇️ Baixar dados do gráfico (CSV)", "home_resumo.csv")

def page_kpis(tx):
    top_header()
    hero("📊 Indicadores Executivos", "KPIs por perfil (CEO, CTO, CFO)")

    if tx.empty:
        st.info("Sem dados de transações."); return

    df, get = normcols(tx)
    tabs = st.tabs(["CEO", "CTO", "CFO"])

    # ---------- CEO ----------
    with tabs[0]:
        st.subheader("📈 CEO — Conversões e Taxa de Adesão")
        df_ceo = ui_global_filters(df, get, title="🎛️ Filtros (CEO)")
        dcol = get("data","data_captura")
        if not dcol or dcol not in df_ceo.columns:
            st.warning("Coluna de data não encontrada.")
        else:
            df_ceo, freq = add_time_widgets(df_ceo, dcol)
            df_ceo[dcol] = pd.to_datetime(df_ceo[dcol], errors="coerce")
            df_ceo["Periodo"] = df_ceo[dcol].dt.to_period(freq).dt.to_timestamp()

            conv = df_ceo.groupby("Periodo").size().rename("Conversões").reset_index()
            conv["Taxa_Adesão_%"] = conv["Conversões"] / max(1, conv["Conversões"].max()) * 100

            c1, c2 = st.columns(2)
            show_ma = c1.checkbox("Média móvel (3)", value=True, key="ceo_ma")
            show_norm = c2.checkbox("Normalizar 0–100%", value=False, key="ceo_norm")

            if show_ma:
                conv["Conversões_MM"] = conv["Conversões"].rolling(3, min_periods=1).mean()

            y_conv = "Conversões_MM" if show_ma else "Conversões"
            if show_norm and conv[y_conv].max() > 0:
                conv[y_conv] = conv[y_conv] / conv[y_conv].max() * 100
                y_title = "Escala Normalizada (0–100)"
            else:
                y_title = "Conversões"

            fig_ceo = go.Figure()
            fig_ceo.add_trace(go.Bar(x=conv["Periodo"], y=conv[y_conv], name="Conversões", marker_color=PRIMARY,
                                     hovertemplate="Período: %{x|%Y-%m}<br>Conversões: %{y:,.0f}<extra></extra>"))
            fig_ceo.add_trace(go.Scatter(x=conv["Periodo"], y=conv["Taxa_Adesão_%"], name="Taxa de Adesão (%)",
                                         yaxis="y2", mode="lines+markers",
                                         hovertemplate="Período: %{x|%Y-%m}<br>Taxa: %{y:.1f}%<extra></extra>"))

            fig_ceo.update_layout(title="Conversões e Taxa de Adesão",
                                  yaxis=dict(title=y_title),
                                  yaxis2=dict(overlaying="y", side="right", title="Taxa de Adesão (%)"))
            fig_ceo = style_fig(fig_ceo)
            fig_ceo = add_time_controls(fig_ceo)
            st.plotly_chart(fig_ceo, use_container_width=True)
            df_download_button(conv, "⬇️ CSV (CEO)", "kpi_ceo.csv")

    # ---------- CTO ----------
    with tabs[1]:
        st.subheader("🔧 CTO — Volume Operacional")
        df_cto = ui_global_filters(df, get, title="🎛️ Filtros (CTO)")
        dcol = get("data","data_captura")
        if not dcol or dcol not in df_cto.columns:
            st.warning("Coluna de data não encontrada.")
        else:
            df_cto, freq = add_time_widgets(df_cto, dcol)
            df_cto[dcol] = pd.to_datetime(df_cto[dcol], errors="coerce")
            df_cto["Periodo"] = df_cto[dcol].dt.to_period(freq).dt.to_timestamp()

            vol = df_cto.groupby("Periodo").size().rename("Eventos").reset_index()

            c1, c2 = st.columns(2)
            topN = c1.slider("Top picos a anotar", 0, 10, 3, key="cto_top")
            show_spikes = c2.checkbox("Mostrar spikes (linhas guias)", True, key="cto_spikes")

            fig_cto = px.bar(vol, x="Periodo", y="Eventos", title="Volume Operacional",
                             labels={"Periodo":"Período","Eventos":"Eventos"},
                             color_discrete_sequence=[PRIMARY])
            if topN > 0 and not vol.empty:
                top = vol.nlargest(topN, "Eventos")
                fig_cto.add_trace(go.Scatter(x=top["Periodo"], y=top["Eventos"], mode="markers+text",
                                             text=[f"▲ {int(v)}" for v in top["Eventos"]],
                                             textposition="top center", name="Picos"))
            if show_spikes:
                fig_cto.update_xaxes(showspikes=True, spikemode="across", spikesnap="cursor", spikethickness=1)

            fig_cto = style_fig(fig_cto)
            fig_cto = add_time_controls(fig_cto)
            st.plotly_chart(fig_cto, use_container_width=True)
            df_download_button(vol, "⬇️ CSV (CTO)", "kpi_cto.csv")

    # ---------- CFO ----------
    with tabs[2]:
        st.subheader("💰 CFO — Receita e ROI por Loja")
        df_cfo, get = normcols(df)  # renormaliza
        df_cfo = ui_global_filters(df_cfo, get, title="🎛️ Filtros (CFO)")
        dcol = get("data","data_captura"); vcol = get("valor_compra","valor"); scol = get("nome_loja","loja")
        if not (dcol and vcol and scol) or any(c not in df_cfo.columns for c in [dcol, vcol, scol]):
            st.warning("Dados insuficientes para CFO.")
        else:
            c1, c2, c3 = st.columns(3)
            topN = c1.slider("Top N lojas por Receita", 5, 20, 10, key="cfo_topn")
            roi_mode = c2.selectbox("Cálculo de ROI", ["Simplificado (35% investimento)", "Detalhado (investimento/lucro)"], index=0, key="cfo_mode")
            sort_by = c3.selectbox("Ordenar por", ["Receita","ROI"], index=0, key="cfo_sort")

            if roi_mode.startswith("Detalhado") and {"investimento_mkt","lucro_bruto"}.issubset(df_cfo.columns):
                agg = df_cfo.groupby(scol).agg(Receita=(vcol,'sum'), Transacoes=(vcol,'count'),
                                               Investimento=('investimento_mkt','sum'), Lucro=('lucro_bruto','sum')).reset_index()
                agg["ROI"] = ((agg["Lucro"] - agg["Investimento"]) / agg["Investimento"] * 100).replace([np.inf, -np.inf], np.nan)
            else:
                agg = df_cfo.groupby(scol)[vcol].agg(['sum','count']).reset_index().rename(columns={'sum':'Receita','count':'Transacoes'})
                agg["Investimento"] = agg["Receita"]*0.35
                agg["ROI"] = ((agg["Receita"] - agg["Investimento"]) / agg["Investimento"] * 100)

            agg = agg.sort_values(sort_by, ascending=False).head(topN)

            fig_cfo = go.Figure()
            fig_cfo.add_trace(go.Bar(x=agg[scol].astype(str), y=agg["Receita"], name="Receita (R$)", marker_color=PRIMARY,
                                     hovertemplate="Loja: %{x}<br>Receita: R$ %{y:,.2f}<extra></extra>"))
            fig_cfo.add_trace(go.Scatter(x=agg[scol].astype(str), y=agg["ROI"], name="ROI (%)", yaxis="y2",
                                         mode="lines+markers", hovertemplate="Loja: %{x}<br>ROI: %{y:.2f}%<extra></extra>"))
            fig_cfo.update_layout(title="Receita e ROI por Loja",
                                  xaxis_title="Loja",
                                  yaxis=dict(title="Receita (R$)"),
                                  yaxis2=dict(overlaying="y", side="right", title="ROI (%)"))
            fig_cfo = style_fig(fig_cfo)
            st.plotly_chart(fig_cfo, use_container_width=True)
            df_download_button(agg, "⬇️ CSV (CFO)", "kpi_cfo.csv")

def page_financeiro(tx):
    top_header()
    hero("💰 Financeiro", "Evolução de Receita, Ticket Médio, Lucro e ROI (%)")

    if tx.empty:
        st.info("Sem dados de transações."); return

    df, get = normcols(tx)
    df = ui_global_filters(df, get, title="🎛️ Filtros (Financeiro)")
    dcol = get("data","data_captura"); vcol = get("valor_compra","valor")
    if not (dcol and vcol) or any(c not in df.columns for c in [dcol, vcol]):
        st.info("Sem dados suficientes."); return

    df, freq = add_time_widgets(df, dcol)
    df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
    df["Periodo"] = df[dcol].dt.to_period(freq).dt.to_timestamp()

    resumo = df.groupby("Periodo")[vcol].agg(Receita="sum", Ticket="mean").reset_index()
    resumo["Lucro"] = resumo["Receita"]*0.65
    resumo["ROI"] = np.where(resumo["Receita"]>0, (resumo["Lucro"]/(resumo["Receita"]*0.35))*100, np.nan)

    c1, c2 = st.columns(2)
    cum  = c1.checkbox("📈 Mostrar acumulado", False)
    pts  = c2.checkbox("● Marcadores", True)

    tabs = st.tabs(["Receita", "Ticket", "Lucro", "ROI"])

    def _line(df_, y, title, color=PRIMARY):
        fig = px.line(df_, x="Periodo", y=y, title=title, labels={"Periodo":"Período", y:y},
                      color_discrete_sequence=[color])
        fig.update_traces(mode="lines+markers" if pts else "lines", line=dict(width=3))
        fig = style_fig(fig); fig = add_time_controls(fig)
        return fig

    with tabs[0]:
        dfp = resumo.copy()
        if cum: dfp["Receita"] = dfp["Receita"].cumsum()
        st.plotly_chart(_line(dfp, "Receita", "Receita Total por Período"), use_container_width=True)
        df_download_button(dfp[["Periodo","Receita"]], "⬇️ CSV Receita", "fin_receita.csv")

    with tabs[1]:
        st.plotly_chart(_line(resumo, "Ticket", "Ticket Médio por Período", color="#2F2F2F"), use_container_width=True)
        df_download_button(resumo[["Periodo","Ticket"]], "⬇️ CSV Ticket", "fin_ticket.csv")

    with tabs[2]:
        dfp = resumo.copy()
        if cum: dfp["Lucro"] = dfp["Lucro"].cumsum()
        st.plotly_chart(_line(dfp, "Lucro", "Lucro Estimado por Período", color="#8BD49C"), use_container_width=True)
        df_download_button(dfp[["Periodo","Lucro"]], "⬇️ CSV Lucro", "fin_lucro.csv")

    with tabs[3]:
        st.plotly_chart(_line(resumo, "ROI", "ROI (%) por Período", color="#7E7E7E"), use_container_width=True)
        df_download_button(resumo[["Periodo","ROI"]], "⬇️ CSV ROI", "fin_roi.csv")

def page_eco():
    top_header()
    hero("📈 Painel Econômico", "SELIC, IPCA e Inadimplência — mensal e anual")

    econ = load_csv(ECON_PATH)
    if econ.empty:
        st.warning("Arquivo assets/economia.csv não encontrado."); return

    econ.columns = [c.strip() for c in econ.columns]
    if "date" in econ.columns:
        econ["date"] = pd.to_datetime(econ["date"], errors="coerce")
        econ["year"] = econ["date"].dt.year
        econ["ym"] = econ["date"].dt.to_period("M").astype(str)

    selic_col = [c for c in econ.columns if "SELIC" in c.upper()]
    ipca_col  = [c for c in econ.columns if "IPCA" in c.upper()]
    inad_col  = [c for c in econ.columns if "INAD" in c.upper()]

    st.subheader("Evolução Mensal")
    cm1, cm2, cm3 = st.columns(3)
    if selic_col:
        fig = px.line(econ, x="ym", y=selic_col[0], markers=True, title=f"SELIC (% a.m.) — Mensal")
        fig.update_traces(hovertemplate="%{x}<br>%{y:.2f}%")
        fig = style_fig(fig); cm1.plotly_chart(fig, use_container_width=True)
        df_download_button(econ[["ym", selic_col[0]]].rename(columns={"ym":"periodo"}), "⬇️ CSV SELIC (mensal)", "eco_selic_mensal.csv")
    if ipca_col:
        fig = px.line(econ, x="ym", y=ipca_col[0], markers=True, title=f"IPCA (% a.m.) — Mensal",
                      color_discrete_sequence=["#2F2F2F"])
        fig.update_traces(hovertemplate="%{x}<br>%{y:.2f}%")
        fig = style_fig(fig); cm2.plotly_chart(fig, use_container_width=True)
        df_download_button(econ[["ym", ipca_col[0]]].rename(columns={"ym":"periodo"}), "⬇️ CSV IPCA (mensal)", "eco_ipca_mensal.csv")
    if inad_col:
        fig = px.line(econ, x="ym", y=inad_col[0], markers=True, title=f"Inadimplência (%) — Mensal",
                      color_discrete_sequence=["#B56576"])
        fig.update_traces(hovertemplate="%{x}<br>%{y:.2f}%")
        fig = style_fig(fig); cm3.plotly_chart(fig, use_container_width=True)
        df_download_button(econ[["ym", inad_col[0]]].rename(columns={"ym":"periodo"}), "⬇️ CSV Inadimplência (mensal)", "eco_inad_mensal.csv")

    st.subheader("Evolução Anual")
    if "year" in econ.columns:
        ca1, ca2, ca3 = st.columns(3)
        if selic_col:
            a = econ.groupby("year")[selic_col[0]].mean().reset_index()
            fig = px.bar(a, x="year", y=selic_col[0], title="SELIC média anual (% a.m.)")
            fig = style_fig(fig); ca1.plotly_chart(fig, use_container_width=True)
            df_download_button(a, "⬇️ CSV SELIC (anual)", "eco_selic_anual.csv")
        if ipca_col:
            a = econ.groupby("year")[ipca_col[0]].sum().reset_index()
            fig = px.bar(a, x="year", y=ipca_col[0], title="IPCA acumulado anual (%)")
            fig = style_fig(fig); ca2.plotly_chart(fig, use_container_width=True)
            df_download_button(a, "⬇️ CSV IPCA (anual)", "eco_ipca_anual.csv")
        if inad_col:
            a = econ.groupby("year")[inad_col[0]].mean().reset_index()
            fig = px.bar(a, x="year", y=inad_col[0], title="Inadimplência média anual (%)")
            fig = style_fig(fig); ca3.plotly_chart(fig, use_container_width=True)
            df_download_button(a, "⬇️ CSV Inadimplência (anual)", "eco_inad_anual.csv")

def page_mapa(tx, stores):
    top_header()
    hero("🗺️ Mapa", "OpenStreetMap — lojas e cupons (tipo, valor, data, cupom)")

    dtx, getx = normcols(tx)
    dst, gets = normcols(stores)

    # Define colunas de loja
    lcol_st = gets("nome_loja","loja","store","parceiro","merchant")
    lcol_tx = getx("nome_loja","loja","store","parceiro","merchant")

    # Encontra coordenadas
    dst, lat_st, lon_st = ensure_lat_lon(dst, gets)
    dtx, lat_tx, lon_tx = ensure_lat_lon(dtx, getx)

    # Flags de disponibilidade
    has_store_coords = (lat_st and lon_st and not dst.empty and lat_st in dst.columns and lon_st in dst.columns and not dst[[lat_st,lon_st]].dropna().empty)
    has_tx_coords    = (lat_tx and lon_tx and not dtx.empty and lat_tx in dtx.columns and lon_tx in dtx.columns and not dtx[[lat_tx,lon_tx]].dropna().empty)

    M = None
    lat_col = lon_col = loc_col = None

    if has_store_coords and lcol_st and lcol_tx and (lcol_st in dst.columns) and (lcol_tx in dtx.columns):
        left = dtx.copy()
        right = dst[[lcol_st, lat_st, lon_st]].dropna().drop_duplicates().copy()
        left[lcol_tx] = left[lcol_tx].astype(str)
        right[lcol_st] = right[lcol_st].astype(str)
        M = left.merge(right, left_on=lcol_tx, right_on=lcol_st, how="left")
        lat_col, lon_col, loc_col = lat_st, lon_st, lcol_tx
    elif has_tx_coords and lcol_tx and (lcol_tx in dtx.columns):
        M = dtx.copy()
        lat_col, lon_col, loc_col = lat_tx, lon_tx, lcol_tx
    else:
        st.warning("Não foram encontradas coordenadas válidas em lojas.xlsx nem em transacoes.xlsx (local_captura).")
        return

    if M.dropna(subset=[lat_col, lon_col]).empty:
        st.warning("Sem coordenadas válidas para o mapa."); return

    M = M.dropna(subset=[lat_col, lon_col])

    # Centro do mapa
    center = [float(M[lat_col].astype(float).mean()), float(M[lon_col].astype(float).mean())]
    fmap = folium.Map(location=center, zoom_start=12, tiles="OpenStreetMap")

    tipo = getx("tipo_cupom","tipo","categoria","segmento","classe")
    vcol = getx("valor_compra","valor","receita","amount","preco")
    dcol = getx("data","data_captura","dt","timestamp","created")
    cup  = getx("valor_cupom","cupom","codigo","id_cupom","cupom_id")

    def color_for(cat):
        if pd.isna(cat): return "blue"
        c = str(cat).lower()
        if "aliment" in c: return "green"
        if "moda" in c: return "purple"
        if "eletr" in c: return "orange"
        return "blue"

    sample = M if len(M) <= 2000 else M.sample(2000, random_state=42)
    for _, row in sample.iterrows():
        loja = row.get(loc_col)
        popup = f"<b>Loja:</b> {loja}<br>"
        if cup and cup in row.index and pd.notna(row[cup]): popup += f"<b>Cupom:</b> {row[cup]}<br>"
        if tipo and tipo in row.index and pd.notna(row[tipo]): popup += f"<b>Tipo:</b> {row[tipo]}<br>"
        if vcol and vcol in row.index and pd.notna(row[vcol]): popup += f"<b>Valor:</b> R$ {row[vcol]:,.2f}<br>"
        if dcol and dcol in row.index and pd.notna(row[dcol]): popup += f"<b>Data:</b> {row[dcol]}"
        try:
            folium.Marker(
                [float(row[lat_col]), float(row[lon_col])],
                tooltip=str(loja),
                popup=folium.Popup(popup, max_width=280),
                icon=folium.Icon(color=color_for(row.get(tipo)), icon="info-sign")
            ).add_to(fmap)
        except Exception:
            pass

    st_folium(fmap, height=560, width=None)

# ------------------------------------------------------------
# AUTH SCREENS
# ------------------------------------------------------------
def login_screen():
    safe_logo(width=72)
    st.markdown(
        """
        <div class="auth-card">
          <div class="auth-title">Entrar no PicMoney</div>
          <div class="auth-sub">Use seu e-mail e senha para acessar o dashboard.</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    with st.form("login", clear_on_submit=False):
        email = st.text_input("E-mail", placeholder="seuemail@gmail.com")
        st.caption("Ex.: seunome@gmail.com")
        pwd   = st.text_input("Senha", type="password", placeholder="mínimo de 6 caracteres")
        st.caption("Dica: utilize pelo menos 6 caracteres.")
        colA, colB = st.columns([1,1])
        ok = colA.form_submit_button("Entrar", use_container_width=True)
        to_signup = colB.form_submit_button("Criar conta", use_container_width=True)

    if to_signup:
        st.session_state.auth_mode = "signup"; st.rerun()

    if ok:
        if email and pwd and check_login(email, pwd):
            st.session_state.auth = True
            st.session_state.user_email = email
            st.session_state.page = "home"
            st.success("✅ Login realizado com sucesso!")
            st.rerun()
        else:
            st.error("❌ E-mail ou senha inválidos.")

def signup_screen():
    safe_logo(width=72)
    st.markdown(
        """
        <div class="auth-card">
          <div class="auth-title">Criar conta</div>
          <div class="auth-sub">Cadastre-se para começar a visualizar seus indicadores.</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    with st.form("signup"):
        nome  = st.text_input("Nome completo", placeholder="Seu nome e sobrenome")
        email = st.text_input("E-mail", placeholder="seuemail@gmail.com")
        st.caption("Ex.: seunome@gmail.com")
        pwd   = st.text_input("Senha", type="password", placeholder="mínimo de 6 caracteres")
        st.caption("Dica: pelo menos 6 caracteres.")
        pwd2  = st.text_input("Confirmar senha", type="password", placeholder="repita a senha")
        ok = st.form_submit_button("Cadastrar", use_container_width=True)

    if st.button("Já tem conta? Ir para Login", use_container_width=True):
        st.session_state.auth_mode = "login"; st.rerun()

    if ok:
        if not (nome and email and pwd and pwd2):
            st.warning("Preencha todos os campos.")
        elif len(pwd) < 6:
            st.warning("A senha deve ter pelo menos 6 caracteres.")
        elif pwd != pwd2:
            st.warning("As senhas não conferem.")
        elif email_exists(load_users(), email):
            st.error("Este e-mail já está cadastrado.")
        else:
            save_user(nome, email, pwd)
            st.success("✅ Cadastro realizado! Agora faça login.")
            st.session_state.auth_mode = "login"; st.rerun()

# ------------------------------------------------------------
# APP STATE + ROUTER
# ------------------------------------------------------------
if "auth" not in st.session_state: st.session_state.auth = False
if "auth_mode" not in st.session_state: st.session_state.auth_mode = "login"
if "user_email" not in st.session_state: st.session_state.user_email = None
if "page" not in st.session_state: st.session_state.page = "home"

def main():
    if not st.session_state.auth:
        if st.session_state.auth_mode == "login":
            login_screen()
        else:
            signup_screen()
    else:
        tx = load_xlsx(PATH_TX)
        stores = load_xlsx(PATH_STORES)
        sidebar_nav()
        page = st.session_state.get("page","home")
        if page == "home": page_home(tx, stores)
        elif page == "kpis": page_kpis(tx)
        elif page == "mapa": page_mapa(tx, stores)
        elif page == "fin": page_financeiro(tx)
        elif page == "eco": page_eco()
        elif page == "login": st.success("Você já está logada. Use o menu para navegar.")

if __name__ == "__main__":
    main()
