import base64
import html
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium import plugins as folium_plugins
from streamlit_folium import st_folium

from backend.data_processing import load_data, clean_data, normalize_data
from backend.index_calculation import calculate_priority_index
from backend.clustering import apply_clustering
from backend.recommendation import generate_recommendation
from backend.early_warning import assess_early_warning
from backend.scheme_advisor import recommend_schemes
from backend.corporator_outreach import (load_directory, find_representative, notification_text, send_email, log_notification)
from backend.account_auth import create_account, authenticate, ensure_demo_accounts
from backend.corporator_lookup import search_representative
from ai_development_recommendations import render_ai_development_recommendations


# ═══════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════
_ICON = "assets/vikas_drishti_logo.png" if Path("assets/vikas_drishti_logo.png").exists() else "assets/vikas_logo.png"
st.set_page_config(
    page_title="Vikas Drishti",
    page_icon=_ICON,
    layout="wide",
    initial_sidebar_state="auto"
)


# ═══════════════════════════════════════════════════
# CSS INJECTION (shared)
# ═══════════════════════════════════════════════════
def load_css():
    try:
        with open("assets/style.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

load_css()


@st.cache_data(show_spinner=False)
def logo_uri():
    """Brand mark as an inline data URI so it renders inside custom HTML."""
    path = Path("assets/vikas_drishti_logo.svg")
    if path.exists():
        return "data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode()
    path = Path("assets/vikas_logo.png")
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


# ═══════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "users" not in st.session_state:
    st.session_state["users"] = {}
if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = False
if "user_role" not in st.session_state:
    st.session_state["user_role"] = ""


# ═══════════════════════════════════════════════════
# SHARED DESIGN CONSTANTS
# ═══════════════════════════════════════════════════
CARTO_ATTR = '&copy; OpenStreetMap contributors &copy; CARTO'
RISK_ORDER = ["Critical", "High", "Medium", "Low"]
RISK_COLORS = {"Critical": "#B42318", "High": "#EA580C", "Medium": "#CA8A04", "Low": "#15803D"}
# Cluster labels come from backend/clustering.py, ordered from most to least deprived.
CLUSTER_ORDER = ["Critical service gaps", "High service gaps", "Moderate service gaps", "Relatively better-served", "Insufficient data for grouping"]
CLUSTER_COLORS = {
    "Critical service gaps": "#8E2457",
    "High service gaps": "#D9622B",
    "Moderate service gaps": "#D4A017",
    "Relatively better-served": "#1B8A6B",
    "Insufficient data for grouping": "#6B7C93",
}
NAV_ICONS = {
    "Dashboard": "dashboard",
    "Smart Priority Scoring": "speed",
    "Advanced Analytics": "analytics",
    "ML Clustering": "hub",
    "GIS Map": "map",
    "AI Recommendations": "auto_awesome",
    "Scheme & Corporator Action": "account_balance",
    "Early Warning System": "warning",
}
PAGE_SUBTITLES = {
    "Smart Priority Scoring": "Transparent 0–100 urgency score for every area, built from its infrastructure indicators.",
    "Advanced Analytics": "Compare priority scores, risk distribution and the relationship with population.",
    "ML Clustering": "K-means groups areas with similar service profiles so interventions can be planned together.",
    "GIS Map": "Where each area is, coloured by its priority risk level.",
    "AI Recommendations": "Dataset-based development recommendations, plus an AI concept view and budget estimate for a site photo.",
    "Scheme & Corporator Action": "Match identified gaps to government scheme pathways and notify the ward representative.",
    "Early Warning System": "Threshold-based assessment of rainfall, drainage, flood history and heat.",
}
ICON_SVG = {
    "areas": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18M5 21V9l7-5 7 5v12M9 21v-6h6v6"/></svg>',
    "alert": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 2 20h20L12 3zM12 10v5M12 18h.01"/></svg>',
    "score": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>',
    "top": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4zM17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3"/></svg>',
}


# ═══════════════════════════════════════════════════
# LOGIN STYLES (injected only when needed)
# ═══════════════════════════════════════════════════
def inject_login_styles():
    """Page-level overrides for the sign-in screen. Component styling lives in assets/style.css."""
    st.markdown("""
    <style>
    [data-testid="stHeader"], footer, [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display:none !important;}
    .stApp { background: radial-gradient(1200px 500px at 85% -10%, #DCEBF5 0%, transparent 60%), #EEF3F8 !important; }
    .block-container { max-width: 1200px !important; padding-top: 1.2rem !important; }
    </style>
    """, unsafe_allow_html=True)


def chart_theme():
    if st.session_state.get("dark_mode", False):
        return {
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font_color": "#C9D6E6",
            "title_font_color": "#F1F5FA",
            "gridcolor": "#26384F",
            "legend_font_color": "#C9D6E6",
        }
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font_color": "#3B4F68",
        "title_font_color": "#0B2545",
        "gridcolor": "#E3E9F0",
        "legend_font_color": "#3B4F68",
    }


