import sys
import asyncio
import speech_recognition as sr
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import keyboard
from pynput.keyboard import Key, Controller
import ctypes
from rapidfuzz import process
from plyer import notification
import time

pynput_keyboard = Controller()


def press_and_release(key):
    pynput_keyboard.press(key)
    pynput_keyboard.release(key)


async def delete_word():
    with pynput_keyboard.pressed(Key.ctrl):
        press_and_release(Key.backspace)


def get_keyboard_layout():
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        thread_id = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, 0)
        layout_id = ctypes.windll.user32.GetKeyboardLayout(thread_id) & 0xFFFF
        return layout_id
    except:
        return 0


def is_russian_layout():
    rus_layout_ids = [0x419, 1049]
    return get_keyboard_layout() in rus_layout_ids


async def fuzzy_match(text, commands, threshold=85):
    if len(text) <= 2:
        return None

    match, score, _ = process.extractOne(text, commands)
    if score >= threshold:
        return match
    return None


class VoiceThread(QThread):
    update_status_signal = pyqtSignal(str)
    voice_control_state_changed = pyqtSignal(bool)
    recognized_text = pyqtSignal(str)

    def __init__(self, mode='default'):
        super().__init__()
        self.mode = mode
        self.running = True
        self.voice_control_enabled = False
        self.russian_layout = is_russian_layout()

        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.5
        self.recognizer.energy_threshold = 400
        self.recognizer.dynamic_energy_threshold = True
        self.microphone = sr.Microphone()

        self.replacements = {
            'точка с запятой': ';',
            'точка': '.',
            'равно': ' = ',
            'запятая': ',',
            'null': 'NULL',
            'пустой': 'NULL',
            'восклицательный знак': '!',
            'восклицательный': '!',
            'собака': '@',
            'двойная кавычка': '""',
            'двойные кавычки': '""',
            'двойные кавычк': '""',
            'двойные кавыч': '""',
            'двойные кавы': '""',
            'двойные кав': '""',
            'двойные ка': '""',
            'двойные к': '""',
            'кавычки': "''",
            'кавычка': "''",
            'решётка': '#',
            'доллар': '$',
            'процент': '%',
            'двоеточие': ':',
            'амперсанд': '&',
            'вопросительный знак': '?',
            'знак вопроса': '?',
            'звёздочка': '*',
            'квадратные скобки': '[]',
            'фигурные скобки': '{}',
            'скобки': '()',
            'квадратная скобка': '[]',
            'фигурная скобка': '{}',
            'скобка': '()',
            'тире': '-',
            'минус': '-',
            'прибавить': '+',
            'слэш': '/',
            'нижнее подчёркивание': '_',
            'больше': '>',
            'меньше': '<',
            'ё': 'e',
            'нет': 'не'
        }

        self.commands = {
            "интер": ["энтер", "интер", 'enter'],
            "таб": ["тап", "так", "таб", "пап", "tab"],
            "удали": ["удали"],
            "копье": ["копье", 'копи', 'копии', 'копьё'],
            "паста": ["паста", "вставка", "paste"],
            "вырезать": ["вырезать"],
            "поиск": ["поиск"],
            "выход": ["выход", "стоп"]
        }

    def run(self):
        asyncio.run(self.async_run())

    def toggle_voice_control(self):
        self.voice_control_enabled = not self.voice_control_enabled
        self.voice_control_state_changed.emit(self.voice_control_enabled)

        if self.voice_control_enabled:
            self.update_status_signal.emit('Голосовое управление включено!')
            notification.notify(
                title="Voice1C",
                message="Программа запущена!",
                timeout=2
            )
        else:
            self.update_status_signal.emit('Голосовое управление остановлено!')
            notification.notify(
                title="Voice1C",
                message="Программа остановлена!",
                timeout=2
            )

    async def async_run(self):
        self.update_status_signal.emit(
            f'Голосовое управление запущено в режиме: '
            f'{"1С" if self.mode == "1c" else "Обычный"}'
        )

        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)

                while self.running:
                    try:
                        audio = await asyncio.to_thread(
                            self.recognizer.listen,
                            source,
                            timeout=5,
                            phrase_time_limit=15
                        )

                        text = await asyncio.to_thread(
                            self.recognizer.recognize_google,
                            audio,
                            language="ru-RU"
                        )
                        text = text.lower()
                        self.recognized_text.emit(text)

                        processed_text = self.process_text(text)
                        await self.process_command(processed_text, text)

                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        self.update_status_signal.emit("Речь не распознана")
                    except sr.RequestError as e:
                        self.update_status_signal.emit(f'Ошибка сервиса: {str(e)}')
                    except Exception as e:
                        self.update_status_signal.emit(f'Ошибка обработки: {str(e)}')

        except Exception as e:
            self.update_status_signal.emit(f'Критическая ошибка: {str(e)}')

    def process_text(self, text):
        # Применяем замены ДО обработки режима
        for key, value in self.replacements.items():
            text = text.replace(key, value)

        # Для отладки
        print(f"After replacements: '{text}'")

        if self.mode == '1c':
            # Сначала заменим составные операторы на специальные метки
            text = text.replace(' = ', ' [EQUAL] ')
            text = text.replace(', ', ' [COMMA] ')

            words = text.split()
            capitalized_words = [word.capitalize() for word in words]
            text = ''.join(capitalized_words)

            # Восстановим операторы с пробелами
            text = text.replace('[equal]', ' = ')
            text = text.replace('[COMMA]', ', ')

            # Дополнительные замены для режима 1С
            text = text.replace('Пробел', ' ')
            text = text.replace('Нет', 'Не')
            # text = text.replace('Нал', "NULL")
            # text = text.replace('Now', "NULL")
            # text = text.replace('Ну', "NULL")
            #  text = text.replace('ДвойнаяКавычка', '""')
            #  text = text.replace('Кавычка', "''")
            text = text.replace(',', ', ')
            text = text.replace(' =', ' = ')
            text = text.replace('= ', ' = ')
            text = text.replace('  =  ', ' = ')  # На случай двойных пробелов

            # Убираем лишние пробелы вокруг NULL
            text = text.replace(' NULL ', 'NULL')
        else:
            text = text.replace('пробел', ' ')
            text = text.replace('точка', '.')

        # Для отладки
        print(f"Final text: '{text}'")
        return text

    async def process_command(self, processed_text, original_text):
        if original_text in ['старт', 'запуск', 'поехали']:
            self.voice_control_enabled = True
            self.voice_control_state_changed.emit(True)
            self.update_status_signal.emit('Голосовое управление включено!')
        elif original_text in ['стоп', 'остановись', 'выход']:
            self.voice_control_enabled = False
            self.voice_control_state_changed.emit(False)
            self.update_status_signal.emit('Голосовое управление остановлено!')

        elif self.voice_control_enabled:
            await self.perform_action(processed_text, original_text)

    async def perform_action(self, processed_text, original_text):
        for action, keywords in self.commands.items():
            match = await fuzzy_match(original_text, keywords)
            if match:
                if action == "интер":
                    press_and_release(Key.enter)
                elif action == "таб":
                    press_and_release(Key.tab)
                elif action == "удали":
                    await delete_word()
                elif action == "копье":
                    self.copy_text()
                elif action == "паста":
                    self.paste_text()
                elif action == "вырезать":
                    self.cut_text()
                elif action == "поиск":
                    self.search_text()
                elif action == "выход":
                    self.running = False
                return

        keyboard.write(processed_text, delay=0.005)

    def copy_text(self):
        with pynput_keyboard.pressed(Key.ctrl):
            press_and_release('с' if self.russian_layout else 'c')

    def paste_text(self):
        with pynput_keyboard.pressed(Key.ctrl):
            press_and_release('м' if self.russian_layout else 'v')

    def cut_text(self):
        with pynput_keyboard.pressed(Key.ctrl):
            press_and_release('ч' if self.russian_layout else 'x')

    def search_text(self):
        with pynput_keyboard.pressed(Key.ctrl):
            press_and_release('а' if self.russian_layout else 'f')

    def stop(self):
        self.running = False