import random
import json
import io
from datetime import datetime

import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(
    page_title="EV Battery Cell Simulator",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Helpers ----------
def rand_val(low, high, precision=2):
    return round(random.uniform(low, high), precision)

def generate_cell(ranges, cell_type):
    r = ranges[cell_type]
    return {
        "type": cell_type,
        "nominal_voltage": rand_val(*r["nominal_voltage"]),
        "min_voltage": rand_val(*r["min_voltage"]),
        "max_voltage": rand_val(*r["max_voltage"]),
        "capacitance_F": rand_val(*r["capacitance_F"]),
        "current_A": rand_val(*r["current_A"]),
        "temperature_C": rand_val(*r["temperature_C"]),
    }

def generate_cells(n, ranges, mix=("LFP", "NMC")):
    out = []
    for _ in range(n):
        t = random.choice(mix)
        out.append(generate_cell(ranges, t))
    return pd.DataFrame(out)

def df_stats(df: pd.DataFrame):
    return {
        "cells": len(df),
        "avg_nominal_V": round(df["nominal_voltage"].mean(), 3) if not df.empty else 0,
        "avg_capacitance_F": round(df["capacitance_F"].mean(), 3) if not df.empty else 0,
        "avg_temp_C": round(df["temperature_C"].mean(), 3) if not df.empty else 0,
    }

def to_csv_bytes(df):
    return df.to_csv(index=False).encode()

def to_json_bytes(df):
    return json.dumps(df.to_dict(orient="records"), indent=2).encode()

# ---------- Defaults ----------
DEFAULT_RANGES = {
    # Typical realistic-ish bounds for simulation. Adjust anytime in the sidebar.
    "LFP": {
        "nominal_voltage": (3.20, 3.35),
        "min_voltage": (2.50, 2.90),
        "max_voltage": (3.55, 3.65),
        "capacitance_F": (10.0, 100.0),
        "current_A": (1.0, 10.0),
        "temperature_C": (20.0, 60.0),
    },
    "NMC": {
        "nominal_voltage": (3.60, 3.75),
        "min_voltage": (3.00, 3.20),
        "max_voltage": (4.15, 4.30),
        "capacitance_F": (10.0, 100.0),
        "current_A": (1.0, 10.0),
        "temperature_C": (20.0, 60.0),
    },
}

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=[
        "type", "nominal_voltage", "min_voltage", "max_voltage",
        "capacitance_F", "current_A", "temperature_C"
    ])

# ---------- Sidebar Controls ----------
st.sidebar.title("⚙️ Controls")

with st.sidebar.expander("Randomization"):
    seed_input = st.text_input("Random Seed (optional)", value="")
    if seed_input.strip():
        try:
            random.seed(int(seed_input.strip()))
        except ValueError:
            random.seed(seed_input.strip())

    count = st.number_input("Number of cells to generate", min_value=1, max_value=10000, value=10, step=1)
    mix_types = st.multiselect("Cell types to include", ["LFP", "NMC"], default=["LFP", "NMC"])
    precision = st.slider("Value precision (decimal places)", 0, 4, 2)

with st.sidebar.expander("Ranges: LFP"):
    lfp_nom = st.slider("Nominal Voltage (LFP)", 3.0, 3.6, DEFAULT_RANGES["LFP"]["nominal_voltage"])
    lfp_min = st.slider("Min Voltage (LFP)", 2.0, 3.2, DEFAULT_RANGES["LFP"]["min_voltage"])
    lfp_max = st.slider("Max Voltage (LFP)", 3.3, 3.9, DEFAULT_RANGES["LFP"]["max_voltage"])
    lfp_cap = st.slider("Capacitance F (LFP)", 1.0, 200.0, DEFAULT_RANGES["LFP"]["capacitance_F"])
    lfp_cur = st.slider("Current A (LFP)", 0.1, 100.0, DEFAULT_RANGES["LFP"]["current_A"])
    lfp_tmp = st.slider("Temperature °C (LFP)", -20.0, 120.0, DEFAULT_RANGES["LFP"]["temperature_C"])

with st.sidebar.expander("Ranges: NMC"):
    nmc_nom = st.slider("Nominal Voltage (NMC)", 3.2, 4.0, DEFAULT_RANGES["NMC"]["nominal_voltage"])
    nmc_min = st.slider("Min Voltage (NMC)", 2.8, 3.5, DEFAULT_RANGES["NMC"]["min_voltage"])
    nmc_max = st.slider("Max Voltage (NMC)", 3.8, 4.4, DEFAULT_RANGES["NMC"]["max_voltage"])
    nmc_cap = st.slider("Capacitance F (NMC)", 1.0, 200.0, DEFAULT_RANGES["NMC"]["capacitance_F"])
    nmc_cur = st.slider("Current A (NMC)", 0.1, 100.0, DEFAULT_RANGES["NMC"]["current_A"])
    nmc_tmp = st.slider("Temperature °C (NMC)", -20.0, 120.0, DEFAULT_RANGES["NMC"]["temperature_C"])

ranges = {
    "LFP": {
        "nominal_voltage": tuple(round(x, precision) for x in lfp_nom),
        "min_voltage": tuple(round(x, precision) for x in lfp_min),
        "max_voltage": tuple(round(x, precision) for x in lfp_max),
        "capacitance_F": tuple(round(x, precision) for x in lfp_cap),
        "current_A": tuple(round(x, precision) for x in lfp_cur),
        "temperature_C": tuple(round(x, precision) for x in lfp_tmp),
    },
    "NMC": {
        "nominal_voltage": tuple(round(x, precision) for x in nmc_nom),
        "min_voltage": tuple(round(x, precision) for x in nmc_min),
        "max_voltage": tuple(round(x, precision) for x in nmc_max),
        "capacitance_F": tuple(round(x, precision) for x in nmc_cap),
        "current_A": tuple(round(x, precision) for x in nmc_cur),
        "temperature_C": tuple(round(x, precision) for x in nmc_tmp),
    },
}