def apply_chart_layout(fig, theme):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor=theme["paper_bgcolor"],
        plot_bgcolor=theme["plot_bgcolor"],
        font=dict(family="Inter, -apple-system, Segoe UI, sans-serif", size=13, color=theme["font_color"]),
        title_font=dict(size=16, color=theme["title_font_color"]),
        title_x=0.01,
        margin=dict(l=16, r=16, t=56, b=16),
        hoverlabel=dict(font_size=13, font_family="Inter, sans-serif"),
        legend=dict(font=dict(color=theme["legend_font_color"]), title_text="",
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(gridcolor=theme["gridcolor"], gridwidth=0.5, zerolinecolor=theme["gridcolor"], linecolor=theme["gridcolor"])
    fig.update_yaxes(gridcolor=theme["gridcolor"], gridwidth=0.5, zerolinecolor=theme["gridcolor"], linecolor=theme["gridcolor"])
    return fig


# ═══════════════════════════════════════════════════
# DASHBOARD THEME INJECTION (light is the default token set in style.css)
# ═══════════════════════════════════════════════════
def inject_dashboard_theme():
    if not st.session_state.get("dark_mode", False):
        return
    st.markdown("""
    <style>
    :root {
      --bg:#0A1220; --surface:#111C2E; --surface-2:#16253A; --ink:#E8EEF6; --ink-2:#B6C3D4; --muted:#8497AE;
      --line:#243349; --brand:#2BB3BE; --brand-strong:#1E9AA5; --brand-soft:rgba(43,179,190,.14);
      --sidebar-bg:#08101D; --sidebar-line:#1A2B44; --field-bg:#0E1827; --input-line:#2B3F5A;
      --risk-critical:#F0605A; --risk-high:#F58B4C; --risk-medium:#E5B53B; --risk-low:#3DB46D;
      --shadow:0 1px 2px rgba(0,0,0,.4), 0 6px 18px rgba(0,0,0,.28);
    }
    .stApp { background: var(--bg) !important; color: var(--ink); }
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stHeader"] * { color: var(--ink-2) !important; }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5 { color: var(--ink) !important; }
    .stApp [data-testid="stMarkdownContainer"] p, .stApp [data-testid="stMarkdownContainer"] li,
    .stApp [data-testid="stWidgetLabel"] p, .stApp label, .stApp [data-testid="stCheckbox"] p { color: var(--ink-2) !important; }
    .stApp [data-testid="stCaptionContainer"] { color: var(--muted) !important; }
    .stApp input, .stApp textarea { color: var(--ink) !important; -webkit-text-fill-color: var(--ink) !important; background: transparent !important; }
    .stApp [data-baseweb="select"] * { color: var(--ink) !important; }
    .stApp [data-baseweb="tag"] { background: #1E3350 !important; }
    [data-baseweb="popover"] > div, [data-baseweb="popover"] [role="listbox"], [data-baseweb="popover"] ul { background: #111C2E !important; border-color: #2B3F5A !important; }
    [data-baseweb="popover"] li:hover { background: #1B2D47 !important; }
    [data-testid="stFileUploaderDropzone"] { background: #0E1827 !important; border-color: #3A5780 !important; }
    [data-testid="stMain"] [data-testid="stFileUploaderDropzone"] * { color: var(--ink-2) !important; }
    [data-testid="stMain"] [data-testid="stFileUploaderDropzone"] button { background: #1B2D47 !important; border-color: #3A5780 !important; }
    .stApp .stButton button, .stApp .stDownloadButton button { background: #16253A; color: var(--ink); border-color: #2B3F5A; }
    .stApp .stButton button[kind="primary"] { background: var(--brand); color: #04222A; border-color: var(--brand); }
    .stApp .stButton button[kind="primary"] p { color: #04222A !important; }
    .stApp .stButton button p, .stApp .stDownloadButton button p { color: inherit; }
    [data-testid="stSidebar"] .stButton button { background: transparent; color: #fff; border-color: #3A5780; }
    [data-testid="stDataFrame"] { filter: invert(0.92) hue-rotate(180deg); border-color: transparent; }
    [data-testid="stExpander"] { background: var(--surface) !important; }
    .stApp [data-testid="stAlert"] { background: #16253A !important; }
    .stApp [data-testid="stAlert"] * { color: var(--ink) !important; }
    .stTabs [data-baseweb="tab"] { color: var(--muted); }
    .metric-card, .cluster-card, .vd-panel, .vd-note, .alert-card { background: var(--surface); }
    .header-box { background: linear-gradient(120deg, #0A1B34 0%, #0F3A6B 60%, #0B6672 130%); border: 1px solid var(--line); }
    .stApp [data-testid="stMetricValue"] { color: var(--ink) !important; }
    </style>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════
# SMALL UI HELPERS
# ═══════════════════════════════════════════════════
def page_header(title, subtitle="", chip=""):
    chip_html = f'<span class="vd-chip">{html.escape(chip)}</span>' if chip else ""
    sub_html = f'<div class="vd-page-sub">{html.escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f'<div class="vd-page-head"><div><h1 class="vd-page-title">{html.escape(title)}</h1>{sub_html}</div>{chip_html}</div>',
        unsafe_allow_html=True,
    )


def section_title(text, hint=""):
    hint_html = f"<small>{html.escape(hint)}</small>" if hint else ""
    st.markdown(f'<div class="vd-section">{html.escape(text)} {hint_html}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════
# LOGIN PAGE (one common sign-in for every role)
# ═══════════════════════════════════════════════════
def login_page():
    """Public entry screen with both sign-in and account creation; no email verification."""
    inject_login_styles()
    ensure_demo_accounts()
    feat_icons = {
        "score": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
        "cluster": '<circle cx="6" cy="7" r="3"/><circle cx="18" cy="8" r="3"/><circle cx="12" cy="18" r="3"/>',
        "map": '<path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
        "scheme": '<path d="M3 10 12 4l9 6M5 10v8M9 10v8M15 10v8M19 10v8M3 21h18"/>',
    }
    def feat(icon, title, desc):
        return f'<li><i><svg viewBox="0 0 24 24">{feat_icons[icon]}</svg></i><span><b>{title}</b><em>{desc}</em></span></li>'

    with st.container(key="vd_login_shell"):
        left, right = st.columns([1.05, 0.95], gap="small")
        with left:
            with st.container(key="vd_login_left"):
                st.markdown(f"""
                <div class="vd-login-brand"><img src="{logo_uri()}" alt="Vikas Drishti logo"/>
                  <div><div class="n">VIKAS DRISHTI</div><div class="t">Monitor · Prioritize · Build a Better Tomorrow</div></div></div>
                <div class="vd-login-pitch">Know which neighbourhoods need help first.</div>
                <div class="vd-login-lead">Vikas Drishti turns area-level data into a ranked, explainable plan for slum development, shared by officers, NGOs and analysts.</div>
                <ul class="vd-feat">{feat("score", "Priority scoring", "A 0–100 score for every area, with the reasons behind it")}{feat("cluster", "Clustering", "Groups areas with similar service gaps")}{feat("map", "GIS map", "See every area and its risk level on the map")}{feat("scheme", "Schemes and ward action", "Match gaps to government schemes and alert the corporator")}</ul>
                <div class="vd-login-foot">Development Monitoring &amp; Decision Support · © 2026</div>
                """, unsafe_allow_html=True)
        with right:
            with st.container(key="vd_login_right"):
                st.markdown('<div class="vd-login-title">Welcome to Vikas Drishti</div><div class="vd-login-sub">Sign in to your account or create a new account to continue.</div>', unsafe_allow_html=True)
                tab_login, tab_signup = st.tabs(["Sign in", "Create account"])
                with tab_login:
                    with st.form("signin_form", clear_on_submit=False):
                        login_username = st.text_input("Username", key="login_username")
                        login_password = st.text_input("Password", type="password", key="login_password")
                        sign_in = st.form_submit_button("Sign in", type="primary", width="stretch")
                    if sign_in:
                        ok, msg, account = authenticate(login_username, login_password)
                        if ok and account:
                            st.session_state["logged_in"] = True
                            st.session_state["username"] = account["username"]
                            st.session_state["user_role"] = account["role"]
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                with tab_signup:
                    with st.form("signup_form", clear_on_submit=False):
                        new_user = st.text_input("Choose username", key="signup_username")
                        new_password = st.text_input("Create password (minimum 8 characters)", type="password", key="signup_password")
                        confirm_password = st.text_input("Confirm password", type="password", key="signup_confirm_password")
                        contact_type = st.radio("Contact type", ["Email", "Phone"], horizontal=True, key="signup_contact_type")
                        contact = st.text_input("Email address" if contact_type == "Email" else "Phone number", placeholder="name@example.com" if contact_type == "Email" else "+919876543210", key="signup_contact")
                        create = st.form_submit_button("Create account", type="primary", width="stretch")
                    if create:
                        if new_password != confirm_password:
                            st.error("Passwords do not match.")
                        else:
                            ok, msg = create_account(new_user, new_password, contact, contact_type)
                            if ok:
                                st.success(msg + " You are now signed in.")
                                st.session_state["logged_in"] = True
                                st.session_state["username"] = new_user.strip()
                                st.session_state["user_role"] = "Data Analyst & Viewer"
                                st.rerun()
                            else:
                                st.error(msg)
                st.caption("New accounts are activated immediately. No email verification or OTP is required. Self-registered accounts receive the Data Analyst & Viewer role.")
                with st.expander("Demo login credentials (for evaluation)"):
                    st.warning("These are public demo credentials. Change or remove them before deploying the application publicly.")
                    st.table(pd.DataFrame([
                        {"Role": "Administrator", "Username": "admin", "Password": "Admin@123"},
                        {"Role": "Administrator", "Username": "administrator", "Password": "Admin@123"},
                        {"Role": "Viewer", "Username": "viewer", "Password": "Viewer@123"},
                        {"Role": "NGO", "Username": "ngo", "Password": "Ngo@123"},
                        {"Role": "Data Analyst", "Username": "dataanalyst", "Password": "Analyst@123"},
                    ])
                    )


if not st.session_state["logged_in"]:
    login_page()
    st.stop()


# ═══════════════════════════════════════════════════
# DASHBOARD — INTEGRATED CONTROL PANEL
# ═══════════════════════════════════════════════════
inject_dashboard_theme()

# Sidebar navigation and user controls
role = st.session_state.get("user_role", "Viewer")
role_pages = {
    "Administrator": ["Dashboard", "Smart Priority Scoring", "Advanced Analytics", "ML Clustering", "GIS Map", "AI Recommendations", "Scheme & Corporator Action", "Early Warning System"],
    "Government Officer": ["Dashboard", "Smart Priority Scoring", "GIS Map", "AI Recommendations", "Scheme & Corporator Action", "Early Warning System"],
    "NGO": ["Dashboard", "Smart Priority Scoring", "GIS Map", "AI Recommendations", "Scheme & Corporator Action"],
    "Data Analyst & Viewer": ["Dashboard", "Smart Priority Scoring", "Advanced Analytics", "ML Clustering", "GIS Map", "AI Recommendations", "Scheme & Corporator Action"],
    "Data Analyst": ["Dashboard", "Smart Priority Scoring", "Advanced Analytics", "ML Clustering", "GIS Map", "AI Recommendations", "Scheme & Corporator Action"],
    "Viewer": ["Dashboard", "Smart Priority Scoring", "Advanced Analytics", "ML Clustering", "GIS Map", "AI Recommendations", "Scheme & Corporator Action"],
}
with st.sidebar:
    st.markdown(f"""
    <div class="vd-brand"><img src="{logo_uri()}" alt=""/><div><div class="vd-brand-name">Vikas Drishti</div><div class="vd-brand-tag">Development decision support</div></div></div>
    <div class="vd-user"><div class="vd-avatar">{html.escape(st.session_state['username'][:1] or '?')}</div>
      <div><div class="vd-user-name">{html.escape(st.session_state['username'])}</div><div class="vd-user-role">{html.escape(role)}</div></div></div>
    """, unsafe_allow_html=True)
    st.divider()
    st.markdown('<div class="vd-nav-title">NAVIGATION</div>', unsafe_allow_html=True)
    available_pages = role_pages.get(role, role_pages["Viewer"])
    page = st.radio("NAVIGATION", available_pages, key="main_navigation",
                    format_func=lambda p: f":material/{NAV_ICONS.get(p, 'chevron_right')}: {p}")
    st.divider()
    uploaded_file = st.file_uploader("Upload slum dataset (CSV)", type=["csv"], help="Upload your area-level development dataset.")
    corporator_file = st.file_uploader("Upload verified corporator directory (CSV)", type=["csv"], help="Columns: Area, Ward, Corporator_Name, Email, Phone, Municipal_Body")
    dark_mode = st.toggle("Dark mode", value=st.session_state.get("dark_mode", False), key="dark_mode_toggle")
    if dark_mode != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode
        st.rerun()
    if st.button("Logout", width="stretch", icon=":material/logout:"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["user_role"] = ""
        st.rerun()


# ═══════════════════════════════════════════════════
# DATA LOADING & PROCESSING
# ═══════════════════════════════════════════════════
try:
    with st.spinner("Processing area data…"):
        df = load_data(uploaded_file)
        df = clean_data(df)
        original_df = df.copy()
        df = normalize_data(df)
        df = calculate_priority_index(df)
        df = apply_clustering(df)
        df["Recommendation"] = df.apply(generate_recommendation, axis=1)
        df["Scheme_Matches"] = df.apply(lambda row: recommend_schemes(row), axis=1)
except Exception as e:
    st.error("Something went wrong while processing the dataset.")
    st.caption(f"Traceback: {e}")
    st.stop()


theme = chart_theme()
dark = st.session_state.get("dark_mode", False)
risk_colors = RISK_COLORS if not dark else {"Critical": "#F0605A", "High": "#F58B4C", "Medium": "#E5B53B", "Low": "#3DB46D"}
dataset_name = uploaded_file.name if uploaded_file is not None else "Sample dataset"

if page != "Dashboard":
    page_header(page, PAGE_SUBTITLES.get(page, ""), chip=role)


# ═══════════════════════════════════════════════════
# PAGES
# ═══════════════════════════════════════════════════
if page == "Dashboard":
    st.markdown(f"""
    <div class="header-box">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:20px;">
            <div style="position:relative;z-index:1">
                <h1>Vikas Drishti</h1>
                <p>Smart slum development priority index: see which areas need attention first and what to do about it.</p>
            </div>
            <div class="header-stat">
                <div class="k">Dataset</div>
                <div class="v">{len(df):,} areas · {html.escape(dataset_name)}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    high_risk = len(df[df["Risk_Level"].isin(["Critical", "High"])])
    avg_score = round(df["Priority_Score"].mean(), 2)
    max_score = df["Priority_Score"].max()
    top_area = str(df.iloc[0]["Area"])
    total_pop = int(df["Population"].sum())
    share = (high_risk / len(df) * 100) if len(df) else 0
    kpis = [
        ("Total areas", f"{len(df):,}", f"{total_pop:,} residents in the dataset", "#0E7C86", "areas"),
        ("Critical / High priority areas", f"{high_risk:,}", f"{share:.0f}% of areas need early action", "#B42318", "alert"),
        ("Average priority score", f"{avg_score}", "Composite index, 0–100", "#CA8A04", "score"),
        ("Highest score", f"{max_score}", f"Top priority: {html.escape(top_area)}", "#12447A", "top"),
    ]
    cards = "".join(
        f'<div class="metric-card" style="--kpi:{c}"><div class="metric-top"><div class="metric-label">{l}</div><div class="metric-icon">{ICON_SVG[i]}</div></div>'
        f'<div class="metric-value">{v}</div><div class="metric-delta">{d}</div></div>'
        for l, v, d, c, i in kpis
    )
    st.markdown(f'<div class="kpi-grid">{cards}</div>', unsafe_allow_html=True)

    ch1, ch2 = st.columns([1, 1.4])
    with ch1:
        counts_df = df["Risk_Level"].value_counts().reindex(RISK_ORDER).dropna().reset_index()
        counts_df.columns = ["Risk_Level", "Areas"]
        fig_d = px.pie(counts_df, names="Risk_Level", values="Areas", hole=0.58, title="Areas by risk level",
                       color="Risk_Level", color_discrete_map=risk_colors, category_orders={"Risk_Level": RISK_ORDER})
        fig_d.update_traces(sort=False, textinfo="value", textfont_size=14, marker=dict(line=dict(color="rgba(0,0,0,0)", width=0)),
                            hovertemplate="%{label}: %{value} areas (%{percent})<extra></extra>")
        fig_d.update_layout(height=320, annotations=[dict(text=f"<b>{len(df)}</b><br>areas", x=0.5, y=0.5, showarrow=False, font=dict(size=16, color=theme["title_font_color"]))])
        st.plotly_chart(apply_chart_layout(fig_d, theme), width="stretch", config={"displayModeBar": False})
    with ch2:
        top5 = df.nlargest(5, "Priority_Score").sort_values("Priority_Score")
        fig_t = px.bar(top5, x="Priority_Score", y="Area", orientation="h", color="Risk_Level", title="Five highest-priority areas",
                       color_discrete_map=risk_colors, category_orders={"Risk_Level": RISK_ORDER}, text="Priority_Score",
                       labels={"Priority_Score": "Priority score (0–100)", "Area": ""})
        fig_t.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
        fig_t.update_xaxes(range=[0, 110])
        fig_t.update_layout(height=320)
        st.plotly_chart(apply_chart_layout(fig_t, theme), width="stretch", config={"displayModeBar": False})

    section_title("Area priority ranking", "Search by name; sort any column")
    search_area = st.text_input(
        "Search area",
        placeholder="Search by area name…",
        label_visibility="collapsed"
    )
    display_df = df.copy()
    if search_area:
        display_df = display_df[display_df["Area"].str.contains(search_area, case=False, na=False)]
    st.dataframe(
        display_df[["Rank", "Area", "Population", "Priority_Score", "Risk_Level", "Cluster", "Cluster_Label"]],
        width="stretch",
        height=min(450, 60 + 36 * max(len(display_df), 1)),
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", width="small"),
            "Area": st.column_config.TextColumn("Area name", width="medium"),
            "Population": st.column_config.NumberColumn("Population", format="%d", width="medium"),
            "Priority_Score": st.column_config.ProgressColumn("Priority score", format="%.2f", min_value=0, max_value=100, width="medium"),
            "Risk_Level": st.column_config.TextColumn("Risk level", width="small"),
            "Cluster": st.column_config.NumberColumn("Cluster", width="small"),
            "Cluster_Label": st.column_config.TextColumn("Cluster profile", width="medium"),
        }
    )
    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download processed report",
        data=csv,
        file_name="vikas_drishti_processed_report.csv",
        mime="text/csv",
        icon=":material/download:",
    )

