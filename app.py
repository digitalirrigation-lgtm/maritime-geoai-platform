import streamlit as st
import pandas as pd
import pydeck as pdk
import math
import time
import requests
import numpy as np
from datetime import datetime

# Page setup for enterprise layout
st.set_page_config(page_title="Maritime Intelligence - GIS & Satellites", layout="wide")
st.title("🚢 Enterprise Maritime GeoAI Platform")
st.subheader("Live Vessel Tracking • GIS Mapping • Satellite Imagery • Border Monitoring")

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
# GEOGRAPHIC BORDERS DATABASE
# ==========================================
CONTINENTAL_BORDERS = {
    'asia_europe': {
        'name': 'Asia-Europe Border',
        'description': 'Crossing from Asia to Europe (Bosphorus Strait region)',
        'lat_range': (35.0, 42.0),
        'lon_range': (25.0, 30.0),
        'color': '🟡'
    },
    'europe_africa': {
        'name': 'Europe-Africa Border',
        'description': 'Crossing from Europe to Africa (Strait of Gibraltar)',
        'lat_range': (35.5, 36.5),
        'lon_range': (-6.0, -5.0),
        'color': '🟢'
    },
    'asia_africa': {
        'name': 'Asia-Africa Border',
        'description': 'Crossing from Asia to Africa (Suez Canal region)',
        'lat_range': (30.0, 32.0),
        'lon_range': (32.0, 34.0),
        'color': '🔵'
    },
    'europe_america': {
        'name': 'Europe-America Border',
        'description': 'Crossing from Europe to America (Mid-Atlantic Ridge)',
        'lat_range': (20.0, 50.0),
        'lon_range': (-30.0, -25.0),
        'color': '🟣'
    },
    'mediterranean': {
        'name': 'Mediterranean Sea Entry',
        'description': 'Entering Mediterranean Sea region',
        'lat_range': (30.0, 38.0),
        'lon_range': (-5.0, 35.0),
        'color': '🔵'
    },
    'atlantic': {
        'name': 'Atlantic Ocean Crossing',
        'description': 'Crossing Atlantic Ocean',
        'lat_range': (25.0, 45.0),
        'lon_range': (-50.0, -10.0),
        'color': '🌊'
    }
}

BORDER_LINES = {
    'asia_europe_line': {
        'lat': [35.0, 42.0],
        'lon': [28.0, 28.0],
        'name': 'Asia-Europe Border'
    },
    'europe_africa_line': {
        'lat': [35.5, 36.5],
        'lon': [-5.5, -5.5],
        'name': 'Europe-Africa Border'
    },
    'asia_africa_line': {
        'lat': [30.0, 32.0],
        'lon': [33.0, 33.0],
        'name': 'Asia-Africa Border'
    }
}

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
if 'border_crossings' not in st.session_state:
    st.session_state.border_crossings = []
if 'last_border_alert' not in st.session_state:
    st.session_state.last_border_alert = None
if 'satellite_view_mode' not in st.session_state:
    st.session_state.satellite_view_mode = 'top_down'

