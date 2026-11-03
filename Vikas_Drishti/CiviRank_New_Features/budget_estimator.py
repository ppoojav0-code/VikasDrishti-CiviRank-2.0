import streamlit as st
import pandas as pd

COSTS = {"Road resurfacing":1200000,"Drainage improvement":800000,
"Street lighting":300000,"Waste management":200000,
"Pedestrian pathway":500000,"Water infrastructure":900000,
"Public-space improvement":600000}

def render_budget_estimator():
    st.subheader("💰 Planning-Level Budget Estimator")
    selected = st.multiselect("Interventions", list(COSTS), key="budget_items")
    rows=[]
    for item in selected:
        amount=st.number_input(f"{item} — estimated cost (₹)",0,int(COSTS[item]),50000,key=f"cost_{item}")
        rows.append({"Intervention":item,"Estimated Cost (₹)":amount})
    if rows:
        df=pd.DataFrame(rows)
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.metric("Estimated Planning Budget",f"₹{df['Estimated Cost (₹)'].sum():,.0f}")
        st.download_button("Download Budget CSV",df.to_csv(index=False),
                           "civirank_budget.csv","text/csv")
    st.warning("Planning estimates only; validate local rates and engineering quantities before real use.")