elif page == "Smart Priority Scoring":
    c1, c2, c3, c4 = st.columns(4)
    counts = df["Risk_Level"].value_counts()
    for col, label in zip([c1, c2, c3, c4], RISK_ORDER):
        col.metric(label, int(counts.get(label, 0)))
    section_title("Score by area")
    score_view = df[[c for c in ["Rank", "Area", "Population", "Housing", "Water", "Sanitation", "Roads", "Drainage", "Priority_Score", "Risk_Level"] if c in df.columns]].copy()
    st.dataframe(score_view, width="stretch", hide_index=True, column_config={
        "Priority_Score": st.column_config.ProgressColumn("Priority score", format="%.2f", min_value=0, max_value=100),
        "Population": st.column_config.NumberColumn("Population", format="%d"),
    })
    fig_priority = px.bar(df.sort_values("Priority_Score", ascending=True), x="Priority_Score", y="Area", color="Risk_Level", orientation="h",
                          title="Area-wise development priority (0–100)", color_discrete_map=risk_colors,
                          category_orders={"Risk_Level": RISK_ORDER}, text="Priority_Score",
                          labels={"Priority_Score": "Priority score (0–100)", "Area": "", "Risk_Level": "Risk level"})
    fig_priority.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
    fig_priority.update_xaxes(range=[0, 112])
    st.plotly_chart(apply_chart_layout(fig_priority, theme), width="stretch")
    with st.expander("How is the score calculated?"):
        st.markdown("""The score combines normalized infrastructure indicators. Poor water, sanitation, housing, roads and drainage conditions increase urgency. Crime risk also increases urgency. The result is scaled to 0–100 and classified as **Critical (80–100), High (60–79.99), Medium (40–59.99), or Low (0–39.99)**. Scores are relative to the dataset supplied and should be verified by field officers.""")

