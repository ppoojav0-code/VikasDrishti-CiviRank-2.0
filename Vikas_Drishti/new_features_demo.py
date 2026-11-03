import streamlit as st
from ai_vision import render_ai_vision
from development_visualizer import render_development_visualizer
from intervention_simulator import render_intervention_simulator
from budget_estimator import render_budget_estimator
from issue_reporting import render_issue_reporting
from development_plan import render_development_plan

st.set_page_config(page_title="CiviRank New Features",page_icon="🏙️",layout="wide")
st.title("🏙️ CiviRank — New Feature Modules")
tabs=st.tabs(["📸 AI Vision","✨ Development Visualizer","🔮 Simulator","💰 Budget","📍 Issues","📝 Plan"])
with tabs[0]: render_ai_vision()
with tabs[1]: render_development_visualizer()
with tabs[2]: render_intervention_simulator()
with tabs[3]: render_budget_estimator()
with tabs[4]: render_issue_reporting()
with tabs[5]: render_development_plan()
