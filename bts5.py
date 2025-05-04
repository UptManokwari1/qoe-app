import pandas as pd
import streamlit as st
import plotly.express as px
import leafmap.foliumap as leafmap
import folium
from folium.plugins import MarkerCluster, MousePosition
import time
import gspread
from google.oauth2.service_account import Credentials
from gspread_pandas import Spread, Client

# Set page config
st.set_page_config(page_title="QoE SIGMON", page_icon="📊", layout="wide")

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
    /* Style untuk koordinat */
    .coordinate-display {
        background-color: rgba(255, 255, 255, 0.8);
        border-radius: 4px;
        padding: 4px 8px;
        font-weight: bold;
        color: #333;
        border: 1px solid #ccc;
    }
    /* Style untuk pop-up koordinat pada peta */
    .leaflet-popup-content {
        font-family: Arial, sans-serif;
        font-size: 13px;
        line-height: 1.5;
    }
    .coords-highlight {
        background-color: #f0f0f0;
        border-left: 3px solid #2196F3;
        padding: 3px 6px;
        margin-top: 4px;
        font-weight: bold;
        font-family: monospace;
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

# Fungsi untuk memformat koordinat dengan benar
def format_coordinates(lat, lon):
    """Format koordinat ke format standar dengan 6 digit desimal"""
    if pd.isna(lat) or pd.isna(lon):
        return "Koordinat tidak tersedia"
    return f"{lat:.6f}, {lon:.6f}"

# Fungsi untuk konversi format koordinat ke Derajat-Menit-Detik
def decimal_to_dms(decimal_coord):
    """Konversi koordinat desimal ke format DMS (Derajat-Menit-Detik)"""
    is_negative = decimal_coord < 0
    decimal_coord = abs(decimal_coord)
    degrees = int(decimal_coord)
    minutes_float = (decimal_coord - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60
    
    if is_negative:
        degrees = -degrees
        
    return f"{degrees}°{minutes}'{seconds:.2f}\""

# Fungsi untuk memuat kredensial Google API
@st.cache_resource
def get_gsheet_credentials():
    # Alternatif 1: Simpan kredensial secara langsung di Streamlit secrets
    if 'gcp_service_account' in st.secrets:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        return credentials
    
    # Alternatif 2: Upload file credentials.json ke Streamlit
    else:
        try:
            # Jika sudah diupload, gunakan file tersebut
            credentials = Credentials.from_service_account_file(
                'credentials.json',
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
            )
            return credentials
        except FileNotFoundError:
            # Jika file belum diupload, minta user untuk mengupload
            st.warning("File kredensial Google API tidak ditemukan.")
            credentials_file = st.file_uploader("Unggah file kredensial Google API (credentials.json)", type=["json"], key="credential_uploader")
            if credentials_file is not None:
                import json
                creds_dict = json.loads(credentials_file.getvalue().decode())
                credentials = Credentials.from_service_account_info(
                    creds_dict,
                    scopes=[
                        "https://www.googleapis.com/auth/spreadsheets",
                        "https://www.googleapis.com/auth/drive"
                    ]
                )
                return credentials
            return None

# Fungsi untuk memuat data dari Google Sheets
@st.cache_data(ttl=300)  # Cache selama 5 menit
def load_data_from_sheets(sheet_id, sheet_name="Sheet1"):
    credentials = get_gsheet_credentials()
    if credentials is None:
        st.error("Kredensial Google API diperlukan untuk mengakses data.")
        return None
    
    try:
        # Inisialisasi klien gspread
        gc = gspread.authorize(credentials)
        
        # Buka spreadsheet berdasarkan ID
        sh = gc.open_by_key(sheet_id)
        
        # Pilih worksheet berdasarkan nama
        worksheet = sh.worksheet(sheet_name)
        
        # Dapatkan semua nilai dan header
        data = worksheet.get_all_records()
        
        # Konversi ke DataFrame pandas
        df = pd.DataFrame(data)
        
        return df
    except Exception as e:
        st.error(f"Error saat mengakses Google Sheets: {str(e)}")
        return None

# Fungsi untuk mendapatkan daftar spreadsheet yang tersedia
@st.cache_data(ttl=600)  # Cache selama 10 menit
def get_available_spreadsheets():
    credentials = get_gsheet_credentials()
    if credentials is None:
        return []
    
    try:
        gc = gspread.authorize(credentials)
        spreadsheets = gc.list_spreadsheet_files()
        return [(sheet['id'], sheet['name']) for sheet in spreadsheets]
    except Exception as e:
        st.error(f"Error saat mendapatkan daftar spreadsheet: {str(e)}")
        return []

# Fungsi untuk mendapatkan daftar worksheet dalam spreadsheet
@st.cache_data(ttl=600)  # Cache selama 10 menit
def get_worksheet_names(sheet_id):
    credentials = get_gsheet_credentials()
    if credentials is None:
        return []
    
    try:
        gc = gspread.authorize(credentials)
        sh = gc.open_by_key(sheet_id)
        return [worksheet.title for worksheet in sh.worksheets()]
    except Exception as e:
        st.error(f"Error saat mendapatkan daftar worksheet: {str(e)}")
        return []

def main():
    st.title("Visualisasi Data QoE SIGMON Operator Seluler")
    
    # Cek kredensial
    credentials = get_gsheet_credentials()
    
    if credentials is None:
        st.warning("Silakan upload file kredensial Google API (credentials.json) untuk mengakses spreadsheet.")
        return
    
    # Tampilkan opsi untuk memilih spreadsheet
    available_sheets = get_available_spreadsheets()
    
    if not available_sheets:
        st.warning("Tidak ada spreadsheet yang tersedia atau kredensial tidak memiliki akses ke spreadsheet.")
        
        # Opsional: Izinkan pengguna memasukkan ID spreadsheet secara langsung
        sheet_id = st.text_input("Masukkan ID Spreadsheet Google Sheets:", 
                                help="ID spreadsheet dapat ditemukan pada URL spreadsheet setelah '/d/'",
                                key="sheet_id_input")
        
        if sheet_id:
            worksheet_names = get_worksheet_names(sheet_id)
            if worksheet_names:
                sheet_name = st.selectbox("Pilih Worksheet:", worksheet_names, key="worksheet_select_direct")
            else:
                sheet_name = "Sheet1"  # Default
        else:
            return
    else:
        sheet_options = {name: id for id, name in available_sheets}
        selected_sheet_name = st.selectbox("Pilih Spreadsheet:", list(sheet_options.keys()), key="spreadsheet_select")
        sheet_id = sheet_options[selected_sheet_name]
        
        # Dapatkan daftar worksheet
        worksheet_names = get_worksheet_names(sheet_id)
        if worksheet_names:
            sheet_name = st.selectbox("Pilih Worksheet:", worksheet_names, key="worksheet_select")
        else:
            sheet_name = "Sheet1"  # Default
    
    # Tombol untuk memuat data
    if st.button("Muat Data", key="load_data_button"):
        with st.spinner("Memuat data dari Google Sheets..."):
            df = load_data_from_sheets(sheet_id, sheet_name)
            
            if df is None or df.empty:
                st.error("Tidak dapat memuat data dari spreadsheet atau spreadsheet kosong.")
                return
            
            # Pastikan koordinat ada dan merupakan tipe numerik
            if 'Latitude' in df.columns and 'Longitude' in df.columns:
                # Ubah ke tipe numerik dan tangani error
                try:
                    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
                    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
                    
                    # Tambahkan kolom koordinat yang diformat
                    df['Koordinat'] = df.apply(lambda row: format_coordinates(row['Latitude'], row['Longitude']), axis=1)
                    
                    # Tambahkan kolom koordinat dalam format DMS
                    df['Koordinat_DMS'] = df.apply(
                        lambda row: (f"{decimal_to_dms(abs(row['Latitude']))}{'S' if row['Latitude'] < 0 else 'N'}, "
                                    f"{decimal_to_dms(abs(row['Longitude']))}{'W' if row['Longitude'] < 0 else 'E'}")
                        if not pd.isna(row['Latitude']) and not pd.isna(row['Longitude']) else "Koordinat tidak tersedia", 
                        axis=1
                    )
                except Exception as e:
                    st.warning(f"Error saat mengkonversi koordinat: {str(e)}")
            else:
                st.warning("Kolom koordinat 'Latitude' dan/atau 'Longitude' tidak ditemukan dalam data.")
            
            # Simpan DataFrame ke session_state agar dapat diakses pada sidebar dan bagian lain
            st.session_state['df'] = df
            
            # Tampilkan data frame
            st.subheader("Data mentah")
            st.dataframe(df)
            
            # Proses data selanjutnya
            process_data(df)
    
    # Jika data sudah dimuat sebelumnya, tampilkan
    if 'df' in st.session_state:
        process_data(st.session_state['df'])

def process_data(df):
    # Pastikan kolom tanggal tersedia dan dalam format datetime
    if 'Tanggal' in df.columns:
        df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        df['Bulan'] = df['Tanggal'].dt.strftime('%B %Y')
        df['Tanggal_str'] = df['Tanggal'].dt.strftime('%d-%m-%Y')  # Format tanggal untuk tooltip
    else:
        st.warning("Kolom 'Tanggal' tidak ditemukan dalam data.")
        return
        
    # Pastikan kolom Jenis Pengukuran tersedia
    if 'Jenis Pengukuran' not in df.columns:
        st.warning("Kolom 'Jenis Pengukuran' tidak ditemukan dalam data.")
        return
       
    # Pastikan kolom koordinat tersedia
    if 'Latitude' not in df.columns or 'Longitude' not in df.columns:
        st.warning("Kolom 'Latitude' dan/atau 'Longitude' tidak ditemukan dalam data.")
        return
    
    # Tambahkan kolom koordinat terformat jika belum ada
    if 'Koordinat' not in df.columns:
        df['Koordinat'] = df.apply(lambda row: format_coordinates(row['Latitude'], row['Longitude']), axis=1)
    
    # Tambahkan kolom koordinat dalam format DMS jika belum ada
    if 'Koordinat_DMS' not in df.columns:
        df['Koordinat_DMS'] = df.apply(
            lambda row: (f"{decimal_to_dms(abs(row['Latitude']))}{'S' if row['Latitude'] < 0 else 'N'}, "
                        f"{decimal_to_dms(abs(row['Longitude']))}{'W' if row['Longitude'] < 0 else 'E'}")
            if not pd.isna(row['Latitude']) and not pd.isna(row['Longitude']) else "Koordinat tidak tersedia", 
            axis=1
        )
    
    # Filter Bulan - PENTING: Menggunakan key unik yang berbeda dari month_select_process_data
    bulan_unik = ['Semua'] + sorted(df['Bulan'].unique().tolist())
    bulan_terpilih = st.selectbox("Pilih Bulan:", bulan_unik, index=0, key="process_data_month_select_primary")  # Key yang lebih jelas & unik
    
    if bulan_terpilih == 'Semua':
        df_filtered = df.copy()
    else:
        df_filtered = df[df['Bulan'] == bulan_terpilih]
        
    # Filter Kabupaten/Kota
    if 'Kabupaten/Kota' in df.columns:
        kabupaten_unik = sorted(df_filtered['Kabupaten/Kota'].unique().tolist())
        kabupaten_terpilih = st.multiselect("Pilih Kabupaten/Kota:", kabupaten_unik, default=kabupaten_unik, key="district_multiselect_main")  # Key lebih spesifik
        
        if kabupaten_terpilih:
            df_filtered = df_filtered[df_filtered['Kabupaten/Kota'].isin(kabupaten_terpilih)]
        else:
            df_filtered = df_filtered.copy()
    else:
        st.warning("Kolom 'Kabupaten/Kota' tidak ditemukan dalam data.")
        df_filtered = df_filtered.copy()
        
    # Pilih lokasi
    lokasi_unik = sorted(df_filtered['Alamat'].unique().tolist())
    lokasi_terpilih = st.multiselect("Pilih Lokasi:", lokasi_unik, default=lokasi_unik, key="location_multiselect_main")  # Key lebih spesifik
           
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
    parameter_unik_route = sorted(df_route_test['Parameter'].unique().tolist()) if not df_route_test.empty else []
    parameter_terpilih_route = st.sidebar.selectbox("Pilih Parameter Route Test:", 
                                                  parameter_unik_route if parameter_unik_route else ['Tidak ada data'], 
                                                  key="route_param_select_sidebar")  # Key lebih spesifik
    
   # Parameter untuk Static Test
    st.sidebar.subheader("Parameter Static Test")
    parameter_unik_static = sorted(df_static_test['Parameter'].unique().tolist()) if not df_static_test.empty else []
    parameter_terpilih_static = st.sidebar.selectbox("Pilih Parameter Static Test:", 
                                                   parameter_unik_static if parameter_unik_static else ['Tidak ada data'], 
                                                   key="static_param_select_sidebar")  # Key lebih spesifik
    
    # Opsi untuk menampilkan koordinat pada peta
    st.sidebar.subheader("Opsi Peta")
    show_coordinates = st.sidebar.checkbox("Tampilkan Koordinat pada Peta", value=True, key="show_coords_checkbox_sidebar")  # Key lebih spesifik
    coordinate_format = st.sidebar.radio("Format Koordinat", 
                                       ["Desimal (DD.DDDDDD)", "Derajat-Menit-Detik (DD°MM'SS\")"], 
                                       index=0, 
                                       key="coord_format_radio_sidebar")  # Key lebih spesifik
    
    # Update fungsi format koordinat berdasarkan pilihan pengguna
    def get_coordinate_display(lat, lon):
        if pd.isna(lat) or pd.isna(lon):
            return "Koordinat tidak tersedia"
        
        if coordinate_format == "Desimal (DD.DDDDDD)":
            return f"{lat:.6f}, {lon:.6f}"
        else:
            lat_dms = decimal_to_dms(abs(lat)) + ("S" if lat < 0 else "N")
            lon_dms = decimal_to_dms(abs(lon)) + ("W" if lon < 0 else "E")
            return f"{lat_dms}, {lon_dms}"
    
    # Membuat 2 kolom untuk menempatkan grafik
    col1, col2 = st.columns(2)
    
    # --- Fungsi untuk membuat grafik dan menampilkan info kualitas ---
    def create_barchart(df, parameter, title, col_key_suffix):
        if df.empty or parameter not in df['Parameter'].values:
            st.write(f"Tidak ada data untuk {title}.")
            return None
        
        try:
            # Pastikan parameter merupakan string yang valid
            parameter_str = str(parameter)
            df_param = df[df['Parameter'] == parameter]
            
            # Melt dataframe dengan penanganan error yang lebih baik
            id_vars = ['Alamat', 'Tanggal', 'Bulan', 'Jenis Pengukuran', 'Parameter', 'Tanggal_str', 
                      'Latitude', 'Longitude', 'Koordinat', 'Koordinat_DMS']
            
            # Tambahkan 'Kabupaten/Kota' jika ada
            if 'Kabupaten/Kota' in df.columns:
                id_vars.append('Kabupaten/Kota')
            
            # Filter operator yang tersedia dalam data
            value_vars = [op for op in operator_unik if op in df.columns]
            
            if not value_vars:
                st.write(f"Tidak ada kolom operator yang valid untuk {title}.")
                return None
            
            # Coba konversi nilai operator ke numerik
            for op in value_vars:
                df_param[op] = pd.to_numeric(df_param[op], errors='coerce')
            
            # Melt dataframe
            df_plot = df_param.melt(
                id_vars=id_vars,
                value_vars=value_vars,
                var_name='Operator',
                value_name='Nilai'
            )
            
            if df_plot.empty:
                st.write(f"Tidak ada data untuk {title} setelah transformasi.")
                return None
            
            # Map warna ke operator
            color_discrete_map = {op: color_map.get(op, 'gray') for op in value_vars}
            
            # Membuat grafik batang
            fig = px.bar(
                df_plot, 
                x='Alamat', 
                y='Nilai', 
                color='Operator', 
                barmode='group',
                title=f"{parameter_str} ({title})",
                hover_data=['Operator', 'Alamat', 'Tanggal_str', 'Nilai', 'Koordinat'],
                color_discrete_map=color_discrete_map
            )
            
            # Menyesuaikan tata letak plot
            fig.update_layout(
                xaxis_title="Lokasi",
                yaxis_title=parameter_str,
                legend_title="Operator"
            )
            
            # Tampilkan grafik
            st.plotly_chart(fig)
            
            # Analisis nilai tertinggi dan terendah dengan penanganan error
            try:
                # Drop baris dengan nilai NaN
                df_plot_clean = df_plot.dropna(subset=['Nilai'])
                
                if not df_plot_clean.empty:
                    # Cari nilai tertinggi dan terendah
                    max_idx = df_plot_clean['Nilai'].idxmax()
                    min_idx = df_plot_clean['Nilai'].idxmin()
                    
                    if max_idx is not None and min_idx is not None:
                        max_row = df_plot_clean.loc[max_idx]
                        min_row = df_plot_clean.loc[min_idx]
                        
                        # Tampilkan informasi tentang operator dan lokasi dengan nilai tertinggi dan terendah
                        st.markdown(f"**Nilai {parameter_str} Tertinggi:** {max_row['Operator']} di lokasi {max_row['Alamat']} ({max_row['Nilai']:.2f})")
                        
                        # Tampilkan koordinat berdasarkan format yang dipilih
                        if coordinate_format == "Desimal (DD.DDDDDD)":
                            st.markdown(f"**Koordinat:** {max_row['Koordinat']}")
                        else:
                            st.markdown(f"**Koordinat:** {max_row['Koordinat_DMS']}")
                        
                        st.markdown(f"**Nilai {parameter_str} Terendah:** {min_row['Operator']} di lokasi {min_row['Alamat']} ({min_row['Nilai']:.2f})")
                        
                        # Tampilkan koordinat berdasarkan format yang dipilih
                        if coordinate_format == "Desimal (DD.DDDDDD)":
                            st.markdown(f"**Koordinat:** {min_row['Koordinat']}")
                        else:
                            st.markdown(f"**Koordinat:** {min_row['Koordinat_DMS']}")
                    else:
                        st.info(f"Tidak dapat menentukan nilai tertinggi dan terendah karena tidak ada indeks yang valid.")
                else:
                    st.info(f"Tidak dapat menentukan nilai tertinggi dan terendah karena tidak ada data numerik yang valid.")
            except Exception as e:
                st.info(f"Nilai tertinggi dan terendah tidak dapat ditentukan: {str(e)}")
            
            return df_plot
        except Exception as e:
            st.error(f"Error saat membuat grafik {title}: {str(e)}")
            return None
            
    # --- Membuat grafik Route Test ---
    with col1:
        st.subheader(f"Grafik {parameter_terpilih_route} (Route Test)")
        df_plot_route = create_barchart(df_route_test, parameter_terpilih_route, "Route Test", "route")
        
    # --- Membuat grafik Static Test ---
    with col2:
        st.subheader(f"Grafik {parameter_terpilih_static} (Static Test)")
        df_plot_static = create_barchart(df_static_test, parameter_terpilih_static, "Static Test", "static")
    
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
        
        # Tambahkan control koordinat ke peta
        if show_coordinates:
            # Format sesuai dengan pilihan user
            if coordinate_format == "Desimal (DD.DDDDDD)":
                formatter = 'function(num) {return L.Util.formatNum(num, 6) + "°";}'
            else:
                # Format DMS untuk MousePosition
                formatter = '''
                function(num) {
                    var deg = Math.floor(Math.abs(num));
                    var min = Math.floor((Math.abs(num) - deg) * 60);
                    var sec = ((Math.abs(num) - deg - min/60) * 3600).toFixed(2);
                    var dir = num >= 0 ? "N" : "S";
                    if (this.options.lngFirst) {
                        dir = num >= 0 ? "E" : "W";
                    }
                    return deg + "°" + min + "'" + sec + '"' + dir;
                }
                '''
                
            mouse_position = MousePosition(
                position='bottomright',
                separator=' | ',
                empty_string='',
                lng_first=False,
                num_digits=6,
                prefix='Koordinat:',
                lat_formatter=formatter,
                lng_formatter=formatter
            )
            m.add_child(mouse_position)
        
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
            .coordinate-display {
                background-color: rgba(255, 255, 255, 0.8);
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
                color: #333;
                border: 1px solid #ccc;
            }
            .coords-highlight {
                background-color: #f0f0f0;
                border-left: 3px solid #2196F3;
                padding: 3px 6px;
                margin-top: 4px;
                font-weight: bold;
                font-family: monospace;
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
                # Konversi ke nilai numerik
                df_route_map[op] = pd.to_numeric(df_route_map[op], errors='coerce')
                
                # Filter data untuk operator ini yang tidak null
                op_data = df_route_map.copy()
                op_data = op_data[op_data[op].notna()]
               
                if not op_data.empty:
                    for _, row in op_data.iterrows():
                        # Format nilai untuk tampilan
                        nilai = row[op]
                        nilai_str = f"{nilai:.2f}" if isinstance(nilai, (int, float)) else str(nilai)
                        
                        # Format koordinat berdasarkan pilihan pengguna
                        coord_display = get_coordinate_display(row['Latitude'], row['Longitude'])
                       
                        popup_content = f"""
                        <div style="font-family: Arial; font-size: 12px;">
                            <b>Jenis Pengukuran:</b> Route Test<br>
                            <b>Lokasi:</b> {row['Alamat']}<br>
                            <b>Operator:</b> {op}<br>
                            <b>Parameter:</b> {param_route}<br>
                            <b>Nilai:</b> {nilai_str}<br>
                            <b>Tanggal:</b> {row['Tanggal_str']}<br>
                            <b>Koordinat:</b> <div class="coords-highlight">{coord_display}</div>
                            {"<b>Kabupaten/Kota:</b> " + row['Kabupaten/Kota'] + "<br>" if 'Kabupaten/Kota' in op_data.columns else ""}
                        </div>
                        """
                       
                        # Buat marker dengan custom icon dan animasi
                        folium.Marker(
                            location=[row['Latitude'], row['Longitude']],
                            icon=create_custom_icon('Route Test', op, nilai),
                            popup=folium.Popup(popup_content, max_width=300),
                            tooltip=f"Route Test: {op} - {row['Alamat']} | {coord_display}"
                        ).add_to(marker_cluster)
       
        # Tambahkan marker untuk Static Test dengan animasi
        if has_static_data:
            for op in [op for op in operator_unik if op in df_static_map.columns]:
                # Konversi ke nilai numerik
                df_static_map[op] = pd.to_numeric(df_static_map[op], errors='coerce')
                
                # Filter data untuk operator ini yang tidak null
                op_data = df_static_map.copy()
                op_data = op_data[op_data[op].notna()]
               
                if not op_data.empty:
                    for _, row in op_data.iterrows():
                        # Format nilai untuk tampilan
                        nilai = row[op]
                        nilai_str = f"{nilai:.2f}" if isinstance(nilai, (int, float)) else str(nilai)
                        
                        # Format koordinat berdasarkan pilihan pengguna
                        coord_display = get_coordinate_display(row['Latitude'], row['Longitude'])
                       
                        popup_content = f"""
                        <div style="font-family: Arial; font-size: 12px;">
                            <b>Jenis Pengukuran:</b> Static Test<br>
                            <b>Lokasi:</b> {row['Alamat']}<br>
                            <b>Operator:</b> {op}<br>
                            <b>Parameter:</b> {param_static}<br>
                            <b>Nilai:</b> {nilai_str}<br>
                            <b>Tanggal:</b> {row['Tanggal_str']}<br>
                            <b>Koordinat:</b> <div class="coords-highlight">{coord_display}</div>
                            {"<b>Kabupaten/Kota:</b> " + row['Kabupaten/Kota'] + "<br>" if 'Kabupaten/Kota' in op_data.columns else ""}
                        </div>
                        """
                       
                        # Buat marker dengan custom icon dan animasi
                        folium.Marker(
                            location=[row['Latitude'], row['Longitude']],
                            icon=create_custom_icon('Static Test', op, nilai),
                            popup=folium.Popup(popup_content, max_width=300),
                            tooltip=f"Static Test: {op} - {row['Alamat']} | {coord_display}"
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
    def create_location_comparison(df, parameter, test_type, comparison_key_suffix):
        if df.empty or parameter not in df['Parameter'].values:
            return None
        
        try:
            df_param = df[df['Parameter'] == parameter].copy()
            
            # Buat DataFrame hasil untuk menyimpan nilai tertinggi dan terendah per operator dan lokasi
            comparison_data = []
            
            # Untuk setiap operator
            for op in [op for op in operator_unik if op in df_param.columns]:
                # Konversi ke numerik dengan penanganan error
                df_param[op] = pd.to_numeric(df_param[op], errors='coerce')
                
                op_data = df_param[['Alamat', 'Tanggal_str', 'Latitude', 'Longitude', 'Koordinat', 'Koordinat_DMS', op]].dropna()
                
                if not op_data.empty:
                    try:
                        # Lokasi dengan nilai tertinggi
                        max_idx = op_data[op].idxmax()
                        max_row = op_data.loc[max_idx]
                        
                        # Lokasi dengan nilai terendah
                        min_idx = op_data[op].idxmin()
                        min_row = op_data.loc[min_idx]
                        
                        # Pilih format koordinat yang sesuai dengan pilihan pengguna
                        if coordinate_format == "Desimal (DD.DDDDDD)":
                            coord_highest = max_row['Koordinat']
                            coord_lowest = min_row['Koordinat']
                        else:
                            coord_highest = max_row['Koordinat_DMS']
                            coord_lowest = min_row['Koordinat_DMS']
                        
                        comparison_data.append({
                            'Operator': op,
                            'Parameter': parameter,
                            'Jenis Test': test_type,
                            'Nilai Tertinggi': max_row[op],
                            'Lokasi Tertinggi': max_row['Alamat'],
                            'Koordinat Tertinggi': coord_highest,
                            'Tanggal Tertinggi': max_row['Tanggal_str'],
                            'Nilai Terendah': min_row[op],
                            'Lokasi Terendah': min_row['Alamat'],
                            'Koordinat Terendah': coord_lowest,
                            'Tanggal Terendah': min_row['Tanggal_str']
                        })
                    except Exception as e:
                        st.warning(f"Error saat menganalisis data operator {op}: {str(e)}")
            
            return pd.DataFrame(comparison_data) if comparison_data else None
        except Exception as e:
            st.error(f"Error saat membuat perbandingan lokasi: {str(e)}")
            return None
    
    # Buat perbandingan untuk Route Test
    if not df_route_test.empty and parameter_terpilih_route in df_route_test['Parameter'].values:
        route_comparison = create_location_comparison(df_route_test, parameter_terpilih_route, "Route Test", "route")
        if route_comparison is not None:
            st.markdown(f"##### Perbandingan {parameter_terpilih_route} (Route Test)")
            st.dataframe(route_comparison)
        else:
            st.info(f"Tidak dapat membuat perbandingan untuk {parameter_terpilih_route} (Route Test).")
    
    # Buat perbandingan untuk Static Test
    if not df_static_test.empty and parameter_terpilih_static in df_static_test['Parameter'].values:
        static_comparison = create_location_comparison(df_static_test, parameter_terpilih_static, "Static Test", "static")
        if static_comparison is not None:
            st.markdown(f"##### Perbandingan {parameter_terpilih_static} (Static Test)")
            st.dataframe(static_comparison)
        else:
            st.info(f"Tidak dapat membuat perbandingan untuk {parameter_terpilih_static} (Static Test).")

# Tambahkan fungsi untuk menyimpan konfigurasi
def save_config():
    st.sidebar.markdown("---")
    st.sidebar.subheader("Simpan Konfigurasi")
    config_name = st.sidebar.text_input("Nama Konfigurasi:", "konfigurasi_default", key="config_name_input")
    
    if st.sidebar.button("Simpan Konfigurasi Saat Ini", key="save_config_button"):
        # Inisialisasi config jika belum ada
        if 'configs' not in st.session_state:
            st.session_state['configs'] = {}
            
        # Dapatkan nilai variabel dari session state atau variabel lokal
        try:
            # Gunakan key yang benar sesuai yang didefinisikan di atas
            bulan_terpilih = st.session_state.get('month_select_main', 'Semua')
            kabupaten_terpilih = st.session_state.get('district_multiselect_main', [])
            lokasi_terpilih = st.session_state.get('location_multiselect_main', [])
            parameter_terpilih_route = st.session_state.get('route_param_select_sidebar', '')
            parameter_terpilih_static = st.session_state.get('static_param_select_sidebar', '')
            show_coordinates = st.session_state.get('show_coords_checkbox_sidebar', True)
            coordinate_format = st.session_state.get('coord_format_radio_sidebar', "Desimal (DD.DDDDDD)")
            
            # Simpan konfigurasi pilihan saat ini
            st.session_state['configs'][config_name] = {
                'bulan': bulan_terpilih,
                'kabupaten': kabupaten_terpilih,
                'lokasi': lokasi_terpilih,
                'param_route': parameter_terpilih_route,
                'param_static': parameter_terpilih_static,
                'show_coordinates': show_coordinates,
                'coordinate_format': coordinate_format
            }
            st.sidebar.success(f"Konfigurasi '{config_name}' berhasil disimpan!")
        except Exception as e:
            st.sidebar.error(f"Error saat menyimpan konfigurasi: {str(e)}")

# Load konfigurasi yang tersimpan
def load_config():
    if 'configs' in st.session_state and st.session_state['configs']:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Muat Konfigurasi")
        
        config_names = list(st.session_state['configs'].keys())
        selected_config = st.sidebar.selectbox("Pilih Konfigurasi:", config_names, key="load_config_select")
        
        if st.sidebar.button("Muat Konfigurasi", key="load_config_button"):
            try:
                config = st.session_state['configs'][selected_config]
                
                # Simpan nilai konfigurasi ke session state dengan key yang benar
                st.session_state['month_select_main'] = config.get('bulan', 'Semua')
                st.session_state['district_multiselect_main'] = config.get('kabupaten', [])
                st.session_state['location_multiselect_main'] = config.get('lokasi', [])
                st.session_state['route_param_select_sidebar'] = config.get('param_route', '')
                st.session_state['static_param_select_sidebar'] = config.get('param_static', '')
                st.session_state['show_coords_checkbox_sidebar'] = config.get('show_coordinates', True)
                st.session_state['coord_format_radio_sidebar'] = config.get('coordinate_format', "Desimal (DD.DDDDDD)")
                
                st.sidebar.success(f"Konfigurasi '{selected_config}' berhasil dimuat!")
                st.experimental_rerun()
            except Exception as e:
                st.sidebar.error(f"Error saat memuat konfigurasi: {str(e)}")

if __name__ == "__main__":
    main()
    
    # Tambahkan opsi untuk menyimpan dan memuat konfigurasi
    save_config()
    load_config()
    
# Tambahkan informasi di bagian bawah
st.markdown("""
<div class='highlight'>
    <h4>Petunjuk Penggunaan:</h4>
    <ol>
        <li>Pilih file pada Menu <b>Pilih Spreadsheet</b> untuk memilih file yang ada, kemudian Klik Tombol <b>Muat Data</b></li>
        <li>klik Menu Filter pada Parameter Route Test maupun Static Test untuk memilih Hasil Pengukurana QoE yang telah dilakukan</li>
        <li>Lakukan filter pada Menu <b>Pilih Bulan</b> untuk memilih bulan yang di inginkan</li>
        <li>Lakukan filter pada Menu <b>Pilih Kabupaten/Kota</b> untuk memilih Kabupaten/Kota yang di inginkan</li>
        <li>Untuk melihat lokasi yang telah dilakukan pengukuran QoE bisa melakukan zoom in / out pada menu <b>Peta</b></li>
        <li>Untuk data <b>Route Test</b> pada Peta bukan merupakan hasil aktual karena menggunakan data koordinat dari <b>Static test</b> yang berfungsi untuk menampilkan data pada aplikasi</li>
        <li>Data <b>Static Test</b> merupakan aktual berdasarkan hasil inputan data dari pengukuran QoE yang telah dilakukan</li>
    </ol>
</div>
""", unsafe_allow_html=True)

# Footer
st.markdown("""
<div style='text-align: center; margin-top: 30px; padding: 10px; color: #888;'>
    <p>© <b>2025 Aplikasi Visualisasi QoE Kualitas Layanan | Loka Monitor SFR Kendari</b></p>
</div>
""", unsafe_allow_html=True)