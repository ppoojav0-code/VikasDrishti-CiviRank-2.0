import streamlit as st
from datetime import date

TYPES=["Damaged road","Water shortage","Drainage / waterlogging","Sanitation",
       "Waste accumulation","Street lighting","Public infrastructure","Other"]

def render_issue_reporting():
    st.subheader("📍 Field & Citizen Issue Reporting")
    kind=st.selectbox("Issue type",TYPES)
    area=st.text_input("Area / Location")
    severity=st.selectbox("Severity",["Low","Moderate","High","Critical"])
    desc=st.text_area("Description")
    photo=st.file_uploader("Supporting photograph",type=["png","jpg","jpeg"])
    if st.button("Submit Issue",type="primary"):
        if not area or not desc:
            st.error("Area and description are required.")
        else:
            issue={"date":str(date.today()),"area":area,"type":kind,
                   "severity":severity,"description":desc,
                   "photo":photo.name if photo else "","status":"Reported"}
            st.session_state.setdefault("reported_issues",[]).append(issue)
            st.success("Issue recorded.")
    if st.session_state.get("reported_issues"):
        st.dataframe(st.session_state["reported_issues"],use_container_width=True,hide_index=True)