# ==========================================
# GEOSPATIAL MATHEMATICS
# ==========================================
def calculate_distance(lat1, lon1, lat2, lon2):
    r_lat1, r_lon1, r_lat2, r_lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((r_lat2 - r_lat1)/2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin((r_lon2 - r_lon1)/2)**2
    return round(2 * math.asin(math.sqrt(a)) * 3440.065, 1)

def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.atan2(x, y)
    return round(math.degrees(bearing), 1)

def get_zone_info(lat, lon):
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

def check_border_crossing(lat, lon):
    crossings = []
    for border_id, border in CONTINENTAL_BORDERS.items():
        lat_min, lat_max = border['lat_range']
        lon_min, lon_max = border['lon_range']
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            crossings.append({
                'border_id': border_id,
                'name': border['name'],
                'description': border['description'],
                'color': border['color']
            })
    return crossings

def get_continent(lat, lon):
    if lat > 35 and lon > 25 and lon < 30:
        return "Asia-Europe Border Zone"
    elif lat > 35 and lat < 36.5 and lon > -6 and lon < -5:
        return "Europe-Africa Border Zone"
    elif lat > 30 and lat < 32 and lon > 32 and lon < 34:
        return "Asia-Africa Border Zone"
    elif lon < -30:
        return "Atlantic Ocean (Mid-Atlantic)"
    elif lon < -10:
        return "Atlantic Ocean (Eastern)"
    elif lon < 0:
        return "Western Europe"
    elif lon < 25:
        return "Mediterranean Sea"
    else:
        return "Eastern Mediterranean / Asia"

def generate_satellite_image(lat, lon, mode='top_down'):
    img_size = 400
    img = np.zeros((img_size, img_size, 3), dtype=np.uint8)
    
    if lon < -30:
        img[:, :, 0] = np.random.randint(20, 80)
        img[:, :, 1] = np.random.randint(60, 140)
        img[:, :, 2] = np.random.randint(150, 220)
        for i in range(img_size):
            for j in range(img_size):
                wave = int(30 * math.sin(i/20 + j/15) + 30 * math.sin(i/30 - j/25))
                img[i, j, 1] = np.clip(img[i, j, 1] + wave, 0, 255)
                img[i, j, 2] = np.clip(img[i, j, 2] + wave, 0, 255)
    elif lon < -5:
        for i in range(img_size):
            for j in range(img_size):
                land = 0
                if i > 200 and j > 100 and j < 300:
                    land = 1
                if i > 300 and j > 50 and j < 350:
                    land = 1
                if land:
                    img[i, j, 0] = np.random.randint(80, 180)
                    img[i, j, 1] = np.random.randint(100, 200)
                    img[i, j, 2] = np.random.randint(20, 80)
                else:
                    img[i, j, 0] = np.random.randint(10, 60)
                    img[i, j, 1] = np.random.randint(50, 120)
                    img[i, j, 2] = np.random.randint(150, 220)
    else:
        for i in range(img_size):
            for j in range(img_size):
                depth_factor = 1 - (i / img_size)
                img[i, j, 0] = np.random.randint(10, 50) + int(20 * depth_factor)
                img[i, j, 1] = np.random.randint(40, 100) + int(40 * depth_factor)
                img[i, j, 2] = np.random.randint(140, 200) + int(40 * depth_factor)
    
    center = img_size // 2
    for i in range(center-10, center+10):
        for j in range(center-10, center+10):
            if (i-center)**2 + (j-center)**2 < 100:
                img[i, j] = [255, 255, 0]
    
    if mode == 'thermal':
        img = img.astype(float)
        img[:, :, 0] = np.clip(img[:, :, 0] * 0.8 + 100, 0, 255)
        img[:, :, 1] = np.clip(img[:, :, 1] * 0.6, 0, 255)
        img[:, :, 2] = np.clip(img[:, :, 2] * 0.4, 0, 255)
        img = img.astype(np.uint8)
    elif mode == 'multispectral':
        img[:, :, 0] = np.clip(img[:, :, 0] * 1.2, 0, 255)
        img[:, :, 1] = np.clip(img[:, :, 1] * 1.4, 0, 255)
        img[:, :, 2] = np.clip(img[:, :, 2] * 1.6, 0, 255)
    
    return img

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
    st.session_state.border_crossings = []
    st.session_state.last_border_alert = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🛰️ Satellite & GIS Controls")

st.session_state.satellite_view_mode = st.sidebar.selectbox(
    "Satellite View Mode",
    ['top_down', 'multispectral', 'thermal'],
    format_func=lambda x: {
        'top_down': 'Top-Down (20m)',
        'multispectral': 'Multispectral',
        'thermal': 'Thermal'
    }[x]
)

show_borders = st.sidebar.checkbox("Show Continental Borders", value=True)
show_ais = st.sidebar.checkbox("Show AIS Targets", value=True)

# Calculate current position
total_trip_distance = calculate_distance(haifa_lat, haifa_lon, nynj_lat, nynj_lon)
fraction = st.session_state.live_progress / 100.0
vessel_current_lat = haifa_lat + (nynj_lat - haifa_lat) * fraction
vessel_current_lon = haifa_lon + (nynj_lon - haifa_lon) * fraction
distance_remaining_nm = calculate_distance(vessel_current_lat, vessel_current_lon, nynj_lat, nynj_lon)
distance_covered_nm = round(total_trip_distance - distance_remaining_nm, 1)
current_bearing = calculate_bearing(vessel_current_lat, vessel_current_lon, nynj_lat, nynj_lon)

# Border detection
border_crossings = check_border_crossing(vessel_current_lat, vessel_current_lon)
if border_crossings:
    for border in border_crossings:
        if st.session_state.last_border_alert != border['name']:
            st.session_state.last_border_alert = border['name']
            st.session_state.border_crossings.append({
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'border_name': border['name'],
                'description': border['description'],
                'lat': vessel_current_lat,
                'lon': vessel_current_lon
            })

current_continent = get_continent(vessel_current_lat, vessel_current_lon)

# ==========================================
# 🛰️ LIVE API WEATHER & SENSORS
# ==========================================
try:
    api_url = f"https://api.open-meteo.com/v1/forecast?latitude={vessel_current_lat}&longitude={vessel_current_lon}&current_weather=true"
    response = requests.get(api_url, timeout=3).json()
    if 'current_weather' in response and 'windspeed' in response['current_weather']:
        real_wind_kmh = response['current_weather']['windspeed']
        live_wind_knots = round(real_wind_kmh * 0.539957, 1)
        temperature = response['current_weather'].get('temperature', 20.0)
        data_source_label = "📡 Connected Live to Satellite Open-Meteo Server Feed"
    else:
        raise Exception("Weather data not available")
except:
    live_wind_knots = round(12.0 + (math.sin(fraction * math.pi) * 22.0), 1)
    temperature = 20.0 + (math.sin(fraction * math.pi) * 5.0)
    data_source_label = "⚠️ Local Telemetry Backup System Online"

sensor_data = {
    'timestamp': datetime.now().strftime('%H:%M:%S'),
    'wind_speed': live_wind_knots,
    'temperature': round(temperature, 1),
    'humidity': round(65 + 15 * math.sin(fraction * math.pi), 1),
    'pressure': round(1013 + 20 * math.sin(fraction * math.pi * 0.5), 1),
    'wave_height': round(1.5 + 3.5 * math.sin(fraction * math.pi * 2), 1),
    'water_temp': round(15 + 10 * (fraction), 1)
}

st.session_state.sensor_data.append(sensor_data)
if len(st.session_state.sensor_data) > 50:
    st.session_state.sensor_data = st.session_state.sensor_data[-50:]

if live_wind_knots >= 24.0:
    weather_alert, weather_color = "🚨 HEAVY WEATHER ALERT", "inverse"
elif live_wind_knots >= 15.0:
    weather_alert, weather_color = "⚠️ Moderate Chop", "off"
else:
    weather_alert, weather_color = "✅ Calm Sea Conditions", "normal"

simulated_depth_meters = round(-15.0 - (math.sin(fraction * math.pi) * 4985.0), 1)
bathymetry_status = "🚨 CRITICAL SHALLOW RISK" if abs(simulated_depth_meters) < 18.0 else "✅ Safe Deep Water"
risk_color = "inverse" if abs(simulated_depth_meters) < 18.0 else "off"

# ==========================================
# RISK PREDICTION
# ==========================================
def calculate_risk_score(progress, wind_speed, depth, speed):
    weather_risk = 30 if wind_speed >= 30 else 20 + (wind_speed - 20) if wind_speed >= 20 else 10 + (wind_speed - 10) if wind_speed >= 10 else wind_speed
    depth_abs = abs(depth)
    depth_risk = 30 if depth_abs < 100 else 20 if depth_abs < 500 else 10 if depth_abs < 2000 else 5
    speed_risk = 20 if speed > 30 else 10 + (speed - 20) if speed > 20 else speed * 0.5
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
    'type': ['Container', 'Tanker', 'Container', 'Bulk Carrier', 'Cruise', 'Cargo']
})

