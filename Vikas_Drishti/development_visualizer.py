import streamlit as st

def build_prompt(area, issues, interventions, style):
    return f"""Create a {style} conceptual urban-development visualization for {area}.
Current visible conditions: {", ".join(issues) or "infrastructure deficiencies"}.
Proposed interventions: {", ".join(interventions) or "appropriate infrastructure improvements"}.
Preserve the general site context. Show practical improvements only where relevant.
Do not depict official approval or exact engineering dimensions.
Label the result as an AI-generated conceptual visualization."""

def render_development_visualizer():
    st.subheader("✨ AI Development Visualizer")
    area = st.text_input("Area / Location", key="viz_area")
    issues = st.multiselect("Current problems",
        ["Damaged road","Potholes","Poor drainage","Waste accumulation",
         "Poor walkway","Insufficient street lighting","Waterlogging"],
        key="viz_issues")
    interventions = st.multiselect("Proposed interventions",
        ["Road resurfacing","Drainage improvement","Waste management",
         "Pedestrian pathway","Street lighting","Public-space improvement",
         "Water infrastructure","Landscaping"], key="viz_interventions")
    style = st.selectbox("Style", ["realistic","architectural concept","community development concept"])
    if st.button("Generate Visualization Prompt", type="primary"):
        prompt = build_prompt(area or "selected area", issues, interventions, style)
        st.code(prompt, language="text")
        st.download_button("Download Prompt", prompt,
                           "civirank_visualization_prompt.txt", "text/plain")
        st.warning("Generated images are conceptual scenarios, not approved engineering designs.")
