import pandas as pd
import streamlit as st
import plotly.express as px

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
            df['Tanggal_str'] = df['Tanggal'].dt.strftime('%d-%m-%Y') # Format tanggal untuk tooltip
        else:
            st.warning("Kolom 'Tanggal' tidak ditemukan dalam file CSV.")
            return

         # Pastikan kolom Jenis Pengukuran tersedia
        if 'Jenis Pengukuran' not in df.columns:
            st.warning("Kolom 'Jenis Pengukuran' tidak ditemukan dalam file CSV.")
            return

        # Tampilkan data frame
        st.subheader("Data mentah")
        st.dataframe(df)

        # Filter Bulan
        bulan_unik = ['Semua'] + df['Bulan'].unique().tolist() #Tambahkan "Semua" ke daftar bulan unik
        bulan_terpilih = st.selectbox("Pilih Bulan:", bulan_unik, index=0)
        if bulan_terpilih == 'Semua':  # Cek apakah memilih semua bulan
            df_filtered = df.copy() #jika dipilih semua bulan maka semua data akan ditampilkan
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

        # Operator seluler
        operator_unik = ['Telkomsel', 'IOH', 'XL Axiata']
        
        # Pisahkan data berdasarkan jenis pengukuran
        df_route_test = df_filtered[df_filtered['Jenis Pengukuran'] == 'Route Test']
        df_static_test = df_filtered[df_filtered['Jenis Pengukuran'] == 'Static Test']

        # Parameter untuk Route Test
        st.sidebar.subheader("Parameter Route Test")
        parameter_unik_route = df_route_test['Parameter'].unique().tolist()
        parameter_terpilih_route = st.sidebar.selectbox("Pilih Parameter Route Test:", parameter_unik_route)

        # Parameter untuk Static Test
        st.sidebar.subheader("Parameter Static Test")
        parameter_unik_static = df_static_test['Parameter'].unique().tolist()
        parameter_terpilih_static = st.sidebar.selectbox("Pilih Parameter Static Test:", parameter_unik_static)

        # Membuat 2 kolom untuk menempatkan grafik
        col1, col2 = st.columns(2)

       # --- Fungsi untuk membuat grafik dan menampilkan info kualitas ---
        def create_barchart(df, parameter, title):
            df_plot = df[df['Parameter'] == parameter].melt(
                id_vars=['Alamat', 'Tanggal', 'Bulan','Kabupaten/Kota', 'Tanggal_str'],
                value_vars=operator_unik,
                var_name='Operator',
                value_name=parameter
            )
            
            if not df_plot.empty:
                # Map warna ke operator
                color_discrete_map = {op: color_map[op] for op in operator_unik if op in color_map}
            
                fig = px.bar(df_plot, x='Alamat', y=parameter, color='Operator', barmode='group',
                             hover_data=['Operator', 'Alamat', 'Tanggal_str', parameter],
                             color_discrete_map=color_discrete_map)
                st.plotly_chart(fig)
                
                 # Ambil nilai maksimum dan minimum HANYA jika kolom numeric
                if pd.api.types.is_numeric_dtype(df_plot[parameter]):
                    #Kelompokkan data berdasarkan operator dan hitung rata-rata parameter
                    df_grouped = df_plot.groupby('Operator')[parameter].mean()

                    # Periksa apakah df_grouped tidak kosong sebelum mencari idxmax dan idxmin
                    if not df_grouped.empty:
                        #Operator dengan kualitas rata-rata tertinggi
                        operator_terbaik = df_grouped.idxmax()
                        nilai_terbaik = df_grouped.max()

                        #Operator dengan kualitas rata-rata terendah
                        operator_terburuk = df_grouped.idxmin()
                        nilai_terburuk = df_grouped.min()

                        st.markdown(f"**Operator {title} Terbaik (rata-rata):** {operator_terbaik} ({nilai_terbaik:.2f})")
                        st.markdown(f"**Operator {title} Terburuk (rata-rata):** {operator_terburuk} ({nilai_terburuk:.2f})")
                    else:
                        st.write(f"Tidak dapat menentukan operator terbaik/terburuk karena tidak ada data yang dikelompokkan untuk {title}.")
                else:
                      st.write(f"Nilai max dan min tidak dapat ditentukan karena {parameter} bukan data numerik.")                
                
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

    else:
        st.info("Silakan unggah file CSV untuk memulai visualisasi.")

if __name__ == "__main__":
    main()
