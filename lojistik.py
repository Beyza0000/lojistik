import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import datetime

st.set_page_config(page_title="Ankara Lojistik Dağıtım", layout="wide")
st.title("🚚 Ankara ve Çevresi Lojistik Dağıtım Planlayıcı")

st.sidebar.header("📂 Veri Yükle")
uploaded_file = st.sidebar.file_uploader("CSV formatında teslimat verisini yükleyin", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("Veri başarıyla yüklendi!")
    st.subheader("1️⃣ Günlük Teslimat Planı")
    st.dataframe(df.sort_values(by=["shift", "time_window_start"]))

    st.subheader("2️⃣ Harita Üzerinde Zaman Pencereli Rotalar")
    m = folium.Map(location=[39.9208, 32.8541], zoom_start=10)

    colors = ['red', 'blue', 'green', 'purple']
    for vehicle_id in sorted(df['assigned_vehicle'].unique()):
        vehicle_data = df[df['assigned_vehicle'] == vehicle_id].copy()
        vehicle_data = vehicle_data.sort_values(by='time_window_start')
        route_points = [(row['latitude'], row['longitude']) for _, row in vehicle_data.iterrows()]

        for _, row in vehicle_data.iterrows():
            folium.Marker(
                [row['latitude'], row['longitude']],
                popup=(f"Araç {row['assigned_vehicle']}\nÜrün: {row['product']}\n"
                       f"Saat: {row['time_window_start']} - {row['time_window_end']}"),
                icon=folium.Icon(color=colors[(vehicle_id - 1) % len(colors)])
            ).add_to(m)

        folium.PolyLine(route_points, color=colors[(vehicle_id - 1) % len(colors)], weight=3, opacity=0.7,
                        tooltip=f"Araç {vehicle_id} rotası").add_to(m)

    st_folium(m, width=900, height=600)

    st.subheader("3️⃣ Vardiya Özet Bilgisi")
    summary = df.groupby(['shift', 'assigned_vehicle']).agg({
        'product': 'count',
        'demand': 'sum'
    }).reset_index().rename(columns={'product': 'Teslimat Sayısı', 'demand': 'Toplam Ürün'})

    def shift_label(shift):
        return "08:00–17:00" if shift == 1 else "17:00–00:00"

    summary['Vardiya'] = summary['shift'].apply(shift_label)
    st.dataframe(summary[['Vardiya', 'assigned_vehicle', 'Teslimat Sayısı', 'Toplam Ürün']])

else:
    st.info("Lütfen sol menüden CSV dosyası yükleyin.")

with st.expander("📄 Beklenen CSV Formatı"):
    st.code("""
address,product,latitude,longitude,demand,shift,time_window_start,time_window_end,assigned_vehicle
Ankara Çankaya,Koli A,39.9107,32.8628,2,1,08:15,09:30,1
... (devamı)
""", language="csv")
