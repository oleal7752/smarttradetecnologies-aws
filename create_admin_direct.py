#!/usr/bin/env python3
"""
Script para crear usuario administrador directamente
"""

import uuid
import sys
from datetime import datetime
from database import get_db, User

def create_admin(email, password, first_name="Admin", last_name="Sistema"):
    """Crea un usuario administrador"""
    
    try:
        with get_db() as db:
            # Verificar si el email ya existe
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                # Hacerlo admin si ya existe
                existing.is_admin = True
                db.commit()
                print(f"✓ Usuario {email} actualizado a administrador")
                print(f"  ID: {existing.id}")
                return
            
            # Crear nuevo usuario administrador
            admin_user = User(
                id=str(uuid.uuid4()),
                email=email,
                first_name=first_name,
                last_name=last_name,
                dni="00000000",
                birth_date=datetime(1990, 1, 1),
                phone="+1234567890",
                country="USA",
                email_verified=True,
                is_active=True,
                is_admin=True
            )
            
            admin_user.set_password(password)
            
            db.add(admin_user)
            db.commit()
            
            print(f"✓ Usuario administrador creado exitosamente")
            print(f"  Email: {email}")
            print(f"  ID: {admin_user.id}")
            print(f"  Contraseña: {password}")
            print(f"\nPuedes acceder al panel administrativo en: /admin")
            
    except Exception as e:
        print(f"✗ Error al crear administrador: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python create_admin_direct.py <email> <password> [nombre] [apellido]")
        print("\nEjemplo:")
        print("  python create_admin_direct.py admin@stc.com Admin123")
        print("  python create_admin_direct.py juan@example.com Pass123 Juan Pérez")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    first_name = sys.argv[3] if len(sys.argv) > 3 else "Admin"
    last_name = sys.argv[4] if len(sys.argv) > 4 else "Sistema"
    
    create_admin(email, password, first_name, last_name)