elif page == "Advanced Analytics":
    a1, a2 = st.columns([2, 1])
    with a1:
        fig_bar = px.bar(
            df, x="Area", y="Priority_Score", color="Risk_Level",
            title="Priority score by area", text="Priority_Score",
            color_discrete_map=risk_colors, category_orders={"Risk_Level": RISK_ORDER},
            labels={"Priority_Score": "Priority score (0–100)", "Risk_Level": "Risk level"}
        )
        fig_bar.update_traces(textposition="outside", texttemplate="%{text:.2f}", cliponaxis=False)
        fig_bar.update_yaxes(range=[0, 115])
        fig_bar = apply_chart_layout(fig_bar, theme)
        st.plotly_chart(fig_bar, width="stretch", config={"displayModeBar": False})
    with a2:
        fig_pie = px.pie(
            df, names="Risk_Level", title="Risk distribution", hole=0.55,
            color="Risk_Level", color_discrete_map=risk_colors, category_orders={"Risk_Level": RISK_ORDER}
        )
        fig_pie.update_traces(sort=False, textposition="inside", textinfo="percent+label",
                              hovertemplate="%{label}: %{value} areas (%{percent})<extra></extra>")
        fig_pie.update_layout(showlegend=False)
        fig_pie = apply_chart_layout(fig_pie, theme)
        fig_pie.update_layout(showlegend=False)
        st.plotly_chart(fig_pie, width="stretch", config={"displayModeBar": False})
    fig_scatter = px.scatter(
        df, x="Population", y="Priority_Score", color="Risk_Level",
        size="Priority_Score", hover_name="Area", size_max=34,
        title="Population vs priority score",
        color_discrete_map=risk_colors, category_orders={"Risk_Level": RISK_ORDER},
        labels={"Priority_Score": "Priority score (0–100)", "Risk_Level": "Risk level"}
    )
    fig_scatter.update_traces(marker=dict(line=dict(width=1.5, color="rgba(255,255,255,.9)"), opacity=.9))
    fig_scatter = apply_chart_layout(fig_scatter, theme)
    st.plotly_chart(fig_scatter, width="stretch", config={"displayModeBar": False})

