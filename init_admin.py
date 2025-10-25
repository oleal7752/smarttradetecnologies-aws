#!/usr/bin/env python3
"""
Script de inicialización: Crea usuario admin si no existe
Se ejecuta automáticamente al iniciar el sistema
"""
from werkzeug.security import generate_password_hash
from database import get_db, User, init_db
import uuid
from datetime import datetime, timedelta

def create_admin_if_not_exists():
    """Crea usuario admin si no existe"""
    try:
        print("🔧 Inicializando base de datos...")
        init_db()
        print("✅ Tablas creadas correctamente")
        
        with get_db() as db:
            # Verificar si ya existe admin@stc.com
            admin = db.query(User).filter_by(email="admin@stc.com").first()
            
            if admin:
                # Asegurar que tiene permisos de admin
                admin.password_hash = generate_password_hash("admin123")
                admin.email_verified = True
                admin.is_admin = True
                admin.is_active = True
                db.commit()
                print("✅ Admin admin@stc.com actualizado")
            else:
                # Crear nuevo admin
                new_admin = User(
                    id=str(uuid.uuid4()),
                    email="admin@stc.com",
                    password_hash=generate_password_hash("admin123"),
                    first_name="Super",
                    last_name="Admin",
                    dni="99999999",
                    birth_date=(datetime.now() - timedelta(days=365*30)).date(),
                    phone="+999999999",
                    country="System"
                )
                new_admin.email_verified = True
                new_admin.is_admin = True
                new_admin.is_active = True
                db.add(new_admin)
                db.commit()
                print("✅ Admin admin@stc.com creado exitosamente")
            
            print("📧 Email: admin@stc.com")
            print("🔐 Password: admin123")
            
    except Exception as e:
        print(f"❌ Error creando admin: {e}")

if __name__ == "__main__":
    create_admin_if_not_exists()
