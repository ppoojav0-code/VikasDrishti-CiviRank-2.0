import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium

from backend.data_processing import load_data, clean_data, normalize_data
from backend.index_calculation import calculate_priority_index
from backend.clustering import apply_clustering
from backend.recommendation import generate_recommendation


# ═══════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════
st.set_page_config(
    page_title="CiviRank | Urban Intelligence",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ═══════════════════════════════════════════════════
# CSS INJECTION
# ═══════════════════════════════════════════════════
def load_css():
    try:
        with open("assets/style.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

load_css()


# ═══════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""


# ═══════════════════════════════════════════════════
# LOGIN PAGE
# ═══════════════════════════════════════════════════
def login_page():
    st.markdown("""
    <div class="login-bg">
        <div class="login-shape login-shape-1"></div>
        <div class="login-shape login-shape-2"></div>
        <div class="login-shape login-shape-3"></div>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 3, 1])
    with col_center:
        st.markdown("""
        <div class="login-wrapper">
            <div class="login-card">
                <div class="login-brand">🏙️</div>
                <div class="login-title">CiviRank</div>
                <div class="login-subtitle">Smart Slum Development Priority Index</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("👤 Username", placeholder="Enter username")
            password = st.text_input("🔑 Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Secure Login →", use_container_width=True)

            if submitted:
                if username == "admin" and password == "admin123":
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.toast("✅ Welcome back, Admin!", icon="🎉")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")

        st.markdown("""
        <div class="login-hint" style="text-align:center;">
            🔓 Demo Login &nbsp;•&nbsp; Username: <b>admin</b> &nbsp;•&nbsp; Password: <b>admin123</b>
        </div>
        """, unsafe_allow_html=True)


if not st.session_state["logged_in"]:
    login_page()
    st.stop()


# ═══════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 20px 0 10px 0;">
        <div style="font-size: 40px; margin-bottom: 8px;">🏙️</div>
        <div style="font-size: 20px; font-weight: 800; color: white;">CiviRank</div>
        <div style="font-size: 12px; color: #94a3b8; letter-spacing: 1px; text-transform: uppercase;">Urban Intelligence</div>
    </div>
    <hr style="border-color: rgba(255,255,255,0.1); margin: 16px 0;">
    """, unsafe_allow_html=True)

    # User profile pill
    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.05); border-radius: 16px; padding: 16px; margin-bottom: 24px; border: 1px solid rgba(255,255,255,0.08);">
        <div style="font-size: 14px; color: #94a3b8; margin-bottom: 4px;">Signed in as</div>
        <div style="font-size: 16px; font-weight: 700; color: white;">{st.session_state["username"]}</div>
        <div style="display: flex; align-items: center; gap: 6px; margin-top: 8px;">
            <div style="width: 8px; height: 8px; background: #14b8a6; border-radius: 50%; box-shadow: 0 0 8px #14b8a6;"></div>
            <span style="font-size: 12px; color: #14b8a6; font-weight: 600;">Active Session</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div style="font-size: 12px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">⚙️ Control Panel</div>',
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Upload Slum Dataset (CSV)",
        type=["csv"],
        help="Upload your dataset or use the default built-in sample data."
    )

    st.markdown("---")
    st.info("📎 Upload a dataset or continue with the default built-in sample data.", icon="ℹ️")

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.rerun()


# ═══════════════════════════════════════════════════
# DATA LOADING & PROCESSING
# ═══════════════════════════════════════════════════
try:
    with st.spinner("🧠 Processing urban intelligence data…"):
        df = load_data(uploaded_file)
        df = clean_data(df)
        original_df = df.copy()
        df = normalize_data(df)
        df = calculate_priority_index(df)
        df = apply_clustering(df)
        df["Recommendation"] = df.apply(generate_recommendation, axis=1)
except Exception as e:
    st.error("🚨 Something went wrong while processing the dataset.")
    st.caption(f"Traceback: {e}")
    st.stop()


# ═══════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════
st.markdown(f"""
<div class="header-box">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <h1 style="color:white; margin:0; font-size: 42px; font-weight: 800;">🏙️ CiviRank</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 18px; font-weight: 400;">
                AI-powered urban intelligence for sustainable slum development planning.
            </p>
            <p style="color: rgba(255,255,255,0.7); margin: 6px 0 0 0; font-size: 14px; font-weight: 400;">
                Smart Priority Index • Risk Analysis • ML Clustering • Map Intelligence
            </p>
        </div>
        <div style="text-align: right; margin-top: 10px;">
            <div style="background: rgba(255,255,255,0.15); border-radius: 16px; padding: 12px 20px; display: inline-block; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);">
                <div style="font-size: 12px; color: rgba(255,255,255,0.8); text-transform: uppercase; letter-spacing: 1px;">Dataset Status</div>
                <div style="font-size: 16px; color: white; font-weight: 700;">{len(df):,} Records Loaded</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════
# METRICS
# ═══════════════════════════════════════════════════
st.markdown(
    '<div style="margin-bottom: 8px; font-size: 14px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 1px;">📊 Urban Development Intelligence Overview</div>',
    unsafe_allow_html=True
)
st.caption("Real-time insights generated from uploaded slum development data.")

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-icon" style="background: linear-gradient(135deg, #3b82f6, #1d4ed8);">🏘️</div>
        <div class="metric-label">Total Areas</div>
        <div class="metric-value">{len(df):,}</div>
        <div class="metric-delta" style="color: #10b981;">▲ Active Regions</div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    high_risk = len(df[df["Risk_Level"] == "High Risk"])
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-icon" style="background: linear-gradient(135deg, #ef4444, #b91c1c);">⚠️</div>
        <div class="metric-label">High Risk Areas</div>
        <div class="metric-value">{high_risk:,}</div>
        <div class="metric-delta" style="color: #ef4444;">Requires Immediate Action</div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    avg_score = round(df["Priority_Score"].mean(), 2)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-icon" style="background: linear-gradient(135deg, #f59e0b, #d97706);">📉</div>
        <div class="metric-label">Avg Priority Score</div>
        <div class="metric-value">{avg_score}</div>
        <div class="metric-delta" style="color: #f59e0b;">Composite Index</div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    max_score = df["Priority_Score"].max()
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-icon" style="background: linear-gradient(135deg, #14b8a6, #0f766e);">🏆</div>
        <div class="metric-label">Highest Score</div>
        <div class="metric-value">{max_score}</div>
        <div class="metric-delta" style="color: #14b8a6;">Top Priority Region</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")


# ═══════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Priority Dashboard",
    "📈 Advanced Analytics",
    "🧠 ML Clustering",
    "🗺️ Geo-Spatial Map",
    "📄 AI Recommendations"
])


with tab1:
    st.markdown(
        '<div style="font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 16px;">🏆 Area Priority Ranking</div>',
        unsafe_allow_html=True
    )

    search_area = st.text_input(
        "🔍 Search Area",
        placeholder="Type area name to filter…",
        label_visibility="collapsed"
    )

    display_df = df.copy()
    if search_area:
        display_df = display_df[display_df["Area"].str.contains(search_area, case=False, na=False)]

    st.dataframe(
        display_df[["Rank", "Area", "Population", "Priority_Score", "Risk_Level", "Cluster"]],
        use_container_width=True,
        height=450,
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", width="small"),
            "Area": st.column_config.TextColumn("Area Name", width="medium"),
            "Population": st.column_config.NumberColumn("Population", width="medium"),
            "Priority_Score": st.column_config.ProgressColumn(
                "Priority Score", min_value=0, max_value=100, width="medium"
            ),
            "Risk_Level": st.column_config.TextColumn("Risk Level", width="medium"),
            "Cluster": st.column_config.NumberColumn("Cluster", width="small"),
        }
    )

    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Processed Report",
        data=csv,
        file_name="civirank_processed_report.csv",
        mime="text/csv",
        use_container_width=False
    )


with tab2:
    st.markdown(
        '<div style="font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 16px;">📈 Priority Score Analysis</div>',
        unsafe_allow_html=True
    )

    a1, a2 = st.columns([2, 1])
    with a1:
        fig_bar = px.bar(
            df,
            x="Area",
            y="Priority_Score",
            color="Risk_Level",
            title="Priority Score by Area",
            text="Priority_Score",
            color_discrete_map={"High Risk": "#ef4444", "Medium Risk": "#f59e0b", "Low Risk": "#10b981"}
        )
        fig_bar.update_traces(textposition="outside", texttemplate="%{text:.2f}")
        fig_bar.update_layout(
            template="plotly_white",
            title_font_size=20,
            title_font_color="#0f172a",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(size=13, color="#334155"),
            margin=dict(l=20, r=20, t=50, b=20),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    with a2:
        fig_pie = px.pie(
            df,
            names="Risk_Level",
            title="Risk Distribution",
            hole=0.45,
            color_discrete_map={"High Risk": "#ef4444", "Medium Risk": "#f59e0b", "Low Risk": "#10b981"}
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label", pull=[0.02, 0.02, 0.02])
        fig_pie.update_layout(
            template="plotly_white",
            title_font_size=18,
            title_font_color="#0f172a",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})

    fig_scatter = px.scatter(
        df,
        x="Population",
        y="Priority_Score",
        color="Risk_Level",
        size="Priority_Score",
        hover_name="Area",
        title="Population vs Priority Score Correlation",
        color_discrete_map={"High Risk": "#ef4444", "Medium Risk": "#f59e0b", "Low Risk": "#10b981"}
    )
    fig_scatter.update_layout(
        template="plotly_white",
        title_font_size=20,
        title_font_color="#0f172a",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13, color="#334155"),
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_scatter, use_container_width=True, config={"displayModeBar": False})


with tab3:
    st.markdown(
        '<div style="font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 16px;">🧠 KMeans Cluster Analysis</div>',
        unsafe_allow_html=True
    )

    fig_cluster = px.scatter(
        df,
        x="Sanitation",
        y="Healthcare",
        color=df["Cluster"].astype(str),
        size="Priority_Score",
        hover_name="Area",
        title="Development Cluster Visualization",
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig_cluster.update_layout(
        template="plotly_white",
        title_font_size=20,
        title_font_color="#0f172a",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13, color="#334155"),
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(title="Cluster", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_cluster, use_container_width=True, config={"displayModeBar": False})

    st.markdown("""
    <div style="background: #f8fafc; border-radius: 14px; padding: 20px; border-left: 5px solid #1f6f8b; margin-top: 16px;">
        <div style="font-weight: 700; color: #0f172a; margin-bottom: 6px;">💡 Insight</div>
        <div style="color: #475569; font-size: 14px;">
            Cluster groups help identify similar areas based on development conditions. Areas within the same cluster share comparable sanitation and healthcare profiles, enabling targeted intervention strategies.
        </div>
    </div>
    """, unsafe_allow_html=True)


with tab4:
    st.markdown(
        '<div style="font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 16px;">🗺️ Geo-Spatial Intelligence Map</div>',
        unsafe_allow_html=True
    )

    if "Latitude" in original_df.columns and "Longitude" in original_df.columns:
        map_data = original_df.copy()
        map_data = map_data.dropna(subset=["Latitude", "Longitude"])

        if map_data.empty:
            st.warning("⚠️ Latitude and Longitude values are empty after dropping missing coordinates.")
        else:
            center_lat = map_data["Latitude"].mean()
            center_lon = map_data["Longitude"].mean()

            google_map = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=12,
                tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
                attr="Google Maps"
            )

            for _, row in map_data.iterrows():
                area_name = row["Area"] if "Area" in row else "Unknown Area"
                matched_row = df[df["Area"] == area_name]

                if not matched_row.empty:
                    risk_level = matched_row["Risk_Level"].values[0]
                    priority_score = matched_row["Priority_Score"].values[0]
                else:
                    risk_level = "Unknown"
                    priority_score = "N/A"

                if risk_level == "High Risk":
                    marker_color = "red"
                elif risk_level == "Medium Risk":
                    marker_color = "orange"
                else:
                    marker_color = "green"

                popup_html = f"""
                <div style="font-family: 'Inter', sans-serif; min-width: 200px;">
                    <div style="background: linear-gradient(135deg, #0f172a, #1f6f8b); color: white; padding: 10px 14px; border-radius: 10px 10px 0 0; font-weight: 700; font-size: 16px;">
                        {area_name}
                    </div>
                    <div style="background: white; padding: 14px; border-radius: 0 0 10px 10px; border: 1px solid #e2e8f0; border-top: none;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <span style="color: #64748b; font-size: 13px;">Priority Score</span>
                            <span style="font-weight: 700; color: #0f172a; font-size: 13px;">{priority_score}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #64748b; font-size: 13px;">Risk Level</span>
                            <span style="font-weight: 700; color: {marker_color}; font-size: 13px;">{risk_level}</span>
                        </div>
                    </div>
                </div>
                """

                folium.Marker(
                    location=[row["Latitude"], row["Longitude"]],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=area_name,
                    icon=folium.Icon(color=marker_color, icon="home", prefix="fa")
                ).add_to(google_map)

            st_folium(google_map, width=None, height=650)
    else:
        st.warning("🗺️ Latitude and Longitude columns are required for map visualization. Please upload a dataset containing coordinate data.")


with tab5:
    st.markdown(
        '<div style="font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 16px;">📄 Smart Development Recommendations</div>',
        unsafe_allow_html=True
    )

    for _, row in df.iterrows():
        risk_color = (
            "#ef4444" if row["Risk_Level"] == "High Risk"
            else "#f59e0b" if row["Risk_Level"] == "Medium Risk"
            else "#10b981"
        )
        with st.expander(f"🏘️ {row['Area']} | Score: {row['Priority_Score']} | {row['Risk_Level']}"):
            c1, c2 = st.columns([1, 3])
            with c1:
                st.markdown(f"""
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #f8fafc, #ffffff); border-radius: 16px; border: 1px solid #e2e8f0;">
                    <div style="font-size: 32px; font-weight: 800; color: #0f172a;">{row['Rank']}</div>
                    <div style="font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px;">Rank</div>
                    <div style="margin-top: 16px; font-size: 14px; font-weight: 700; color: {risk_color}; background: {risk_color}15; padding: 6px 12px; border-radius: 20px; display: inline-block;">
                        {row['Risk_Level']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div style="margin-bottom: 8px;">
                    <span style="font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;">Population</span>
                    <div style="font-size: 18px; font-weight: 700; color: #0f172a;">{row['Population']:,}</div>
                </div>
                <div style="margin-bottom: 8px;">
                    <span style="font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;">Priority Score</span>
                    <div style="font-size: 18px; font-weight: 700; color: #0f172a;">{row['Priority_Score']}</div>
                </div>
                <div>
                    <span style="font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;">AI Recommendation</span>
                    <div style="font-size: 15px; color: #334155; line-height: 1.6; margin-top: 6px; background: #f8fafc; padding: 14px; border-radius: 12px; border-left: 4px solid #1f6f8b;">
                        {row['Recommendation']}
                    </div>
                </div>
                """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════
st.markdown("""
<div class="footer">
    <div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">CiviRank</div>
    <div style="font-size: 13px; color: #64748b;">Smart Slum Development Priority Index © 2026</div>
    <div style="font-size: 12px; color: #94a3b8; margin-top: 8px;">Powered by AI • ML Clustering • Geo-Spatial Analytics</div>
</div>
""", unsafe_allow_html=True)
