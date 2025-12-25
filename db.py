import mysql.connector, os

def get_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASS', 'Yash@2005'),
        database=os.getenv('DB_NAME', 'hospital_database'),
        port=int(os.getenv('DB_PORT', 3306))
    )