# updater.py
import os
import sys
import json
import requests
import tempfile
import subprocess
from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QTextEdit, QVBoxLayout, QDialog, QDialogButtonBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal


class UpdateDialog(QDialog):
    def __init__(self, version_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Доступно обновление")
        self.setModal(True)

        layout = QVBoxLayout(self)

        message = f"Доступна новая версия {version_info['version']}\n\n"
        text_edit = QTextEdit()
        text_edit.setPlainText(message + version_info.get('changelog', 'Нет информации об изменениях'))
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class DownloadThread(QThread):
    progress_updated = pyqtSignal(int)
    download_finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            # Для GitHub может потребоваться заголовок User-Agent
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(self.url, stream=True, headers=headers)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            downloaded = 0

            # Создаем временный файл
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.exe')

            for data in response.iter_content(block_size):
                downloaded += len(data)
                temp_file.write(data)
                progress = int(downloaded / total_size * 100) if total_size > 0 else 0
                self.progress_updated.emit(progress)

            temp_file.close()
            self.download_finished.emit(temp_file.name)

        except Exception as e:
            self.error_occurred.emit(str(e))


class Updater:
    def __init__(self, current_version, pastebin_url):
        self.current_version = current_version
        self.pastebin_url = pastebin_url
        self.version_info = None

    def check_for_updates(self):
        try:
            # Получаем raw-контент с Pastebin
            response = requests.get(self.pastebin_url)
            response.raise_for_status()

            self.version_info = response.json()
            latest_version = self.version_info['version']

            # Сравниваем версии
            return self.compare_versions(latest_version, self.current_version)
        except Exception as e:
            print(f"Ошибка при проверке обновлений: {e}")
            return False

    def compare_versions(self, v1, v2):
        # Простое сравнение версий формата X.Y.Z
        v1_parts = list(map(int, v1.split('.')))
        v2_parts = list(map(int, v2.split('.')))

        for i in range(max(len(v1_parts), len(v2_parts))):
            v1_part = v1_parts[i] if i < len(v1_parts) else 0
            v2_part = v2_parts[i] if i < len(v2_parts) else 0

            if v1_part > v2_part:
                return True
            elif v1_part < v2_part:
                return False

        return False  # Версии равны

    def show_update_dialog(self, parent):
        dialog = UpdateDialog(self.version_info, parent)
        return dialog.exec_() == QDialog.Accepted

    def download_and_install(self, parent):
        download_url = self.version_info['download_url']
        progress = QProgressDialog("Загрузка обновления...", "Отмена", 0, 100, parent)
        progress.setWindowTitle("Обновление")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        download_thread = DownloadThread(download_url)

        def update_progress(value):
            progress.setValue(value)

        def download_finished(temp_file):
            progress.close()
            self.install_update(temp_file)

        def download_error(error):
            progress.close()
            QMessageBox.warning(parent, "Ошибка", f"Ошибка загрузки: {error}")

        download_thread.progress_updated.connect(update_progress)
        download_thread.download_finished.connect(download_finished)
        download_thread.error_occurred.connect(download_error)

        # Отмена загрузки
        progress.canceled.connect(download_thread.terminate)

        download_thread.start()

    def install_update(self, temp_file_path):
        try:
            if getattr(sys, 'frozen', False):
                # Если программа собрана в exe
                script_path = os.path.abspath(sys.argv[0])
                updater_script = self.create_updater_script(script_path, temp_file_path)

                # Запускаем процесс обновления
                subprocess.Popen([sys.executable, updater_script])
                sys.exit(0)
        except Exception as e:
            QMessageBox.critical(None, "Ошибка обновления", f"Не удалось установить обновление: {str(e)}")

    def create_updater_script(self, target_path, temp_file_path):
        script_content = f"""
import time
import os
import shutil

try:
    # Ждем завершения основной программы
    time.sleep(2)

    # Заменяем старую версию на новую
    os.remove(r"{target_path}")
    shutil.move(r"{temp_file_path}", r"{target_path}")

    # Запускаем обновленную программу
    os.startfile(r"{target_path}")
except Exception as e:
    with open(r"{os.path.join(tempfile.gettempdir(), 'update_error.log')}", 'w') as f:
        f.write(f"Ошибка обновления: {{e}}")
    input("Нажмите Enter для выхода...")
"""
        script_path = os.path.join(tempfile.gettempdir(), "updater_script.py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        return script_path