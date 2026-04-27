# 🤳 Auditoría de Marketing en Tiempo Real

**Sistema de análisis inteligente de audiencia con visión artificial para medir engagement y reacciones demográficas a anuncios publicitarios.**

---

## 📋 Características

✅ **Detección de Rostros en Vivo**
- Captura múltiples rostros simultáneamente (hasta 6)
- Análisis en tiempo real con MediaPipe Face Mesh

✅ **Análisis Demográfico**
- Detección de género (Hombre/Mujer)
- Estimación de edad aproximada
- Identificación de niños (<13 años)

✅ **Medición de Engagement**
- Detección de sonrisa (Gusta vs Neutral)
- Tiempo de visualización por anuncio
- Sincronización con playlist de comerciales

✅ **Dashboard Completo**
- Transmisión en vivo con overlay de datos
- Reportes con gráficos y KPIs
- Visor de base de datos con filtros
- Descarga de datos en CSV

---

## 🚀 Instalación Rápida

### 1. Clonar el Proyecto
```bash
cd c:\proyectos\marketing\
git clone <repo-url> visionMarketing
cd visionMarketing
```

### 2. Crear Entorno Virtual
```bash
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

**Primera ejecución:** DeepFace descargará modelos (~500MB), puede tardar 1-2 minutos.

### 4. Ejecutar la Aplicación
```bash
streamlit run app/main.py
```

La app se abrirá en `http://localhost:8501`

---

## 📁 Estructura del Proyecto

```
visionMarketing/
├── app/
│   ├── main.py              # App principal con Streamlit
│   ├── reports.py           # Módulo de reportes y base de datos
│   └── hardware.py          # Configuración de hardware (futuro)
├── database/
│   ├── tools.py             # AudienceTracker con IA de rostros
│   ├── database.py          # SQLite y gestión de datos
│   └── __init__.py
├── data/
│   └── audience_analytics.db # Base de datos SQLite (se crea automáticamente)
├── requirements.txt          # Dependencias Python
└── README.md                 # Este archivo
```

---

## 📖 Cómo Usar

### 1. Configurar la Playlist (Sidebar)
En la barra lateral izquierda, edita los anuncios que deseas mostrar:
- **banner**: Nombre del anuncio (ej: "Apple_iPhone_15")
- **duracion**: Duración en segundos

Ejemplo:
| banner | duracion |
|--------|----------|
| Apple_iPhone_15 | 10 |
| LG_OLED_TV | 15 |
| Nike_Running | 10 |

### 2. Iniciar Transmisión
1. Presiona el botón **"🚀 COMENZAR CICLO Y CÁMARA"**
2. Permite el acceso a la cámara en el navegador
3. La transmisión comenzará a mostrar:
   - Anuncio actual
   - Gesto detectado (Gusta/Neutral)
   - Número de rostros
   - Género estimado
   - Edad aproximada
   - Grupo etario (Niño/a o Adulto)

### 3. Ver Reportes
Haz click en la pestaña **"📊 Reportes"** para ver:
- Atención promedio por sesión
- Total de gestos positivos
- Tasa de conversión visual
- Edad promedio de audiencia
- Cantidad de niños detectados
- Gráficos de rendimiento por comercial
- Distribución de género

### 4. Consultar Base de Datos
Haz click en la pestaña **"💾 Base de Datos"** para:
- Ver todos los registros capturados
- Filtrar por nombre de anuncio
- Filtrar por emoción (Gusta/Neutral)
- Descargar datos en CSV
- Limpiar la BD (botón rojo)

---

## 🔧 Configuración Avanzada

### Ajustar Sensibilidad de Sonrisa
En `database/tools.py`, línea ~15:
```python
self.smile_threshold = 3.5  # Aumentar para menos sensibilidad, disminuir para más
```

### Cambiar Número de Rostros Detectados
En `database/tools.py`, línea ~14:
```python
self.max_num_faces = 6  # Cambiar a 4, 6, 8, 10, etc.
```

### Ajustar Intervalo de Análisis Demográfico
En `database/tools.py`, línea ~15:
```python
self.demographics_interval_sec = 5.0  # Segundos entre análisis (5.0 = menos lag)
```

---

## 📊 Base de Datos

**Tabla: `view_sessions`**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | ID único del registro |
| timestamp | DATETIME | Fecha y hora de captura |
| commercial_id | TEXT | Nombre del anuncio |
| seconds_watched | REAL | Segundos de visualización |
| emotion_detected | TEXT | Gusta / Neutral |
| age_estimated | INTEGER | Edad estimada |
| gender_detected | TEXT | Hombre / Mujer / NULL |
| is_child | INTEGER | 1 = niño, 0 = adulto, NULL = desconocido |

**Ubicación:** `data/audience_analytics.db` (SQLite)

---

## 🛠️ Solución de Problemas

### ❌ "ModuleNotFoundError: No module named 'deepface'"
```bash
pip install deepface
```

### ❌ "No se pudo iniciar el detector facial"
- Asegúrate de que DeepFace esté instalado
- Primera ejecución descarga modelos (~500MB)
- Verifica conexión a internet

### ❌ "AttributeError: st.session_state has no attribute 'start_time'"
- Reinicia Streamlit: `Ctrl+C` y vuelve a ejecutar

### ❌ Lag o rendimiento lento
- Aumenta `demographics_interval_sec` a 7-10 segundos
- Reduce `max_num_faces` a 4 si tienes muchos rostros

### ❌ "protobuf version conflict"
```bash
pip install "protobuf<5,>=4.25.3" --force-reinstall
```

---

## 📦 Dependencias Principales

| Paquete | Versión | Uso |
|---------|---------|-----|
| streamlit | >=1.38.0 | Framework web |
| streamlit-webrtc | latest | Transmisión de video en vivo |
| opencv-python | >=4.10.0.84 | Procesamiento de imágenes |
| mediapipe | ==0.10.14 | Detección de rostros |
| deepface | >=0.0.93 | Análisis de edad y género |
| pandas | >=2.2.0 | Manipulación de datos |
| numpy | >=2.1.0 | Cálculos numéricos |

---

## 🎯 Casos de Uso

✅ **Tiendas Retail:** Medir reacciones a cambios de escaparate

✅ **Eventos Publicitarios:** Captar atención de asistentes a anuncios

✅ **Cines Digitales:** Analizar engagement de publicidad en pantallas

✅ **Research de Mercado:** Datos demográficos de visionado voluntario

✅ **Estudios de UX:** Medir reacción emocional a interfaces

---

## 📝 Notas Técnicas

- **Privacidad:** Los datos se guardan localmente, sin conexión a servidores
- **Precisión:** La edad y género son estimaciones (±2-3 años, ~85% de precisión)
- **Latencia:** ~500-1000ms entre análisis de frame
- **Requerimientos:** Cámara web, Windows/Mac/Linux, Python 3.10+

---

## 👤 Autor

Proyecto de Visión Artificial para Marketing Analytics  
**Fecha:** Abril 2026

---

## 📞 Soporte

Para problemas o sugerencias:
1. Revisa la sección "Solución de Problemas"
2. Verifica que todas las dependencias estén instaladas
3. Reinicia Streamlit y el navegador

---

## 📜 Licencia

Proyecto propietario para uso interno en marketing.

---

**¡Listo para analizar tu audiencia! 🎬📊**