elif page == "ML Clustering":
    st.caption("K-means groups locations using all available service indicators. Service scores are treated as better when higher; Crime is treated as risk severity. Cluster IDs are ordered from greatest to least deprivation.")
    cluster_counts = df.groupby(["Cluster", "Cluster_Label"], as_index=False).agg(
        Areas=("Area", "count"), Population=("Population", "sum"), Mean_Priority=("Priority_Score", "mean")).sort_values("Cluster")
    cards = "".join(
        f'<div class="cluster-card" style="--cc:{CLUSTER_COLORS.get(item["Cluster_Label"], "#0E7C86")}">'
        f'<div class="t"><span class="sw"></span>Cluster {int(item["Cluster"])} · {html.escape(str(item["Cluster_Label"]))}</div>'
        f'<div class="n">{int(item["Areas"])} {"area" if int(item["Areas"]) == 1 else "areas"}</div>'
        f'<div class="m">{int(item["Population"]):,} people<br>Average priority score {item["Mean_Priority"]:.1f}</div></div>'
        for _, item in cluster_counts.iterrows()
    )
    st.markdown(f'<div class="cluster-grid">{cards}</div>', unsafe_allow_html=True)

    available_axes = [c for c in ["Sanitation", "Water", "Healthcare", "Housing", "Roads", "Drainage"] if c in df.columns]
    plot_df = df.copy()
    for axis in available_axes:
        plot_df[axis] = plot_df[axis] * 100
    axis_labels = {a: f"{a} score (0–100)" for a in available_axes}
    axis_labels.update({"Cluster_Label": "Cluster profile", "Priority_Score": "Priority score", "Risk_Level": "Risk level"})
    cmap = {k: v for k, v in CLUSTER_COLORS.items()}
    if len(available_axes) >= 3:
        fig_cluster = px.scatter_3d(plot_df, x=available_axes[0], y=available_axes[1], z=available_axes[2],
            color="Cluster_Label", size="Priority_Score", hover_name="Area", hover_data={"Population": ":,", "Risk_Level": True, "Priority_Score": ":.1f"},
            title="3D development cluster map · service scores out of 100",
            color_discrete_map=cmap, category_orders={"Cluster_Label": CLUSTER_ORDER}, labels=axis_labels, size_max=26)
        fig_cluster.update_traces(marker=dict(line=dict(width=1, color="rgba(255,255,255,.85)"), opacity=.95))
        fig_cluster.update_layout(scene_camera=dict(eye=dict(x=1.25, y=1.25, z=0.85)), scene=dict(
            xaxis=dict(range=[0, 100], backgroundcolor="rgba(0,0,0,0)", gridcolor=theme["gridcolor"]),
            yaxis=dict(range=[0, 100], backgroundcolor="rgba(0,0,0,0)", gridcolor=theme["gridcolor"]),
            zaxis=dict(range=[0, 100], backgroundcolor="rgba(0,0,0,0)", gridcolor=theme["gridcolor"]),
        ))
    else:
        x_axis, y_axis = (available_axes + ["Priority_Score", "Population"])[:2]
        fig_cluster = px.scatter(plot_df, x=x_axis, y=y_axis, color="Cluster_Label", size="Priority_Score",
            hover_name="Area", title="Development cluster map", color_discrete_map=cmap,
            category_orders={"Cluster_Label": CLUSTER_ORDER}, labels=axis_labels, size_max=26)
    fig_cluster = apply_chart_layout(fig_cluster, theme)
    fig_cluster.update_layout(height=640, margin=dict(l=10, r=10, t=96, b=40), title_y=0.97,
                              legend=dict(orientation="h", x=0, xanchor="left", y=0.93, yanchor="top", title_text=""))
    st.plotly_chart(fig_cluster, width="stretch", config={"displayModeBar": True, "scrollZoom": True})

    if {"Latitude", "Longitude"}.issubset(df.columns) and df[["Latitude", "Longitude"]].notna().all(axis=1).any():
        geo = df.dropna(subset=["Latitude", "Longitude"]).copy()
        lat_span = max(geo["Latitude"].max() - geo["Latitude"].min(), 0.005)
        lon_span = max(geo["Longitude"].max() - geo["Longitude"].min(), 0.005)
        zoom = max(3, min(14, 8.2 - 1.45 * float(__import__("math").log2(max(lat_span, lon_span, 0.01) * 10))))
        fig_geo = px.scatter_map(
            geo, lat="Latitude", lon="Longitude", color="Cluster_Label", size="Population", size_max=30,
            hover_name="Area", hover_data={"Latitude": False, "Longitude": False, "Population": ":,", "Priority_Score": ":.1f", "Risk_Level": True},
            color_discrete_map=cmap, category_orders={"Cluster_Label": CLUSTER_ORDER},
            labels={"Cluster_Label": "Cluster profile", "Priority_Score": "Priority score", "Risk_Level": "Risk level"},
            map_style="carto-darkmatter" if dark else "carto-positron", zoom=zoom,
            center=dict(lat=float(geo["Latitude"].mean()), lon=float(geo["Longitude"].mean())),
            title="Where each cluster is · bubble size shows population")
        fig_geo = apply_chart_layout(fig_geo, theme)
        fig_geo.update_layout(height=520, margin=dict(l=0, r=0, t=90, b=0), title_y=0.97,
                              legend=dict(orientation="h", x=0.01, xanchor="left", y=0.93, yanchor="top", title_text=""))
        st.plotly_chart(fig_geo, width="stretch", config={"scrollZoom": True})

    heat_features = [c for c in ["Sanitation", "Water", "Education", "Healthcare", "Electricity", "Housing", "Roads", "Drainage"] if c in df.columns]
    if heat_features:
        profile = (df.groupby(["Cluster", "Cluster_Label"])[heat_features].mean() * 100).reset_index().sort_values("Cluster")
        profile["Row"] = "Cluster " + profile["Cluster"].astype(int).astype(str) + " · " + profile["Cluster_Label"].astype(str)
        matrix = profile.set_index("Row")[heat_features]
        fig_heat = px.imshow(matrix, text_auto=".0f", aspect="auto", zmin=0, zmax=100,
                             color_continuous_scale="Teal", title="Average service score by cluster (0 = very poor, 100 = good)",
                             labels=dict(color="Score", x="Service", y=""))
        fig_heat.update_layout(height=120 + 70 * len(matrix), coloraxis_colorbar=dict(title="Score", thickness=12))
        fig_heat.update_xaxes(side="top")
        st.plotly_chart(apply_chart_layout(fig_heat, theme), width="stretch")
    section_title("Cluster membership")
    st.dataframe(df[["Area", "Population", "Cluster", "Cluster_Label", "Priority_Score", "Risk_Level"]], width="stretch", hide_index=True, column_config={
        "Priority_Score": st.column_config.ProgressColumn("Priority score", format="%.2f", min_value=0, max_value=100),
        "Population": st.column_config.NumberColumn("Population", format="%d"),
    })
    st.markdown("""
    <div class="vd-note"><b>How to read this.</b> Areas in the same cluster share comparable service conditions, so one intervention plan can often serve all of them. Clusters are numbered from the greatest to the least deprivation.</div>
    """, unsafe_allow_html=True)

