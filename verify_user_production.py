"""
Script para verificar usuarios manualmente en producción
Ejecutar cuando un usuario se registre y no reciba el email
"""

from database import get_db, User

def verify_user_by_email(email: str):
    """Verificar usuario manualmente por email"""
    with get_db() as db:
        user = db.query(User).filter_by(email=email).first()
        
        if not user:
            print(f"❌ Usuario {email} no encontrado")
            return False
        
        if user.email_verified:
            print(f"✅ Usuario {email} ya estaba verificado")
            return True
        
        user.email_verified = True
        user.email_verification_token = None
        db.commit()
        
        print(f"✅ Usuario {email} verificado exitosamente")
        return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("❌ Uso: python verify_user_production.py email@usuario.com")
        sys.exit(1)
    
    email = sys.argv[1]
    verify_user_by_email(email)
