import streamlit as st
from PIL import Image

ISSUES = [
    "Damaged road / potholes", "Poor or open drainage",
    "Waste accumulation", "Poor pedestrian pathway",
    "Insufficient visible street lighting", "Waterlogging / standing water",
    "Damaged public infrastructure"
]

def render_ai_vision():
    st.subheader("📸 AI Infrastructure Vision")
    st.caption("Upload a location image and record visible infrastructure conditions.")
    image = st.file_uploader("Upload location photograph", type=["png","jpg","jpeg"], key="vision_upload")
    if image:
        st.image(Image.open(image), caption="Location image", use_container_width=True)
        selected = st.multiselect("Visible issues", ISSUES, key="vision_issues")
        severity = st.select_slider("Overall visible severity",
                                    ["Low","Moderate","High","Critical"],
                                    value="Moderate", key="vision_severity")
        if st.button("Save Visual Assessment", type="primary"):
            st.session_state["vision_assessment"] = {
                "issues": selected, "severity": severity, "image_name": image.name
            }
            st.success("Assessment saved for this session.")
        st.info("Production: connect this module to a computer-vision model. AI observations should be field-verified.")
