import os
import sys
import ctypes
from ctypes import POINTER, cast
from comtypes import CLSCTX_ALL
import torch
import soundfile as sf
from transformers import AutoProcessor, AutoModelForCTC
from screen_brightness_control import set_brightness
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLabel, QPushButton, QWidget, QFrame
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import sounddevice as sd
import queue
from rapidfuzz import fuzz, process  # For fuzzy matching

# Load pre-trained Urdu ASR model and processor
processor = AutoProcessor.from_pretrained("kingabzpro/wav2vec2-urdu")
model = AutoModelForCTC.from_pretrained("kingabzpro/wav2vec2-urdu")

# Function to ensure admin privileges
def run_as_admin():
    """Relaunch the script with admin privileges if not already running as admin."""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False

    if not is_admin:
        script = sys.argv[0]
        params = ' '.join([f'"{param}"' for param in sys.argv[1:]])
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{script}" {params}', None, 1
            )
        except Exception as e:
            print(f"Failed to request admin privileges: {e}")
        sys.exit()

# Volume control functions
def set_system_volume(level):
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    volume.SetMasterVolumeLevelScalar(level, None)

def increase_volume():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    current_volume = volume.GetMasterVolumeLevelScalar()
    volume.SetMasterVolumeLevelScalar(min(1.0, current_volume + 0.1), None)

def decrease_volume():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    current_volume = volume.GetMasterVolumeLevelScalar()
    volume.SetMasterVolumeLevelScalar(max(0.0, current_volume - 0.1), None)

# Bluetooth commands
def turn_on_bluetooth():
    os.system('powershell "Start-Service bthserv"')
    os.system('powershell "Get-PnpDevice -Class Bluetooth | Enable-PnpDevice -Confirm:$false"')
    print("Bluetooth turned on.")

def turn_off_bluetooth():
    os.system('powershell "Get-PnpDevice -Class Bluetooth | Disable-PnpDevice -Confirm:$false"')
    os.system('powershell "Stop-Service bthserv"')
    print("Bluetooth turned off.")

# commands list
commands = {
    "نوٹ پیڈ کھولو": "open_notepad",
    "وائی فائی بند کرو": "turn_off_wifi",
    "وائی فا چلاوٴ": "turn_on_wifi",
    "چمک بڑھاؤ": "increase_brightness",
    "چمک کم کرو": "decrease_brightness",
    "آواز بڑھاؤ": "increase_volume",
    "آواز کم کرو": "decrease_volume",
    "بلوٹوتھ چلاوٴ": "turn_on_bluetooth",
    "بلوٹوتھ بند کرو": "turn_off_bluetooth",
    "ایئر پلین موڈ  چلاوٴ": "turn_on_airplane_mode",
    "ایئر پلین موڈ بند کرو": "turn_off_airplane_mode",
    "کروم کھولو": "open_chrome",
    "ایکسپلورر کھولو": "open_file_explorer",
    "کیلکولیٹر کھولو": "open_calculator",
    "سپوٹیفائی کھولو": "open_spotify",
    "واٹس ایپ کھولو": "open_whatsapp"
}

# Action handlers for the commands
def execute_command(command):
    if command == "open_notepad":
        os.system("notepad.exe")
    elif command == "turn_off_wifi":
        os.system("netsh interface set interface Wi-Fi disable")
    elif command == "turn_on_wifi":
        os.system("netsh interface set interface Wi-Fi enable")
    elif command == "increase_brightness":
        set_brightness(100)  # Set brightness to 100%
    elif command == "decrease_brightness":
        set_brightness(30)  # Set brightness to 30%
    elif command == "increase_volume":
        increase_volume()  # Increase volume by 10%
    elif command == "decrease_volume":
        decrease_volume()  # Decrease volume by 10%
    elif command == "turn_on_bluetooth":
        turn_on_bluetooth()  # Turn on Bluetooth
    elif command == "turn_off_bluetooth":
        turn_off_bluetooth()  # Turn off Bluetooth
    elif command == "turn_on_airplane_mode":
        os.system("netsh interface set interface Wi-Fi disable")
        os.system("Stop bluetooth")
    elif command == "turn_off_airplane_mode":
        os.system("netsh interface set interface Wi-Fi enable")
        os.system("Start bluetooth")
    elif command == "open_chrome":
        os.system("start chrome")
    elif command == "open_file_explorer":
        os.system("explorer")
    elif command == "open_calculator":
        os.system("calc")
    elif command == "open_spotify":
        os.system("start spotify")
    elif command == "open_whatsapp":
        os.system("start shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App")

# Audio recording and processing functions
def record_audio(duration=5, sample_rate=16000):
    q = queue.Queue()

    def callback(indata, frames, time, status):
        q.put(indata.copy())

    print("Listening... Speak now.")
    audio = []
    with sd.InputStream(samplerate=sample_rate, channels=1, callback=callback):
        for _ in range(0, int(sample_rate / 1024 * duration)):
            audio.extend(q.get())

    audio = torch.tensor(audio, dtype=torch.float32).numpy()
    sf.write("temp_audio.wav", audio, sample_rate)
    return "temp_audio.wav"

def transcribe(audio_path):
    try:
        speech, rate = sf.read(audio_path)
        if len(speech.shape) > 1:
            speech = speech[:, 0]
        inputs = processor(speech, sampling_rate=rate, return_tensors="pt", padding=True)
        with torch.no_grad():
            logits = model(**inputs).logits
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = processor.batch_decode(predicted_ids)
        return transcription[0]
    except Exception as e:
        print(f"Error in transcription: {e}")
        return ""

def match_command(transcription, commands, threshold=60):
    match = process.extractOne(transcription, commands.keys(), scorer=fuzz.ratio)
    if match:
        matched_command, score = match[0], match[1]
        if score >= threshold:
            return commands[matched_command]
    return None

# GUI Implementation
class CommandApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Urdu Voice Command System")
        self.setGeometry(200, 200, 600, 400)
        self.init_ui()

    def init_ui(self):
        # Main container
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Urdu Voice Command System")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #4CAF50; margin-bottom: 20px;")
        main_layout.addWidget(title)

        # Display Area
        self.info_label = QLabel("Press 'Start Listening' to issue a command.")
        self.info_label.setFont(QFont("Arial", 12))
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet(
            "border: 1px solid #ccc; padding: 10px; background-color: #f9f9f9; margin-bottom: 20px;"
        )
        main_layout.addWidget(self.info_label)

        # Start Listening Button
        self.listen_button = QPushButton("Start Listening")
        self.listen_button.setFont(QFont("Arial", 14))
        self.listen_button.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50; color: white; padding: 10px;
                border-radius: 5px; font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            """
        )
        self.listen_button.clicked.connect(self.listen_and_execute)
        main_layout.addWidget(self.listen_button)

    def listen_and_execute(self):
        try:
            audio_path = record_audio()
            recognized_text = transcribe(audio_path)
            self.info_label.setText(f"Recognized Text: {recognized_text}")

            action = match_command(recognized_text, commands, threshold=60)
            if action:
                execute_command(action)
                self.info_label.setText(f"Executed Command: {action}")
            else:
                self.info_label.setText("Command not recognized. Please try again.")
        except Exception as e:
            self.info_label.setText(f"Error: {e}")


def main():
    app = QApplication(sys.argv)
    window = CommandApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()