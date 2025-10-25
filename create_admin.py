#!/usr/bin/env python3
"""
Script para crear usuario administrador
Uso: python create_admin.py
"""

import uuid
import sys
from datetime import datetime
from database import get_db, User

def create_admin_user():
    """Crea un usuario administrador"""
    
    print("=== CREAR USUARIO ADMINISTRADOR ===\n")
    
    email = input("Email del administrador: ").strip()
    if not email:
        print("Error: Email es requerido")
        sys.exit(1)
    
    password = input("Contraseña: ").strip()
    if not password or len(password) < 6:
        print("Error: Contraseña debe tener al menos 6 caracteres")
        sys.exit(1)
    
    first_name = input("Nombre: ").strip() or "Admin"
    last_name = input("Apellido: ").strip() or "Sistema"
    dni = input("DNI: ").strip() or "00000000"
    phone = input("Teléfono: ").strip() or "+1234567890"
    country = input("País: ").strip() or "USA"
    
    try:
        with get_db() as db:
            # Verificar si el email ya existe
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                print(f"\nError: Ya existe un usuario con el email {email}")
                
                # Preguntar si quiere hacerlo admin
                make_admin = input("¿Desea hacerlo administrador? (s/n): ").strip().lower()
                if make_admin == 's':
                    existing.is_admin = True
                    db.commit()
                    print(f"\n✓ Usuario {email} ahora es administrador")
                return
            
            # Crear nuevo usuario administrador
            admin_user = User(
                id=str(uuid.uuid4()),
                email=email,
                first_name=first_name,
                last_name=last_name,
                dni=dni,
                birth_date=datetime(1990, 1, 1),
                phone=phone,
                country=country,
                email_verified=True,
                is_active=True,
                is_admin=True
            )
            
            admin_user.set_password(password)
            
            db.add(admin_user)
            db.commit()
            
            print(f"\n✓ Usuario administrador creado exitosamente")
            print(f"  Email: {email}")
            print(f"  ID: {admin_user.id}")
            print(f"  Nombre: {first_name} {last_name}")
            print(f"\nPuedes acceder al panel administrativo en: /admin")
            
    except Exception as e:
        print(f"\nError al crear administrador: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_admin_user()
