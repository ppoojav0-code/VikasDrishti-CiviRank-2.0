import streamlit as st
import pandas as pd

def render_development_plan():
    st.subheader("📝 Development Plan Generator")
    area=st.text_input("Area")
    score=st.number_input("Priority Score",0.,100.,75.,.1)
    risk=st.selectbox("Risk",["HIGH","MEDIUM","LOW"])
    problems=st.text_area("Problems (one per line)","Damaged road\nPoor drainage\nWater deficiency")
    actions=st.text_area("Interventions (one per line)","Road resurfacing\nDrainage improvement\nWater infrastructure")
    budget=st.number_input("Planning budget (₹)",0,100000000,3000000,100000)
    if st.button("Generate Development Plan",type="primary"):
        p=[x.strip() for x in problems.splitlines() if x.strip()]
        a=[x.strip() for x in actions.splitlines() if x.strip()]
        df=pd.DataFrame({"Problem":p,"Proposed Intervention":a[:len(p)]})
        st.markdown(f"**{area or 'Selected Area'}** · Score **{score:.2f}/100** · Risk **{risk}** · Budget **₹{budget:,.0f}**")
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.download_button("Download Plan",df.to_csv(index=False),"civirank_plan.csv","text/csv")
