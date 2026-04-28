import os
import logging
import cv2
import numpy as np
import time
import tempfile

# Reduce ruido de logs de TensorFlow / MediaPipe en consola.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("GLOG_minloglevel", "3")
os.environ.setdefault("ABSL_LOG_LEVEL", "3")
logging.getLogger("tensorflow").setLevel(logging.ERROR)

import mediapipe as mp

try:
    from deepface import DeepFace
except Exception:
    DeepFace = None


def _env_flag(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_float(name, default):
    raw = os.getenv(name)
    if raw is None:
        return float(default)
    try:
        return float(raw)
    except Exception:
        return float(default)

class AudienceTracker:
    def __init__(self, enable_demographics=False, demographics_interval_sec=8.0):
        self.smile_threshold = 3.5
        self.max_num_faces = 6
        # Parametros calibrables para distancia aprox: d ~= (f * IPD_real) / IPD_pixeles
        self.focal_length_px = _env_float("FOCAL_LENGTH_PX", 700.0)
        self.real_ipd_m = _env_float("REAL_IPD_M", 0.063)
        self.demographics_interval_sec = float(demographics_interval_sec)
        self.last_demographics_ts = 0.0
        self.last_demographics = {"age": None, "gender": None, "is_child": None}
        env_enabled = _env_flag("ENABLE_DEMOGRAPHICS", default=False)
        self.demographics_enabled = (enable_demographics or env_enabled) and DeepFace is not None
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=self.max_num_faces,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
    def get_smile_score(self, landmarks):
        """Calcula si la persona sonríe midiendo la distancia de las comisuras."""
        # Puntos de la boca en FaceMesh
        left_mouth = landmarks[61]  # Comisura izquierda
        right_mouth = landmarks[291] # Comisura derecha
        top_lip = landmarks[13]      # Labio superior
        bottom_lip = landmarks[14]   # Labio inferior
        
        # Distancia horizontal vs vertical
        width = np.linalg.norm(np.array([left_mouth.x, left_mouth.y]) - np.array([right_mouth.x, right_mouth.y]))
        height = np.linalg.norm(np.array([top_lip.x, top_lip.y]) - np.array([bottom_lip.x, bottom_lip.y]))
        
        # Ratio simple: si la boca se estira horizontalmente, es una sonrisa
        return width / (height + 0.0001)

    def _estimate_distance_meters(self, landmarks, frame_width_px):
        # Landmarks exteriores aproximados de ojo izquierdo y derecho en FaceMesh.
        left_eye_outer = landmarks[33]
        right_eye_outer = landmarks[263]

        left_x = left_eye_outer.x * frame_width_px
        right_x = right_eye_outer.x * frame_width_px
        ipd_px = abs(right_x - left_x)
        if ipd_px < 1.0:
            return None

        distance_m = (self.focal_length_px * self.real_ipd_m) / ipd_px
        # Limite de seguridad para descartar outliers de tracking.
        if distance_m <= 0 or distance_m > 8:
            return None
        return distance_m

    def process_frame(self, frame):
        results = self.face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        face_detected = False
        is_smiling = False
        face_count = 0
        distance_m = None
        
        if results.multi_face_landmarks:
            face_detected = True
            face_count = len(results.multi_face_landmarks)
            frame_width = frame.shape[1]

            for face_landmarks in results.multi_face_landmarks:
                landmarks = face_landmarks.landmark
                smile_ratio = self.get_smile_score(landmarks)
                current_distance_m = self._estimate_distance_meters(landmarks, frame_width)
                if current_distance_m is not None:
                    if distance_m is None or current_distance_m < distance_m:
                        distance_m = current_distance_m
                # Si al menos una persona sonríe, marcamos sonrisa en el frame.
                if smile_ratio < self.smile_threshold:
                    is_smiling = True
                    break

            if self.demographics_enabled and self._should_refresh_demographics():
                self.last_demographics = self._estimate_demographics(frame)
                self.last_demographics_ts = time.time()

        return face_detected, is_smiling, self.last_demographics, face_count, distance_m

    def _should_refresh_demographics(self):
        return (time.time() - self.last_demographics_ts) >= self.demographics_interval_sec

    def _estimate_demographics(self, frame):
        if not self.demographics_enabled:
            return self.last_demographics

        try:
            # DeepFace funciona bien con resolución menor y reduce consumo de CPU.
            h, w = frame.shape[:2]
            if w > 640:
                scale = 640.0 / float(w)
                frame = cv2.resize(frame, (640, int(h * scale)), interpolation=cv2.INTER_AREA)

            # Guardar el frame en un archivo temporal para DeepFace
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                temp_path = tmp_file.name
                cv2.imwrite(temp_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            
            try:
                analysis = DeepFace.analyze(
                    img_path=temp_path,
                    actions=["age", "gender"],
                    detector_backend="opencv",
                    enforce_detection=False,
                    silent=True,
                )

                if isinstance(analysis, list):
                    analysis = analysis[0] if analysis else {}

                raw_age = analysis.get("age")
                age = int(round(raw_age)) if raw_age is not None else None

                dominant_gender = analysis.get("dominant_gender")
                gender = None
                if isinstance(dominant_gender, str):
                    lowered = dominant_gender.lower()
                    if lowered in ("man", "male"):
                        gender = "Hombre"
                    elif lowered in ("woman", "female"):
                        gender = "Mujer"

                is_child = age is not None and age < 13
                return {"age": age, "gender": gender, "is_child": is_child}
            finally:
                # Limpiar archivo temporal
                if os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
        except Exception:
            # Silenciar excepciones para no crashear la app
            return self.last_demographics
