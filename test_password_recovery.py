#!/usr/bin/env python3
"""
Script de Verificación: Sistema de Recuperación de Contraseña
Prueba el flujo completo end-to-end
"""

import requests
import json
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:5000"
TEST_EMAIL = "admin@stc.com"  # Usuario admin para prueba

def test_password_recovery_flow():
    """Prueba el flujo completo de recuperación de contraseña"""
    
    print("🔐 TESTING: Sistema de Recuperación de Contraseña")
    print("=" * 60)
    
    # PASO 1: Solicitar reset de contraseña
    print("\n1️⃣ SOLICITANDO RESET DE CONTRASEÑA...")
    response = requests.post(
        f"{BASE_URL}/api/auth/request-password-reset",
        json={"email": TEST_EMAIL},
        headers={"Content-Type": "application/json"}
    )
    
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    if response.status_code == 200:
        print("   ✅ Email de recuperación enviado correctamente")
    else:
        print(f"   ❌ Error: {response.json().get('error')}")
        return False
    
    # PASO 2: Ver tabla de tokens (solo para verificación)
    print("\n2️⃣ VERIFICANDO TOKENS EN BD...")
    from database import get_db, PasswordReset
    from sqlalchemy import desc
    
    with get_db() as db:
        tokens = db.query(PasswordReset).order_by(desc(PasswordReset.created_at)).limit(3).all()
        
        if tokens:
            print(f"   ✅ {len(tokens)} tokens encontrados en BD")
            latest = tokens[0]
            print(f"   Token más reciente:")
            print(f"     - ID: {latest.id}")
            print(f"     - Token: {latest.token[:10]}...")
            print(f"     - Expira: {latest.expires_at}")
            print(f"     - Usado: {latest.used}")
            
            # Simular que el usuario hizo click en el email
            reset_token = latest.token
            
            # PASO 3: Reset de contraseña con el token
            print("\n3️⃣ RESETEANDO CONTRASEÑA...")
            response = requests.post(
                f"{BASE_URL}/api/auth/reset-password",
                json={
                    "token": reset_token,
                    "new_password": "nueva_password_123"
                },
                headers={"Content-Type": "application/json"}
            )
            
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            
            if response.status_code == 200:
                print("   ✅ Contraseña reseteada exitosamente")
                
                # PASO 4: Verificar que el token se marcó como usado
                print("\n4️⃣ VERIFICANDO TOKEN USADO...")
                db.refresh(latest)
                
                if latest.used:
                    print("   ✅ Token marcado como usado correctamente")
                else:
                    print("   ❌ Token NO se marcó como usado")
                    return False
                
                # PASO 5: Intentar usar el mismo token de nuevo (debe fallar)
                print("\n5️⃣ PROBANDO REUTILIZACIÓN DE TOKEN (debe fallar)...")
                response = requests.post(
                    f"{BASE_URL}/api/auth/reset-password",
                    json={
                        "token": reset_token,
                        "new_password": "otra_password"
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 400:
                    print("   ✅ Token rechazado correctamente (seguridad OK)")
                else:
                    print(f"   ❌ Token debería rechazarse pero status: {response.status_code}")
                    return False
                
                print("\n" + "=" * 60)
                print("✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
                print("=" * 60)
                return True
            else:
                print(f"   ❌ Error reseteando: {response.json().get('error')}")
                return False
        else:
            print("   ❌ No se encontraron tokens en BD")
            return False

if __name__ == "__main__":
    try:
        success = test_password_recovery_flow()
        
        if success:
            print("\n🎉 SISTEMA DE RECUPERACIÓN DE CONTRASEÑA: 100% FUNCIONAL")
        else:
            print("\n❌ Algunas pruebas fallaron")
    except Exception as e:
        print(f"\n❌ Error ejecutando pruebas: {e}")
        import traceback
        traceback.print_exc()
