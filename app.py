import streamlit as st
import pandas as pd
import pydeck as pdk
import math
import time
import requests
import numpy as np
from datetime import datetime, timedelta

# Page setup for enterprise layout
st.set_page_config(page_title="Maritime Intelligence - Risk Analysis", layout="wide")
st.title("🚢 Enterprise Maritime GeoAI Platform")
st.subheader("Live Vessel Tracking & Intelligent Route Analytics with Risk Prediction")

# Fixed Terminal Coordinates (Haifa to New York)
haifa_lat, haifa_lon = 32.8191, 34.9983
nynj_lat, nynj_lon = 40.6815, -74.1145

# Safe explicit color handles
h_red_val, h_green_val, h_blue_val = 0, 255, 0
n_red_val, n_green_val, n_blue_val = 255, 0, 0
cyan_r, cyan_g, cyan_b = 0, 191, 255
orange_r, orange_g, orange_b = 255, 140, 0
white_color, trail_green = 255, 127

# ==========================================
# 4D TIME ENGINE: STATE INITIALIZATION
# ==========================================
if 'live_progress' not in st.session_state:
    st.session_state.live_progress = 35.0
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = True
if 'time_counter' not in st.session_state:
    st.session_state.time_counter = 0
if 'traffic_offset' not in st.session_state:
    st.session_state.traffic_offset = np.random.uniform(-3, 3, 4)
if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = time.time()
if 'risk_history' not in st.session_state:
    st.session_state.risk_history = []

