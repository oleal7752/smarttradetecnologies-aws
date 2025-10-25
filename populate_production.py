"""
Script para poblar la base de datos de PRODUCCIÓN
Ejecutar UNA SOLA VEZ en producción
"""

import os
import sys
from datetime import datetime, timedelta
from database import get_db, User, Bot

def populate_production_db():
    """Crea datos esenciales en la BD de producción"""
    
    print("🚀 POBLANDO BASE DE DATOS DE PRODUCCIÓN")
    print("=" * 60)
    
    with get_db() as db:
        # 1. CREAR ADMIN
        print("\n1️⃣ Verificando usuario admin...")
        admin = db.query(User).filter_by(email='admin@stc.com').first()
        
        if not admin:
            print("   ➕ Creando admin...")
            admin = User(
                id='admin-uuid-12345',
                email='admin@stc.com',
                first_name='Admin',
                last_name='STC',
                dni='00000000',
                birth_date=datetime(1990, 1, 1),
                phone='+0000000000',
                country='Global',
                is_admin=True,
                is_active=True,
                email_verified=True,
                created_at=datetime.utcnow()
            )
            admin.set_password('admin123')
            db.add(admin)
            print("   ✅ Admin creado: admin@stc.com / admin123")
        else:
            print("   ✅ Admin ya existe")
        
        # 2. CREAR BOTS
        print("\n2️⃣ Verificando bots...")
        existing_bots = db.query(Bot).count()
        
        if existing_bots == 0:
            print("   ➕ Creando 8 bots predefinidos...")
            
            bots_config = [
                {
                    'name': 'RSI EURUSD M5',
                    'strategy': 'RSI Oversold/Overbought',
                    'symbol': 'EURUSD',
                    'timeframe': 'M5',
                    'amount': 10.0
                },
                {
                    'name': 'MACD EURUSD M15',
                    'strategy': 'MACD Crossover',
                    'symbol': 'EURUSD',
                    'timeframe': 'M15',
                    'amount': 10.0
                },
                {
                    'name': 'Bollinger BTCUSD M5',
                    'strategy': 'Bollinger Bands Bounce',
                    'symbol': 'BTCUSD',
                    'timeframe': 'M5',
                    'amount': 10.0
                },
                {
                    'name': 'Probability EURUSD M5',
                    'strategy': 'Probability + Gale System',
                    'symbol': 'EURUSD',
                    'timeframe': 'M5',
                    'amount': 10.0
                },
                {
                    'name': 'Kolmogorov-Markov M15',
                    'strategy': 'Kolmogorov-Markov Chain',
                    'symbol': 'EURUSD',
                    'timeframe': 'M15',
                    'amount': 10.0
                },
                {
                    'name': 'Complexity EURUSD M5',
                    'strategy': 'Kolmogorov Complexity',
                    'symbol': 'EURUSD',
                    'timeframe': 'M5',
                    'amount': 10.0
                },
                {
                    'name': 'STC Academy Pro',
                    'strategy': 'SmartTradeAcademy1',
                    'symbol': 'EURUSD',
                    'timeframe': 'M5',
                    'amount': 10.0
                },
                {
                    'name': 'Tablero Binarias M5',
                    'strategy': 'Tablero Binarias',
                    'symbol': 'EURUSD',
                    'timeframe': 'M5',
                    'amount': 10.0
                }
            ]
            
            for i, bot_cfg in enumerate(bots_config, 1):
                bot = Bot(
                    id=f'bot-{i:04d}-prod',
                    user_id=admin.id,
                    name=bot_cfg['name'],
                    strategy_name=bot_cfg['strategy'],
                    symbol=bot_cfg['symbol'],
                    timeframe=bot_cfg['timeframe'],
                    trade_amount=bot_cfg['amount'],
                    trade_duration=5,
                    active=False,
                    use_dual_gale=True,
                    max_daily_loss=100.0,
                    max_daily_trades=50,
                    created_at=datetime.utcnow()
                )
                db.add(bot)
                print(f"   ✅ Bot {i}/8: {bot_cfg['name']}")
        else:
            print(f"   ✅ Ya existen {existing_bots} bots")
        
        # COMMIT
        db.commit()
        print("\n" + "=" * 60)
        print("✅ BASE DE DATOS DE PRODUCCIÓN POBLADA EXITOSAMENTE")
        print("=" * 60)
        print("\n📧 Credenciales Admin:")
        print("   Email: admin@stc.com")
        print("   Password: admin123")
        print("\n🤖 Bots creados: 8")
        print("\n🌐 URL Producción: https://smart-trade-academy-ia.replit.app")
        print("=" * 60)


if __name__ == "__main__":
    try:
        populate_production_db()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)
