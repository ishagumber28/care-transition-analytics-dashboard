import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# PAGE CONFIG
st.set_page_config(layout="wide")

# TITLE
st.title("Care Transition Efficiency & Placement Outcome Analytics Dashboard")

st.markdown("""
This dashboard provides an end-to-end analysis of the CBP → HHS → Sponsor care pipeline, 
tracking how efficiently children move through the system while identifying delays, backlog accumulation, 
and breakdowns in placement outcomes that impact overall system performance.
""")

# LOAD DATA
df = pd.read_csv("hhs_children_transition_data.csv")

df.columns = [
    "Date", "Apprehended", "In_CBP",
    "Transferred_Out", "In_HHS", "Discharged"
]

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
df["In_HHS"] = df["In_HHS"].astype(str).str.replace(",", "").astype(float)
df.info()


# KPIs
df['transfer_efficiency'] = np.where(df['In_CBP'] == 0, 0, df['Transferred_Out'] / df['In_CBP'])
df['discharge_effectiveness'] = np.where(df['In_HHS'] == 0, 0, df['Discharged'] / df['In_HHS'])
df['throughput'] = np.where(df['Apprehended'] == 0, 0, df['Discharged'] / df['Apprehended'])
df['backlog_accumulation_rate'] = np.where(df['Transferred_Out'] == 0, 0,
    (df['Transferred_Out'] - df['Discharged']) / df['Transferred_Out'])
df['HHS_backlog_change'] = df['Transferred_Out'] - df['Discharged']

df['HHS_backlog_7d'] = df['HHS_backlog_change'].rolling(7).mean()
df['transfer_eff_7d'] = df['transfer_efficiency'].rolling(7).mean()
df['discharge_eff_7d'] = df['discharge_effectiveness'].rolling(7).mean()
df['throughput_7d'] = df['throughput'].rolling(7).mean()
df['outcome_stability'] = df['discharge_effectiveness'].rolling(7).std()

# DATE FILTER
with st.sidebar:
    st.header("Filters")
    start_date = st.date_input("Start Date", df["Date"].min())
    end_date = st.date_input("End Date", df["Date"].max())

df = df[(df["Date"] >= pd.to_datetime(start_date)) &
        (df["Date"] <= pd.to_datetime(end_date))]

# SAFE INDEXING (prevents crash)
if len(df) < 10:
    st.warning("Not enough data for KPI comparison")
    st.stop()

# KPI DISPLAY
st.header("📊 Key Performance Indicators")

col1, col2, col3, col4, col5 = st.columns(5)

te = df['transfer_eff_7d'].iloc[-1]
de = df['discharge_eff_7d'].iloc[-1]
tp = df['throughput_7d'].iloc[-1]
ba = df['backlog_accumulation_rate'].rolling(7).mean().iloc[-1]
os = df['outcome_stability'].iloc[-1]

te_prev = df['transfer_eff_7d'].iloc[-8]
de_prev = df['discharge_eff_7d'].iloc[-8]
tp_prev = df['throughput_7d'].iloc[-8]
ba_prev = df['backlog_accumulation_rate'].rolling(7).mean().iloc[-8]
os_prev = df['outcome_stability'].iloc[-8]

col1.metric("Transfer Eff.", round(te, 2), round(te - te_prev, 2))
col2.metric("Discharge Eff.", round(de, 3), round(de - de_prev, 3))
col3.metric("Throughput", round(tp, 2), round(tp - tp_prev, 2))
col4.metric("Backlog Rate", round(ba, 2), round(ba - ba_prev, 2))
col5.metric("Outcome Stability", round(os, 3), round(os - os_prev, 3))


# ALERTS
st.subheader("System Alerts")

tp_delta = tp - tp_prev

if tp_delta < -0.05:
    st.warning("⚠️ Throughput is declining, indicating weakening system performance")

if de < 0.01:
    st.error("🚨 Critical: Discharge effectiveness has collapsed below 1%")
elif de < 0.03:
    st.warning("⚠️ Warning: Discharge effectiveness is low")

if tp < 1:
    st.error("🚨 Critical: Throughput below 1 → system not clearing cases")
elif tp < 1.2:
    st.warning("⚠️ Throughput weakening")

if ba > 0:
    st.warning("⚠️ Backlog accumulation detected")

if te < 0.5:
    st.warning("⚠️ Transfer efficiency is low")

st.markdown("---")

st.info("""
📌 Insight:
Despite low discharge effectiveness, throughput remains above 1 due to reduced inflow, 
not improved system efficiency. This indicates hidden structural weakness.
""")

# CLEAN PLOTTING FUNCTION (FIXED)
def plot_graph(x, y1, y2=None, title=""):
    fig, ax = plt.subplots(figsize=(10, 4))

    ax.plot(x, y1, alpha=0.3, label="Daily")
    if y2 is not None:
        ax.plot(x, y2, linewidth=2, label="7-Day Avg")

    ax.set_title(title)

    # ✅ FIX: proper horizontal dates
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.xticks(rotation=45,fontsize=8,ha='right')  # <- THIS fixes zig-zag

    ax.legend()
    ax.grid(True)

    st.pyplot(fig)

