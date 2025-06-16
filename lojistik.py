import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import numpy as np

st.set_page_config(page_title="Ankara Lojistik Dağıtım", layout="wide")
st.title("🚚 Ankara ve Çevresi Lojistik Dağıtım Planlayıcı")

st.sidebar.header("📂 Veri Yükle")
uploaded_file = st.sidebar.file_uploader("CSV formatında teslimat verisini yükleyin", type="csv")
st.sidebar.header("🚐 Araç Bilgisi")
vehicle_count = st.sidebar.slider("Araç Sayısı", min_value=1, max_value=10, value=2)
vehicle_capacity = st.sidebar.number_input("Araç Kapasitesi (ürün sayısı)", min_value=1, value=10)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.success("Veri başarıyla yüklendi!")
    st.subheader("Veri Önizleme")
    st.dataframe(df.head())

    if {'latitude', 'longitude', 'demand'}.issubset(df.columns):
        st.subheader("Harita Üzerinde Noktalar")
        m = folium.Map(location=[39.9208, 32.8541], zoom_start=8)

        locations = [(39.9208, 32.8541)] + list(zip(df['latitude'], df['longitude']))
        demands = [0] + list(df['demand'])

        for i, loc in enumerate(locations):
            if i == 0:
                folium.Marker(loc, popup="Merkez (Ankara)", icon=folium.Icon(color='green')).add_to(m)
            else:
                folium.Marker(loc, popup=f"{df.iloc[i-1]['address']}", icon=folium.Icon(color='blue')).add_to(m)

        st_folium(m, width=700, height=500)

        st.subheader("🔄 Rota Optimizasyonu (Çoklu Araç + Kapasite Kısıtı)")
        dist_matrix = [[int(geodesic(loc1, loc2).km * 1000) for loc2 in locations] for loc1 in locations]

        def solve_vrp(dist_matrix, demands, vehicle_count, vehicle_capacity):
            manager = pywrapcp.RoutingIndexManager(len(dist_matrix), vehicle_count, 0)
            routing = pywrapcp.RoutingModel(manager)

            def distance_callback(from_index, to_index):
                return dist_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

            def demand_callback(from_index):
                return demands[manager.IndexToNode(from_index)]

            demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
            routing.AddDimensionWithVehicleCapacity(
                demand_callback_index,
                0,
                [vehicle_capacity] * vehicle_count,
                True,
                'Capacity')

            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

            solution = routing.SolveWithParameters(search_parameters)

            if solution:
                routes = []
                for vehicle_id in range(vehicle_count):
                    index = routing.Start(vehicle_id)
                    route = []
                    while not routing.IsEnd(index):
                        node = manager.IndexToNode(index)
                        route.append(node)
                        index = solution.Value(routing.NextVar(index))
                    route.append(manager.IndexToNode(index))
                    routes.append(route)
                return routes
            return []

        routes = solve_vrp(dist_matrix, demands, vehicle_count, vehicle_capacity)

        if routes:
            st.success("Rotalar başarıyla oluşturuldu!")
            for v, route in enumerate(routes):
                st.subheader(f"Araç {v+1} Rota")
                route_df = pd.DataFrame(columns=["Sıra", "Adres", "Ürün", "Mesafe (km)"])
                total_distance = 0
                for i in range(1, len(route)):
                    from_loc = locations[route[i-1]]
                    to_loc = locations[route[i]]
                    distance = geodesic(from_loc, to_loc).km
                    total_distance += distance

                    if route[i] != 0:
                        row = df.iloc[route[i] - 1]
                        route_df.loc[len(route_df)] = [i, row['address'], row['product'], round(distance, 2)]
                st.dataframe(route_df)
                st.metric(f"Araç {v+1} Toplam Mesafe", f"{round(total_distance, 2)} km")

                route_map = folium.Map(location=[39.9208, 32.8541], zoom_start=8)
                for i in range(len(route)):
                    idx = route[i]
                    lat, lon = locations[idx]
                    if idx == 0:
                        popup = "Merkez"
                        color = "green"
                    else:
                        popup = df.iloc[idx - 1]["address"]
                        color = "blue"
                    folium.Marker([lat, lon], popup=popup, icon=folium.Icon(color=color)).add_to(route_map)
                folium.PolyLine([locations[i] for i in route], color="red", weight=2.5, opacity=1).add_to(route_map)
                st_folium(route_map, width=700, height=500)

        else:
            st.error("Rota oluşturulamadı.")
    else:
        st.error("CSV'de 'latitude', 'longitude' ve 'demand' sütunları olmalı!")
else:
    st.info("Lütfen sol menüden CSV dosyası yükleyin.")

with st.expander("📄 Örnek CSV Formatı"):
    st.code("""
address,product,latitude,longitude,demand
"Ankara Çankaya",Koli 1,39.9107,32.8628,2
"Polatlı",Koli 2,39.5845,32.1458,3
"Kırıkkale",Koli 3,39.8468,33.5153,4
"Kırşehir",Koli 4,39.1458,34.1606,1
"Aksaray",Koli 5,38.3726,34.0254,2
""", language="csv")
