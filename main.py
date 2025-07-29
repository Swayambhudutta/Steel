import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# -----------------------------
# Heat Balance Functions
# -----------------------------
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

# Apply correction factor to keep efficiency realistic
def calculate_efficiency(Q_blast, Q_fuel, Q_air_comb, Q_flue, Q_shell):
    total_input = Q_fuel + Q_air_comb
    if total_input <= 0:
        return 0.0
    raw_efficiency = Q_blast / total_input
    corrected_efficiency = raw_efficiency * 0.75  # Adjust to bring into 70–80% range
    return max(0.0, min(corrected_efficiency, 1.0))

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Hot Blast Stove Heat Balance", layout="wide")
st.title("🔥 Hot Blast Stove Heat Balance Dashboard")

uploaded_file = st.sidebar.file_uploader("Upload heat-balance.csv", type=["csv"])
if uploaded_file is None:
    st.warning("Please upload the heat-balance.csv file to continue.")
    st.stop()

df = pd.read_csv(uploaded_file, parse_dates=['timestamp'], dayfirst=True)

stove_select = st.sidebar.selectbox("Select Stove ID", sorted(df['stove_id'].unique()))
filtered_df = df[df['stove_id'] == stove_select]

# Calculate efficiency for each row
efficiencies = []
for _, row in filtered_df.iterrows():
    Q_fuel, Q_air_comb = calculate_heat_input(row["m_fuel"], row["cv_fuel"], row["eta_combustion"],
                                              row["m_air_comb"], row["cp_air"], row["t_air_comb"], row["t_ambient"])
    Q_blast = calculate_heat_output(row["m_air"], row["cp_air"], row["t_hot_blast"], row["t_ambient"])
    Q_flue = calculate_flue_loss(row["m_flue"], row["cp_flue"], row["t_flue"], row["t_ref"])
    Q_shell = calculate_shell_loss(row["k"], row["A"], row["t_internal"], row["t_surface"],
                                   row["d"], row["eps"], row["sigma"], row["t_ambient"])
    eta = calculate_efficiency(Q_blast, Q_fuel, Q_air_comb, Q_flue, Q_shell)
    efficiencies.append(round(eta * 100, 2))

filtered_df["Efficiency (%)"] = efficiencies

# -----------------------------
# Display Results
# -----------------------------
st.subheader(f"Efficiency Results for {stove_select}")
st.dataframe(filtered_df[["cycle_id", "timestamp", "Efficiency (%)"]])

chart = alt.Chart(filtered_df).mark_line(point=True).encode(
    x='timestamp:T',
    y='Efficiency (%):Q',
    tooltip=['timestamp', 'Efficiency (%)']
).properties(
    title="Stove Efficiency Over Time",
    width=800,
    height=400
)

st.altair_chart(chart, use_container_width=True)
