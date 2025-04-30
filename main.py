import psycopg2
import bcrypt
from PyQt5 import QtWidgets, QtGui, QtCore
from psycopg2 import sql
from inside import LoginWindow
from generate import connect_DB
import sys
from language import LanguageManager
import json
import os
from two_fa import VerificationWindow


def create_table(conn):
    """Создает таблицу users, если она не существует."""
    try:
        cursor = conn.cursor()
        cursor.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            )
        """))
        conn.commit()
        cursor.close()
    except psycopg2.Error as e:
        conn.rollback()


class Main_Window(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.lang_manager = LanguageManager()
        self.initUI()

        # Подключение к базе данных и создание таблицы
        self.conn = connect_DB()
        if self.conn:
            create_table(self.conn)
            self.load_users_from_json(self.conn, 'data/users.json')

    def tr(self, key: str) -> str:
        return self.lang_manager.translations.get(key, key)

    def generate_code(self, length=4):
        import random
        digits = '0123456789'
        return ''.join(random.choice(digits) for _ in range(length))

    def check_verification_code(self, username, code):
        return (
                hasattr(self, 'current_verification_code') and
                self.current_verification_code == code and
                self.current_username == username
        )

    def open_login_window(self):
        self.inside_window = LoginWindow()
        self.inside_window.show()
        self.close()

    def update_texts(self):
        t = self.lang_manager.translations
        try:
            self.lang_btn.setText(t['language_button'])
            self.username_label.setText(t['username'])
            self.password_label.setText(t['password'])
            self.login_button.setText(t['login'])
            self.create_button.setText(t['create_account'])
            self.setWindowTitle(t['window_title'])
            self.toggle_password_button.setToolTip(t['toggle_password'])
        except KeyError as e:
            print(f"{e}")

    def initUI(self):
        # Создаем все элементы интерфейса
        self.setGeometry(0, 0, 1920, 1080)
        self.setWindowTitle('Password Keeper')

        # Установка фона
        oImage = QtGui.QImage("image/Main.png")
        sImage = oImage.scaled(self.size(), QtCore.Qt.KeepAspectRatioByExpanding)
        palette = QtGui.QPalette()
        palette.setBrush(QtGui.QPalette.Window, QtGui.QBrush(sImage))
        self.setPalette(palette)

        # Создание полупрозрачного прямоугольника
        self.overlay = QtWidgets.QWidget(self)
        self.overlay.setGeometry(580, 230, 650, 350)
        self.overlay.setStyleSheet("background-color: rgba(150, 150, 150, 230);")

        # Создание элементов интерфейса
        self.username_label = QtWidgets.QLabel('Введите логин:', self)
        self.username_label.move(660, 270)
        self.username_label.setStyleSheet("font-size: 20px;")

        self.username_input = QtWidgets.QLineEdit(self)
        self.username_input.setGeometry(665, 300, 400, 50)
        self.username_input.setStyleSheet("border-radius: 20px; padding: 10px; font-size: 17px;")

        self.password_label = QtWidgets.QLabel('Введите пароль:', self)
        self.password_label.move(660, 370)
        self.password_label.setStyleSheet("font-size: 20px;")

        self.password_input = QtWidgets.QLineEdit(self)
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password_input.setGeometry(665, 400, 400, 50)
        self.password_input.setStyleSheet("border-radius: 20px; padding: 10px; font-size: 17px;")

        # Кнопка скрытия/отображения пароля
        self.toggle_password_button = QtWidgets.QPushButton(self)
        self.toggle_password_button.setGeometry(1075, 400, 50, 50)
        self.toggle_password_button.setStyleSheet("""
            QPushButton {
                background-color: #c2c2c2;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        self.toggle_password_button.setIcon(QtGui.QIcon("image/hide.png"))
        self.toggle_password_button.setIconSize(QtCore.QSize(30, 30))
        self.toggle_password_button.clicked.connect(self.toggle_password_visibility)

        # Кнопки
        button_style = """
            QPushButton {
                background-color: #c2c2c2;
                color: black;
                border: none;
                border-radius: 15px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #fdfdfd;
            }
        """

        self.login_button = QtWidgets.QPushButton('Войти', self)
        self.login_button.setGeometry(1020, 500, 200, 35)
        self.login_button.setStyleSheet(button_style)
        self.login_button.clicked.connect(self.handle_login)

        self.create_button = QtWidgets.QPushButton('Создать аккаунт', self)
        self.create_button.setGeometry(600, 500, 200, 35)
        self.create_button.setStyleSheet(button_style)
        self.create_button.clicked.connect(self.handle_create_account)

        # Настройка языковой кнопки
        self.setup_language_switch()

        # Обновление текстов должно быть ПОСЛЕ создания всех элементов
        self.update_texts()

    def setup_language_switch(self):
        self.lang_btn = QtWidgets.QPushButton(self)
        self.lang_btn.setGeometry(1100, 240, 120, 40)
        self.lang_btn.setStyleSheet("""
                QPushButton {
                    font-size: 16px;
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton::menu-indicator {
                    width: 20px;
                }
            """)

        # Создаем выпадающее меню
        self.lang_menu = QtWidgets.QMenu(self)

        # Пункты меню
        self.ru_action = self.lang_menu.addAction("Русский")
        self.en_action = self.lang_menu.addAction("English")

        # Подключаем сигналы
        self.ru_action.triggered.connect(lambda: self.change_language('ru'))
        self.en_action.triggered.connect(lambda: self.change_language('en'))

        # Привязываем меню к кнопке
        self.lang_btn.setMenu(self.lang_menu)

    def change_language(self, lang_code):
        self.lang_manager.load_language(lang_code)
        self.update_texts()

    def toggle_password_visibility(self):
        """Переключает видимость пароля."""
        if self.password_input.echoMode() == QtWidgets.QLineEdit.Password:
            self.password_input.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.toggle_password_button.setIcon(QtGui.QIcon("image/look.png"))
        else:
            self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
            self.toggle_password_button.setIcon(QtGui.QIcon("image/hide.png"))

    def load_users_from_json(self, conn, file_path):
        """Загружает пользователей из JSON файла в базу данных."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    user_data = json.loads(line.strip())
                    self.save_user(conn, user_data['username'], user_data['password_hash'])
        except FileNotFoundError as e:
            print(f"{e}")
        except json.JSONDecodeError as e:
            print(f"{e}")

    def save_user(self, conn, username, password_hash):
        """Сохраняет пользователя в базу данных."""
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password_hash))
            conn.commit()
            return True  # Успешное добавление пользователя
        except psycopg2.IntegrityError:
            conn.rollback()  # Пользователь уже существует
            return False  # Не удалось добавить пользователя
        except psycopg2.Error as e:
            conn.rollback()
            return False  # Не удалось добавить пользователя
        finally:
            cursor.close()

    @staticmethod
    def read_users_from_json(file_path):
        """Читает пользователей из JSON файла."""
        users = set()
        try:
            if not os.path.exists(file_path):
                return users

            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    user_data = json.loads(line.strip())
                    users.add(user_data['username'])
        except Exception as e:
            print(f"Error reading JSON: {str(e)}")
        return users

    def write_user_to_json(self, file_path, username, password_hash):
        """Записывает нового пользователя в JSON файл."""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            existing_users = self.read_users_from_json(file_path)

            if username in existing_users:
                return False

            with open(file_path, 'a', encoding='utf-8') as f:
                json.dump({
                    "username": username,
                    "password_hash": password_hash
                }, f)
                f.write('\n')
            return True
        except Exception as e:
            print(f"Error writing to JSON: {str(e)}")
            return False

    def handle_create_account(self):
        try:
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()

            if not username or not password:
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr('error'),
                    self.tr('error_empty_fields')
                )
                return

            # Хеширование пароля
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            hashed_str = hashed.decode('utf-8')

            # Сохраняем в БД
            db_success = self.save_user(self.conn, username, hashed_str)

            # Сохраняем в JSON
            json_success = self.write_user_to_json('data/users.json', username, hashed_str)

            if db_success and json_success:
                QtWidgets.QMessageBox.information(
                    self,
                    self.tr('success'),
                    self.tr('success_create')
                )
                # Создаем новое окно перед закрытием текущего
                self.inside_window = LoginWindow()
                self.inside_window.show()
                self.close()
            else:
                error_msg = ""
                if not db_success:
                    error_msg += self.tr('error_user_exists_db') + "\n"
                if not json_success:
                    error_msg += self.tr('error_user_exists_json')

                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr('error'),
                    error_msg.strip()
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                self.tr('error'),
                f"Critical error: {str(e)}"
            )
            print(e.format_exc())

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            QtWidgets.QMessageBox.warning(
                self,
                self.tr('error'),
                self.tr('error_empty_fields')
            )
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE username=%s", (username,))
            result = cursor.fetchone()

            if result and bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8')):
                # Генерируем код подтверждения
                code = self.generate_code()
                self.current_verification_code = code
                self.current_username = username

                # Показываем код пользователю (в реальном приложении отправляем по email/SMS)
                QtWidgets.QMessageBox.information(
                    self,
                    self.tr('verification_code'),
                    f"{self.tr('your_code_is')} {code}"
                )

                # Показываем окно верификации
                self.verification_window = VerificationWindow(self, username)
                self.verification_window.show()
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr('error'),
                    self.tr('error_invalid_credentials')
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                self.tr('error'),
                str(e)
            )
        finally:
            if cursor:
                cursor.close()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = Main_Window()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()