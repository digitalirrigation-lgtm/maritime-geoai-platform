import streamlit as st
import pandas as pd
import pydeck as pdk
import math
import time
import requests
import numpy as np
from datetime import datetime, timedelta
import json

# Page setup for enterprise layout
st.set_page_config(page_title="Maritime Intelligence - GIS & Sensors", layout="wide")
st.title("🚢 Enterprise Maritime GeoAI Platform")
st.subheader("Live Vessel Tracking • GIS Mapping • Sensor Network • Risk Prediction")

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
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = []

# ==========================================
# GEOSPATIAL MATHEMATICS
# ==========================================
def calculate_distance(lat1, lon1, lat2, lon2):
    r_lat1, r_lon1, r_lat2, r_lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((r_lat2 - r_lat1)/2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin((r_lon2 - r_lon1)/2)**2
    return round(2 * math.asin(math.sqrt(a)) * 3440.065, 1)

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate bearing between two points"""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.atan2(x, y)
    return round(math.degrees(bearing), 1)

def get_zone_info(lat, lon):
    """Get maritime zone information"""
    if lon < -60:
        return "US Exclusive Economic Zone (EEZ)", "🇺🇸"
    elif lon < -10:
        return "International Waters - Atlantic", "🌊"
    elif lon < -5.5:
        return "Strait of Gibraltar", "🌉"
    elif lon < 30:
        return "Mediterranean Sea", "🌅"
    else:
        return "Eastern Mediterranean", "🌊"

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
    st.session_state.sensor_data = []
    st.rerun()

# GIS Layer Controls in Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("🗺️ GIS Layer Controls")
show_bathymetry = st.sidebar.checkbox("Show Bathymetry", value=True)
show_currents = st.sidebar.checkbox("Show Ocean Currents", value=True)
show_sensors = st.sidebar.checkbox("Show Sensor Network", value=True)
show_weather = st.sidebar.checkbox("Show Weather Fronts", value=True)
show_ais = st.sidebar.checkbox("Show AIS Targets", value=True)

# Calculate current position
total_trip_distance = calculate_distance(haifa_lat, haifa_lon, nynj_lat, nynj_lon)
fraction = st.session_state.live_progress / 100.0
vessel_current_lat = haifa_lat + (nynj_lat - haifa_lat) * fraction
vessel_current_lon = haifa_lon + (nynj_lon - haifa_lon) * fraction
distance_remaining_nm = calculate_distance(vessel_current_lat, vessel_current_lon, nynj_lat, nynj_lon)
distance_covered_nm = round(total_trip_distance - distance_remaining_nm, 1)

# Calculate bearing
current_bearing = calculate_bearing(vessel_current_lat, vessel_current_lon, nynj_lat, nynj_lon)

# ==========================================
# 🛰️ LIVE API WEATHER & SENSORS
# ==========================================
try:
    api_url = f"https://api.open-meteo.com/v1/forecast?latitude={vessel_current_lat}&longitude={vessel_current_lon}&current_weather=true&hourly=temperature_2m,relative_humidity_2m,precipitation,pressure_msl"
    response = requests.get(api_url, timeout=3).json()
    if 'current_weather' in response and 'windspeed' in response['current_weather']:
        real_wind_kmh = response['current_weather']['windspeed']
        live_wind_knots = round(real_wind_kmh * 0.539957, 1)
        temperature = response['current_weather']['temperature'] if 'temperature' in response['current_weather'] else 20.0
        data_source_label = "📡 Connected Live to Satellite Open-Meteo Server Feed"
    else:
        raise Exception("Weather data not available")
except:
    live_wind_knots = round(12.0 + (math.sin(fraction * math.pi) * 22.0), 1)
    temperature = 20.0 + (math.sin(fraction * math.pi) * 5.0)
    data_source_label = "⚠️ Local Telemetry Backup System Online"

# Generate sensor data
sensor_data = {
    'timestamp': datetime.now().strftime('%H:%M:%S'),
    'wind_speed': live_wind_knots,
    'temperature': round(temperature, 1),
    'humidity': round(65 + 15 * math.sin(fraction * math.pi), 1),
    'pressure': round(1013 + 20 * math.sin(fraction * math.pi * 0.5), 1),
    'wave_height': round(1.5 + 3.5 * math.sin(fraction * math.pi * 2), 1),
    'water_temp': round(15 + 10 * (fraction), 1),
    'salinity': round(35 + 2 * math.sin(fraction * math.pi), 1)
}

# Store sensor history
st.session_state.sensor_data.append(sensor_data)
if len(st.session_state.sensor_data) > 50:
    st.session_state.sensor_data = st.session_state.sensor_data[-50:]

# Weather alert
if live_wind_knots >= 24.0:
    weather_alert, weather_color = "🚨 HEAVY WEATHER ALERT", "inverse"
elif live_wind_knots >= 15.0:
    weather_alert, weather_color = "⚠️ Moderate Chop", "off"
else:
    weather_alert, weather_color = "✅ Calm Sea Conditions", "normal"

# Bathymetry
simulated_depth_meters = round(-15.0 - (math.sin(fraction * math.pi) * 4985.0), 1)
bathymetry_status = "🚨 CRITICAL SHALLOW RISK" if abs(simulated_depth_meters) < 18.0 else "✅ Safe Deep Water"
risk_color = "inverse" if abs(simulated_depth_meters) < 18.0 else "off"

# ==========================================
# RISK PREDICTION ENGINE
# ==========================================
def calculate_risk_score(progress, wind_speed, depth, speed):
    weather_risk = 30 if wind_speed >= 30 else 20 + (wind_speed - 20) * 1 if wind_speed >= 20 else 10 + (wind_speed - 10) * 1 if wind_speed >= 10 else wind_speed * 1
    depth_abs = abs(depth)
    depth_risk = 30 if depth_abs < 100 else 20 + (500 - depth_abs) / 400 * 10 if depth_abs < 500 else 10 + (2000 - depth_abs) / 1500 * 10 if depth_abs < 2000 else max(0, 10 - (depth_abs - 2000) / 1000 * 10)
    speed_risk = 20 if speed > 30 else 10 + (speed - 20) * 1 if speed > 20 else speed * 0.5
    port_risk = 20 - progress * 2 if progress < 10 else 20 - (100 - progress) * 2 if progress > 90 else 0
    total_risk = min(100, weather_risk + depth_risk + speed_risk + port_risk)
    return round(total_risk)

def get_risk_level(score):
    if score >= 70: return "🔴 CRITICAL", "inverse"
    elif score >= 50: return "🟠 HIGH", "inverse"
    elif score >= 30: return "🟡 MODERATE", "off"
    else: return "🟢 LOW", "normal"

risk_score = calculate_risk_score(st.session_state.live_progress, live_wind_knots, simulated_depth_meters, vessel_speed_knots)
risk_level, risk_delta_color = get_risk_level(risk_score)

# Store risk history
st.session_state.risk_history.append({
    'progress': st.session_state.live_progress,
    'risk_score': risk_score,
    'time': datetime.now().strftime('%H:%M:%S')
})
if len(st.session_state.risk_history) > 100:
    st.session_state.risk_history = st.session_state.risk_history[-100:]

# ==========================================
# 🚢 FLEET & GIS DATA
# ==========================================
traffic_offset = st.session_state.traffic_offset

# AIS Targets (simulated)
ais_targets = pd.DataFrame({
    'latitude': [
        38.5 + traffic_offset[0], 34.2 + traffic_offset[1], 
        41.1 + traffic_offset[2], 35.8 + traffic_offset[3],
        39.0 + traffic_offset[0]*0.5, 36.0 + traffic_offset[1]*0.5
    ],
    'longitude': [
        -35.4 + traffic_offset[0]*0.5, -42.1 + traffic_offset[1]*0.5, 
        -22.5 + traffic_offset[2]*0.5, -50.2 + traffic_offset[3]*0.5,
        -30.0 + traffic_offset[0]*0.3, -45.0 + traffic_offset[1]*0.3
    ],
    'vessel_name': ['MV-Rotterdam-Express', 'MV-Atlantic-Titan', 'MV-Hamburg-Carrier', 'MV-Tokyo-Maru', 'MV-Olympic-Star', 'MV-Celestial'],
    'type': ['Container', 'Tanker', 'Container', 'Bulk Carrier', 'Cruise', 'Cargo'],
    'speed': np.random.uniform(10, 25, 6),
    'course': np.random.uniform(0, 360, 6)
})

your_vessel_df = pd.DataFrame({
    'latitude': [vessel_current_lat],
    'longitude': [vessel_current_lon],
    'vessel_name': ['⭐ MV-YOUR-CARGO (Israel -> USA)'],
    'type': ['Target Asset'],
    'speed': [vessel_speed_knots],
    'course': [current_bearing]
})

ship_ports_df = pd.DataFrame({
    'latitude': [haifa_lat, nynj_lat, 35.0, 37.0], 
    'longitude': [haifa_lon, nynj_lon, -5.0, -25.0],
    'port_name': ['Port of Haifa (Origin)', 'Port of NY/NJ (Destination)', 'Gibraltar (Waypoint)', 'Azores (Waypoint)'],
    'color_r': [h_red_val, n_red_val, 255, 255], 
    'color_g': [h_green_val, n_green_val, 165, 165], 
    'color_b': [h_blue_val, n_blue_val, 0, 0]
})

route_data = pd.DataFrame({
    'start_lon': [haifa_lon], 
    'start_lat': [haifa_lat], 
    'end_lon': [nynj_lon], 
    'end_lat': [nynj_lat]
})

# ==========================================
# CREATE GIS LAYERS
# ==========================================

# 1. BATHYMETRY CONTOURS (simulated)
bathymetry_points = []
for i in range(20):
    f = i / 20.0
    lat = haifa_lat + (nynj_lat - haifa_lat) * f
    lon = haifa_lon + (nynj_lon - haifa_lon) * f
    for j in range(8):
        angle = j * math.pi / 4
        radius = 5 + f * 10
        bathymetry_points.append({
            'lat': lat + radius * math.cos(angle),
            'lon': lon + radius * math.sin(angle),
            'depth': abs(simulated_depth_meters) * (1 + 0.3 * math.sin(f * math.pi + j))
        })
bathymetry_df = pd.DataFrame(bathymetry_points)

# 2. OCEAN CURRENTS
currents_data = []
for i in range(15):
    f = i / 15.0
    lat = haifa_lat + (nynj_lat - haifa_lat) * f
    lon = haifa_lon + (nynj_lon - haifa_lon) * f
    current_speed = 1.5 + 1.0 * math.sin(f * math.pi * 2)
    current_dir = 270 + 30 * math.sin(f * math.pi * 1.5)
    currents_data.append({
        'lat': lat, 'lon': lon,
        'speed': current_speed,
        'direction': current_dir
    })
currents_df = pd.DataFrame(currents_data)

# 3. SENSOR NETWORK
sensor_network = pd.DataFrame({
    'latitude': [vessel_current_lat + d for d in [-5, -3, 0, 3, 5]],
    'longitude': [vessel_current_lon + d for d in [-8, -4, 0, 4, 8]],
    'sensor_id': ['SENS-001', 'SENS-002', 'SENS-003', 'SENS-004', 'SENS-005'],
    'type': ['Buoy', 'Drifter', 'Weather Station', 'Research Vessel', 'Fishing Vessel'],
    'status': ['Active', 'Active', 'Maintenance', 'Active', 'Active']
})

# 4. WEATHER FRONTS
fronts_data = [
    {'lat1': 30, 'lon1': -10, 'lat2': 35, 'lon2': -15, 'type': 'Cold Front'},
    {'lat1': 35, 'lon1': -20, 'lat2': 40, 'lon2': -25, 'type': 'Warm Front'},
    {'lat1': 38, 'lon1': -30, 'lat2': 42, 'lon2': -35, 'type': 'Stationary'}
]
fronts_df = pd.DataFrame(fronts_data)

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
    d = 15.0 if i == 0 or i == 100 else abs(-15.0 - (math.sin(f * math.pi) * 4985.0))
    depth_data.append({'Voyage Progress (%)': i, 'Ocean Depth (m)': d})
analytics_df = pd.DataFrame(depth_data).set_index('Voyage Progress (%)')

# Voyage calculations
total_hours_remaining = distance_remaining_nm / vessel_speed_knots if vessel_speed_knots > 0 else 0
days = int(total_hours_remaining // 24)
hours = int(total_hours_remaining % 24)
dynamic_burn_per_day = 45.0 * ((vessel_speed_knots / 20.0) ** 3) if vessel_speed_knots > 0 else 0
predicted_fuel_mt = round(dynamic_burn_per_day * (total_hours_remaining / 24.0), 1)
total_co2_emissions_mt = round(predicted_fuel_mt * 3.114, 1)

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

# Top metrics row
m1, m2, m3, m4 = st.columns(4)
m1.metric("🗺️ Remaining Distance", f"{distance_remaining_nm} NM", delta=f"{distance_covered_nm} NM Covered")
m2.metric("⏱️ ETA Countdown", f"{days}d {hours}h", delta=f"Speed: {vessel_speed_knots} kts")
m3.metric("📦 Cargo Profile", cargo_profile)
m4.metric("🧭 Current Heading", f"{current_bearing}°", delta="True Course")

# Sensor dashboard
st.markdown("##### 🌊 Environmental Sensor Suite")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("🌡️ Air Temp", f"{sensor_data['temperature']}°C")
col2.metric("💧 Humidity", f"{sensor_data['humidity']}%")
col3.metric("📊 Pressure", f"{sensor_data['pressure']} hPa")
col4.metric("🌊 Wave Height", f"{sensor_data['wave_height']}m")
col5.metric("🌡️ Water Temp", f"{sensor_data['water_temp']}°C")

st.markdown("##### Environmental, Weather & Real-Time Fleet Telemetry")
e1, e2, e3, e4, e5 = st.columns(5)
e1.metric("⛽ Fuel ETE", f"{predicted_fuel_mt} MT")
e2.metric("🌱 CO2 Impact", f"{total_co2_emissions_mt} MT")
e3.metric("🌊 Depth", f"{simulated_depth_meters} m", delta=bathymetry_status, delta_color=risk_color)
e4.metric("💨 Wind", f"{live_wind_knots} kts", delta=weather_alert, delta_color=weather_color, help=data_source_label)
e5.metric("⚠️ Risk Score", f"{risk_score}/100", delta=risk_level, delta_color=risk_delta_color)

# Zone info
zone_name, zone_flag = get_zone_info(vessel_current_lat, vessel_current_lon)
st.info(f"{zone_flag} **Current Maritime Zone:** {zone_name} | **Position:** {vessel_current_lat:.2f}°N, {abs(vessel_current_lon):.2f}°{'W' if vessel_current_lon < 0 else 'E'}")

st.markdown("---")

# ==========================================
# ENHANCED GIS MAP WITH ALL LAYERS
# ==========================================

# Layer 1: Bathymetry
layer_bathymetry = pdk.Layer(
    'ScatterplotLayer',
    data=bathymetry_df,
    get_position='[lon, lat]',
    get_color='[255, 200 - depth/20, 100, 100]',
    get_radius=50000,
    opacity=0.3
) if show_bathymetry else None

# Layer 2: Ocean Currents
layer_currents = pdk.Layer(
    'LineLayer',
    data=currents_df,
    get_source_position='[lon, lat]',
    get_target_position='[lon + direction_speed*0.5, lat + direction_speed*0.3]',
    get_color=[0, 150, 255, 200],
    get_width=2
) if show_currents else None

# Layer 3: Sensor Network
layer_sensors = pdk.Layer(
    'ScatterplotLayer',
    data=sensor_network,
    get_position='[longitude, latitude]',
    get_color=[0, 255, 0, 200],
    get_radius=30000,
    pickable=True,
    tooltip={"text": "Sensor: {sensor_id}\nType: {type}\nStatus: {status}"}
) if show_sensors else None

# Layer 4: Weather Fronts
layer_fronts = pdk.Layer(
    'LineLayer',
    data=fronts_df,
    get_source_position='[lon1, lat1]',
    get_target_position='[lon2, lat2]',
    get_color=[255, 0, 0, 200] if 'Cold' in fronts_df['type'].iloc[0] else [0, 255, 0, 200],
    get_width=3
) if show_weather else None

# Layer 5: AIS Targets
layer_ais = pdk.Layer(
    'ScatterplotLayer',
    data=ais_targets,
    get_position='[longitude, latitude]',
    get_color=[100, 150, 255, 200],
    get_radius=40000,
    pickable=True,
    tooltip={"text": "Vessel: {vessel_name}\nType: {type}\nSpeed: {speed} kts\nCourse: {course}°"}
) if show_ais else None

# Layer 6: Ports
layer_ports = pdk.Layer(
    'ScatterplotLayer', 
    data=ship_ports_df, 
    get_position='[longitude, latitude]', 
    get_color='[color_r, color_g, color_b, 200]', 
    get_radius=80000,
    pickable=True,
    tooltip={"text": "Port: {port_name}"}
)

# Layer 7: Route
layer_arc = pdk.Layer(
    'ArcLayer', 
    data=route_data, 
    get_source_position='[start_lon, start_lat]', 
    get_target_position='[end_lon, end_lat]', 
    get_source_color=[cyan_r, cyan_g, cyan_b, 180], 
    get_target_color=[orange_r, orange_g, orange_b, 180], 
    get_width=3
)

# Layer 8: Trail
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

# Layer 9: Target Vessel
layer_target_vessel = pdk.Layer(
    'ScatterplotLayer', 
    data=your_vessel_df,
    get_position='[longitude, latitude]',
    get_color=[255, 255, 0, 255],    
    get_radius=120000, 
    pickable=True,
    tooltip={"text": "{vessel_name}\nType: {type}\nSpeed: {speed} kts\nCourse: {course}°"}
)

# Layer 10: Risk Zone
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
    get_color=[risk_color_r, risk_color_g, risk_color_b, 80],
    get_radius=risk_radius,
    pickable=True,
    tooltip={"text": "Risk Zone: {risk_level}"}
)

# Build active layers
active_layers = [layer_arc, layer_ports, layer_risk_zone, layer_target_vessel]
if layer_trail: active_layers.append(layer_trail)
if show_bathymetry and layer_bathymetry: active_layers.append(layer_bathymetry)
if show_currents and layer_currents: active_layers.append(layer_currents)
if show_sensors and layer_sensors: active_layers.append(layer_sensors)
if show_weather and layer_fronts: active_layers.append(layer_fronts)
if show_ais and layer_ais: active_layers.append(layer_ais)

# Map center and zoom
map_center_lat = vessel_current_lat
map_center_lon = vessel_current_lon
zoom_level = 5.5 if st.session_state.live_progress < 10 or st.session_state.live_progress > 90 else 4.5

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
    tooltip={"text": "{vessel_name}"}
))

# Enhanced Map Legend
st.markdown("### 🗺️ GIS Map Legend")
legend_col1, legend_col2, legend_col3, legend_col4 = st.columns(4)
legend_col1.markdown("🟡 **Your Ship** (Yellow)")
legend_col2.markdown("🟢 **Ports** (Green/Red)")
legend_col3.markdown(f"🔴 **Risk Zone** ({risk_level})")
legend_col4.markdown("🟦 **AIS Targets** (Blue)")

legend_col5, legend_col6, legend_col7, legend_col8 = st.columns(4)
legend_col5.markdown("🟩 **Sensors** (Green)" if show_sensors else "🟩 **Sensors** (Hidden)")
legend_col6.markdown("🌊 **Currents** (Blue)" if show_currents else "🌊 **Currents** (Hidden)")
legend_col7.markdown("🗺️ **Bathymetry** (Orange)" if show_bathymetry else "🗺️ **Bathymetry** (Hidden)")
legend_col8.markdown("🌤️ **Weather Fronts** (Red/Green)" if show_weather else "🌤️ **Weather Fronts** (Hidden)")

# ==========================================
# SENSOR HISTORY CHART
# ==========================================
st.markdown("### 📊 Sensor Data History")
if len(st.session_state.sensor_data) > 1:
    sensor_df = pd.DataFrame(st.session_state.sensor_data)
    sensor_col1, sensor_col2 = st.columns(2)
    with sensor_col1:
        st.line_chart(sensor_df[['wind_speed', 'temperature']])
    with sensor_col2:
        st.line_chart(sensor_df[['wave_height', 'water_temp']])
else:
    st.info("Collecting sensor data...")

# ==========================================
# RISK HISTORY CHART
# ==========================================
st.markdown("### 📊 Risk Score History")
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

status_icon = "🟢 LIVE" if st.session_state.simulation_running else "⏸️ PAUSED"
status_delta = "Streaming" if st.session_state.simulation_running else "Stopped"

col1.metric("Vessel Status", f"{status_icon}", delta=status_delta)
col2.metric("Voyage Progress", f"{round(st.session_state.live_progress, 1)}%", delta=f"{distance_covered_nm} NM traveled")
col3.metric("Risk Level", f"{risk_level}", delta=f"Score: {risk_score}/100")

st.markdown("### 📍 Current Vessel Position")
st.info(f"**Latitude:** {vessel_current_lat:.4f}° | **Longitude:** {vessel_current_lon:.4f}° | **View:** Top-down at {zoom_level}x zoom | **Altitude:** 20 meters | **Heading:** {current_bearing}°")

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
st.caption("© 2026 Maritime Intelligence Platform | Real-time vessel tracking from Israel to USA | GIS Mapping • Sensor Network • Risk Prediction")
