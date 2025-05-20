import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_javascript import st_javascript

# Page configuration
st.set_page_config(page_title="🌱 Energy saver Spain", layout="wide")

is_dark = st_javascript("window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches")

# Page styles
st.markdown("""
    <style>
    .main {
        background-color: #ffffff;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 375px;
        padding-right: 375px;
    }
    @media (max-width: 1170px) {
      .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 20px;
        padding-right: 20px;
    }
    }

    .st-bd {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 10px;
    }

    .stButton>button {
        background-color: #4CAF50;
        color: white;
    }

    .stTabs [data-baseweb="tab"] {
        margin: 0 10px;
        padding: 10px 20px;
        font-size: 16px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)
if is_dark:
    st.markdown("""
        <style>
        /* Main input and selectbox */
        input, textarea, select, .stTextInput > div > div > input, .stSelectbox > div > div > div {
            background-color: #222222 !important;
            color: #ffffff !important;
        }
        .stTextInput > div > div > input,
        .stSelectbox > div > div > div {
            border: 1px solid #444444 !important;
        }
        label, .stSelectbox label, .stTextInput label {
            color: #ffffff !important;
        }
        /* Dropdown menu for selectbox (BaseWeb) */
        div[data-baseweb="popover"] {
            background-color: #222222 !important;
            color: #ffffff !important;
        }
        div[data-baseweb="menu"] {
            background-color: #222222 !important;
            color: #ffffff !important;
        }
        div[data-baseweb="option"] {
            background-color: #222222 !important;
            color: #ffffff !important;
        }
        div[data-baseweb="option"]:hover, div[data-baseweb="option"][aria-selected="true"] {
            background-color: #444444 !important;
            color: #ffffff !important;
        }
        </style>
    """, unsafe_allow_html=True)


# Get API keys from Streamlit Cloud Secrets
OPENWEATHER_API_KEY = st.secrets["OPENWEATHER_API_KEY"]
ELECTRICITYMAP_API_KEY = st.secrets["ELECTRICITYMAP_API_KEY"]

# HTTP requests from APIs
def get_weather_forecast(city):
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def get_current_weather(city):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def get_air_pollution(lat, lon):
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def get_carbon_intensity(region):
    url = f"https://api.electricitymap.org/v3/carbon-intensity/latest?zone={region}"
    headers = {"auth-token": ELECTRICITYMAP_API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, dict):
            return data
        else:
            return {"carbonIntensity": data}
    return None

def get_power_breakdown_history(region):
    url = f"https://api.electricitymap.org/v3/power-breakdown/history?zone={region}"
    headers = {"auth-token": ELECTRICITYMAP_API_KEY}
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None

def get_solar_radiation(lat, lon):
    today = datetime.now().strftime("%Y-%m-%d")
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&hourly=shortwave_radiation&start_date={today}&end_date={today}&timezone=Europe/Madrid"
    )
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

# Scores
def estimate_energy_use(temp, heating):
    if heating == "Electric":
        return max(0, 25 - temp) * 0.8
    elif heating == "Gas":
        return max(0, 25 - temp) * 0.5
    else:
        return max(0, 25 - temp) * 0.3

def score_energy_consumption_day(carbon_intensity, aqi, temp):
    carbon_score = max(0, 10 - (carbon_intensity / 100))
    aqi_score = max(2, 12 - aqi * 2)
    temp_diff = abs(temp - 20)
    temp_score = max(0, 10 - (temp_diff / 4))
    final_score = (carbon_score * 0.5) + (aqi_score * 0.2) + (temp_score * 0.3)
    return round(final_score, 1)

def wind_direction_arrow(deg):
    dirs = [
        ("N", "⬆"), ("NE", "↗"), ("E", "➡"), ("SE", "↘"),
        ("S", "⬇"), ("SW", "↙"), ("W", "⬅"), ("NW", "↖")
    ]
    ix = int((deg + 22.5) % 360 // 45)
    return dirs[ix][1], dirs[ix][0]

def wind_speed_category(speed_kmh):
    if speed_kmh < 10:
        return "Calm", "green"
    elif speed_kmh < 25:
        return "Moderate", "orange"
    else:
        return "Strong", "red"

# App
st.title("🌱 Energy saver app for Spain")
st.markdown("Analyze your energy consumption using real-time **climate**, **air quality**, and **electric grid** data.")

city_options = [
    "Barcelona", "Valencia", "Sevilla", "Zaragoza", "Palma",
        "Las Palmas de Gran Canaria", "Bilbao", "Alicante", "Córdoba", "Valladolid", "Vigo",
        "Gijón", "L'Hospitalet de Llobregat", "A Coruña", "Vitoria-Gasteiz", "Granada", "Elche",
        "Oviedo", "Badalona", "Cartagena", "Terrassa", "Jerez de la Frontera", "Sabadell",
        "Santa Cruz de Tenerife", "Móstoles", "Alcalá de Henares", "Fuenlabrada", "Pamplona",
        "Almería", "Leganés", "San Sebastián", "Castellón de la Plana", "Burgos", "Santander",
        "Albacete", "Getafe", "Alcorcón", "Logroño", "San Cristóbal de La Laguna", "Badajoz",
        "Salamanca", "Huelva", "Marbella", "Lérida", "Tarragona", "León", "Dos Hermanas",
        "Parla", "Mataró", "Cádiz", "Santa Coloma de Gramenet", "Jaén", "Igualada", "Teruel"
        "Algeciras", "Reus", "Ourense", "Telde", "Baracaldo", "Málaga", "Torrejón de Ardoz", 
        "Santiago de Compostela", "Lugo", "San Fernando", "Avilés", "Girona", 
        "Melilla", "Toledo", "Lorca", "Ciudad Real", "Guadalajara", "Roquetas de Mar",
        "Ceuta", "Pontevedra", "Rubí", "Manresa", "Toledo", "Ferrol", "Cuenca", 
        "Benidorm", "Pozuelo de Alarcón", "Arrecife", "Murcia", "Chiclana de la Frontera", "Zamora",
        "Talavera de la Reina", "Cáceres", "Valdepeñas", "Gavá", "Sória", "Blanes",
        "Majadahonda", "Orihuela", "Coslada", "Valdemoro", "Mollet del Vallès", "Sagunto",
        "Collado Villalba", "Aranjuez", "Ávila", "Torremolinos", "Palencia", "Elda", 
        "Granollers", "Villareal", "Motril", "Girona", "Ibiza", "Puerto Real", "Soria", "Sanlúcar de Barrameda",
        "Manacor", "Huesca", "Paterna", "Inca", "Segovia", "Denia", "Viladecans", "Antequera",
        "Alcoy", "Rincón de la Victoria", "Figueras", "Cambrils", "Aranda de Duero", "Moncada y Reixach",
        "Puertollano", "Ronda", "Cerdanyola del Vallès", "Estepona", "Gandía", "Torrevieja", "Irun",
        "Eivissa", "Vic", "Benalmádena", "Don Benito", "Lucena", "Villena", "El Ejido",
        "Utrera", "Alcobendas", "San Sebastián de los Reyes"
]
city_choice = st.selectbox(
    "🏢 Select your city:",
    ["Madrid"] + ["Other (type below)"] + city_options 
)
if city_choice == "Other (type below)":
    city = st.text_input("Type your city:", "")
else:
    city = city_choice

region_code = st.text_input("📍 Region code:", "ES", disabled=True)
heating_type = st.selectbox("🔥 Select your heating type:", ["Electric", "Gas", "Heat pump"])

if st.button("Analyze", key="analyze_button"):
    current_weather = get_current_weather(city)
    forecast_data = get_weather_forecast(city)

    if current_weather and forecast_data:
        lat = current_weather['coord']['lat']
        lon = current_weather['coord']['lon']
        air_quality = get_air_pollution(lat, lon)
        carbon_data = get_carbon_intensity(region_code)
        power_history = get_power_breakdown_history(region_code)

        tabs = st.tabs([
            "Current climate & energy use",
            "Forecast & consumption",
            "Air quality & ventilation",
            "Carbon intensity & sustainability",
            "Energy sources breakdown",
            "Daily efficiency score"
        ])

        # Tab 1: Current conditions
        with tabs[0]:
            st.subheader(f"Current weather and energy use in {city}")
            
            temp = current_weather['main']['temp']
            feels_like = current_weather['main']['feels_like']
            icon_desc = current_weather['weather'][0]['description'].capitalize()
            icon_id = current_weather['weather'][0]['icon']
            emoji_map = {
                "01": "☀️", "02": "⛅", "03": "☁️", "04": "☁️",
                "09": "🌧️", "10": "🌦️", "11": "⛈", "13": "❄️", "50": "🌫️"
            }
            emoji = emoji_map.get(icon_id[:2], "❓")
            energy_now = estimate_energy_use(temp, heating_type)
        
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("**🌡️ Temp / Feels like**", f"{temp}°C / {feels_like}°C")
            with col2:
                st.metric("**⛅ Weather**", f"{icon_desc} {emoji}")
            with col3:
                energy_now = estimate_energy_use(temp, heating_type)
                st.metric("**⚡ Estimated use now**", f"{energy_now:.2f} kWh")

            st.write("### Heating type energy estimates")
            types = ["Electric", "Gas", "Heat pump"]
            values = [estimate_energy_use(temp, t) for t in types]
            fig_bar, ax_bar = plt.subplots(figsize=(4, 2))
            ax_bar.bar(types, values, color=['skyblue', 'orange', 'green'])
            ax_bar.set_facecolor('#ffffff')
            fig_bar.patch.set_facecolor('#ffffff')
            ax_bar.tick_params(axis='both', labelsize=8)
            ax_bar.set_ylabel("Estimated kWh", fontsize=10)
            st.pyplot(fig_bar)

        # Tab 2: Forecast and energy
        with tabs[1]:
            st.subheader("Weather forecast vs energy consumption")

            daily_forecast = {}
            for entry in forecast_data['list']:
                date = entry['dt_txt'].split(" ")[0]
                temp = entry['main']['temp']
                daily_forecast.setdefault(date, []).append(temp)
        
            results = []
            for date, temps in list(daily_forecast.items())[:5]:
                avg_temp = sum(temps) / len(temps)
                energy = estimate_energy_use(avg_temp, heating_type)
                results.append({"Date": date, "Avg Temp (°C)": avg_temp, "Estimated Energy (kWh)": energy})
        
            df = pd.DataFrame(results)
        
            fig, ax = plt.subplots(figsize=(5.5, 3))
            ax.plot(df['Date'], df['Avg Temp (°C)'], label="Avg Temp", color='orange')
            ax.plot(df['Date'], df['Estimated Energy (kWh)'], label="Energy", color='blue')
            ax.set_ylabel("Temperature (°C) / Estimated Energy (kWh)", fontsize=10)
            ax.tick_params(axis='both', labelsize=8)
            ax.legend(fontsize=8)
            ax.set_facecolor('#ffffff')
            fig.patch.set_facecolor('#ffffff')
            st.pyplot(fig)
        
            st.write("### Power production breakdown")
            stacked = pd.DataFrame({
                'Electric': [estimate_energy_use(t, 'Electric') for t in df['Avg Temp (°C)']],
                'Gas': [estimate_energy_use(t, 'Gas') for t in df['Avg Temp (°C)']],
                'Heat Pump': [estimate_energy_use(t, 'Heat pump') for t in df['Avg Temp (°C)']]
            }, index=df['Date'])
        
            fig2, ax2 = plt.subplots(figsize=(5.5, 3))
            stacked.plot.area(ax=ax2, colormap='Set2')
            ax2.set_ylabel("Estimated Energy (kWh)", fontsize=10)
            ax2.tick_params(axis='both', labelsize=8)
            ax2.set_facecolor('#ffffff')
            fig2.patch.set_facecolor('#ffffff')
            st.pyplot(fig2)

            avg_electric = stacked['Electric'].mean()
            avg_gas = stacked['Gas'].mean()
            avg_heatpump = stacked['Heat Pump'].mean()
            
            if avg_heatpump > avg_electric and avg_heatpump > avg_gas:
                st.info(f"🌿 Heat pumps dominate energy use: great for efficient heating! Keep optimizing usage for best savings.")
            elif avg_electric > avg_gas:
                st.info(f"⚡ Electric heating is the main source: consider shifting to off-peak hours to save on costs.")
            else:
                st.info(f"🔥 Gas heating still used significantly: consider improving insulation or upgrading to cleaner tech.")
            

        # Tab 3: Air quality
        with tabs[2]:
            st.subheader("Air quality & ventilation")
            if air_quality:
                aqi = air_quality['list'][0]['main']['aqi']
                st.metric("Air Quality Index (1 Good - 5 Poor)", str(aqi))
                levels = air_quality['list'][0]['components']
        
                st.write("### Pollutants levels")
                df_pollutants = pd.DataFrame(levels.items(), columns=['Pollutant', 'μg/m³'])
                fig_poll, ax_poll = plt.subplots(figsize=(5, 2.5))
                ax_poll.bar(df_pollutants['Pollutant'], df_pollutants['μg/m³'], color='teal')
                ax_poll.set_ylabel("Concentration (μg/m³)", fontsize=10)  # Título eje Y
                ax_poll.tick_params(axis='both', labelsize=8)
                ax_poll.set_facecolor('#ffffff')
                fig_poll.patch.set_facecolor('#ffffff')
                st.pyplot(fig_poll)

                if aqi <= 2:
                    st.success("✅ It's a good time to ventilate your home.")
                elif aqi >= 4:
                    st.warning("⚠️ Avoid opening windows now due to poor air.")
                else:
                    st.info("🕗 Moderate conditions. Ventilate briefly if needed.")

        # Tab 4: Carbon intensity
        with tabs[3]:
            st.subheader("Carbon intensity and sustainability")
            if carbon_data:
                intensity = carbon_data.get("carbonIntensity")
                if isinstance(intensity, dict):
                    intensity = intensity.get("carbonIntensity")
                st.metric("Current Intensity (gCO₂/kWh)", intensity)
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=intensity,
                    title={'text': "Carbon Intensity"},
                    gauge={
                        'axis': {'range': [0, 600]},
                        'bar': {'color': "green" if intensity < 150 else "orange" if intensity < 300 else "red"},
                        'bgcolor': "#f0f9f9",
                        'steps': [
                            {'range': [0, 150], 'color': "lightgreen"},
                            {'range': [150, 300], 'color': "yellow"},
                            {'range': [300, 600], 'color': "lightcoral"}
                        ]
                    }
                ))

                fig_gauge.update_layout(
                    paper_bgcolor="#ffffff", 
                    plot_bgcolor="#ffffff"
                )
                
                st.plotly_chart(fig_gauge)
        
                if intensity < 150:
                    st.success("✅ Clean energy available! Great moment to use high-energy appliances.")
                elif intensity < 300:
                    st.info("🕗 Mixed sources. Consider moderate energy usage.")
                else:
                    st.warning("⚠️ High emissions now. Try to delay non-essential electricity use.")
        
        # Tab 5: Power sources breakdown
        with tabs[4]:
            st.subheader("Power sources breakdown")
            if power_history and "history" in power_history:
                hist = power_history['history']
                df_hist = pd.json_normalize(hist)
                df_hist['datetime'] = pd.to_datetime(df_hist['datetime'])
                df_hist.rename(columns=lambda x: x.replace("powerConsumptionBreakdown.", ""), inplace=True)
                df_hist.set_index("datetime", inplace=True)
        
                cols_to_plot = df_hist.select_dtypes(include='number').columns.difference(['fossil', 'renewable'])
                df_positive = df_hist[cols_to_plot].copy()
                df_positive[df_positive < 0] = 0
        
                fig_sources = go.Figure()
        
                for col in df_positive.columns:
                    fig_sources.add_trace(go.Scatter(
                        x=df_positive.index,
                        y=df_positive[col],
                        mode='lines',
                        name=col,
                        stackgroup='one',
                        hoverinfo='x+y+name',
                        showlegend=False
                    ))
        
                fig_sources.update_layout(
                    margin=dict(l=20, r=20, t=30, b=30),
                    paper_bgcolor='#ffffff',
                    plot_bgcolor='#ffffff',
                    yaxis_title="Power (MW)",
                    xaxis_title="Time"
                )
        
                st.plotly_chart(fig_sources, use_container_width=True)

                if not df_positive.empty:
                    total_by_source = df_positive.sum()
                    main_source = total_by_source.idxmax()
                    main_value = total_by_source.max()
                    st.info(f"⚡ The most used energy source in the displayed period is *{main_source}* with a total of {main_value:.0f} MW.")
                else:
                    st.warning("There is not enough data to analyze which energy source is used the most.")
            else:
                st.warning("❌ No historical energy data available for this region at the moment.")

            solar_radiation = get_solar_radiation(lat, lon)
            
            st.subheader("Solar radiation today")
            if solar_radiation and "hourly" in solar_radiation and "shortwave_radiation" in solar_radiation["hourly"]:
                hours = solar_radiation["hourly"]["time"]
                radiation = solar_radiation["hourly"]["shortwave_radiation"]
                df_rad = pd.DataFrame({
                    "Hour": pd.to_datetime(hours).strftime("%H:%M"),
                    "Radiation (W/m²)": radiation
                })
                fig_rad, ax_rad = plt.subplots(figsize=(7, 3))
                ax_rad.plot(df_rad["Hour"], df_rad["Radiation (W/m²)"], color="gold")
                ax_rad.set_ylabel("Radiation (W/m²)")
                ax_rad.set_xlabel("Hour")
                ax_rad.set_title("Hourly Solar Radiation Today")
                ax_rad.tick_params(axis='x', rotation=45)
                st.pyplot(fig_rad)
                max_rad = max(radiation)

                if max_rad > 600:
                    st.success(f"☀️ Solar radiation is high today (max: {max_rad:.0f} W/m²). It's a great time to use solar energy!")
                elif 300 <= max_rad <= 600:
                    st.info(f"🌤️ Solar radiation is moderate today (max: {max_rad:.0f} W/m²). Solar panels will work, but output may vary.")
                else:
                    st.warning(f"🌥️ Solar radiation is low today (max: {max_rad:.0f} W/m²). Solar panel performance may be limited.")

            else:
                st.warning("No solar radiation data available for today.")

            
            st.subheader("Wind conditions")
            wind = current_weather.get("wind", {})
            wind_speed = wind.get("speed", 0)
            wind_deg = wind.get("deg", 0)
            wind_gust = wind.get("gust", None)
            wind_speed_kmh = wind_speed * 3.6
            wind_gust_kmh = wind_gust * 3.6 if wind_gust else None
            arrow, compass = wind_direction_arrow(wind_deg)
            wind_label, wind_color = wind_speed_category(wind_speed_kmh)

            wind_col1, wind_col2 = st.columns([2, 3])
            with wind_col1:
                st.markdown(
                    f"""
                    <div style="margin-top: 9em; display: flex; flex-direction: column; justify-content: center; height: 100%; text-align: center;">
                        <div style="margin-bottom: 0.5em;">
                            <b>Speed:</b> <span style='color:{wind_color};font-weight:bold'>{wind_speed_kmh:.1f} km/h</span>
                        </div>
                        <div style="margin-bottom: 0.5em;">
                            <b>Direction:</b> {arrow} <b>{compass}</b> ({wind_deg}°)
                        </div>
                        {"<div style='margin-bottom: 0.5em;'><b>Gusts:</b> <span style='color:orange;font-weight:bold'>{:.1f} km/h</span></div>".format(wind_gust_kmh) if wind_gust_kmh else ""}
                        <div>
                            <b>Category:</b> <span style='color:{wind_color};font-weight:bold'>{wind_label}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            with wind_col2:
                fig, ax = plt.subplots(figsize=(2.5,2.5), subplot_kw={'projection': 'polar'})
                theta = np.deg2rad((270 - wind_deg) % 360)
                ax.arrow(theta, 0, 0, 1, width=0.08, head_width=0.25, head_length=0.2, fc=wind_color, ec=wind_color)
                ax.set_yticklabels([])
                ax.set_xticks(np.deg2rad(np.arange(0, 360, 45)))
                ax.set_xticklabels(['E', 'NE', 'N', 'NW', 'W', 'SW', 'S', 'SE'])
                ax.set_theta_zero_location('N')
                ax.set_theta_direction(-1)
                ax.set_title("Wind direction", fontsize=10)
                ax.grid(False)
                ax.spines['polar'].set_visible(False)
                st.pyplot(fig)

            if wind_speed_kmh >= 25 or (wind_gust_kmh and wind_gust_kmh >= 40):
                st.warning(f"🌬 Strong wind from {compass} – {wind_speed_kmh:.0f} km/h" +
                               (f" with gusts up to {wind_gust_kmh:.0f} km/h." if wind_gust_kmh else "."))
            elif wind_speed_kmh >= 15:
                st.info(f"💨 Moderate wind from {compass} – {wind_speed_kmh:.0f} km/h.")
            else: 
                st.success(f"🍃 Calm wind from {compass} – {wind_speed_kmh:.0f} km/h.")
            
            if wind_speed_kmh >= 25:
                st.success("💨 Strong winds favor higher wind power generation, increasing the share of renewable electricity in the grid.")
            elif wind_speed_kmh >= 15:
                st.info("🌬 Moderate wind allows wind turbines to operate efficiently, contributing to clean energy production.")
            else:
                st.warning("🍃 Light wind: wind power generation will be low, so the grid will rely more on other energy sources.")

        
        # Tab 6: Score and recommendation
        with tabs[5]:
            st.subheader("Efficiency score and advice")
            if intensity and air_quality:
                score = score_energy_consumption_day(intensity, air_quality['list'][0]['main']['aqi'], current_weather['main']['temp'])
                score_pct = int((score / 10) * 100)
        
                if score >= 7:
                    color = "green"
                elif score >= 4:
                    color = "orange"
                else:
                    color = "red"
        
                st.markdown(f"### Efficiency score: {score}/10")
        
                progress_bar_html = f"""
                <div style="background-color: lightgray; border-radius: 10px; padding: 2px; width: 100%; max-width: 400px;">
                  <div style="
                    width: {score_pct}%;
                    background-color: {color};
                    height: 25px;
                    border-radius: 10px;
                    text-align: center;
                    color: white;
                    font-weight: bold;
                    line-height: 25px;
                  ">{score_pct}%</div>
                </div>
                """
                st.markdown(progress_bar_html, unsafe_allow_html=True)

                st.write("")
        
                if score >= 7:
                    st.success("✅ Great day to use appliances or charge devices.")
                elif score >= 4:
                    st.warning("⚠️ Moderate conditions. Be conscious of use.")
                else:
                    st.error("🚫 High impact today. Limit energy use where possible.")
        
                st.markdown("### Smart tips:")
                tips = []
                if score >= 8:
                    tips.append("🔋 Charge electric car or do laundry today.")
                if intensity < 150:
                    tips.append("🧼 Run the dishwasher or washing machine during this clean energy window.")
                if air_quality['list'][0]['main']['aqi'] <= 2:
                    tips.append("🌬️ Open windows to refresh indoor air naturally.")
                temp = current_weather['main']['temp']
                if temp < 15:
                    tips.append("🧣 Dress warmer to reduce heating needs.")
                elif temp > 28:
                    tips.append("🌞 Close blinds to cool your home naturally.")
        
                for tip in tips:
                    st.markdown(tip)
            else:
                st.error("❌ Failed to retrieve weather or electricity data.")