st.sidebar.markdown("---")
col_gen1, col_gen2, col_gen3 = st.sidebar.columns([1,1,1])
with col_gen1:
    if st.button("Generate Cells", use_container_width=True):
        if not mix_types:
            st.error("Select at least one cell type.")
        else:
            df_new = generate_cells(count, ranges, mix=tuple(mix_types))
            st.session_state.df = pd.concat([st.session_state.df, df_new], ignore_index=True)
with col_gen2:
    if st.button("Add 1 Random", use_container_width=True):
        t = random.choice(mix_types or ["LFP", "NMC"])
        new_row = pd.DataFrame([generate_cell(ranges, t)])
        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
with col_gen3:
    if st.button("Clear All", type="primary", use_container_width=True):
        st.session_state.df = st.session_state.df.iloc[0:0]

# ---------- Header ----------
st.title("🔋 EV Battery Cell Simulator")
st.caption("Generate, filter, edit, visualize, and export LFP/NMC cell properties.")

# ---------- Filters Row ----------
with st.container():
    filt_col1, filt_col2, filt_col3, filt_col4 = st.columns([1,1,2,2])
    with filt_col1:
        f_types = st.multiselect("Filter: Type", ["LFP", "NMC"], default=["LFP", "NMC"])
    with filt_col2:
        f_temp = st.slider("Filter: Temperature °C", -20.0, 120.0, (20.0, 60.0))
    with filt_col3:
        f_nom = st.slider("Filter: Nominal V", 3.0, 4.0, (3.0, 4.0))
    with filt_col4:
        f_cap = st.slider("Filter: Capacitance F", 0.0, 200.0, (0.0, 200.0))

df = st.session_state.df.copy()

if not df.empty:
    df = df[
        df["type"].isin(f_types)
        & df["temperature_C"].between(f_temp[0], f_temp[1])
        & df["nominal_voltage"].between(f_nom[0], f_nom[1])
        & df["capacitance_F"].between(f_cap[0], f_cap[1])
    ]

# ---------- KPIs ----------
kpi = df_stats(df)
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Cells", kpi["cells"])
k2.metric("Avg Nominal Voltage (V)", kpi["avg_nominal_V"])
k3.metric("Avg Capacitance (F)", kpi["avg_capacitance_F"])
k4.metric("Avg Temperature (°C)", kpi["avg_temp_C"])

st.markdown("---")

# ---------- Editable Table ----------
st.subheader("📋 Data")
st.caption("You can edit values inline. Changes affect charts and downloads.")
edited = st.data_editor(
    df,
    use_container_width=True,
    height=360,
    num_rows="dynamic",
    column_config={
        "type": st.column_config.SelectboxColumn("type", options=["LFP", "NMC"]),
        "nominal_voltage": st.column_config.NumberColumn("nominal_voltage", step=0.01),
        "min_voltage": st.column_config.NumberColumn("min_voltage", step=0.01),
        "max_voltage": st.column_config.NumberColumn("max_voltage", step=0.01),
        "capacitance_F": st.column_config.NumberColumn("capacitance_F", step=0.01),
        "current_A": st.column_config.NumberColumn("current_A", step=0.01),
        "temperature_C": st.column_config.NumberColumn("temperature_C", step=0.1),
    },
    key="editor",
)

# Push edits back to session (only for filtered subset rows)
if not df.empty:
    # Update the matching indices in the original df
    st.session_state.df.loc[edited.index, :] = edited

# ---------- Charts ----------
st.subheader("📈 Visualizations")
chart_col1, chart_col2 = st.columns(2)

if not edited.empty:
    with chart_col1:
        st.caption("Nominal vs Max Voltage (by type)")
        c1 = (
            alt.Chart(edited.reset_index(drop=True))
            .mark_circle(size=80, opacity=0.7)
            .encode(
                x=alt.X("nominal_voltage:Q"),
                y=alt.Y("max_voltage:Q"),
                color="type:N",
                tooltip=list(edited.columns),
            )
            .interactive()
        )
        st.altair_chart(c1, use_container_width=True)

    with chart_col2:
        st.caption("Temperature Distribution")
        c2 = (
            alt.Chart(edited.reset_index(drop=True))
            .mark_bar(opacity=0.8)
            .encode(
                x=alt.X("temperature_C:Q", bin=alt.Bin(maxbins=20)),
                y=alt.Y("count():Q"),
                color="type:N",
                tooltip=["type", "temperature_C"],
            )
            .interactive()
        )
        st.altair_chart(c2, use_container_width=True)
else:
    st.info("No data to visualize. Generate cells or adjust filters.")

st.markdown("---")

# ---------- Export Row ----------
st.subheader("📦 Export")
exp1, exp2, exp3 = st.columns([1,1,2])
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

with exp1:
    st.download_button(
        label="Download CSV",
        data=to_csv_bytes(edited),
        file_name=f"cells_{timestamp}.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=edited.empty,
    )
with exp2:
    st.download_button(
        label="Download JSON",
        data=to_json_bytes(edited),
        file_name=f"cells_{timestamp}.json",
        mime="application/json",
        use_container_width=True,
        disabled=edited.empty,
    )
with exp3:
    st.caption("Tip: Use the random seed in the sidebar for reproducible datasets.")

st.markdown("---")
st.caption("Built with Streamlit • Edit values inline • Export for your ML/analysis pipelines")
