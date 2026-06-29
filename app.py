import streamlit as st
import pandas as pd
import pydeck as pdk
import math
import time
import requests  # NEW: Library used to pull real data over the internet!

# Page setup for enterprise layout
st.set_page_config(page_title="Maritime Intelligence", layout="wide")
st.title("🚢 Enterprise Maritime GeoAI Platform")
st.subheader("Live Vessel Tracking & Intelligent Route Analytics")

# Basic parameters
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
    st.session_state.simulation_running = False

# ==========================================
# SIDEBAR CONTROL ROOM
# ==========================================
st.sidebar.header("🕹️ Fleet Control Center")

sim_toggle = st.sidebar.button(
    label="⏸️ Pause Telemetry Simulation" if st.session_state.simulation_running else "▶️ Launch Live Telemetry Stream"
)

if sim_toggle:
    st.session_state.simulation_running = not st.session_state.simulation_running

vessel_speed_knots = st.sidebar.slider("Vessel Cruising Speed (Knots)", 5.0, 35.0, 20.0, 0.5)

voyage_progress = st.sidebar.slider(
    label="Vessel Voyage Progress (%)", 
    min_value=0, 
    max_value=100, 
    value=int(st.session_state.live_progress)
)

st.session_state.live_progress = float(voyage_progress)
cargo_profile = st.sidebar.selectbox("Cargo Priority Profile", ["Standard Freight", "High-Value Express", "Eco-Friendly Slow Steaming"])

