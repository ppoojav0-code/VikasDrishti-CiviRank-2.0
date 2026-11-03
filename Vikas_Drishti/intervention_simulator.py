import streamlit as st
import pandas as pd

WEIGHTS = {"Sanitation":.25,"Water":.20,"Education":.15,
           "Healthcare":.20,"Crime":.10,"Electricity":.10}

def priority(v):
    return round(((1-v["Sanitation"])*.25+(1-v["Water"])*.20+
                  (1-v["Education"])*.15+(1-v["Healthcare"])*.20+
                  v["Crime"]*.10+(1-v["Electricity"])*.10)*100,2)

def risk(score):
    return "HIGH" if score >= 70 else "MEDIUM" if score >= 40 else "LOW"

def render_intervention_simulator():
    st.subheader("🔮 Intervention Impact Simulator")
    current, projected = {}, {}
    cols = st.columns(2)
    defaults = {"Sanitation":.35,"Water":.40,"Education":.55,
                "Healthcare":.38,"Crime":.60,"Electricity":.50}
    for i, name in enumerate(defaults):
        with cols[i % 2]:
            current[name] = st.slider(f"Current {name}",0.,1.,defaults[name],.01,key=f"cur_{name}")
            projected[name] = st.slider(f"Projected {name}",0.,1.,
                                        min(1.,defaults[name]+.20),.01,key=f"proj_{name}")
    before, after = priority(current), priority(projected)
    a,b,c = st.columns(3)
    a.metric("Current", f"{before}/100", risk(before))
    b.metric("Projected", f"{after}/100", risk(after))
    c.metric("Score Reduction", f"{before-after:.2f}")
    st.dataframe(pd.DataFrame({"Indicator":list(defaults),
        "Current":[current[x] for x in defaults],
        "Projected":[projected[x] for x in defaults]}), use_container_width=True, hide_index=True)