elif page == "Scheme & Corporator Action":
    st.caption("Recommendations are explainable data matches, not a government eligibility approval. Verify current guidelines and beneficiary/land conditions with the relevant ULB.")
    directory = load_directory(corporator_file)
    st.download_button("Download corporator directory template", data=pd.read_csv("data/corporator_directory_template.csv").to_csv(index=False), file_name="corporator_directory_template.csv", mime="text/csv", icon=":material/download:")
    if directory.empty:
        st.warning("No verified corporator directory is configured. Upload the directory in the sidebar; the app will not guess elected representatives or invent contact details.")
    area_options = df["Area"].astype(str).tolist()
    selected_area = st.selectbox("Select an area", area_options, key="scheme_area_select")
    selected = df[df["Area"].astype(str) == selected_area].iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Priority score", f"{selected['Priority_Score']:.1f}/100")
    c2.metric("Risk", str(selected["Risk_Level"]))
    c3.metric("Cluster", str(selected.get("Cluster_Label", selected.get("Cluster", "—"))))
    section_title("Development needs identified from the data")
    st.info(str(selected["Recommendation"]))
    matches = recommend_schemes(selected)
    section_title("Recommended government scheme pathways")
    if matches:
        for match in matches:
            with st.expander(f"{match['scheme']} · {match['focus']}", expanded=True):
                st.write("**Data evidence:** " + "; ".join(match["evidence"]))
                st.write(match["detail"])
                st.caption("Implementing route: " + match["authority"])
                st.markdown(f"[Official scheme information]({match['url']})")
    else:
        st.info("No scheme pathway matched the available indicators. Add more complete area data or carry out a field assessment.")
    section_title("Corporator / ward representative")
    with st.expander("Find public corporator details online", expanded=directory.empty):
        lookup_city = st.text_input("City / municipal area", value="Bengaluru", key="corp_lookup_city")
        lookup_ward = st.text_input("Ward number or name (if known)", key="corp_lookup_ward")
        if st.button("Search public sources", type="primary", key="corp_search_button"):
            results, status = search_representative(selected_area, lookup_city, lookup_ward)
            st.session_state["corp_lookup_results"] = results
            st.session_state["corp_lookup_status"] = status
        if st.session_state.get("corp_lookup_status"):
            st.info(st.session_state["corp_lookup_status"])
        for item in st.session_state.get("corp_lookup_results", []):
            st.markdown(f"**{html.escape(item['title'])}**  ")
            st.write(item["snippet"])
            st.markdown(f"[Open source]({item['link']})")
        st.caption("Search results are only leads. Confirm identity, ward and contact details on an official municipal/election source before saving; the app will not invent or silently trust personal details.")
        with st.form("corp_save_form"):
            st.markdown("**Save officially verified details to the local directory**")
            verified_name = st.text_input("Corporator / councillor name")
            verified_ward = st.text_input("Ward")
            verified_email = st.text_input("Official public office email")
            verified_phone = st.text_input("Public office phone")
            verified_body = st.text_input("Municipal body", value=lookup_city)
            source_url = st.text_input("Official source URL used for verification")
            save_corp = st.form_submit_button("Save verified representative")
        if save_corp:
            if not verified_name.strip() or not source_url.strip().startswith("http"):
                st.error("Enter the representative name and an official source URL.")
            else:
                import csv
                Path("data").mkdir(exist_ok=True)
                save_path = Path("data/corporator_directory.csv")
                updated = directory.copy()
                updated = updated[updated["Area"].astype(str).str.casefold() != selected_area.casefold()]
                new_row = {"Area":selected_area,"Ward":verified_ward,"Corporator_Name":verified_name,"Email":verified_email,"Phone":verified_phone,"Municipal_Body":verified_body}
                updated = pd.concat([updated, pd.DataFrame([new_row])], ignore_index=True)
                updated.to_csv(save_path, index=False)
                st.success("Verified representative saved in data/corporator_directory.csv. Refresh the page to load the updated entry.")
    representative = find_representative(directory, selected_area)
    if representative:
        a, b, c = st.columns(3)
        a.write("**Name**\n" + (representative.get("Corporator_Name") or "Not supplied"))
        b.write("**Ward**\n" + (representative.get("Ward") or "Not supplied"))
        c.write("**Municipal body**\n" + (representative.get("Municipal_Body") or "Not supplied"))
        st.write("**Public office email:** " + (representative.get("Email") or "Not supplied"))
        st.write("**Public office phone:** " + (representative.get("Phone") or "Not supplied"))
    else:
        st.warning("No verified representative mapping found for this area. Add the area-to-ward mapping and publicly verified contact details to the directory CSV.")
    body = notification_text(selected_area, selected, representative or {}, matches)
    subject = f"Vikas Drishti area development alert – {selected_area}"
    section_title("Notification preview")
    message_key = f"corporator_message_preview_{selected_area}"  # per-area key so the text follows the selected area
    st.text_area("Message to corporator / ward office", value=body, height=260, key=message_key)
    recipient = (representative or {}).get("Email", "")
    if recipient:
        if st.button("Send notification to verified office email", type="primary", icon=":material/send:"):
            ok, message = send_email(recipient, subject, st.session_state.get(message_key, body))
            log_notification(selected_area, recipient, subject, "Sent" if ok else "Failed / not configured")
            (st.success if ok else st.error)(message)
    else:
        st.caption("Sending is disabled until a verified public office email is available.")
    st.download_button("Download notification draft", data=body, file_name=f"{selected_area.replace(' ', '_')}_corporator_notice.txt", mime="text/plain", icon=":material/download:")
    log_path = "data/corporator_notification_log.csv"
    if role == "Administrator" and __import__("os").path.exists(log_path):
        section_title("Notification delivery log")
        st.dataframe(pd.read_csv(log_path).tail(50), width="stretch", hide_index=True)

