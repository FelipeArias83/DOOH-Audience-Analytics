import os
import logging
import cv2
import numpy as np
import time
import tempfile

# Reduce ruido de logs de TensorFlow / MediaPipe en consola.
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GLOG_minloglevel"] = "3"
logging.getLogger("tensorflow").setLevel(logging.ERROR)

import mediapipe as mp

try:
    from deepface import DeepFace
except Exception:
    DeepFace = None

class AudienceTracker:
    def __init__(self):
        self.smile_threshold = 3.5
        self.max_num_faces = 6
        self.demographics_interval_sec = 5.0  # Aumentado para evitar lag
        self.last_demographics_ts = 0.0
        self.last_demographics = {"age": None, "gender": None, "is_child": None}
        self.demographics_enabled = DeepFace is not None
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

    def process_frame(self, frame):
        results = self.face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        face_detected = False
        is_smiling = False
        face_count = 0
        
        if results.multi_face_landmarks:
            face_detected = True
            face_count = len(results.multi_face_landmarks)

            for face_landmarks in results.multi_face_landmarks:
                landmarks = face_landmarks.landmark
                smile_ratio = self.get_smile_score(landmarks)
                # Si al menos una persona sonríe, marcamos sonrisa en el frame.
                if smile_ratio < self.smile_threshold:
                    is_smiling = True
                    break

            if self._should_refresh_demographics():
                self.last_demographics = self._estimate_demographics(frame)
                self.last_demographics_ts = time.time()

        return face_detected, is_smiling, self.last_demographics, face_count

    def _should_refresh_demographics(self):
        return (time.time() - self.last_demographics_ts) >= self.demographics_interval_sec

    def _estimate_demographics(self, frame):
        if not self.demographics_enabled:
            return self.last_demographics

        try:
            # Guardar el frame en un archivo temporal para DeepFace
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                temp_path = tmp_file.name
                cv2.imwrite(temp_path, frame)
            
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
        except Exception as e:
            # Silenciar excepciones para no crashear la app
            return self.last_demographics