st.subheader("🚚 Transition Efficiency Analysis(CBP → HHS)")
st.caption("Short insight here")

plot_graph(df["Date"], df["transfer_efficiency"], df["transfer_eff_7d"],
           "Transfer Efficiency Trend")

st.markdown("""
Transfer efficiency remained relatively stable between 0.7–0.9 until early 2025, indicating consistent CBP-to-HHS transitions. A brief spike is observed around early 2025; however, this is not sustained. Post-2025, transfer efficiency declines significantly and stabilizes at lower levels (~0.3–0.5), suggesting reduced system performance and potential operational disruption.
Transfer efficiency was initially stable, but declined significantly after 2025, indicating reduced transition performance.
""")

st.markdown("---")

st.subheader("🏠 Discharge Effectiveness (HHS → Placement)")
plot_graph(df["Date"], df["discharge_effectiveness"], df["discharge_eff_7d"],
           "Discharge Effectiveness Trend")

st.markdown("""Discharge effectiveness remained relatively stable between 3–4% during the initial period, indicating consistent but limited placement capacity. However, a sharp structural decline is observed in early 2025, where effectiveness drops drastically below 1% and remains persistently low thereafter. This indicates a major disruption in the discharge process and sustained deterioration in placement outcomes.""")
st.markdown("---")

# INFLOW VS OUTFLOW
st.subheader("🔄 System Flow (Inflow vs Outflow)")

fig, ax = plt.subplots(figsize=(10,5))
ax.plot(df["Date"], df["Apprehended"], label="Inflow")
ax.plot(df["Date"], df["Discharged"], label="Outflow")
ax.legend()
ax.set_title("Inflow vs Outflow")
ax.tick_params(axis='x', rotation=45)
ax.grid(True)

st.pyplot(fig)

st.markdown("""
Initially, discharge volumes exceeded intake levels, indicating effective case clearance and backlog reduction. Over time, the gap between inflow and outflow narrowed, suggesting a transition towards equilibrium. However, a sharp decline in both apprehensions and discharges is observed around early 2025. Despite reduced inflow, discharge volumes remain disproportionately low, aligning with the observed collapse in discharge effectiveness and indicating persistent inefficiency in the system.""")

st.markdown("---")

# BACKLOG
st.subheader("📦 Backlog Accumulation")

plot_graph(df["Date"], df["HHS_backlog_change"], df["HHS_backlog_7d"],
           "HHS Backlog Trend")

st.markdown("""
Backlog trends indicate that during the early phase, the system was effectively clearing cases, as reflected by consistently negative backlog values. However, from mid-2024 onwards, the backlog trend shifts toward positive values, indicating sustained accumulation of cases within the HHS stage. Although the system stabilizes near equilibrium after early 2025, this is driven by reduced inflow rather than improved discharge efficiency, confirming persistent inefficiency in case resolution.
""")
st.markdown("---")

# OUTCOME STABILITY
st.subheader("📊 Outcome Stability & Throughput")

fig, ax = plt.subplots(figsize=(10,5))
ax.plot(df["Date"], df["outcome_stability"], label="Variability")
ax.legend()
ax.set_title("Outcome Stability")
ax.tick_params(axis='x', rotation=45)
ax.grid(True)
st.pyplot(fig)

st.markdown("""
Outcome stability analysis shows moderate variability in discharge effectiveness during the initial period, indicating inconsistent but active system performance. However, a sharp decline in variability is observed after early 2025. While this suggests increased consistency, it coincides with a collapse in discharge effectiveness, indicating that the system has stabilized at a consistently low level of performance rather than improving operational stability.
""")
st.markdown("---")

# THROUGHPUT
st.subheader("⚙️ Pipeline Throughput")
plot_graph(df["Date"], df["throughput"], df["throughput_7d"],
           "Pipeline Throughput Trend")

st.markdown("""
Pipeline throughput initially remains high, indicating strong backlog clearance where discharge volumes significantly exceed new inflows. However, throughput declines over time, approaching equilibrium levels by late 2024, suggesting reduced system efficiency. Although intermittent spikes are observed in 2025, these are not sustained, and overall throughput remains inconsistent, reflecting unstable and weakening end-to-end system performance.""")

# FINAL CONCLUSION
st.markdown("---")
st.subheader("📌 Final Conclusion")

st.markdown("""
The care pipeline initially operated efficiently, with stable transfer rates and effective backlog clearance. 
However, a structural breakdown emerges around early 2025, marked by a sharp decline in discharge effectiveness, 
reduced transfer efficiency, and growing backlog accumulation.

The analysis identifies the HHS discharge stage as the primary bottleneck, where reduced placement capacity limits 
overall system performance. As a result, throughput becomes inconsistent and the system stabilizes at a lower level of efficiency.

These findings highlight the need for improvements in discharge processes and case management workflows to restore 
system performance and support timely reunification outcomes.
""")