elif page == "GIS Map":
    if "Latitude" in original_df.columns and "Longitude" in original_df.columns:
        map_data = original_df.copy()
        map_data = map_data.dropna(subset=["Latitude", "Longitude"])
        if map_data.empty:
            st.warning("Latitude and Longitude values are empty after dropping missing coordinates.")
        else:
            risk_counts = df["Risk_Level"].value_counts()
            pills = "".join(
                f'<span class="badge" style="background:{RISK_COLORS[r]};margin-right:8px">{r}: {int(risk_counts.get(r, 0))}</span>' for r in RISK_ORDER
            )
            st.markdown(f'<div style="margin-bottom:12px">{pills}<span style="color:var(--muted);font-size:.85rem">{len(map_data)} areas with coordinates · use the layer control (top right) to switch base maps or hide risk levels</span></div>', unsafe_allow_html=True)
            center_lat = map_data["Latitude"].mean()
            center_lon = map_data["Longitude"].mean()
            google_map = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=12,
                tiles=None,
            )
            folium.TileLayer("https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google Maps", name="Google Maps").add_to(google_map)
            folium.TileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", attr=CARTO_ATTR, subdomains="abcd", name="Light map", show=False).add_to(google_map)
            folium.TileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr=CARTO_ATTR, subdomains="abcd", name="Dark map", show=False).add_to(google_map)
            folium.TileLayer("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", attr="Google Satellite", name="Satellite", show=False).add_to(google_map)
            groups = {r: folium.FeatureGroup(name=f"{r} risk", show=True) for r in RISK_ORDER}
            groups["Unknown"] = folium.FeatureGroup(name="Unknown risk", show=True)
            for _, row in map_data.iterrows():
                area_name = row["Area"] if "Area" in row else "Unknown Area"
                matched_row = df[df["Area"] == area_name]
                if not matched_row.empty:
                    risk_level = matched_row["Risk_Level"].values[0]
                    priority_score = matched_row["Priority_Score"].values[0]
                    cluster_label = matched_row["Cluster_Label"].values[0]
                else:
                    risk_level = "Unknown"
                    priority_score = "N/A"
                    cluster_label = "N/A"
                marker_color = (
                    "darkred" if risk_level == "Critical"
                    else "red" if risk_level == "High"
                    else "orange" if risk_level == "Medium"
                    else "green"
                )
                badge_color = RISK_COLORS.get(risk_level, "#6B7C93")
                pop_text = f"{int(row['Population']):,}" if "Population" in row and pd.notna(row["Population"]) else "N/A"
                popup_html = f"""
                <div style="font-family: Inter, 'Segoe UI', sans-serif; min-width: 220px;">
                    <div style="background:#0B2545;color:#fff;padding:10px 14px;border-radius:8px 8px 0 0;font-weight:700;font-size:15px;">{html.escape(str(area_name))}</div>
                    <div style="background:#fff;padding:12px 14px;border:1px solid #DCE3EC;border-top:none;border-radius:0 0 8px 8px;font-size:13px;color:#3B4F68;">
                        <table style="width:100%;border-collapse:collapse">
                          <tr><td style="padding:3px 0;color:#6B7C93">Priority score</td><td style="text-align:right;font-weight:700;color:#0B2545">{priority_score}</td></tr>
                          <tr><td style="padding:3px 0;color:#6B7C93">Risk level</td><td style="text-align:right"><span style="background:{badge_color};color:#fff;border-radius:999px;padding:2px 9px;font-weight:700;font-size:12px">{risk_level}</span></td></tr>
                          <tr><td style="padding:3px 0;color:#6B7C93">Population</td><td style="text-align:right;font-weight:600">{pop_text}</td></tr>
                          <tr><td style="padding:3px 0;color:#6B7C93">Cluster</td><td style="text-align:right;font-weight:600">{html.escape(str(cluster_label))}</td></tr>
                        </table>
                    </div>
                </div>
                """
                folium.Marker(
                    location=[row["Latitude"], row["Longitude"]],
                    popup=folium.Popup(popup_html, max_width=320),
                    tooltip=f"{area_name} · {risk_level}",
                    icon=folium.Icon(color=marker_color, icon="home", prefix="fa")
                ).add_to(groups.get(risk_level, groups["Unknown"]))
            for g in groups.values():
                if len(g._children) > 0:
                    g.add_to(google_map)
            folium.LayerControl(collapsed=True, position="topright").add_to(google_map)
            folium_plugins.Fullscreen(position="topleft").add_to(google_map)
            google_map.fit_bounds([[map_data["Latitude"].min(), map_data["Longitude"].min()], [map_data["Latitude"].max(), map_data["Longitude"].max()]], padding=(40, 40))
            legend_rows = "".join(
                f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0"><span style="width:12px;height:12px;border-radius:50%;background:{RISK_COLORS[r]};display:inline-block"></span>{r}</div>' for r in RISK_ORDER
            )
            google_map.get_root().html.add_child(folium.Element(
                f'<div style="position:fixed;bottom:26px;left:12px;z-index:9999;background:#fff;border:1px solid #DCE3EC;border-radius:10px;padding:10px 14px;font:600 12px Inter,Segoe UI,sans-serif;color:#0B2545;box-shadow:0 2px 10px rgba(11,37,69,.18)"><div style="font-weight:700;margin-bottom:4px">Priority risk</div>{legend_rows}</div>'
            ))
            st_folium(google_map, width=None, height=650, returned_objects=[], key="gis_map")
    else:
        st.warning("Latitude and Longitude columns are required for map visualization. Please upload a dataset containing coordinate data.")

