import pytest
from PyQt5 import QtWidgets
import psycopg2
from unittest.mock import MagicMock, patch
from inside import LoginWindow, create_table
from generate import connect_DB
import datetime

TEST_DB_CONFIG = {
    'dbname': 'PassKeep',
    'user': 'postgres',
    'password': 'ssn23mzw',
    'host': 'localhost'
}


@pytest.fixture(scope='module')
def test_db_connection():
    """Фикстура подключения с изоляцией тестовой схемы"""
    conn = psycopg2.connect(**TEST_DB_CONFIG)
    conn.autocommit = True
    cursor = conn.cursor()

    cursor.execute("DROP SCHEMA IF EXISTS test_schema CASCADE;")
    cursor.execute("CREATE SCHEMA test_schema;")
    cursor.execute("SET search_path TO test_schema;")

    yield conn

    cursor.execute("DROP SCHEMA test_schema CASCADE;")
    conn.close()


@pytest.fixture
def test_app(test_db_connection, qtbot):
    """Фикстура приложения с моком времени для inside.py"""
    mock_datetime = MagicMock()
    mock_datetime.datetime.now.return_value.timestamp.return_value = 1640995200.0

    with patch('inside.datetime', new=mock_datetime), \
            patch('inside.connect_DB', return_value=test_db_connection), \
            patch('generate.connect_DB', return_value=test_db_connection):
        # Очистка данных
        with test_db_connection.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS services, all_records CASCADE;")
        test_db_connection.commit()

        app = LoginWindow()
        qtbot.addWidget(app)
        yield app

        # Постобработка
        with test_db_connection.cursor() as cur:
            cur.execute("TRUNCATE TABLE services, all_records CASCADE;")
        test_db_connection.commit()


def test_create_tables(test_db_connection):
    """Тест создания таблиц"""
    create_table(test_db_connection)

    with test_db_connection.cursor() as cur:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'test_schema'
            AND table_name IN ('all_records', 'services');
        """)
        tables = {row[0] for row in cur.fetchall()}

    assert tables == {'all_records', 'services'}


def test_add_service(test_app, test_db_connection):
    """Тест добавления сервиса"""
    initial_buttons = test_app.service_buttons_layout.count()

    with patch('PyQt5.QtWidgets.QInputDialog.getText',
               return_value=('Test Service', True)):
        test_app.add_service_button()

    # Проверка интерфейса
    assert test_app.service_buttons_layout.count() == initial_buttons + 1

    # Проверка БД
    with test_db_connection.cursor() as cur:
        cur.execute("SELECT table_id FROM test_schema.services;")
        assert cur.fetchone()[0] == 'service_1640995200'


def test_service_uniqueness(test_app, test_db_connection):
    """Тест уникальности сервисов"""
    with patch('PyQt5.QtWidgets.QInputDialog.getText',
               return_value=('My Service', True)):
        test_app.add_service_button()

    with patch('PyQt5.QtWidgets.QInputDialog.getText',
               return_value=('My Service', True)), \
            patch('PyQt5.QtWidgets.QMessageBox.warning') as mock_warning:
        test_app.add_service_button()
        mock_warning.assert_called_once()

    with test_db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM test_schema.services;")
        assert cur.fetchone()[0] == 1

