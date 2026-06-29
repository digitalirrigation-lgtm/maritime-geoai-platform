import streamlit as st
import pandas as pd
import pydeck as pdk
import math
import time
import requests

st.set_page_config(page_title="Maritime Intelligence", layout="wide")
st.title("🚢 Enterprise Maritime GeoAI Platform")
st.subheader("Live Vessel Tracking & Intelligent Route Analytics")

haifa_lat, haifa_lon = 32.8191, 34.9983
nynj_lat, nynj_lon = 40.6815, -74.1145

if 'live_progress' not in st.session_state:
    st.session_state.live_progress = 0.0
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False

if st.session_state.simulation_running:
    if st.session_state.live_progress < 100.0:
        st.session_state.live_progress += 1.0
        time.sleep(0.5)
        st.rerun()
    else:
        st.session_state.simulation_running = False

st.sidebar.header("🕹️ Fleet Control Center")
if st.sidebar.button("▶️ Launch Live Telemetry Stream"):
    st.session_state.simulation_running = True
    st.rerun()
if st.sidebar.button("⏸️ Pause Telemetry Stream"):
    st.session_state.simulation_running = False
    st.rerun()
if st.sidebar.button("🔄 Reset Voyage to Israel"):
    st.session_state.live_progress = 0.0
    st.session_state.simulation_running = False
    st.rerun()

vessel_speed_knots = st.sidebar.slider("Vessel Cruising Speed (Knots)", 5.0, 35.0, 20.0, 0.5)
voyage_progress = st.sidebar.slider("Vessel Voyage Progress (%)", 0, 100, int(st.session_state.live_progress))
st.session_state.live_progress = float(voyage_progress)
cargo_profile = st.sidebar.selectbox("Cargo Priority Profile", ["Standard Freight", "High-Value Express", "Eco-Friendly Slow Steaming"])

