import pytest
import psycopg2
import bcrypt
import json
from unittest.mock import patch, MagicMock, PropertyMock
from PyQt5 import QtWidgets, QtCore
from main import create_table, Main_Window, LoginWindow


# Фикстура для QApplication
@pytest.fixture(scope="session")
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app
    app.quit()


# Фикстура для тестовой базы данных
@pytest.fixture
def test_db():
    conn = psycopg2.connect(
        dbname="PassKeep",
        user="postgres",
        password="ssn23mzw",
        host="localhost",
        port="5432"
    )
    with conn.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS users")
    conn.commit()
    yield conn
    with conn.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS users")
    conn.commit()
    conn.close()


def test_create_table(test_db):
    create_table(test_db)
    with test_db.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            )
        """)
        assert cursor.fetchone()[0] is True


def test_save_user_success(qapp, test_db):
    window = Main_Window()
    result = window.save_user(
        test_db,
        "test_user",
        bcrypt.hashpw(b"test", bcrypt.gensalt()).decode()
    )
    assert result is True


def test_save_user_duplicate(test_db):
    window = Main_Window()
    window.save_user(test_db, "test_user", "hash1")
    result = window.save_user(test_db, "test_user", "hash2")
    assert result is False


def test_handle_create_account_valid(qapp, qtbot, test_db, tmp_path):
    window = Main_Window()
    qtbot.addWidget(window)
    window.conn = test_db

    with patch.object(Main_Window, 'write_user_to_json') as mock_write, \
            patch.object(QtWidgets.QMessageBox, 'information') as mock_info:
        mock_write.return_value = True
        type(window).json_path = PropertyMock(return_value=tmp_path / "users.json")

        qtbot.keyClicks(window.username_input, "new_user")
        qtbot.keyClicks(window.password_input, "password")
        qtbot.mouseClick(window.create_button, QtCore.Qt.LeftButton)

        mock_info.assert_called_once()


def test_handle_login_valid(qapp, qtbot, test_db):
    window = Main_Window()
    qtbot.addWidget(window)
    window.conn = test_db
    hashed = bcrypt.hashpw(b"password", bcrypt.gensalt()).decode()
    window.save_user(test_db, "valid_user", hashed)

    with patch.object(LoginWindow, 'show') as mock_show:
        qtbot.keyClicks(window.username_input, "valid_user")
        qtbot.keyClicks(window.password_input, "password")
        qtbot.mouseClick(window.login_button, QtCore.Qt.LeftButton)
        mock_show.assert_called_once()


def test_toggle_password_visibility(qapp, qtbot):
    window = Main_Window()
    qtbot.addWidget(window)
    initial_mode = window.password_input.echoMode()
    qtbot.mouseClick(window.toggle_password_button, QtCore.Qt.LeftButton)
    assert window.password_input.echoMode() != initial_mode


def test_load_users_from_json(qapp, test_db, tmp_path):
    window = Main_Window()
    test_file = tmp_path / "users.json"

    with open(test_file, 'w') as f:
        user = {"username": "json_user", "password_hash": "hash"}
        json.dump(user, f)
        f.write('\n')

    window.load_users_from_json(test_db, test_file)

    with test_db.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE username = 'json_user'")
        assert cursor.fetchone() is not None


def test_language_change(qapp, qtbot):
    window = Main_Window()
    qtbot.addWidget(window)
    window.change_language('en')
    assert window.lang_manager.current_lang == 'en'
    assert "Login" in window.login_button.text()


def test_database_error_handling(qapp):
    window = Main_Window()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.execute.side_effect = psycopg2.Error("DB error")

    result = window.save_user(mock_conn, "user", "hash")
    assert result is False
    mock_conn.rollback.assert_called_once()