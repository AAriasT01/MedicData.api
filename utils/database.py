from dotenv import load_dotenv
import os
import pyodbc
import logging
import json

load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

"""
driver = os.getenv('SQL_DRIVER')
server = os.getenv('SQL_SERVER')
database = os.getenv('SQL_DATABASE')
username = os.getenv('SQL_USERNAME')
password = os.getenv('SQL_PASSWORD')
"""
#connection_string = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}"
#connection_string = f"DRIVER={{{driver}}};SERVER={server}.database.windows.net;DATABASE={database};UID={username};PWD={password}"
#connection_string = f"DRIVER={driver} ;SERVER={server};DATABASE={database};UID={username};PWD={password}"
#connection_string = f"Driver={ODBC Driver 18 for SQL Server};Server=tcp:sqlserver-medicdata-dev.database.windows.net,1433;Database=medicdata.db;Uid=sqladmin;Pwd={your_password_here};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30"


# Obtener los valores de las variables de entorno
server = os.getenv('DB_SERVER')
port = os.getenv('DB_PORT')
database = os.getenv('DB_NAME')
user = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')
encrypt = os.getenv('DB_ENCRYPT')
trust_server_certificate = os.getenv('DB_TRUST_SERVER_CERTIFICATE')
connection_timeout = os.getenv('DB_CONNECTION_TIMEOUT')

# Construir la cadena de conexión
connection_string = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER=tcp:{server},{port};"
    f"DATABASE={database};"
    f"Uid={user};"
    f"Pwd={password};"
    f"Encrypt={encrypt};"
    f"TrustServerCertificate={trust_server_certificate};"
    f"Connection Timeout={connection_timeout};"
)



async def get_db_connection():
    try:
        logger.info(f"Intentando conectar a la base de datos con la cadena de conexión: {connection_string}")
        conn = pyodbc.connect(connection_string, timeout=10)
        logger.info("Conexión exitosa a la base de datos.")
        return conn
    except pyodbc.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise Exception(f"Database connection error: {str(e)}")

async def fetch_query_as_json(query):
    conn = await get_db_connection()
    cursor = conn.cursor()
    logger.info(f"Ejecutando query: {query}")
    try:
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        results = []
        logger.info(f"Columns: {columns}")
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))

        return json.dumps(results)

    except pyodbc.Error as e:
        raise Exception(f"Error ejecutando el query: {str(e)}")
    finally:
        cursor.close()
        conn.close()