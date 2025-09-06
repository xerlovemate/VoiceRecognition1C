import sys
from PyQt5.QtWidgets import QApplication
from gui import VoiceControlApp
from updater import Updater

# Конфигурация обновлений
CURRENT_VERSION = "1.0.0"
PASTEBIN_URL = "https://pastebin.com/raw/VbzsWDw5"


def check_updates():
    updater = Updater(CURRENT_VERSION, PASTEBIN_URL)
    if updater.check_for_updates():
        return updater
    return None


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Проверяем обновления
    updater = check_updates()

    window = VoiceControlApp()
    window.show()

    # Если есть обновление, показываем диалог
    if updater and updater.show_update_dialog(window):
        updater.download_and_install(window)

    sys.exit(app.exec_())