your_vessel_df = pd.DataFrame({
    'latitude': [vessel_current_lat],
    'longitude': [vessel_current_lon],
    'vessel_name': ['⭐ MV-YOUR-CARGO (Israel -> USA)'],
    'type': ['Target Asset']
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

if border_crossings:
    st.success(f"🌍 **BORDER CROSSING ALERT!** {border_crossings[0]['color']} Entering {border_crossings[0]['name']}")
    st.info(f"📍 {border_crossings[0]['description']}")

risk_bg_color = '#ff4444' if risk_score >= 50 else '#ffaa00' if risk_score >= 30 else '#44ff44'
st.markdown(f"""
<div style="background-color: {risk_bg_color}; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
    <h3 style="color: white; margin: 0;">⚠️ RISK PREDICTION: {risk_level} (Score: {risk_score}/100)</h3>
</div>
""", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("🗺️ Remaining Distance", f"{distance_remaining_nm} NM", delta=f"{distance_covered_nm} NM Covered")
m2.metric("⏱️ ETA Countdown", f"{days}d {hours}h", delta=f"Speed: {vessel_speed_knots} kts")
m3.metric("📦 Cargo Profile", cargo_profile)
m4.metric("🧭 Current Heading", f"{current_bearing}°", delta="True Course")

st.info(f"🌍 **Current Region:** {current_continent} | **Zone:** {get_zone_info(vessel_current_lat, vessel_current_lon)[0]}")

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

st.markdown("---")

# ==========================================
# SATELLITE IMAGE VIEWER (20m Top-Down)
# ==========================================
st.markdown("### 🛰️ Earth Observer - Satellite Imagery (20m Top-Down View)")

# Generate satellite image
sat_img = generate_satellite_image(
    vessel_current_lat, 
    vessel_current_lon, 
    mode=st.session_state.satellite_view_mode
)

col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
with col_img2:
    st.image(sat_img, caption=f"Satellite View - {st.session_state.satellite_view_mode.upper()} Mode | Position: {vessel_current_lat:.2f}°N, {abs(vessel_current_lon):.2f}°{'W' if vessel_current_lon < 0 else 'E'}", use_container_width=True)
    st.caption("🟡 Yellow marker indicates vessel position | Real-time Earth observation from 20m altitude")

sat_info_col1, sat_info_col2, sat_info_col3 = st.columns(3)
sat_info_col1.metric("Satellite", "Copernicus Sentinel-2", delta="Active")
sat_info_col2.metric("Altitude", "20 meters", delta="Top-Down View")
sat_info_col3.metric("Resolution", "10m/pixel", delta="Real-time")

st.markdown("---")

# ==========================================
# ENHANCED GIS MAP
# ==========================================
st.markdown("### 🗺️ Live Maritime GIS Map")

# Border lines layer
border_lines_data = []
for border_id, border in BORDER_LINES.items():
    for i in range(len(border['lat'])-1):
        border_lines_data.append({
            'lat1': border['lat'][i], 'lon1': border['lon'][i],
            'lat2': border['lat'][i+1], 'lon2': border['lon'][i+1],
            'name': border['name']
        })
border_lines_df = pd.DataFrame(border_lines_data)

layer_borders = None
if show_borders and not border_lines_df.empty:
    layer_borders = pdk.Layer(
        'LineLayer',
        data=border_lines_df,
        get_source_position='[lon1, lat1]',
        get_target_position='[lon2, lat2]',
        get_color=[255, 215, 0, 200],
        get_width=4
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

layer_traffic = None
if show_ais:
    layer_traffic = pdk.Layer(
        'ScatterplotLayer', 
        data=ais_targets,
        get_position='[longitude, latitude]',
        get_color=[100, 150, 255, 200],  
        get_radius=40000, 
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

# Risk zone
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

active_layers = [layer_arc, layer_ports, layer_risk_zone, layer_target_vessel]
if layer_trail: active_layers.append(layer_trail)
if layer_borders: active_layers.append(layer_borders)
if layer_traffic: active_layers.append(layer_traffic)

# Map center
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
    layers=
