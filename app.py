import streamlit as st
import pandas as pd
import pydeck as pdk
import math
import time

# Page configuration
st.set_page_config(page_title="🚢 Enterprise Maritime GeoAI Platform", layout="wide")
st.title("🚢 Enterprise Maritime GeoAI Platform")
st.subheader("Live Vessel Tracking & Intelligent Route Analytics")

# Static coordinates
haifa_lat, haifa_lon = 32.8191, 34.9983
nynj_lat, nynj_lon = 40.6815, -74.1145

# Initialize session state
if 'live_progress' not in st.session_state:
    st.session_state['live_progress'] = 0
if 'simulation_running' not in st.session_state:
    st.session_state['simulation_running'] = False

# Sidebar controls
st.sidebar.header("🕹️ Fleet Control Center")
if st.sidebar.button("▶️ Launch Live Telemetry Stream"):
    st.session_state['simulation_running'] = True

if st.sidebar.button("⏸️ Pause Telemetry Stream"):
    st.session_state['simulation_running'] = False

if st.sidebar.button("🔄 Reset Voyage to Israel"):
    st.session_state['live_progress'] = 0
    st.session_state['simulation_running'] = False

# Slider for voyage progress
st.sidebar.write("Vessel Voyage Progress (%)")
voyage_progress = st.sidebar.slider(
    "Vessel Voyage Progress",
    0, 100,
    int(st.session_state['live_progress']),
    key='progress_slider'
)
st.session_state['live_progress'] = float(voyage_progress)

# Run simulation with smooth progress update
if st.session_state['simulation_running']:
    progress_bar = st.progress(st.session_state['live_progress'] / 100.0)
    for _ in range(int(st.session_state['live_progress']), 100):
        time.sleep(0.1)  # Delay for smooth update
        st.session_state['live_progress'] += 1
        progress_bar.progress(st.session_state['live_progress'] / 100.0)
        # Allow pause
        if not st.session_state['simulation_running']:
            break
    st.experimental_rerun()

# Display current progress
st.write(f"Vessel Voyage Progress: {int(st.session_state['live_progress'])}%")

# Calculate vessel position based on progress
progress_fraction = st.session_state['live_progress'] / 100.0

# Interpolated latitude and longitude
lat = haifa_lat + (nynj_lat - haifa_lat) * progress_fraction
lon = haifa_lon + (nynj_lon - haifa_lon) * progress_fraction

# Map data
vessel_data = pd.DataFrame([{
    'lat': lat,
    'lon': lon,
    'name': 'Vessel'
}])

# Map layers
layer = pdk.Layer(
    "ScatterplotLayer",
    data=vessel_data,
    get_position='[lon, lat]',
    get_color='[255, 0, 0, 160]',
    get_radius=50000,
)

# View state
view_state = pdk.ViewState(
    latitude=lat,
    longitude=lon,
    zoom=3,
    pitch=0,
)

# Render map
r = pdk.Deck(
    map_style='mapbox://styles/mapbox/light-v9',
    layers=[layer],
    initial_view_state=view_state,
)

st.pydeck_chart(r)

# Optional: Add more analytics or info below
st.write("Tracking vessel progress and route analytics in real-time.")
