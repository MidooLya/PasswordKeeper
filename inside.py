from PyQt5 import QtWidgets, QtGui, QtCore
import psycopg2
import sys
import datetime
from generate import connect_DB
from language import LanguageManager


def create_table(conn):
    """Создает таблицы в базе данных."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS all_records (
                id SERIAL PRIMARY KEY,
                service_id INTEGER,
                name VARCHAR(255),
                login VARCHAR(255),
                password VARCHAR(255),
                email VARCHAR(255),
                date_added DATE DEFAULT CURRENT_DATE
            );
        """)
        conn.commit()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id SERIAL PRIMARY KEY,
                service_name VARCHAR(255) UNIQUE NOT NULL,
                table_id VARCHAR(255) UNIQUE NOT NULL
            );
        """)
        conn.commit()

        cursor.close()
    except psycopg2.Error as e:
        conn.rollback()


class LoginWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.lang_manager = LanguageManager()
        self.conn = connect_DB()
        self.current_view = None
        self.current_service_id = None
        self.initUI()
        self.setup_language_switch()
        self.update_texts()
        if self.conn:
            create_table(self.conn)
            self.initialize_services()

    def setup_language_switch(self):
        """Инициализация языковой кнопки"""
        self.lang_btn = QtWidgets.QPushButton(self)
        self.lang_btn.setGeometry(550, 115, 120, 40)
        self.lang_btn.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
            }
        """)

        self.lang_menu = QtWidgets.QMenu(self)
        self.ru_action = self.lang_menu.addAction("Русский")
        self.en_action = self.lang_menu.addAction("English")

        self.ru_action.triggered.connect(lambda: self.change_language('ru'))
        self.en_action.triggered.connect(lambda: self.change_language('en'))
        self.lang_btn.setMenu(self.lang_menu)

    def change_language(self, lang_code):
        """Переключение языка и обновление кнопки"""
        self.lang_manager.load_language(lang_code)
        self.update_texts()
        if self.current_view == 'all':
            self.load_all_records()
        elif self.current_view == 'service':
            self.show_service_table_by_id(self.current_service_id)

    def update_texts(self):
        """Обновляет тексты интерфейса при смене языка."""
        t = self.lang_manager.translations
        self.lang_btn.setText(t.get('language', 'Language'))
        self.plus_button.setText(t.get('add_service', '+'))

        # Обновляем текст кнопки "Все записи"
        for i in range(self.service_buttons_layout.count()):
            widget = self.service_buttons_layout.itemAt(i).widget()
            if widget and widget.property('is_all_records'):
                widget.setText(t.get('all_records', 'Все записи'))
                break

    def initialize_services(self):
        """Инициализирует сервисы и записывает их в базу данных."""
        cur = self.conn.cursor()
        cur.execute("SELECT service_name, table_id FROM services;")
        existing_services = cur.fetchall()

        for service_name, table_id in existing_services:
            button = QtWidgets.QPushButton(service_name, self)
            button.setStyleSheet(
                "background-color: white; border-radius: 20px; padding: 10px; font-size: 20px; text-align: center;"
            )
            button.clicked.connect(self.change_table)
            button.mouseDoubleClickEvent = lambda event, btn=button: self.rename_service(btn, event)
            self.service_buttons_layout.addWidget(button)

        cur.close()

    def save_data(self, service_id, data):
        """Сохраняет запись в базу данных."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                """ SELECT * FROM all_records WHERE service_id=%s AND login=%s AND password=%s AND email=%s AND date_added=%s; """,
                (service_id, data['login'], data['password'], data['email'], data['date_added']))
            existing_record = cur.fetchone()
            if existing_record:
                if existing_record[2:] == (data['login'], data['password'], data['email'], data['date_added']):
                    pass
                else:
                    cur.execute(
                        """ UPDATE all_records SET login=%s, password=%s, email=%s, date_added=%s WHERE service_id=%s AND id=%s; """,
                        (data['login'], data['password'], data['email'], data['date_added'], service_id,
                         existing_record[0]))
                    self.conn.commit()
            else:
                cur.execute(
                    """ INSERT INTO all_records (service_id, name, login, password, email, date_added) VALUES (%s, %s, %s, %s, %s, %s); """,
                    (service_id, data['name'], data['login'], data['password'], data['email'], data['date_added']))
                self.conn.commit()
        except Exception as e:
            self.conn.rollback()
        finally:
            cur.close()

    def cell_changed(self, row, column):
        """Обновляет дату при изменении данных"""
        if column != 4:  # Если изменена не колонка с датой
            date_item = self.table_widget.item(row, 4)
            if date_item and date_item.text():
                # Обновляем дату только для существующих записей
                date_item.setText(datetime.date.today().strftime("%Y-%m-%d"))

    def initUI(self):
        self.setGeometry(0, 0, 1920, 1080)
        self.setWindowTitle('PasswordKeeper')

        # Установка фона
        oImage = QtGui.QImage("image/dragon.jpg")
        sImage = oImage.scaled(self.size(), QtCore.Qt.KeepAspectRatioByExpanding)
        palette = QtGui.QPalette()
        palette.setBrush(QtGui.QPalette.Window, QtGui.QBrush(sImage))
        self.setPalette(palette)

        # Создание основного окна
        self.overlay3 = QtWidgets.QWidget(self)
        self.overlay3.setGeometry(500, 100, 1300, 800)
        self.overlay3.setStyleSheet(
            "background-color: rgba(150, 150, 150, 170); border-radius: 30px; padding: 10px; font-size: 20px;")

        # Создание QScrollArea для кнопок сервисов
        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setGeometry(10, 10, 380, 980)
        self.scroll_area.setWidgetResizable(True)

        self.button_container = QtWidgets.QWidget()
        self.button_container.setStyleSheet("background-color: rgba(200, 200, 200, 255);")
        self.service_buttons_layout = QtWidgets.QVBoxLayout(self.button_container)

        # Добавление кнопки "Все записи" с динамическим переводом
        self.all_records_button = QtWidgets.QPushButton(
            self.lang_manager.translations.get('all_records', 'Все записи'),
            self
        )
        self.all_records_button.setProperty('is_all_records', True)
        self.all_records_button.setStyleSheet(
            "background-color: white; border-radius: 20px; padding: 10px; font-size: 20px; text-align: center;"
        )
        self.all_records_button.clicked.connect(self.change_table)
        self.service_buttons_layout.addWidget(self.all_records_button)

        # Кнопка добавления сервисов
        self.plus_button = QtWidgets.QPushButton('+', self)
        self.plus_button.setStyleSheet(
            """QPushButton { background-color: #c2c2c2; color: black; border: none; 
            border-radius: 10px; font-size: 30px; } QPushButton:hover { background-color: #fdfdfd; }""")
        self.plus_button.clicked.connect(self.add_service_button)
        self.service_buttons_layout.addWidget(self.plus_button)

        self.scroll_area.setWidget(self.button_container)

        # Создание таблицы
        self.white_window = QtWidgets.QWidget(self)
        self.white_window.setGeometry(520, 170, 1250, 700)
        scroll_area_table = QtWidgets.QScrollArea(self.white_window)
        scroll_area_table.setGeometry(0, 0, 1250, 700)
        scroll_area_table.setWidgetResizable(True)

        self.table_widget = QtWidgets.QTableWidget()
        self.table_widget.cellChanged.connect(self.cell_changed)
        scroll_area_table.setWidget(self.table_widget)

        # Кнопки управления
        self.pen_button = QtWidgets.QPushButton('', self)
        self.pen_button.setGeometry(1700, 110, 50, 50)
        self.pen_button.setIcon(QtGui.QIcon('image/pen.png'))
        self.pen_button.setIconSize(QtCore.QSize(60, 30))
        self.pen_button.clicked.connect(self.toggle_editing)

        self.password_button = QtWidgets.QPushButton('', self)
        self.password_button.setGeometry(1640, 110, 50, 50)
        self.password_button.setIcon(QtGui.QIcon('image/key.png'))
        self.password_button.setIconSize(QtCore.QSize(60, 30))
        self.password_button.clicked.connect(self.open_password_window)

        self.save_button = QtWidgets.QPushButton('', self)
        self.save_button.setGeometry(1580, 110, 50, 50)
        self.save_button.setIcon(QtGui.QIcon('image/save.png'))
        self.save_button.setIconSize(QtCore.QSize(60, 30))
        self.save_button.clicked.connect(self.save_table_data)

    def toggle_editing(self):
        if self.current_view is None:
            QtWidgets.QMessageBox.information(self, "Ошибка", "Сначала выберите таблицу.")
            return

        if self.current_view == 'all':
            QtWidgets.QMessageBox.information(self, "Информация", "Редактирование в режиме всех записей запрещено.")
            return

        if self.table_widget.editTriggers() == QtWidgets.QAbstractItemView.NoEditTriggers:
            self.table_widget.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
            self.pen_button.setStyleSheet("background-color: gray;")
        else:
            self.table_widget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.pen_button.setStyleSheet("")

    def show_service_table_by_id(self, service_id):
        try:
            self.current_service_id = service_id
            self.current_view = 'service'

            cur = self.conn.cursor()
            cur.execute("""
                SELECT name, login, password, email, date_added 
                FROM all_records 
                WHERE service_id = %s
                ORDER BY id
            """, (service_id,))
            rows = cur.fetchall()

            t = self.lang_manager.translations.get('columns', {})
            headers = [
                t.get('name', 'Name'),
                t.get('login', 'Login'),
                t.get('password', 'Password'),
                t.get('email', 'Email'),
                t.get('date_added', 'Date Added')
            ]
            self.table_widget.setColumnCount(len(headers))
            self.table_widget.setHorizontalHeaderLabels(headers)
            self.table_widget.setRowCount(len(rows) + 1)

            for row_idx, row in enumerate(rows):
                for col_idx, value in enumerate(row):
                    self.table_widget.setItem(row_idx, col_idx, QtWidgets.QTableWidgetItem(str(value)))

            for col_idx in range(len(headers)):
                self.table_widget.setItem(len(rows), col_idx, QtWidgets.QTableWidgetItem(""))

            self.table_widget.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки: {str(e)}")
        finally:
            cur.close() if 'cur' in locals() else None

    def open_password_window(self):
        from generate import PasswordWindow
        """Открывает окно генерации пароля."""

        self.password_window = PasswordWindow()
        self.password_window.show()

    def change_table(self):
        sender = self.sender()
        if sender.property('is_all_records'):  # Проверяем свойство вместо текста
            self.current_view = 'all'
            self.pen_button.setEnabled(False)
            self.table_widget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.load_all_records()
        else:
            self.current_view = 'service'
            self.pen_button.setEnabled(True)
            service_id = self.get_service_id(sender)
            self.show_service_table_by_id(service_id)

    def update_record(self, service_id, row, data):
        """Обновляет запись в базе данных."""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE all_records SET login=%s, password=%s, email=%s, date_added=%s
            WHERE service_id=%s AND id=%s;
        """, (data['login'], data['password'], data['email'], data['date_added'], service_id, row + 1))
        self.conn.commit()
        cur.close()

    def delete_record(self, service_id, row_id):
        """Удаляет запись из базы данных."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM all_records WHERE service_id=%s AND id=%s;", (service_id, row_id))
        self.conn.commit()
        cur.close()

    def load_records(self, service_id):
        """Загружает записи из базы данных и отображает их в таблице."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM all_records WHERE service_id=%s;", (service_id,))
        rows = cur.fetchall()
        self.table_widget.setRowCount(len(rows))

        for i in range(len(rows)):
            for j in range(len(rows[i])):
                item = QtWidgets.QTableWidgetItem(str(rows[i][j]))
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.table_widget.setItem(i, j, item)

        cur.close()

    def save_table_data(self, row):
        t = self.lang_manager.translations
        try:
            if self.current_view != 'service' or not self.current_service_id:
                QtWidgets.QMessageBox.warning(self, t['messages']['required_fields'], f"{t['messages']['required_fields']} {row + 1}")
                return

            cur = self.conn.cursor()
            headers = ["Название", "Логин", "Пароль", "Почта", "Дата добавления"]

            for row in range(self.table_widget.rowCount()):
                # Сбор данных
                data = {
                    'name': self.table_widget.item(row, 0).text().strip() if self.table_widget.item(row, 0) else "",
                    'login': self.table_widget.item(row, 1).text().strip() if self.table_widget.item(row, 1) else "",
                    'password': self.table_widget.item(row, 2).text().strip() if self.table_widget.item(row, 2) else "",
                    'email': self.table_widget.item(row, 3).text().strip() if self.table_widget.item(row, 3) else "",
                    'date_added': self.table_widget.item(row, 4).text() if self.table_widget.item(row, 4) else ""
                }

                # Пропуск пустых строк
                if not data['name'] and not data['login'] and not data['password']:
                    continue

                # Проверка обязательных полей
                if not data['name'] or not data['login'] or not data['password']:
                    QtWidgets.QMessageBox.warning(self, "Ошибка", f"Заполните обязательные поля в строке {row + 1}")
                    continue

                # Проверка email
                if data['email'] and '@' not in data['email']:
                    QtWidgets.QMessageBox.warning(self, t['messages']['invalid_email'], f"{t['messages']['invalid_email']} {row + 1}")
                    continue

                # Обновление или добавление записи
                if data['date_added']:  # Если есть дата - обновляем
                    cur.execute("""
                        UPDATE all_records SET
                        name = %s,
                        login = %s,
                        password = %s,
                        email = %s
                        WHERE service_id = %s
                        AND date_added = %s
                    """, (data['name'], data['login'], data['password'], data['email'],
                          self.current_service_id, data['date_added']))
                else:  # Новая запись
                    cur.execute("""
                        INSERT INTO all_records 
                        (service_id, name, login, password, email, date_added)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_DATE)
                        RETURNING date_added
                    """, (self.current_service_id, data['name'], data['login'],
                          data['password'], data['email']))

                    # Обновляем дату в таблице
                    new_date = cur.fetchone()[0]
                    date_item = QtWidgets.QTableWidgetItem(new_date.strftime("%Y-%m-%d"))
                    self.table_widget.setItem(row, 4, date_item)

            self.conn.commit()
            QtWidgets.QMessageBox.information(self, t['messages']['save_success'], t['messages']['save_success'])

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {str(e)}")
            self.conn.rollback()
        finally:
            cur.close() if 'cur' in locals() else None

    def validate_data(self, data):
        """Проверяет обязательные поля и формат email."""
        if not data['name'] or not data['login'] or not data['password']:
            return False
        if '@' not in data['email']:
            return False
        return True

    def get_service_id(self, button):
        """Получает ID сервиса по кнопке."""
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM services WHERE service_name=%s;", (button.text(),))
        result = cur.fetchone()
        cur.close()
        return result[0] if result else None

    def get_service_name(self, service_id):
        """Получает название сервиса по его ID."""
        cur = self.conn.cursor()
        cur.execute("SELECT service_name FROM services WHERE id=%s;", (service_id,))
        result = cur.fetchone()
        cur.close()
        return result[0] if result else None

    def add_service_button(self):
        """Обработчик кнопки добавления сервиса."""
        t = self.lang_manager.translations
        new_name, ok = QtWidgets.QInputDialog.getText(
            self,
            t.get('add_service', 'Add Service'),
            t.get('service_name', 'Service Name') + ':',
            QtWidgets.QLineEdit.Normal,
            ''
        )

        if not ok or not new_name.strip():
            return

        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT id FROM services WHERE service_name = %s", (new_name,))
            if cur.fetchone():
                QtWidgets.QMessageBox.warning(self, "Ошибка", "Сервис уже существует!")
                return

            # Добавляем новый сервис
            cur.execute(
                "INSERT INTO services (service_name, table_id) VALUES (%s, %s) RETURNING id;",
                (new_name, f"service_{int(datetime.datetime.now().timestamp())}")
            )
            service_id = cur.fetchone()[0]
            self.conn.commit()

            # Создаем новую кнопку (ИСПРАВЛЕННАЯ ЧАСТЬ)
            button = QtWidgets.QPushButton(new_name, self)
            button.setStyleSheet(
                "background-color: white; border-radius: 20px; padding: 10px; font-size: 20px; text-align: center;"
            )
            button.clicked.connect(lambda: self.show_service_table_by_id(service_id))
            # Исправленный обработчик двойного клика
            button.mouseDoubleClickEvent = lambda event, btn=button: self.rename_service(btn, event)

            self.service_buttons_layout.insertWidget(
                self.service_buttons_layout.count() - 1,
                button
            )

        except psycopg2.Error as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка БД", f"Ошибка: {str(e)}")
            self.conn.rollback()
        finally:
            if cur: cur.close()

    def create_service_table(self, service_name):
        """Создает таблицу для нового сервиса в базе данных."""
        cur = self.conn.cursor()
        table_id = f"service_{len(self.service_buttons_layout) + 1}"
        cur.execute("""
            INSERT INTO services (service_name, table_id)
            VALUES (%s, %s)
            ON CONFLICT (service_name) DO NOTHING;
        """, (service_name, table_id))
        self.conn.commit()
        cur.close()

    def rename_service(self, button, event):
        event.accept()
        t = self.lang_manager.translations
        old_name = button.text()

        new_name, ok = QtWidgets.QInputDialog.getText(
            self,
            t.get('messages', {}).get('rename_dialog_title', 'Rename Service'),
            t.get('messages', {}).get('rename_service', 'Enter new service name:'),
            QtWidgets.QLineEdit.Normal,
            old_name
        )

        if ok and new_name and new_name != old_name:
            try:
                cur = self.conn.cursor()
                cur.execute(
                    "UPDATE services SET service_name = %s WHERE service_name = %s",
                    (new_name, old_name))
                self.conn.commit()
                button.setText(new_name)
            except psycopg2.Error as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    t.get('messages', {}).get('error', 'Error'),
                    f"{t.get('messages', {}).get('rename_error', 'Error renaming service')}:\n{str(e)}"
                )
                self.conn.rollback()
            finally:
                cur.close() if 'cur' in locals() else None

    def load_all_records(self):
        try:
            t = self.lang_manager.translations.get('columns', {})
            headers = [
                t.get('service', 'Service'),
                t.get('name', 'Name'),
                t.get('login', 'Login'),
                t.get('password', 'Password'),
                t.get('email', 'Email'),
                t.get('date_added', 'Date Added')
            ]
            self.table_widget.setHorizontalHeaderLabels(headers)

            cur = self.conn.cursor()
            cur.execute("""
                SELECT s.service_name, ar.name, ar.login, ar.password, ar.email, ar.date_added 
                FROM all_records ar
                JOIN services s ON ar.service_id = s.id
                ORDER BY ar.id;
            """)
            rows = cur.fetchall()
            self.table_widget.setRowCount(len(rows))

            for row_idx, row in enumerate(rows):
                for col_idx, value in enumerate(row):
                    item = QtWidgets.QTableWidgetItem(str(value))
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                    self.table_widget.setItem(row_idx, col_idx, item)

            self.current_view = 'all'
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки: {str(e)}")
        finally:
            cur.close() if 'cur' in locals() else None


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
