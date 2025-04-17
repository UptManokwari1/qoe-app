import pandas as pd
import streamlit as st
import plotly.express as px
import leafmap.foliumap as leafmap
import folium
from folium.plugins import MarkerCluster
import time

# Fungsi untuk memuat data
@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    return df

st.set_page_config(page_title="QoE SIGMON", page_icon="📊:bar_chart:", layout="wide")

# CSS untuk styling
st.markdown(
    """
    <style>
    div.stMultiSelect > label {
        background-color: #e1f5fe !important;
        padding: 5px;
        border-radius: 3px;
    }
    /* Mengubah warna tombol multiselect menjadi hijau */
    .stMultiSelect .css-15tx2eq {
        background-color: #4CAF50 !important; /* Warna hijau */
        color: white !important;
    }
    /* Mengubah warna tombol multiselect saat dihover */
    .stMultiSelect .css-15tx2eq:hover {
        background-color: #367c39 !important;
    }
    /* Warna sidebar subheader untuk Route Test */
    .stSidebar > div:nth-child(1) > div:nth-child(3) {
        color: purple;
    }
    /* Warna sidebar subheader untuk Static Test */
    .stSidebar > div:nth-child(1) > div:nth-child(5) {
        color: orange;
    }
    /* Warna latar belakang untuk Parameter Route Test (Ungu) */
    [data-baseweb="select"] > div:nth-child(3) > div {
        background-color: #e0b0ff !important;
    }
    /* Warna latar belakang untuk Parameter Static Test (Orange) */
    [data-baseweb="select"] > div:nth-child(4) > div {
        background-color: #ffc04d !important;
    }
    /* CSS untuk peta */
    .leaflet-container {
        height: 500px !important;
        width: 100% !important;
    }
    /* Animasi kedip untuk marker */
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.4; }
        100% { opacity: 1; }
    }
    .marker-pulse {
        animation: pulse 1.5s infinite;
    }
    .highlight-best {
        background-color: #e6f4ea;
        padding: 3px 5px;
        border-radius: 3px;
        border-left: 3px solid #0f9d58;
    }
    .highlight-worst {
        background-color: #fce8e6;
        padding: 3px 5px;
        border-radius: 3px;
        border-left: 3px solid #d93025;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Definisi Warna Operator
color_map = {
    'Telkomsel': 'red',
    'XL Axiata': 'blue',
    'IOH': 'yellow'
}

def main():
    st.title("Visualisasi Data QoE SIGMON Operator Seluler")
    
    # Upload file CSV
    uploaded_file = st.file_uploader("Unggah file CSV Anda", type="csv")
    
    if uploaded_file is not None:
        df = load_data(uploaded_file)
        
        # Pastikan kolom tanggal tersedia dan dalam format datetime
        if 'Tanggal' in df.columns:
            df['Tanggal'] = pd.to_datetime(df['Tanggal'])
            df['Bulan'] = df['Tanggal'].dt.strftime('%B %Y')
            df['Tanggal_str'] = df['Tanggal'].dt.strftime('%d-%m-%Y')  # Format tanggal untuk tooltip
        else:
            st.warning("Kolom 'Tanggal' tidak ditemukan dalam file CSV.")
            return
            
        # Pastikan kolom Jenis Pengukuran tersedia
        if 'Jenis Pengukuran' not in df.columns:
            st.warning("Kolom 'Jenis Pengukuran' tidak ditemukan dalam file CSV.")
            return
           
        # Pastikan kolom koordinat tersedia
        if 'Latitude' not in df.columns or 'Longitude' not in df.columns:
            st.warning("Kolom 'Latitude' dan/atau 'Longitude' tidak ditemukan dalam file CSV.")
            return
            
        # Tampilkan data frame
        st.subheader("Data mentah")
        st.dataframe(df)
        
        # Filter Bulan
        bulan_unik = ['Semua'] + df['Bulan'].unique().tolist()  # Tambahkan "Semua" ke daftar bulan unik
        bulan_terpilih = st.selectbox("Pilih Bulan:", bulan_unik, index=0)
        
        if bulan_terpilih == 'Semua':  # Cek apakah memilih semua bulan
            df_filtered = df.copy()  # jika dipilih semua bulan maka semua data akan ditampilkan
        else:
            df_filtered = df[df['Bulan'] == bulan_terpilih]
            
        # Filter Kabupaten/Kota
        if 'Kabupaten/Kota' in df.columns:
            kabupaten_unik = df_filtered['Kabupaten/Kota'].unique().tolist()
            kabupaten_terpilih = st.multiselect("Pilih Kabupaten/Kota:", kabupaten_unik, default=kabupaten_unik)
            
            if kabupaten_terpilih:  # Cek apakah ada kabupaten/kota yang dipilih
                df_filtered = df_filtered[df_filtered['Kabupaten/Kota'].isin(kabupaten_terpilih)]
            else:
                df_filtered = df_filtered.copy()  # Jika tidak ada yang dipilih, gunakan semua data
        else:
            st.warning("Kolom 'Kabupaten/Kota' tidak ditemukan dalam file CSV.")
            df_filtered = df_filtered.copy()
            
        # Pilih lokasi
        lokasi_unik = df_filtered['Alamat'].unique().tolist()
        lokasi_terpilih = st.multiselect("Pilih Lokasi:", lokasi_unik, default=lokasi_unik)
               
        # Filter data berdasarkan lokasi yang dipilih
        df_filtered = df_filtered[df_filtered['Alamat'].isin(lokasi_terpilih)]
        
        # Operator seluler - pastikan ketiga operator tersedia dalam dataframe
        operator_unik = ['Telkomsel', 'IOH', 'XL Axiata']
       
        # Periksa keberadaan kolom operator
        for op in operator_unik:
            if op not in df_filtered.columns:
                st.warning(f"Kolom operator '{op}' tidak ditemukan dalam dataset.")
       
        # Pisahkan data berdasarkan jenis pengukuran
        df_route_test = df_filtered[df_filtered['Jenis Pengukuran'] == 'Route Test']
        df_static_test = df_filtered[df_filtered['Jenis Pengukuran'] == 'Static Test']
        
        # Parameter untuk Route Test
        st.sidebar.subheader("Parameter Route Test")
        parameter_unik_route = df_route_test['Parameter'].unique().tolist() if not df_route_test.empty else []
        parameter_terpilih_route = st.sidebar.selectbox("Pilih Parameter Route Test:", parameter_unik_route if parameter_unik_route else ['Tidak ada data'])
        
        # Parameter untuk Static Test
        st.sidebar.subheader("Parameter Static Test")
        parameter_unik_static = df_static_test['Parameter'].unique().tolist() if not df_static_test.empty else []
        parameter_terpilih_static = st.sidebar.selectbox("Pilih Parameter Static Test:", parameter_unik_static if parameter_unik_static else ['Tidak ada data'])
        
        # Membuat 2 kolom untuk menempatkan grafik
        col1, col2 = st.columns(2)
        
        # --- Fungsi untuk membuat grafik dan menampilkan info kualitas ---
        def create_barchart(df, parameter, title):
            if df.empty or parameter not in df['Parameter'].values:
                st.write(f"Tidak ada data untuk {title}.")
                return None
               
            df_plot = df[df['Parameter'] == parameter].melt(
                id_vars=['Alamat', 'Tanggal', 'Bulan', 'Jenis Pengukuran', 'Parameter', 'Tanggal_str', 'Latitude', 'Longitude'] +
                        (['Kabupaten/Kota'] if 'Kabupaten/Kota' in df.columns else []),
                value_vars=[op for op in operator_unik if op in df.columns],
                var_name='Operator',
                value_name='Nilai'
            )
           
            if not df_plot.empty:
                # Map warna ke operator
                color_discrete_map = {op: color_map[op] for op in operator_unik if op in color_map}
           
                fig = px.bar(df_plot, x='Alamat', y='Nilai', color='Operator', barmode='group',
                             title=f"{parameter} ({title})",
                             hover_data=['Operator', 'Alamat', 'Tanggal_str', 'Nilai'],
                             color_discrete_map=color_discrete_map)
               
                # Menyesuaikan tata letak plot
                fig.update_layout(
                    xaxis_title="Lokasi",
                    yaxis_title=parameter,
                    legend_title="Operator"
                )
               
                st.plotly_chart(fig)
               
                # Analisis nilai tertinggi dan terendah untuk setiap operator dan lokasi
                if pd.api.types.is_numeric_dtype(df_plot['Nilai']):
                    # Cari nilai tertinggi dan terendah di seluruh dataset
                    max_row = df_plot.loc[df_plot['Nilai'].idxmax()]
                    min_row = df_plot.loc[df_plot['Nilai'].idxmin()]
                    
                    # Tampilkan informasi tentang operator dan lokasi dengan nilai tertinggi dan terendah
                    st.markdown(f"**Nilai {parameter} Tertinggi:** {max_row['Operator']} di lokasi {max_row['Alamat']} ({max_row['Nilai']:.2f})")
                    st.markdown(f"**Nilai {parameter} Terendah:** {min_row['Operator']} di lokasi {min_row['Alamat']} ({min_row['Nilai']:.2f})")
                else:
                    st.write(f"Nilai tertinggi dan terendah tidak dapat ditentukan karena parameter bukan data numerik.")                
               
                return df_plot
            else:
                st.write(f"Tidak ada data untuk {title}.")
                return None
                
        # --- Membuat grafik Route Test ---
        with col1:
            st.subheader(f"Grafik {parameter_terpilih_route} (Route Test)")
            df_plot_route = create_barchart(df_route_test, parameter_terpilih_route, "Route Test")
            
        # --- Membuat grafik Static Test ---
        with col2:
            st.subheader(f"Grafik {parameter_terpilih_static} (Static Test)")
            df_plot_static = create_barchart(df_static_test, parameter_terpilih_static, "Static Test")
        
        # ----- PETA GABUNGAN UNTUK ROUTE TEST DAN STATIC TEST -----
        st.subheader("Peta Lokasi QoE SIGMON (Route Test & Static Test)")
       
        # Fungsi untuk membuat peta gabungan dengan kedua jenis pengukuran dan animasi kedip
        def create_combined_map(df_route, df_static, param_route, param_static):
            # Cek apakah ada data untuk ditampilkan
            has_route_data = not df_route.empty and param_route in df_route['Parameter'].values
            has_static_data = not df_static.empty and param_static in df_static['Parameter'].values
           
            if not has_route_data and not has_static_data:
                st.write("Tidak ada data untuk ditampilkan pada peta.")
                return None
           
            # Filter data berdasarkan parameter yang dipilih
            df_route_map = df_route[df_route['Parameter'] == param_route] if has_route_data else pd.DataFrame()
            df_static_map = df_static[df_static['Parameter'] == param_static] if has_static_data else pd.DataFrame()
           
            # Gabungkan data untuk menentukan titik tengah peta
            df_combined = pd.concat([df_route_map, df_static_map])
           
            if df_combined.empty:
                st.write("Tidak ada data untuk parameter yang dipilih.")
                return None
           
            # Menghitung nilai tengah koordinat untuk titik awal peta
            center_lat = df_combined['Latitude'].mean()
            center_lon = df_combined['Longitude'].mean()
           
            # Buat peta dengan leafmap - set zoom awal lebih jauh (nilai zoom lebih kecil)
            m = leafmap.Map(center=[center_lat, center_lon], zoom=8)
            # Tambahkan basemap
            m.add_basemap("OpenStreetMap")
            
            # Tambahkan CSS untuk animasi kedip ke peta
            folium.Element("""
            <style>
                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.4; }
                    100% { opacity: 1; }
                }
                .marker-pulse {
                    animation: pulse 1.5s infinite;
                }
                .marker-pulse-fast {
                    animation: pulse 0.8s infinite;
                }
            </style>
            """).add_to(m)
           
            # Membuat grup marker untuk clustering titik-titik yang berdekatan
            marker_cluster = MarkerCluster().add_to(m)
           
            # Fungsi untuk membuat ikon berdasarkan jenis test dan operator dengan efek kedipan
            def create_custom_icon(jenis_test, operator, nilai):
                # Tentukan warna berdasarkan operator
                color = color_map.get(operator, 'gray')
                
                # Tentukan jenis ikon dan kelas animasi berdasarkan jenis test
                if jenis_test == 'Route Test':
                    # Untuk Route Test, gunakan ikon pin lokasi dengan animasi pulse
                    icon_html = f"""
                    <div class="marker-pulse" style="animation-delay: {(hash(operator) % 5) * 0.2}s;">
                        <i class="fa fa-map-marker fa-2x" style="color:{color};"></i>
                    </div>
                    """
                    return folium.DivIcon(
                        html=icon_html,
                        icon_size=(30, 30),
                        icon_anchor=(15, 30)
                    )
                else:
                    # Untuk Static Test, gunakan ikon wifi dengan animasi pulse
                    icon_html = f"""
                    <div class="marker-pulse-fast" style="animation-delay: {(hash(operator) % 3) * 0.3}s;">
                        <i class="fa fa-wifi fa-2x" style="color:{color};"></i>
                    </div>
                    """
                    return folium.DivIcon(
                        html=icon_html,
                        icon_size=(30, 30),
                        icon_anchor=(15, 15)
                    )
           
            # Tambahkan marker untuk Route Test dengan animasi
            if has_route_data:
                for op in [op for op in operator_unik if op in df_route_map.columns]:
                    # Filter data untuk operator ini yang tidak null
                    op_data = df_route_map.copy()
                    op_data = op_data[op_data[op].notna()]
                   
                    if not op_data.empty:
                        for _, row in op_data.iterrows():
                            # Format nilai untuk tampilan
                            nilai = row[op]
                            nilai_str = f"{nilai:.2f}" if isinstance(nilai, (int, float)) else str(nilai)
                           
                            popup_content = f"""
                            <div style="font-family: Arial; font-size: 12px;">
                                <b>Jenis Pengukuran:</b> Route Test<br>
                                <b>Lokasi:</b> {row['Alamat']}<br>
                                <b>Operator:</b> {op}<br>
                                <b>Parameter:</b> {param_route}<br>
                                <b>Nilai:</b> {nilai_str}<br>
                                <b>Tanggal:</b> {row['Tanggal_str']}<br>
                                {"<b>Kabupaten/Kota:</b> " + row['Kabupaten/Kota'] + "<br>" if 'Kabupaten/Kota' in op_data.columns else ""}
                            </div>
                            """
                           
                            # Buat marker dengan custom icon dan animasi
                            folium.Marker(
                                location=[row['Latitude'], row['Longitude']],
                                icon=create_custom_icon('Route Test', op, nilai),
                                popup=folium.Popup(popup_content, max_width=300),
                                tooltip=f"Route Test: {op} - {row['Alamat']}"
                            ).add_to(marker_cluster)
           
            # Tambahkan marker untuk Static Test dengan animasi
            if has_static_data:
                for op in [op for op in operator_unik if op in df_static_map.columns]:
                    # Filter data untuk operator ini yang tidak null
                    op_data = df_static_map.copy()
                    op_data = op_data[op_data[op].notna()]
                   
                    if not op_data.empty:
                        for _, row in op_data.iterrows():
                            # Format nilai untuk tampilan
                            nilai = row[op]
                            nilai_str = f"{nilai:.2f}" if isinstance(nilai, (int, float)) else str(nilai)
                           
                            popup_content = f"""
                            <div style="font-family: Arial; font-size: 12px;">
                                <b>Jenis Pengukuran:</b> Static Test<br>
                                <b>Lokasi:</b> {row['Alamat']}<br>
                                <b>Operator:</b> {op}<br>
                                <b>Parameter:</b> {param_static}<br>
                                <b>Nilai:</b> {nilai_str}<br>
                                <b>Tanggal:</b> {row['Tanggal_str']}<br>
                                {"<b>Kabupaten/Kota:</b> " + row['Kabupaten/Kota'] + "<br>" if 'Kabupaten/Kota' in op_data.columns else ""}
                            </div>
                            """
                           
                            # Buat marker dengan custom icon dan animasi
                            folium.Marker(
                                location=[row['Latitude'], row['Longitude']],
                                icon=create_custom_icon('Static Test', op, nilai),
                                popup=folium.Popup(popup_content, max_width=300),
                                tooltip=f"Static Test: {op} - {row['Alamat']}"
                            ).add_to(marker_cluster)
           
            # Tambahkan legenda untuk operator dan jenis pengukuran
            legend_html = """
            <div style="position: fixed; bottom: 50px; right: 50px; z-index: 1000; background-color: white;
                        padding: 10px; border: 2px solid grey; border-radius: 5px">
                <div style="margin-bottom: 5px;"><b>Operator:</b></div>
            """
           
            # Legenda untuk operator dengan animasi
            for op in operator_unik:
                legend_html += f"""
                <div style="margin-bottom: 3px;">
                    <i style="background:{color_map.get(op, 'gray')}; width: 12px; height: 12px; display: inline-block; border: 1px solid black;" 
                       class="marker-pulse"></i> {op}
                </div>
                """
           
            # Legenda untuk jenis pengukuran dengan animasi
            legend_html += """
                <div style="margin-top: 10px; margin-bottom: 5px;"><b>Jenis Pengukuran:</b></div>
                <div style="margin-bottom: 3px;" class="marker-pulse"><i class="fa fa-map-marker" style="color:gray;"></i> Route Test</div>
                <div style="margin-bottom: 3px;" class="marker-pulse-fast"><i class="fa fa-wifi" style="color:gray;"></i> Static Test</div>
            </div>
            """
           
            m.add_html(html=legend_html, position="bottomright")
           
            return m
            
        # Buat dan tampilkan peta gabungan dengan ikon berkedip
        combined_map = create_combined_map(df_route_test, df_static_test, parameter_terpilih_route, parameter_terpilih_static)
        if combined_map:
            combined_map.to_streamlit(height=500)
        else:
            st.write("Tidak ada data untuk ditampilkan pada peta gabungan.")
            
        # Tambahkan ringkasan perbandingan untuk setiap parameter
        st.subheader("Ringkasan Perbandingan Parameter Antar Operator")
        
        # Fungsi untuk membuat tabel perbandingan lokasi terbaik dan terburuk
        def create_location_comparison(df, parameter, test_type):
            if df.empty or parameter not in df['Parameter'].values:
                return None
                
            df_param = df[df['Parameter'] == parameter].copy()
            
            # Buat DataFrame hasil untuk menyimpan nilai tertinggi dan terendah per operator dan lokasi
            comparison_data = []
            
            # Untuk setiap operator
            for op in [op for op in operator_unik if op in df_param.columns]:
                op_data = df_param[['Alamat', 'Tanggal_str', op]].dropna()
                
                if not op_data.empty and pd.api.types.is_numeric_dtype(op_data[op]):
                    # Lokasi dengan nilai tertinggi
                    max_idx = op_data[op].idxmax()
                    max_row = op_data.loc[max_idx]
                    
                    # Lokasi dengan nilai terendah
                    min_idx = op_data[op].idxmin()
                    min_row = op_data.loc[min_idx]
                    
                    comparison_data.append({
                        'Operator': op,
                        'Parameter': parameter,
                        'Jenis Test': test_type,
                        'Nilai Tertinggi': max_row[op],
                        'Lokasi Tertinggi': max_row['Alamat'],
                        'Tanggal Tertinggi': max_row['Tanggal_str'],
                        'Nilai Terendah': min_row[op],
                        'Lokasi Terendah': min_row['Alamat'],
                        'Tanggal Terendah': min_row['Tanggal_str']
                    })
            
            return pd.DataFrame(comparison_data) if comparison_data else None
        
        # Buat perbandingan untuk Route Test
        if not df_route_test.empty and parameter_terpilih_route in df_route_test['Parameter'].values:
            route_comparison = create_location_comparison(df_route_test, parameter_terpilih_route, "Route Test")
            if route_comparison is not None:
                st.markdown(f"##### Perbandingan {parameter_terpilih_route} (Route Test)")
                st.dataframe(route_comparison)
        
        # Buat perbandingan untuk Static Test
        if not df_static_test.empty and parameter_terpilih_static in df_static_test['Parameter'].values:
            static_comparison = create_location_comparison(df_static_test, parameter_terpilih_static, "Static Test")
            if static_comparison is not None:
                st.markdown(f"##### Perbandingan {parameter_terpilih_static} (Static Test)")
                st.dataframe(static_comparison)
                
    else:
        st.info("Silakan unggah file CSV untuk memulai visualisasi.")

if __name__ == "__main__":
    main()