import pandas as pd
import streamlit as st
import plotly.express as px

# Fungsi untuk memuat data
@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    return df

def main():
    st.title("Visualisasi Data QoE SIGMON Operator Seluler")

    # Upload file CSV
    uploaded_file = st.file_uploader("Unggah file CSV Anda", type="csv")

    if uploaded_file is not None:
        df = load_data(uploaded_file)

        # Pastikan kolom tanggal tersedia dan dalam format datetime
        if 'Tanggal' in df.columns:
            df['Tanggal'] = pd.to_datetime(df['Tanggal'])  # Konversi kolom Tanggal ke format datetime

        # Tampilkan data frame
        st.subheader("Data mentah")
        st.dataframe(df)

        # Pilih lokasi
        lokasi_unik = df['Alamat'].unique().tolist()
        lokasi_terpilih = st.multiselect("Pilih Lokasi:", lokasi_unik, default=lokasi_unik)

        # Filter data berdasarkan lokasi yang dipilih
        df_filtered = df[df['Alamat'].isin(lokasi_terpilih)]

        # Operator seluler
        operator_unik = ['Telkomsel', 'IOH', 'XL Axiata']

        # Parameter yang akan divisualisasikan
        parameter_unik = df['Parameter'].unique().tolist()
        parameter_terpilih = st.selectbox("Pilih Parameter:", parameter_unik)

        # Membuat barchart
        st.subheader(f"Grafik {parameter_terpilih} di Lokasi Terpilih")

        # Menggabungkan data berdasarkan lokasi dan parameter
        df_plot = df_filtered[df_filtered['Parameter'] == parameter_terpilih].melt(
            id_vars=['Alamat'],
            value_vars=operator_unik,
            var_name='Operator',
            value_name=parameter_terpilih
        )

        # Menentukan operator dengan nilai tertinggi untuk parameter tertentu
        # operator_terbaik = df_plot.loc[df_plot[parameter_terpilih].idxmax(), 'Operator']
        # lokasi_terbaik = df_plot.loc[df_plot[parameter_terpilih].idxmax(), 'Alamat']
        # keterangan_dinamis = f"{operator_terbaik} memiliki nilai {parameter_terpilih} tertinggi di {lokasi_terbaik}."
        # st.markdown(f"**Keterangan:** {keterangan_dinamis}")

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
        fig = px.bar(df_plot, x='Alamat', y=parameter_terpilih, color='Operator', barmode='group')
        st.plotly_chart(fig)
    else:
        st.info("Silakan unggah file CSV untuk memulai visualisasi.")

        
if __name__ == "__main__":
    main()
