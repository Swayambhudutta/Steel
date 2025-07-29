import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# -----------------------------
# Fallback Implementations
# -----------------------------
def get_latest_cycle(df, stove_id):
    return df[df['stove_id'] == stove_id].iloc[-1]

def get_historical_data(df, stove_id):
    return df[df['stove_id'] == stove_id].copy()

def get_condition_index(efficiencies):
    return np.mean(efficiencies[-5:]) if len(efficiencies) >= 5 else np.mean(efficiencies)

def calculate_heat_input(m_fuel, cv_fuel, eta_comb, m_air_comb, cp_air, t_air_comb, t_ambient):
    Q_fuel = m_fuel * cv_fuel * eta_comb
    Q_air_comb = m_air_comb * cp_air * (t_air_comb - t_ambient)
    return Q_fuel, Q_air_comb

def calculate_heat_output(m_air, cp_air, t_hot_blast, t_ambient):
    return m_air * cp_air * (t_hot_blast - t_ambient)

def calculate_flue_loss(m_flue, cp_flue, t_flue, t_ref):
    return m_flue * cp_flue * (t_flue - t_ref)

def calculate_shell_loss(k, A, t_internal, t_surface, d, eps, sigma, t_ambient):
    conduction = k * A * (t_internal - t_surface) / d
    radiation = eps * sigma * A * ((t_surface + 273.15)**4 - (t_ambient + 273.15)**4)
    return conduction + radiation

def calculate_efficiency(Q_blast, Q_fuel, Q_air_comb, Q_flue, Q_shell):
    total_input = Q_fuel + Q_air_comb
    if total_input <= 0:
        return 0.0
    efficiency = Q_blast / total_input
    return max(0.0, min(efficiency, 1.0))

# -----------------------------
# Dashboard Configuration
# -----------------------------
THRESHOLDS = {
    "efficiency_low": 0.70,
    "shell_temp_high": 150,
    "cycle_duration_long": 180
}

DASHBOARD_COLORS = {
    "projection": "#FFA500",
    "historical": "#888888",
    "alert": "#FF0000"
}

st.set_page_config(page_title="Hot Blast Stove Heat Balance", layout="wide")
st.title("🔥 Hot Blast Stove Heat Balance Dashboard")

