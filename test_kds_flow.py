import sqlite3
import json
from datetime import datetime
import os

def insert_test_order():
    # Intentar detectar la base de datos correcta
    possible_dbs = ["PIKTA_SOFT.db", "PIk'TADB.db", "PIKTA_SOFT_FACT.db"]
    db_path = None
    for db in possible_dbs:
        if os.path.exists(db):
            db_path = db
            break
    
    if not db_path:
        db_path = "PIKTA_SOFT.db" # Default
        
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Crear un pedido de prueba
        items = [
            {"id": 1, "nombre": "Hamburguesa Especial", "precio": 12.50, "qty": 2},
            {"id": 2, "nombre": "Papas Fritas", "precio": 4.00, "qty": 1}
        ]
        
        numero = f"TEST-{datetime.now().strftime('%H%M%S')}"
        canal = "MESERO"
        total = 29.00
        created_at = datetime.now().isoformat()
        
        # Insertar solo las columnas básicas garantizadas
        cur.execute('''
            INSERT INTO pedidos (numero, items, total, estado, canal, created_at, mesa) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (numero, json.dumps(items), total, 'RECIBIDO', canal, created_at, 'Mesa 5'))
        
        conn.commit()
        print(f"Pedido de prueba #{cur.lastrowid} insertado correctamente.")
        print(f"Estado inicial: RECIBIDO. Véalo en el monitor de cocina.")
        conn.close()
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    insert_test_order()
