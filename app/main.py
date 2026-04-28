import streamlit as st
import warnings
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration, WebRtcMode
import av 
import cv2
import sys
import time
import pandas as pd
from pathlib import Path

# --- CONFIGURACIÓN DE RUTAS ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from database.tools import AudienceTracker
from database.database import log_view_session, get_analytics_summary

# Ignorar advertencias de MediaPipe/Protobuf
warnings.filterwarnings(
    "ignore",
    message=r"SymbolDatabase\.GetPrototype\(\) is deprecated.*",
    category=UserWarning,
)

# --- FUNCIONES DE APOYO ---
def get_current_ad(start_time, playlist_df):
    """Calcula qué anuncio corresponde según el tiempo transcurrido."""
    if playlist_df.empty:
        return "Sin Anuncio"
    
    total_duration = playlist_df['duracion'].sum()
    elapsed = (time.time() - start_time) % total_duration
    
    acumulado = 0
    for _, row in playlist_df.iterrows():
        acumulado += row['duracion']
        if elapsed < acumulado:
            return row['banner']
    return playlist_df.iloc[-1]['banner']

# --- PROCESADOR DE VIDEO ---
class VideoProcessor(VideoTransformerBase):
    def __init__(self, playlist, start_time, enable_demographics=False, demographics_interval_sec=8.0):
        self.tracker = AudienceTracker(
            enable_demographics=enable_demographics,
            demographics_interval_sec=demographics_interval_sec,
        )
        self.playlist = playlist
        self.start_time = start_time
        self.viewing_start = None
        self.last_emotion = "Neutral"
        self.last_age = None
        self.last_gender = None
        self.last_is_child = None
        self.last_face_count = 0
        self.last_distance_m = None

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        
        # 1. Identificar anuncio actual mediante el ciclo interno
        current_ad = get_current_ad(self.start_time, self.playlist)
        
        # 2. Analizar rostros
        looking, smiling, demographics, face_count, distance_m = self.tracker.process_frame(img)
        self.last_face_count = face_count
        self.last_distance_m = distance_m
        
        if looking:
            if self.viewing_start is None:
                self.viewing_start = time.time()
            
            self.last_emotion = "Gusta" if smiling else "Neutral"
            self.last_age = demographics.get("age")
            self.last_gender = demographics.get("gender")
            self.last_is_child = demographics.get("is_child")
            
            # UI en el frame (Feedback para el móvil)
            color = (0, 255, 0) if smiling else (255, 255, 0)
            cv2.putText(img, f"Anuncio: {current_ad}", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(img, f"Gesto: {self.last_emotion}", (20, 75), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(img, f"Rostros: {self.last_face_count}", (20, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            if self.last_distance_m is not None:
                cv2.putText(img, f"Distancia aprox: {self.last_distance_m:.2f} m", (20, 145),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            if self.last_gender:
                cv2.putText(img, f"Genero: {self.last_gender}", (20, 180),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            if self.last_age is not None:
                cv2.putText(img, f"Edad aprox: {self.last_age}", (20, 215),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            if self.last_is_child is not None:
                etiqueta_infancia = "Nino/a" if self.last_is_child else "Adulto"
                cv2.putText(img, f"Grupo: {etiqueta_infancia}", (20, 250),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        else:
            if self.viewing_start:
                duration = time.time() - self.viewing_start
                # Guardar métrica vinculada al anuncio que estaba activo
                log_view_session(
                    duration,
                    self.last_emotion,
                    current_ad,
                    age=self.last_age,
                    gender=self.last_gender,
                    is_child=self.last_is_child,
                )
                self.viewing_start = None

        return av.VideoFrame.from_ndarray(img, format="bgr24")

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Marketing Analytics AI", layout="wide")
st.title("🤳 Auditoría de Marketing en Tiempo Real")

# Crear pestañas
tab1, tab2, tab3 = st.tabs(["📹 En Vivo", "📊 Reportes", "💾 Base de Datos"])

with tab1:
    st.header("Transmisión en Vivo y Control")
    
    # Configuración WebRTC
    RTC_CONFIGURATION = RTCConfiguration(
        {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    )

    # 1. Gestión de Playlist
    st.sidebar.header("📋 Programación de Ciclo")
    if 'playlist_data' not in st.session_state:
        st.session_state.playlist_data = pd.DataFrame([
            {"banner": "Apple_iPhone_15", "duracion": 10},
            {"banner": "LG_OLED_TV", "duracion": 15},
            {"banner": "Nike_Running", "duracion": 10}
        ])

    edited_playlist = st.sidebar.data_editor(
        st.session_state.playlist_data, 
        num_rows="dynamic",
        key="playlist_editor"
    )

    # 2. Modo de analítica demográfica (opcional para evitar descargas pesadas en nube)
    st.sidebar.subheader("⚙️ Rendimiento")
    enable_demographics = st.sidebar.toggle(
        "Análisis demográfico (edad/género)",
        value=False,
        help="Activa DeepFace. La primera vez puede descargar modelos grandes y agregar latencia.",
    )
    demographics_interval_sec = st.sidebar.slider(
        "Intervalo demográfico (seg)",
        min_value=5.0,
        max_value=20.0,
        value=8.0,
        step=1.0,
        help="Un valor mayor reduce CPU y evita lag durante la transmisión.",
        disabled=not enable_demographics,
    )
    if enable_demographics:
        st.sidebar.warning("Modo demográfico activo: mayor consumo de CPU y posible demora inicial.")

    # 3. Control de Inicio
    if 'start_time' not in st.session_state:
        st.session_state.start_time = None

    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("🚀 COMENZAR CICLO Y CÁMARA"):
            st.session_state.start_time = time.time()
            st.success("Ciclo sincronizado e iniciado.")

        if st.session_state.start_time:
            # Capturar start_time como variable local para evitar acceso a session_state en contexto async
            captured_start_time = st.session_state.start_time
            captured_playlist = edited_playlist.copy() if hasattr(edited_playlist, 'copy') else edited_playlist
            captured_enable_demographics = enable_demographics
            captured_demographics_interval = demographics_interval_sec
            
            # Iniciamos el WebRTC pasando la playlist y el tiempo de inicio al procesador
            webrtc_streamer(
                key="audience-tracker",
                mode=WebRtcMode.SENDRECV,
                rtc_configuration=RTC_CONFIGURATION,
                video_processor_factory=lambda: VideoProcessor(
                    playlist=captured_playlist, 
                    start_time=captured_start_time,
                    enable_demographics=captured_enable_demographics,
                    demographics_interval_sec=captured_demographics_interval,
                ),
                media_stream_constraints={
                    "video": {"facingMode": "user"}, # Fuerza cámara frontal en móviles
                    "audio": False
                },
                async_processing=True,
            )

    with col2:
        st.subheader("Estado del Sistema")
        if st.session_state.start_time:
            # Mostrar qué anuncio debería estar saliendo en el LED ahora mismo
            placeholder_ad = st.empty()
            # Pequeño loop para refrescar el nombre del anuncio en el dashboard
            ad_actual = get_current_ad(st.session_state.start_time, edited_playlist)
            placeholder_ad.info(f"Anuncio Activo: **{ad_actual}**")
            
            st.write("---")
            st.write("📈 *Las métricas se guardan automáticamente en la base de datos al finalizar cada visualización.*")
        else:
            st.info("Configura la playlist y presiona Start para comenzar la auditoría.")

with tab2:
    # Importar y mostrar reportes
    from app.reports import render_reports
    render_reports()

with tab3:
    # Importar y mostrar datos brutos
    from app.reports import render_database
    render_database()