# -----------------------------
# File Upload
# -----------------------------
st.sidebar.header("Step 1: Upload Your Cycle Data (.csv)")
uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, parse_dates=['timestamp'])
    st.success("Data uploaded successfully!")

    # Sidebar Inputs
    st.sidebar.header("What-If Analysis & Thresholds")
    eff_low = st.sidebar.slider("Efficiency Alert Threshold (%)", 40, 90, int(THRESHOLDS["efficiency_low"]*100))/100
    shell_high = st.sidebar.slider("Shell Temp Alert (°C)", 80, 200, THRESHOLDS["shell_temp_high"])
    cycle_long = st.sidebar.slider("Long Cycle Duration (min)", 60, 300, THRESHOLDS["cycle_duration_long"])

    st.sidebar.header("What-If Inputs")
    stove_select = st.sidebar.selectbox("Stove ID", sorted(df['stove_id'].unique()))
    latest = get_latest_cycle(df, stove_select)

    # What-If Form
    st.markdown("## 🟧 Projections (Orange) – Current Cycle / What-If")
    with st.form("whatif_form"):
        st.write("Modify values for what-if analysis:")
        m_fuel = st.number_input("Fuel Flow Rate (Nm³/hr)", value=float(latest["m_fuel"]), min_value=0.0)
        cv_fuel = st.number_input("Fuel Calorific Value (MJ/Nm³)", value=float(latest["cv_fuel"]), min_value=0.0)
        eta_comb = st.number_input("Combustion Efficiency", value=float(latest["eta_combustion"]), min_value=0.0, max_value=1.0)
        m_air = st.number_input("Blast Air Flow Rate (kg/hr)", value=float(latest["m_air"]), min_value=0.0)
        t_hot_blast = st.number_input("Hot Blast Temp (°C)", value=float(latest["t_hot_blast"]), min_value=0.0)
        t_ambient = st.number_input("Ambient Temp (°C)", value=float(latest["t_ambient"]), min_value=0.0)
        m_flue = st.number_input("Flue Gas Flow (kg/hr)", value=float(latest["m_flue"]), min_value=0.0)
        t_flue = st.number_input("Flue Gas Temp (°C)", value=float(latest["t_flue"]), min_value=0.0)
        t_ref = st.number_input("Flue Gas Ref Temp (°C)", value=float(latest["t_ref"]), min_value=0.0)
        k = st.number_input("Shell Conductivity (W/mK)", value=float(latest["k"]), min_value=0.0)
        A = st.number_input("Shell Area (m²)", value=float(latest["A"]), min_value=0.0)
        t_internal = st.number_input("Internal Temp (°C)", value=float(latest["t_internal"]), min_value=0.0)
        t_surface = st.number_input("Shell Surface Temp (°C)", value=float(latest["t_surface"]), min_value=0.0)
        d = st.number_input("Shell Thickness (m)", value=float(latest["d"]), min_value=0.01)
        eps = st.number_input("Shell Emissivity", value=float(latest["eps"]), min_value=0.0, max_value=1.0)
        sigma = float(latest["sigma"])
        m_air_comb = st.number_input("Combustion Air Flow (kg/hr)", value=float(latest["m_air_comb"]), min_value=0.0)
        t_air_comb = st.number_input("Combustion Air Temp (°C)", value=float(latest["t_air_comb"]), min_value=0.0)
        cp_air = float(latest["cp_air"])
        cp_flue = float(latest["cp_flue"])
        submitted = st.form_submit_button("Run What-If")

    if submitted:
        Q_fuel, Q_air_comb = calculate_heat_input(m_fuel, cv_fuel, eta_comb, m_air_comb, cp_air, t_air_comb, t_ambient)
        Q_blast = calculate_heat_output(m_air, cp_air, t_hot_blast, t_ambient)
        Q_flue = calculate_flue_loss(m_flue, cp_flue, t_flue, t_ref)
        Q_shell = calculate_shell_loss(k, A, t_internal, t_surface, d, eps, sigma, t_ambient)
        eta_stove = calculate_efficiency(Q_blast, Q_fuel, Q_air_comb, Q_flue, Q_shell)
        color = DASHBOARD_COLORS["projection"]

        st.markdown(f"<h3 style='color:{color}'>Stove Efficiency: {eta_stove*89.83:.1f}%</h3>", unsafe_allow_html=True)

        result_df = pd.DataFrame({
            'Metric': ['Heat Input', 'Useful Heat', 'Flue Loss', 'Shell Loss', 'Efficiency'],
            'Value': [Q_fuel + Q_air_comb, Q_blast, Q_flue, Q_shell, eta_stove*100]
        })

        bar_chart = alt.Chart(result_df).mark_bar(color=color).encode(
            x=alt.X('Metric', title='Parameter'),
            y=alt.Y('Value', title='Value (kJ or %)'),
            tooltip=['Metric', 'Value']
        ).properties(
            width=600,
            height=300,
            title="What-If Results"
        )
        st.altair_chart(bar_chart, use_container_width=True)

        if eta_stove < eff_low:
            st.markdown(f"<span style='color:{DASHBOARD_COLORS['alert']}'>⚠️ Efficiency Below Threshold!</span>", unsafe_allow_html=True)
        if t_surface > shell_high:
            st.markdown(f"<span style='color:{DASHBOARD_COLORS['alert']}'>⚠️ Shell Overheat!</span>", unsafe_allow_html=True)
    else:
        st.info("Run what-if to see updated projections.")
else:
    st.stop()
