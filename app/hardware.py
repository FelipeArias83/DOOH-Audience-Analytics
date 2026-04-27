import serial
import time

class HardwareBridge:
    def __init__(self, port='COM3', baudrate=115200):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            time.sleep(2) # Esperar a que el hardware reinicie
            print(f"Conectado al hardware en {port}")
        except Exception as e:
            self.ser = None
            print(f"Error de conexión hardware: {e}")

    def send_signal(self, command):
        """Envía un comando (ej: 'S' para Smile, 'N' para Neutral)."""
        if self.ser and self.ser.is_open:
            self.ser.write(command.encode())