# ==========================================
# DISTANCE & POSITION INTERPOLATION
# ==========================================
def calculate_distance(lat1, lon1, lat2, lon2):
    r_lat1, r_lon1, r_lat2, r_lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((r_lat2 - r_lat1)/2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin((r_lon2 - r_lon1)/2)**2
    return round(2 * math.asin(math.sqrt(a)) * 3440.065, 1)

trip_distance_nm = calculate_distance(haifa_lat, haifa_lon, nynj_lat, nynj_lon)

fraction = st.session_state.live_progress / 100.0
vessel_current_lat = haifa_lat + (nynj_lat - haifa_lat) * fraction
vessel_current_lon = haifa_lon + (nynj_lon - haifa_lon) * fraction

# Bathymetry tracking
if int(st.session_state.live_progress) == 0 or int(st.session_state.live_progress) == 100:
    simulated_depth_meters = -15.0 
else:
    simulated_depth_meters = round(-15.0 - (math.sin(fraction * math.pi) * 4985.0), 1)

bathymetry_status = "🚨 CRITICAL SHALLOW RISK" if abs(simulated_depth_meters) < 18.0 else "✅ Safe Deep Water"
risk_color = "normal" if abs(simulated_depth_meters) < 18.0 else "off"

# ==========================================
# NEW NEW NEW: REAL-WORLD LIVE METEOROLOGICAL API ENGINE
# ==========================================
# We connect to an open public weather API and request real live coordinates
try:
    api_url = f"https://open-meteo.com{vessel_current_lat}&longitude={vessel_current_lon}&current_weather=true"
    response = requests.get(api_url, timeout=5).json()
    
    # Extract the real live current wind speed at this exact coordinate point!
    # Convert km/h to knots by multiplying by 0.539957
    real_wind_kmh = response['current_weather']['windspeed']
    simulated_wind_knots = round(real_wind_kmh * 0.539957, 1)
    data_source_label = "📡 Live Satellite Open-Meteo API Feed"
except:
    # Backup fallback if your computer loses internet connection
    simulated_wind_knots = 15.0
    data_source_label = "⚠️ API Offline - Using Cached Fallback"

if simulated_wind_knots >= 34.0:
    weather_alert, weather_color = "🚨 GALE WARNING", "normal"
elif simulated_wind_knots >= 22.0:
    weather_alert, weather_color = "⚠️ Moderate Chop", "inverse"
else:
    weather_alert, weather_color = "✅ Calm Sea", "off"

# Registries & Calculations
ship_data = pd.DataFrame({
    'latitude': [haifa_lat, nynj_lat], 'longitude': [haifa_lon, nynj_lon],
    'port_name': ['Port of Haifa (Origin)', 'Port of NY/NJ (Destination)'],
    'color_r': [h_red_val, n_red_val], 'color_g': [h_green_val, n_green_val], 'color_b': [h_blue_val, n_blue_val]
})

route_data = pd.DataFrame({'start_lon': [haifa_lon], 'start_lat': [haifa_lat], 'end_lon': [nynj_lon], 'end_lat': [nynj_lat]})
vessel_registry = pd.DataFrame({'latitude': [vessel_current_lat], 'longitude': [vessel_current_lon], 'vessel_name': ['MV-GeoAI-Explorer'], 'wind': [simulated_wind_knots]})

total_hours = trip_distance_nm / vessel_speed_knots
days, hours = int(total_hours // 24), int(total_hours % 24)
dynamic_burn_per_day = 45.0 * ((vessel_speed_knots / 20.0) ** 3) if vessel_speed_knots > 0 else 0
predicted_fuel_mt = round(dynamic_burn_per_day * (total_hours / 24.0), 1)
total_co2_emissions_mt = round(predicted_fuel_mt * 3.114, 1)

# Precompute historical segments
chart_list, trail_points = [], []
step_count = max(1, int(st.session_state.live_progress))

for i in range(101):
    f = i / 100.0
    d = -15.0 if i == 0 or i == 100 else round(-15.0 - (math.sin(f * math.pi) * 4985.0), 1)
    if i <= step_count:
        trail_points.append({'lon': haifa_lon + (nynj_lon - haifa_lon) * f, 'lat': haifa_lat + (nynj_lat - haifa_lat) * f})
    chart_list.append({'Voyage Progress (%)': i, 'Ocean Depth (m)': abs(d)})

analytics_df = pd.DataFrame(chart_list).set_index('Voyage Progress (%)')
trail_df = pd.DataFrame(trail_points)

history_segments = []
if len(trail_df) > 1:
    for idx in range(len(trail_df) - 1):
        history_segments.append({
            's_lon': trail_df.iloc[idx]['lon'], 's_lat': trail_df.iloc[idx]['lat'],
            'e_lon': trail_df.iloc[idx+1]['lon'], 'e_lat': trail_df.iloc[idx+1]['lat']
        })
history_df = pd.DataFrame(history_segments)

# ==========================================
# RENDER LAYOUT
# ==========================================
m1, m2, m3 = st.columns(3)
m1.metric("🗺️ Distance", f"{trip_distance_nm} NM")
m2.metric("⏱️ Trip Duration Estimate", f"{days}d {hours}h")
m3.metric("📦 Cargo Profile", cargo_profile)

st.markdown("##### Environmental, Weather & Bathymetry Telemetry")
e1, e2, e3, e4 = st.columns(4)
e1.metric("⛽ Predicted Fuel", f"{predicted_fuel_mt} MT")
e2.metric("🌱 Estimated CO2", f"{total_co2_emissions_mt} MT")
e3.metric("🌊 Ocean Depth", f"{simulated_depth_meters} m", delta=bathymetry_status, delta_color=risk_color)
e4.metric("💨 Real-World Wind Speed", f"{simulated_wind_knots} kts", delta=weather_alert, delta_color=weather_color, help=data_source_label)

st.markdown("---")

# Render Map Layers
layer_ports = pdk.Layer('ScatterplotLayer', data=ship_data, get_position='[longitude, latitude]', get_color='[color_r, color_g, color_b, 200]', get_radius=100000)
layer_arc = pdk.Layer('ArcLayer', data=route_data, get_source_position='[start_lon, start_lat]', get_target_position='[end_lon, end_lat]', get_source_color=[cyan_r, cyan_g, cyan_b, 100], get_target_color=[orange_r, orange_g, orange_b, 100], get_width=2)
layer_vessel = pdk.Layer('ScatterplotLayer', data=vessel_registry, get_position='[longitude, latitude]', get_color=[white_color, white_color, white_color, 255], get_radius=140000)

map_layers = [layer_arc, layer_ports]
if not history_df.empty:
    map_layers.append(pdk.Layer('LineLayer', data=history_df, get_source_position='[s_lon, s_lat]', get_target_position='[e_lon, e_lat]', get_color=[h_red_val, trail_green, trail_green, white_color], get_width=5))
map_layers.append(layer_vessel)

st.pydeck_chart(pdk.Deck(
    map_style='mapbox://styles/mapbox/dark-v10',
    initial_view_state=pdk.ViewState(latitude=36.0, longitude=-20.0, zoom=2, pitch=45),
    layers=map_layers,
    tooltip={"text": "{vessel_name} | Wind: {wind}kts"}
))

# Render charts
st.markdown("### 📈 Voyage Time-Series Risk Predictor")
st.line_chart(analytics_df['Ocean Depth (m)'])

# ==========================================
# AUTOMATION REFRESH PROCESSING
# ==========================================
if st.session_state.simulation_running:
    if st.session_state.live_progress < 100.0:
        st.session_state.live_progress += 1.0
        time.sleep(1.0)  
        st.rerun()      
    else:
        st.session_state.simulation_running = False
        st.rerun()
