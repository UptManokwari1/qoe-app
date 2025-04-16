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
    </style>
    """,
    unsafe_allow_html=True
)

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

        # Parameter yang akan divisualisasikan
        parameter_unik = df_filtered['Parameter'].unique().tolist()
        parameter_terpilih = st.selectbox("Pilih Parameter:", parameter_unik)

        # Membuat barchart
        st.subheader(f"Grafik {parameter_terpilih} di Lokasi Terpilih")

        # Menggabungkan data berdasarkan lokasi dan parameter
        df_plot = df_filtered[df_filtered['Parameter'] == parameter_terpilih].melt(
            id_vars=['Alamat', 'Tanggal', 'Bulan','Kabupaten/Kota', 'Tanggal_str'], #Menambahkan Kabupaten/Kota ke id_vars
            value_vars=operator_unik,
            var_name='Operator',
            value_name=parameter_terpilih
        )

        # Menentukan operator dengan nilai tertinggi untuk parameter tertentu
        operator_terbaik = df_plot.loc[df_plot[parameter_terpilih].idxmax(), 'Operator']
        lokasi_terbaik = df_plot.loc[df_plot[parameter_terpilih].idxmax(), 'Alamat']

        # Menentukan operator dengan nilai terendah untuk parameter tertentu
        operator_terburuk = df_plot.loc[df_plot[parameter_terpilih].idxmin(), 'Operator']
        lokasi_terburuk = df_plot.loc[df_plot[parameter_terpilih].idxmin(), 'Alamat']

        # Membuat keterangan dinamis
        keterangan_dinamis_terbaik = f"{operator_terbaik} memiliki nilai {parameter_terpilih} tertinggi di {lokasi_terbaik}."
        keterangan_dinamis_terburuk = f"{operator_terburuk} memiliki nilai {parameter_terpilih} terendah di {lokasi_terburuk}."

        # Menampilkan keterangan di aplikasi Streamlit
        st.markdown(f"**Keterangan:** {keterangan_dinamis_terbaik}")
        st.markdown(f"**Keterangan Tambahan:** {keterangan_dinamis_terburuk}")

        # Membuat grafik menggunakan plotly
        fig = px.bar(df_plot, x='Alamat', y=parameter_terpilih, color='Operator', barmode='group',
             hover_data=['Operator', 'Alamat', 'Tanggal_str', parameter_terpilih]) #Tambahkan hover data
        st.plotly_chart(fig)
    else:
        st.info("Silakan unggah file CSV untuk memulai visualisasi.")


if __name__ == "__main__":
    main()