def calculate_distance(lat1, lon1, lat2, lon2):
    r_lat1, r_lon1, r_lat2, r_lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((r_lat2 - r_lat1)/2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin((r_lon2 - r_lon1)/2)**2
    return round(2 * math.asin(math.sqrt(a)) * 3440.065, 1)

total_trip_distance = calculate_distance(haifa_lat, haifa_lon, nynj_lat, nynj_lon)
fraction = st.session_state.live_progress / 100.0
vessel_current_lat = haifa_lat + (nynj_lat - haifa_lat) * fraction
vessel_current_lon = haifa_lon + (nynj_lon - haifa_lon) * fraction

distance_remaining_nm = calculate_distance(vessel_current_lat, vessel_current_lon, nynj_lat, nynj_lon)
distance_covered_nm = round(total_trip_distance - distance_remaining_nm, 1)

if int(st.session_state.live_progress) == 0 or int(st.session_state.live_progress) == 100:
    simulated_depth_meters = -15.0 
else:
    simulated_depth_meters = round(-15.0 - (math.sin(fraction * math.pi) * 4985.0), 1)

bathymetry_status = "🚨 CRITICAL SHALLOW RISK" if abs(simulated_depth_meters) < 18.0 else "✅ Safe Deep Water"
risk_color = "normal" if abs(simulated_depth_meters) < 18.0 else "off"

try:
    api_url = f"https://open-meteo.com{vessel_current_lat}&longitude={vessel_current_lon}&current_weather=true"
    response = requests.get(api_url, timeout=3).json()
    real_wind_kmh = response['current_weather']['windspeed']
    live_wind_knots = round(real_wind_kmh * 0.539957, 1)
    data_source_label = "📡 Connected Live to Satellite Server"
except:
    live_wind_knots = round(12.0 + (math.sin(fraction * math.pi) * 22.0), 1)
    data_source_label = "⚠️ Backup Local Telemetry Online"

if live_wind_knots >= 24.0:
    weather_alert, weather_color = "🚨 HEAVY WEATHER ALERT", "normal"
elif live_wind_knots >= 15.0:
    weather_alert, weather_color = "⚠️ Moderate Chop", "inverse"
else:
    weather_alert, weather_color = "✅ Calm Sea Conditions", "off"

your_vessel_df = pd.DataFrame({
    'latitude': [vessel_current_lat], 'longitude': [vessel_current_lon],
    'vessel_name': ['⭐ MV-YOUR-CARGO (Israel -> USA)'], 'type': ['Target Asset']
})

traffic_records = [
    {'latitude': 38.5, 'longitude': -35.4, 'vessel_name': 'MV-Rotterdam-Express', 'type': 'Neighboring Traffic'},
    {'latitude': 34.2, 'longitude': -42.1, 'vessel_name': 'MV-Atlantic-Titan', 'type': 'Neighboring Traffic'},
    {'latitude': 41.1, 'longitude': -22.5, 'vessel_name': 'MV-Hamburg-Carrier', 'type': 'Neighboring Traffic'},
    {'latitude': 35.8, 'longitude': -50.2, 'vessel_name': 'MV-Tokyo-Maru', 'type': 'Neighboring Traffic'}
]
other_traffic_df = pd.DataFrame(traffic_records)

# SECURE FIX: Solid arrays with complete matching rows for our ports
ship_ports_df = pd.DataFrame({
    'latitude': [haifa_lat, nynj_lat], 
    'longitude': [haifa_lon, nynj_lon],
    'port_name': ['Port of Haifa (Origin)', 'Port of NY/NJ (Destination)'],
    'color_r':, 
    'color_g':, 
    'color_b': [0, 0]
})

route_data = pd.DataFrame({'start_lon': [haifa_lon], 'start_lat': [haifa_lat], 'end_lon': [nynj_lon], 'end_lat': [nynj_lat]})

total_hours_remaining = distance_remaining_nm / vessel_speed_knots
days, hours = int(total_hours_remaining // 24), int(total_hours_remaining % 24)
dynamic_burn_per_day = 45.0 * ((vessel_speed_knots / 20.0) ** 3) if vessel_speed_knots > 0 else 0
predicted_fuel_mt = round(dynamic_burn_per_day * (total_hours_remaining / 24.0), 1)
total_co2_emissions_mt = round(predicted_fuel_mt * 3.114, 1)

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

m1, m2, m3 = st.columns(3)
m1.metric("🗺️ Remaining Distance to Destination", f"{distance_remaining_nm} NM", delta=f"{distance_covered_nm} NM Covered")
m2.metric("⏱️ Dynamic ETA Countdown", f"{days}d {hours}h", delta=f"Speed: {vessel_speed_knots} kts")
m3.metric("📦 Cargo Profile Mode", cargo_profile)

st.markdown("##### Environmental, Weather & Real-Time Fleet Telemetry")
e1, e2, e3, e4 = st.columns(4)
e1.metric("⛽ Fuel ETE Requirements", f"{predicted_fuel_mt} MT")
e2.metric("🌱 CO2 Voyage Impact", f"{total_co2_emissions_mt} MT")
e3.metric("🌊 Ocean Depth Under Keel", f"{simulated_depth_meters} m", delta=bathymetry_status, delta_color=risk_color)
e4.metric("💨 Live Wind at Ship Location", f"{live_wind_knots} kts", delta=weather_alert, delta_color=weather_color, help=data_source_label)

st.markdown("---")

layer_ports = pdk.Layer('ScatterplotLayer', data=ship_ports_df, get_position='[longitude, latitude]', get_color='[color_r, color_g, color_b, 200]', get_radius=120000)
layer_arc = pdk.Layer('ArcLayer', data=route_data, get_source_position='[start_lon, start_lat]', get_target_position='[end_lon, end_lat]', get_source_color=[0, 191, 255, 180], get_target_color=[255, 140, 0, 180], get_width=3)
layer_traffic = pdk.Layer('ScatterplotLayer', data=other_traffic_df, get_position='[longitude, latitude]', get_color=[128, 128, 128, 200], get_radius=120000, pickable=True)
layer_target_vessel = pdk.Layer('ScatterplotLayer', data=your_vessel_df, get_position='[longitude, latitude]', get_color=[255, 255, 0, 255], get_radius=160000, pickable=True)

map_layers = [layer_arc, layer_ports, layer_traffic, layer_target_vessel]
if not history_df.empty:
    layer_trail = pdk.Layer('LineLayer', data=history_df, get_source_position='[s_lon, s_lat]', get_target_position='[e_lon, e_lat]', get_color=[0, 255, 127, 255], get_width=5)
    map_layers.append(layer_trail)

st.pydeck_chart(pdk.Deck(
    map_style='mapbox://styles/mapbox/satellite-v9',
    initial_view_state=pdk.ViewState(latitude=36.0, longitude=-20.0, zoom=1.8, pitch=0),
    layers=map_layers,
    tooltip={"text": "Vessel Profile:\n{vessel_name}\nClassification: {type}"}
))

st.markdown("### 📈 Voyage Time-Series Bathymetric Risk Predictor")
st.line_chart(analytics_df['Ocean Depth (m)'])

st.markdown("### 📡 Active Satellite System Telemetry Stream")
st.info(f"**Vessel Status:** Track Online | **Voyage Progress:** {round(st.session_state.live_progress, 1)}% Completed | **Core Data Source:** {data_source_label}")