elif page == "AI Recommendations":
    st.markdown("<div class='recommendation-readable'>Upload a photograph of an underdeveloped location. The AI can create a conceptual improved-area image and a preliminary budget estimate.</div>", unsafe_allow_html=True)

    # Existing dataset-based recommendations remain available below the new image workflow.
    render_ai_development_recommendations()
    st.markdown("---")
    section_title("Area-wise recommendations from the project dataset")
    for _, row in df.iterrows():
        risk_color = (
            "#b91c1c" if row["Risk_Level"] == "Critical"
            else "#ef4444" if row["Risk_Level"] == "High"
            else "#d97706" if row["Risk_Level"] == "Medium"
            else "#059669"
        )
        with st.expander(f"{row['Area']} | Score: {row['Priority_Score']} | {row['Risk_Level']}"):
            st.markdown(f"""
            <div class="recommendation-card">
              <div class="recommendation-grid">
                <div><span class="recommendation-label">Rank</span><div class="recommendation-value">{row['Rank']}</div></div>
                <div><span class="recommendation-label">Population</span><div class="recommendation-value">{row['Population']:,}</div></div>
                <div><span class="recommendation-label">Priority score</span><div class="recommendation-value">{row['Priority_Score']}</div></div>
                <div><span class="recommendation-label">Risk level</span><div class="recommendation-value" style="color:{risk_color}">{row['Risk_Level']}</div></div>
              </div>
              <div class="recommendation-label" style="margin-top:14px">Development recommendation</div>
              <div class="recommendation-copy" style="padding:14px;border-radius:10px;line-height:1.65">{row['Recommendation']}</div>
            </div>
            """, unsafe_allow_html=True)


elif page == "Early Warning System":
    st.info("Enter a forecast or field observation for the selected area. This is a threshold-based decision-support tool; it is not connected to a live weather or government alert feed.")
    selected_area = st.selectbox("Select vulnerable area", df["Area"].astype(str).tolist(), key="warning_area")
    selected_row = df[df["Area"].astype(str) == selected_area].iloc[0]
    left, right = st.columns(2)
    with left:
        rainfall = st.number_input("Expected rainfall (mm / 24 hours)", min_value=0.0, max_value=500.0, value=35.0, step=5.0)
        drainage_default = int(round(float(selected_row["Drainage"]) * 100)) if "Drainage" in selected_row.index else int(round(float(selected_row.get("Sanitation", 0.5)) * 100))
        drainage = st.slider("Drainage condition (0 = very poor, 100 = good)", 0, 100, max(0, min(100, drainage_default)))
    with right:
        flood_history = st.checkbox("Flooding reported in this area previously")
        heat_index = st.number_input("Expected heat index (°C)", min_value=0.0, max_value=60.0, value=36.0, step=1.0)
    if st.button("Assess environmental risk", type="primary", width="stretch"):
        assessment = assess_early_warning(rainfall, drainage, flood_history, heat_index)
        st.session_state["latest_warning"] = {"Area": selected_area, **assessment}
    assessment = st.session_state.get("latest_warning")
    if assessment and assessment.get("Area") == selected_area:
        color = "#b91c1c" if assessment["Alert_Level"] == "High Alert" else "#d97706" if assessment["Alert_Level"] == "Watch" else "#059669"
        g1, g2 = st.columns([1.5, 1])
        with g1:
            st.markdown(f"<div class='alert-card' style='--ac:{color}'><div class='k'>Environmental alert · {html.escape(str(assessment['Area']))}</div><div class='v'>{assessment['Alert_Level']} · {assessment['Alert_Score']}/100</div><div class='a'>{assessment['Recommended_Action']}</div></div>", unsafe_allow_html=True)
            st.write("**Detected risk factors**")
            for reason in assessment["Reasons"]:
                st.write("• " + reason)
        with g2:
            gauge = go.Figure(go.Indicator(
                mode="gauge+number", value=assessment["Alert_Score"], number=dict(suffix="/100", font=dict(size=28)),
                gauge=dict(axis=dict(range=[0, 100]), bar=dict(color=color, thickness=0.28),
                           steps=[dict(range=[0, 30], color="rgba(21,128,61,.18)"), dict(range=[30, 60], color="rgba(202,138,4,.2)"), dict(range=[60, 100], color="rgba(180,35,24,.2)")]),
                title=dict(text="Alert score (Normal < 30 · Watch 30–59 · High Alert 60+)", font=dict(size=12))))
            gauge.update_layout(height=250)
            st.plotly_chart(apply_chart_layout(gauge, theme), width="stretch", config={"displayModeBar": False})
        st.caption("Threshold-based decision support only. Officers should verify local conditions before taking action.")

# ═══════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════
st.markdown("""
<div class="footer">
    <b>Vikas Drishti</b> · Smart Slum Development Priority Index © 2026<br>
    Priority scoring · ML clustering · Geo-spatial analytics
</div>
""", unsafe_allow_html=True)
