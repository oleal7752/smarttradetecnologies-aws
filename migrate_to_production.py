#!/usr/bin/env python3
"""
Script de Migración Profesional: Desarrollo → Producción
Exporta datos esenciales de desarrollo para importar en producción
"""
import json
from database import get_db, User, Bot, PromoCode
from datetime import datetime

def export_essential_data():
    """Exporta usuarios, bots y códigos promocionales esenciales"""
    export_data = {
        'users': [],
        'bots': [],
        'promo_codes': [],
        'export_date': datetime.utcnow().isoformat()
    }
    
    with get_db() as db:
        # Exportar usuarios esenciales (admin y usuarios reales, no de prueba)
        users = db.query(User).filter(
            User.email.in_(['admin@stc.com', 'oleal77752@gmail.com', 'raikerleal33@gmail.com'])
        ).all()
        
        for user in users:
            export_data['users'].append({
                'id': user.id,
                'email': user.email,
                'password_hash': user.password_hash,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'dni': user.dni,
                'birth_date': user.birth_date.isoformat() if user.birth_date else None,
                'phone': user.phone,
                'country': user.country,
                'email_verified': user.email_verified,
                'is_active': user.is_active,
                'is_admin': user.is_admin
            })
        
        # Exportar bots configurados
        bots = db.query(Bot).all()
        for bot in bots:
            export_data['bots'].append({
                'id': bot.id,
                'user_id': bot.user_id,
                'name': bot.name,
                'strategy_name': bot.strategy_name,
                'symbol': bot.symbol,
                'timeframe': bot.timeframe,
                'trade_amount': bot.trade_amount,
                'trade_duration': bot.trade_duration,
                'active': bot.active,
                'auto_restart': bot.auto_restart,
                'use_dual_gale': bot.use_dual_gale,
                'gale_level': bot.gale_level,
                'max_daily_loss': bot.max_daily_loss,
                'max_daily_trades': bot.max_daily_trades
            })
        
        # Exportar códigos promocionales activos
        promo_codes = db.query(PromoCode).filter(PromoCode.is_active == True).all()
        for code in promo_codes:
            export_data['promo_codes'].append({
                'id': code.id,
                'code': code.code,
                'type': code.type,
                'duration_hours': code.duration_hours,
                'is_active': code.is_active,
                'created_by': code.created_by,
                'assigned_to': code.assigned_to,
                'is_used': code.is_used,
                'expires_at': code.expires_at.isoformat() if code.expires_at else None,
                'activated_at': code.activated_at.isoformat() if code.activated_at else None
            })
    
    # Guardar a archivo
    with open('production_migration_data.json', 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print("✅ Datos exportados exitosamente")
    print(f"📊 {len(export_data['users'])} usuarios")
    print(f"🤖 {len(export_data['bots'])} bots")
    print(f"🎟️  {len(export_data['promo_codes'])} códigos promocionales")
    print(f"💾 Archivo: production_migration_data.json")
    
    return export_data

if __name__ == "__main__":
    export_essential_data()
