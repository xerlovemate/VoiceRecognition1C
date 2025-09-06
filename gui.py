from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget
from PyQt5.QtGui import QIcon
from voice_control import VoiceThread


class VoiceControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Voice 1C')
        self.setGeometry(100, 100, 600, 300)
        self.setWindowIcon(QIcon('icon.ico'))
        self.setFixedSize(600, 300)

        self.status_label = QLabel('Выберите режим', self)
        self.mode_selection_widget = QWidget(self)
        self.mode_selection_layout = QVBoxLayout(self.mode_selection_widget)

        self.mode_1c_button = QPushButton('Режим 1С', self)
        self.default_mode_button = QPushButton('Обычный режим', self)
        self.return_to_menu_button = QPushButton('Вернуться в меню', self)
        self.toggle_voice_button = QPushButton('Старт', self)

        self.return_to_menu_button.setVisible(False)
        self.toggle_voice_button.setVisible(False)

        self.mode_selection_layout.addWidget(self.mode_1c_button)
        self.mode_selection_layout.addWidget(self.default_mode_button)
        self.mode_selection_widget.setLayout(self.mode_selection_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.status_label, alignment=Qt.AlignCenter)
        main_layout.addWidget(self.mode_selection_widget, alignment=Qt.AlignCenter)
        main_layout.addWidget(self.toggle_voice_button, alignment=Qt.AlignCenter)
        main_layout.addWidget(self.return_to_menu_button, alignment=Qt.AlignCenter)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.load_stylesheet('styles.css')

        self.mode_1c_button.clicked.connect(self.start_mode_1c)
        self.default_mode_button.clicked.connect(self.start_default_mode)
        self.return_to_menu_button.clicked.connect(self.return_to_menu)
        self.toggle_voice_button.clicked.connect(self.toggle_voice_control)

    def load_stylesheet(self, filename):
        with open(filename, 'r') as f:
            stylesheet = f.read()
        self.setStyleSheet(stylesheet)

    def start_mode_1c(self):
        self.start_voice_thread('1c')

    def start_default_mode(self):
        self.start_voice_thread('default')

    def start_voice_thread(self, mode):
        self.status_label.setText(f'Запуск голосового управления ({mode})...')
        self.mode_selection_widget.setVisible(False)
        self.return_to_menu_button.setVisible(True)
        self.toggle_voice_button.setVisible(True)

        try:
            self.voice_thread = VoiceThread(mode=mode)
            self.voice_thread.update_status_signal.connect(self.update_status)
            self.voice_thread.voice_control_state_changed.connect(self.update_voice_button)
            self.voice_thread.start()
        except Exception as e:
            self.status_label.setText(f'Ошибка при запуске потока: {str(e)}')

    def update_status(self, status):
        self.status_label.setText(status)

    def update_voice_button(self, enabled):
        self.toggle_voice_button.setText('Стоп' if enabled else 'Старт')

    def toggle_voice_control(self):
        if hasattr(self, 'voice_thread'):
            self.voice_thread.toggle_voice_control()

    def return_to_menu(self):
        if hasattr(self, 'voice_thread') and self.voice_thread.isRunning():
            self.voice_thread.running = False
            self.voice_thread.wait()
        self.status_label.setText('Выберите режим')
        self.mode_selection_widget.setVisible(True)
        self.return_to_menu_button.setVisible(False)
        self.toggle_voice_button.setVisible(False)