# ==========================================
# GEOSPATIAL MATHEMATICS
# ==========================================
def calculate_distance(lat1, lon1, lat2, lon2):
    r_lat1, r_lon1, r_lat2, r_lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((r_lat2 - r_lat1)/2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin((r_lon2 - r_lon1)/2)**2
    return round(2 * math.asin(math.sqrt(a)) * 3440.065, 1)

# ==========================================
# SIDEBAR CONTROL ROOM
# ==========================================
st.sidebar.header("🕹️ Fleet Control Center")

sim_toggle = st.sidebar.button(
    label="⏸️ Pause Telemetry Stream" if st.session_state.simulation_running else "▶️ Launch Live Telemetry Stream"
)

if sim_toggle:
    st.session_state.simulation_running = not st.session_state.simulation_running
    if st.session_state.simulation_running:
        st.session_state.last_update_time = time.time()

vessel_speed_knots = st.sidebar.slider("Vessel Cruising Speed (Knots)", 5.0, 35.0, 20.0, 0.5)

# Auto-update progress when simulation is running
if st.session_state.simulation_running:
    current_time = time.time()
    time_delta = current_time - st.session_state.last_update_time
    st.session_state.last_update_time = current_time
    
    speed_factor = vessel_speed_knots / 20.0
    progress_increment = 0.15 * speed_factor * (time_delta / 0.1)
    
    if st.session_state.live_progress < 100.0:
        st.session_state.live_progress = min(100.0, st.session_state.live_progress + progress_increment)
        st.session_state.time_counter += 1
        
        if st.session_state.time_counter % 30 == 0:
            st.session_state.traffic_offset = np.random.uniform(-3, 3, 4)
    else:
        st.session_state.simulation_running = False
        st.success("🎉 Voyage Complete! Ship has arrived at destination!")

voyage_progress = st.sidebar.slider(
    label="Vessel Voyage Progress (%)", 
    min_value=0, 
    max_value=100, 
    value=int(st.session_state.live_progress)
)
if voyage_progress != int(st.session_state.live_progress):
    st.session_state.live_progress = float(voyage_progress)

cargo_profile = st.sidebar.selectbox("Cargo Priority Profile", ["Standard Freight", "High-Value Express", "Eco-Friendly Slow Steaming"])

auto_play = st.sidebar.checkbox("🔄 Auto-Advance Voyage", value=st.session_state.simulation_running)
if auto_play != st.session_state.simulation_running:
    st.session_state.simulation_running = auto_play
    if st.session_state.simulation_running:
        st.session_state.last_update_time = time.time()

if st.sidebar.button("🔄 Reset Voyage"):
    st.session_state.live_progress = 0.0
    st.session_state.simulation_running = True
    st.session_state.time_counter = 0
    st.session_state.traffic_offset = np.random.uniform(-3, 3, 4)
    st.session_state.last_update_time = time.time()
    st.session_state.risk_history = []
    st.rerun()

# Calculate current position
total_trip_distance = calculate_distance(haifa_lat, haifa_lon, nynj_lat, nynj_lon)
fraction = st.session_state.live_progress / 100.0
vessel_current_lat = haifa_lat + (nynj_lat - haifa_lat) * fraction
vessel_current_lon = haifa_lon + (nynj_lon - haifa_lon) * fraction
distance_remaining_nm = calculate_distance(vessel_current_lat, vessel_current_lon, nynj_lat, nynj_lon)
distance_covered_nm = round(total_trip_distance - distance_remaining_nm, 1)

# ==========================================
# 🛰️ LIVE API WEATHER (MUST BE BEFORE RISK CALCULATION)
# ==========================================
try:
    api_url = f"https://api.open-meteo.com/v1/forecast?latitude={vessel_current_lat}&longitude={vessel_current_lon}&current_weather=true"
    response = requests.get(api_url, timeout=3).json()
    if 'current_weather' in response and 'windspeed' in response['current_weather']:
        real_wind_kmh = response['current_weather']['windspeed']
        live_wind_knots = round(real_wind_kmh * 0.539957, 1)
        data_source_label = "📡 Connected Live to Satellite Open-Meteo Server Feed"
    else:
        raise Exception("Weather data not available")
except:
    live_wind_knots = round(12.0 + (math.sin(fraction * math.pi) * 22.0), 1)
    data_source_label = "⚠️ Local Telemetry Backup System Online"

# Weather alert based on wind
if live_wind_knots >= 24.0:
    weather_alert, weather_color = "🚨 HEAVY WEATHER ALERT", "inverse"
elif live_wind_knots >= 15.0:
    weather_alert, weather_color = "⚠️ Moderate Chop", "off"
else:
    weather_alert, weather_color = "✅ Calm Sea Conditions", "normal"

# Bathymetry calculation
simulated_depth_meters = round(-15.0 - (math.sin(fraction * math.pi) * 4985.0), 1)
bathymetry_status = "🚨 CRITICAL SHALLOW RISK" if abs(simulated_depth_meters) < 18.0 else "✅ Safe Deep Water"
risk_color = "inverse" if abs(simulated_depth_meters) < 18.0 else "off"

# ==========================================
# RISK PREDICTION ENGINE
# ==========================================
def calculate_risk_score(progress, wind_speed, depth, speed):
    """Calculate comprehensive risk score 0-100"""
    # Weather risk (0-30 points)
    if wind_speed >= 30:
        weather_risk = 30
    elif wind_speed >= 20:
        weather_risk = 20 + (wind_speed - 20) * 1
    elif wind_speed >= 10:
        weather_risk = 10 + (wind_speed - 10) * 1
    else:
        weather_risk = wind_speed * 1
    
    # Depth risk (0-30 points)
    depth_abs = abs(depth)
    if depth_abs < 100:
        depth_risk = 30
    elif depth_abs < 500:
        depth_risk = 20 + (500 - depth_abs) / 400 * 10
    elif depth_abs < 2000:
        depth_risk = 10 + (2000 - depth_abs) / 1500 * 10
    else:
        depth_risk = max(0, 10 - (depth_abs - 2000) / 1000 * 10)
    
    # Speed risk (0-20 points)
    if speed > 30:
        speed_risk = 20
    elif speed > 20:
        speed_risk = 10 + (speed - 20) * 1
    else:
        speed_risk = speed * 0.5
    
    # Proximity to ports (0-20 points)
    if progress < 10:
        port_risk = 20 - progress * 2
    elif progress > 90:
        port_risk = 20 - (100 - progress) * 2
    else:
        port_risk = 0
    
    total_risk = min(100, weather_risk + depth_risk + speed_risk + port_risk)
    return round(total_risk)

def get_risk_level(score):
    if score >= 70:
        return "🔴 CRITICAL", "inverse"
    elif score >= 50:
        return "🟠 HIGH", "inverse"
    elif score >= 30:
        return "🟡 MODERATE", "off"
    else:
        return "🟢 LOW", "normal"

def get_risk_factors(score, progress, wind_speed, depth, speed):
    factors = []
    if score >= 70:
        factors.append("🚨 Immediate action required")
    if score >= 50:
        factors.append("⚠️ Caution advised")
    if abs(depth) < 100:
        factors.append("🌊 Shallow waters ahead")
    if wind_speed >= 20:
        factors.append("💨 Strong winds detected")
    if speed > 25:
        factors.append("⚡ High speed in sensitive area")
    if progress < 10:
        factors.append("🏗️ Port congestion zone - Departure")
    elif progress > 90:
        factors.append("🏗️ Approaching busy port - Arrival")
    if 40 < progress < 60:
        factors.append("🌊 Mid-ocean crossing - Monitor conditions")
    return factors

# Calculate current risk (NOW live_wind_knots is defined)
risk_score = calculate_risk_score(st.session_state.live_progress, live_wind_knots, simulated_depth_meters, vessel_speed_knots)
risk_level, risk_delta_color = get_risk_level(risk_score)
risk_factors = get_risk_factors(risk_score, st.session_state.live_progress, live_wind_knots, simulated_depth_meters, vessel_speed_knots)

# Store risk history
st.session_state.risk_history.append({
    'progress': st.session_state.live_progress,
    'risk_score': risk_score,
    'time': datetime.now().strftime('%H:%M:%S')
})
if len(st.session_state.risk_history) > 100:
    st.session_state.risk_history = st.session_state.risk_history[-100:]

# ==========================================
# 🚢 FLEET DATA
# ==========================================
traffic_offset = st.session_state.traffic_offset

other_traffic_df = pd.DataFrame({
    'latitude': [
        38.5 + traffic_offset[0], 
        34.2 + traffic_offset[1], 
        41.1 + traffic_offset[2], 
        35.8 + traffic_offset[3]
    ],
    'longitude': [
        -35.4 + traffic_offset[0] * 0.5, 
        -42.1 + traffic_offset[1] * 0.5, 
        -22.5 + traffic_offset[2] * 0.5, 
        -50.2 + traffic_offset[3] * 0.5
    ],
    'vessel_name': ['MV-Rotterdam-Express', 'MV-Atlantic-Titan', 'MV-Hamburg-Carrier', 'MV-Tokyo-Maru'],
    'type': ['Neighboring Traffic', 'Neighboring Traffic', 'Neighboring Traffic', 'Neighboring Traffic']
})

your_vessel_df = pd.DataFrame({
    'latitude': [vessel_current_lat],
    'longitude': [vessel_current_lon],
    'vessel_name': ['⭐ MV-YOUR-CARGO (Israel -> USA)'],
    'type': ['Target Asset']
})

ship_ports_df = pd.DataFrame({
    'latitude': [haifa_lat, nynj_lat], 
    'longitude': [haifa_lon, nynj_lon],
    'port_name': ['Port of Haifa (Origin)', 'Port of NY/NJ (Destination)'],
    'color_r': [h_red_val, n_red_val], 
    'color_g': [h_green_val, n_green_val], 
    'color_b': [h_blue_val, n_blue_val]
})

route_data = pd.DataFrame({
    'start_lon': [haifa_lon], 
    'start_lat': [haifa_lat], 
    'end_lon': [nynj_lon], 
    'end_lat': [nynj_lat]
})

# ==========================================
# CREATE BORDERS AND BOUNDARIES
# ==========================================
borders_data = pd.DataFrame([
    {'lat1': 30.0, 'lon1': 30.0, 'lat2': 30.0, 'lon2': 40.0, 'name': 'Mediterranean Sea'},
    {'lat1': 30.0, 'lon1': 40.0, 'lat2': 35.0, 'lon2': 40.0, 'name': 'Mediterranean Sea'},
    {'lat1': 35.0, 'lon1': -5.5, 'lat2': 36.0, 'lon2': -5.5, 'name': 'Strait of Gibraltar'},
    {'lat1': 36.0, 'lon1': -10.0, 'lat2': 40.0, 'lon2': -10.0, 'name': 'Atlantic Ocean'},
    {'lat1': 40.0, 'lon1': -75.0, 'lat2': 42.0, 'lon2': -75.0, 'name': 'US Coastal Waters'},
    {'lat1': 42.0, 'lon1': -75.0, 'lat2': 42.0, 'lon2': -70.0, 'name': 'US Coastal Waters'},
])

# Shipping lane corridor
corridor_points = []
for i in range(11):
    f = i / 10.0
    lat = haifa_lat + (nynj_lat - haifa_lat) * f
    lon = haifa_lon + (nynj_lon - haifa_lon) * f
    offset_lat = 2.0 * math.sin(f * math.pi)
    offset_lon = 2.0 * math.cos(f * math.pi)
    corridor_points.append({'lat': lat + offset_lat, 'lon': lon + offset_lon})
    corridor_points.append({'lat': lat - offset_lat, 'lon': lon - offset_lon})
corridor_df = pd.DataFrame(corridor_points)

# Voyage calculations
total_hours_remaining = distance_remaining_nm / vessel_speed_knots if vessel_speed_knots > 0 else 0
days = int(total_hours_remaining // 24)
hours = int(total_hours_remaining % 24)
dynamic_burn_per_day = 45.0 * ((vessel_speed_knots / 20.0) ** 3) if vessel_speed_knots > 0 else 0
predicted_fuel_mt = round(dynamic_burn_per_day * (total_hours_remaining / 24.0), 1)
total_co2_emissions_mt = round(predicted_fuel_mt * 3.114, 1)

# Trail segments
trail_points = []
step_count = int(st.session_state.live_progress)

for i in range(0, step_count + 1):
    f = i / 100.0
    trail_points.append({
        'lon': haifa_lon + (nynj_lon - haifa_lon) * f, 
        'lat': haifa_lat + (nynj_lat - haifa_lat) * f
    })

trail_df = pd.DataFrame(trail_points)

history_segments = []
if len(trail_df) > 1:
    for idx in range(len(trail_df) - 1):
        history_segments.append({
            's_lon': trail_df.iloc[idx]['lon'], 
            's_lat': trail_df.iloc[idx]['lat'],
            'e_lon': trail_df.iloc[idx+1]['lon'], 
            'e_lat': trail_df.iloc[idx+1]['lat']
        })
history_df = pd.DataFrame(history_segments)

# Depth analytics
depth_data = []
for i in range(101):
    f = i / 100.0
    if i == 0 or i == 100:
        d = 15.0
    else:
        d = abs(-15.0 - (math.sin(f * math.pi) * 4985.0))
    depth_data.append({'Voyage Progress (%)': i, 'Ocean Depth (m)': d})
analytics_df = pd.DataFrame(depth_data).set_index('Voyage Progress (%)')

# ==========================================
# RENDER LAYOUT
# ==========================================
if st.session_state.simulation_running:
    st.sidebar.success("🟢 LIVE TELEMETRY ACTIVE")
else:
    st.sidebar.warning("⏸️ TELEMETRY PAUSED")

# Top risk banner
risk_bg_color = '#ff4444' if risk_score >= 50 else '#ffaa00' if risk_score >= 30 else '#44ff44'
st.markdown(f"""
<div style="background-color: {risk_bg_color}; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
    <h3 style="color: white; margin: 0;">⚠️ RISK PREDICTION: {risk_level} (Score: {risk_score}/100)</h3>
</div>
""", unsafe_allow_html=True)

# Risk factors
if risk_factors:
    st.warning("🔔 **Risk Factors Detected:** " + " | ".join(risk_factors))

m1, m2, m3 = st.columns(3)
m1.metric("🗺️ Remaining Distance", f"{distance_remaining_nm} NM", delta=f"{distance_covered_nm} NM Covered")
m2.metric("⏱️ ETA Countdown", f"{days}d {hours}h", delta=f"Speed: {vessel_speed_knots} kts")
m3.metric("📦 Cargo Profile", cargo_profile)

st.markdown("##### Environmental, Weather & Real-Time Fleet Telemetry")
e1, e2, e3, e4, e5 = st.columns(5)
e1.metric("⛽ Fuel ETE", f"{predicted_fuel_mt} MT")
e2.metric("🌱 CO2 Impact", f"{total_co2_emissions_mt} MT")
e3.metric("🌊 Depth", f"{simulated_depth_meters} m", delta=bathymetry_status, delta_color=risk_color)
e4.metric("💨 Wind", f"{live_wind_knots} kts", delta=weather_alert, delta_color=weather_color, help=data_source_label)
e5.metric("⚠️ Risk Score", f"{risk_score}/100", delta=risk_level, delta_color=risk_delta_color)

st.markdown("---")

# ==========================================
# ENHANCED MAP WITH BORDERS AND 20M VIEW
# ==========================================
layer_borders = pdk.Layer(
    'LineLayer',
    data=borders_data,
    get_source_position='[lon1, lat1]',
    get_target_position='[lon2, lat2]',
    get_color=[255, 255, 0, 150],
    get_width=2
)

layer_corridor = pdk.Layer(
    'ScatterplotLayer',
    data=corridor_df,
    get_position='[lon, lat]',
    get_color=[0, 100, 255, 80],
    get_radius=50000,
    opacity=0.3
)

layer_ports = pdk.Layer(
    'ScatterplotLayer', 
    data=ship_ports_df, 
    get_position='[longitude, latitude]', 
    get_color='[color_r, color_g, color_b, 200]', 
    get_radius=80000,
    pickable=True,
    tooltip={"text": "Port: {port_name}"}
)

layer_arc = pdk.Layer(
    'ArcLayer', 
    data=route_data, 
    get_source_position='[start_lon, start_lat]', 
    get_target_position='[end_lon, end_lat]', 
    get_source_color=[cyan_r, cyan_g, cyan_b, 180], 
    get_target_color=[orange_r, orange_g, orange_b, 180], 
    get_width=3
)

layer_trail = None
if not history_df.empty:
    layer_trail = pdk.Layer(
        'LineLayer', 
        data=history_df, 
        get_source_position='[s_lon, s_lat]', 
        get_target_position='[e_lon, e_lat]', 
        get_color=[0, 255, 100, 200], 
        get_width=6
    )

layer_traffic = pdk.Layer(
    'ScatterplotLayer', 
    data=other_traffic_df,
    get_position='[longitude, latitude]',
    get_color=[160, 160, 160, 200],  
    get_radius=50000, 
    pickable=True,
    tooltip={"text": "Vessel: {vessel_name}\nType: {type}"}
)

layer_target_vessel = pdk.Layer(
    'ScatterplotLayer', 
    data=your_vessel_df,
    get_position='[longitude, latitude]',
    get_color=[255, 255, 0, 255],    
    get_radius=120000, 
    pickable=True,
    tooltip={"text": "{vessel_name}\nType: {type}\nProgress: " + str(round(st.session_state.live_progress, 1)) + "%"}
)

# Risk zone overlay
risk_radius = 150000 + (risk_score / 100) * 200000
risk_color_r = 255 if risk_score >= 50 else 255 if risk_score >= 30 else 0
risk_color_g = 0 if risk_score >= 50 else 200 if risk_score >= 30 else 255
risk_color_b = 0 if risk_score >= 50 else 0 if risk_score >= 30 else 0

layer_risk_zone = pdk.Layer(
    'ScatterplotLayer',
    data=pd.DataFrame({
        'latitude': [vessel_current_lat],
        'longitude': [vessel_current_lon],
        'risk_level': [risk_level]
    }),
    get_position='[longitude, latitude]',
    get_color=[risk_color_r, risk_color_g, risk_color_b, 100],
    get_radius=risk_radius,
    pickable=True,
    tooltip={"text": "Risk Zone: {risk_level}"}
)

active_layers = [layer_borders, layer_corridor, layer_arc, layer_ports, layer_traffic, layer_risk_zone]
if layer_trail is not None:
    active_layers.append(layer_trail)
active_layers.append(layer_target_vessel)

# Center map on ship
map_center_lat = vessel_current_lat
map_center_lon = vessel_current_lon

# Zoom level - closer view from 20 meters above
if st.session_state.live_progress < 10 or st.session_state.live_progress > 90:
    zoom_level = 5.5
else:
    zoom_level = 4.5

st.pydeck_chart(pdk.Deck(
    map_style='mapbox://styles/mapbox/satellite-streets-v11',
    initial_view_state=pdk.ViewState(
        latitude=map_center_lat, 
        longitude=map_center_lon, 
        zoom=zoom_level,        
        pitch=0,
        bearing=0
    ),
    layers=active_layers,
    tooltip={"text": "{vessel_name}\nClassification: {type}"}
))

# Map legend
st.markdown("### 🗺️ Map Legend")
legend_col1, legend_col2, legend_col3, legend_col4 = st.columns(4)
legend_col1.markdown("🟡 **Your Ship** (Yellow)")
legend_col2.markdown("🔵 **Shipping Lane** (Blue)")
legend_col3.markdown("🟢 **Ports** (Green/Red)")
legend_col4.markdown(f"🔴 **Risk Zone** ({risk_level})")

# Border information
st.markdown("### 🌍 Border & Navigation Information")
border_col1, border_col2 = st.columns(2)

current_region = "Mediterranean Sea"
if vessel_current_lon < -5.5 and vessel_current_lon > -10:
    current_region = "Strait of Gibraltar"
elif vessel_current_lon < -10 and vessel_current_lon > -60:
    current_region = "Atlantic Ocean"
elif vessel_current_lon < -60:
    current_region = "US Coastal Waters"

border_col1.info(f"📍 **Current Region:** {current_region}")
border_col2.info(f"🗺️ **Position:** {vessel_current_lat:.2f}°N, {abs(vessel_current_lon):.2f}°{'W' if vessel_current_lon < 0 else 'E'}")

# ==========================================
# RISK HISTORY CHART
# ==========================================
st.markdown("### 📊 Risk Score History (Last 100 updates)")
if len(st.session_state.risk_history) > 1:
    risk_df = pd.DataFrame(st.session_state.risk_history)
    st.line_chart(risk_df.set_index('progress')['risk_score'])
else:
    st.info("Collecting risk data...")

# ==========================================
# CHARTS AND TELEMETRY
# ==========================================
st.markdown("### 📈 Voyage Time-Series Bathymetric Risk Predictor")
st.line_chart(analytics_df['Ocean Depth (m)'])

st.markdown("### 📡 Active Satellite System Telemetry Stream")
col1, col2, col3 = st.columns(3)

if st.session_state.simulation_running:
    status_icon = "🟢 LIVE"
    status_delta = "Streaming"
else:
    status_icon = "⏸️ PAUSED"
    status_delta = "Stopped"

col1.metric("Vessel Status", f"{status_icon}", delta=status_delta)
col2.metric("Voyage Progress", f"{round(st.session_state.live_progress, 1)}%", delta=f"{distance_covered_nm} NM traveled")
col3.metric("Risk Level", f"{risk_level}", delta=f"Score: {risk_score}/100")

st.markdown("### 📍 Current Vessel Position")
st.info(f"**Latitude:** {vessel_current_lat:.4f}° | **Longitude:** {vessel_current_lon:.4f}° | **View:** Top-down at {zoom_level}x zoom | **Altitude:** 20 meters")

st.markdown("### ⏱️ Real-Time ETA Countdown")
progress_bar = st.progress(st.session_state.live_progress / 100.0)
col1, col2 = st.columns(2)
col1.write(f"**Distance Remaining:** {distance_remaining_nm} NM")
col2.write(f"**Estimated Arrival:** {days}d {hours}h at {vessel_speed_knots} knots")

# ==========================================
# AUTO-REFRESH
# ==========================================
if st.session_state.simulation_running and st.session_state.live_progress < 100.0:
    time.sleep(0.05)
    st.rerun()

# Footer
st.markdown("---")
st.caption("© 2026 Maritime Intelligence Platform | Real-time vessel tracking from Israel to USA | Risk Prediction & Border Monitoring Active")
