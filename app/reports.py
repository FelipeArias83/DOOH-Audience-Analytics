import streamlit as st
import pandas as pd
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from database.database import get_analytics_summary

def render_reports():
    st.header("📊 Análisis de Rendimiento de Marketing")
    df = get_analytics_summary()

    if df.empty:
        st.warning("No hay datos suficientes para generar reportes.")
        return


def render_database():
    """Visualiza los datos brutos de la base de datos."""
    st.header("💾 Datos de la Base de Datos")
    df = get_analytics_summary()

    if df.empty:
        st.info("La base de datos está vacía. Comienza a grabar sesiones para ver datos.")
        return

    st.subheader(f"Total de registros: {len(df)}")
    
    # Mostrar tabla completa con opciones de filtrado
    col1, col2 = st.columns([1, 1])
    with col1:
        search_term = st.text_input("🔍 Filtrar por anuncio:", "")
    with col2:
        emotion_filter = st.selectbox("Filtrar por emoción:", ["Todos"] + list(df['emotion_detected'].unique()))
    
    # Aplicar filtros
    filtered_df = df.copy()
    if search_term:
        filtered_df = filtered_df[filtered_df['commercial_id'].str.contains(search_term, case=False, na=False)]
    if emotion_filter != "Todos":
        filtered_df = filtered_df[filtered_df['emotion_detected'] == emotion_filter]
    
    st.dataframe(filtered_df, width="stretch")
    
    # Opciones de descarga
    col1, col2, col3 = st.columns(3)
    with col1:
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name="audience_analytics.csv",
            mime="text/csv"
        )
    
    with col2:
        st.metric("Registros mostrados", len(filtered_df))
    
    with col3:
        if st.button("🗑️ Limpiar Base de Datos"):
            import sqlite3
            from database.database import DB_PATH, init_db
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM view_sessions")
                conn.commit()
                conn.close()
                st.success("Base de datos limpiada correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al limpiar: {e}")

    # 1. Métricas Clave (KPIs)
    avg_attention = df['seconds_watched'].mean()
    total_smiles = len(df[df['emotion_detected'] == 'Gusta'])
    avg_age = pd.to_numeric(df.get('age_estimated'), errors='coerce').mean()
    total_children = int(pd.to_numeric(df.get('is_child'), errors='coerce').fillna(0).sum())
    
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("Atención Promedio", f"{avg_attention:.1f}s")
    kpi2.metric("Total 'Likes' (Gestos)", total_smiles)
    kpi3.metric("Conversión Visual", f"{(total_smiles/len(df))*100:.1f}%")
    kpi4.metric("Edad Promedio", f"{avg_age:.1f}" if pd.notna(avg_age) else "N/D")
    kpi5.metric("Niños Detectados", total_children)

    # 2. Rendimiento por Anuncio
    st.subheader("Tiempo de Atención por Comercial")
    ad_stats = df.groupby('commercial_id')['seconds_watched'].agg(['mean', 'count'])
    st.bar_chart(ad_stats['mean'])

    # 3. Mapa de Sentimiento
    st.subheader("Reacción por Anuncio")
    sentiment_map = pd.crosstab(df['commercial_id'], df['emotion_detected'])
    st.line_chart(sentiment_map)

    # 4. Distribución por Género
    st.subheader("Distribución de Género")
    gender_series = df.get('gender_detected')
    if gender_series is not None:
        gender_counts = gender_series.fillna('Desconocido').value_counts()
        st.bar_chart(gender_counts)