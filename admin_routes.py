import uuid
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session, render_template
from database import (
    get_db, PromoCode, User, PromoCodeType, 
    Subscription, SubscriptionPlan, SubscriptionStatus,
    Bot, Payment, BacktestMasterRun, BacktestMasterSignal
)
from auth_routes import admin_required, login_required
from strategy_engine import StrategyEngine
import subprocess
import threading
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

admin_bp = Blueprint('admin', __name__)

# Inicializar strategy engine para consultar estrategias
strategy_engine = StrategyEngine()


@admin_bp.route('/api/admin/promo/create', methods=['POST'])
@admin_required
def create_promo_code():
    """Crear código promocional (solo admin)"""
    try:
        data = request.json
        
        required_fields = ['type', 'duration_hours']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Campo {field} es requerido'}), 400
        
        promo_type = data['type']
        duration_hours = int(data['duration_hours'])
        
        if promo_type not in ['revendedor', 'agente', 'cortesia']:
            return jsonify({'success': False, 'error': 'Tipo inválido'}), 400
        
        if duration_hours <= 0:
            return jsonify({'success': False, 'error': 'Duración debe ser positiva'}), 400
        
        code = secrets.token_urlsafe(8).upper()
        
        with get_db() as db:
            promo_code = PromoCode(
                id=str(uuid.uuid4()),
                code=code,
                type=PromoCodeType(promo_type),
                duration_hours=duration_hours,
                created_by=session['user_id'],
                is_active=True,
                is_used=False
            )
            
            db.add(promo_code)
            db.commit()
            
            return jsonify({
                'success': True,
                'promo_code': {
                    'id': promo_code.id,
                    'code': promo_code.code,
                    'type': promo_code.type.value,
                    'duration_hours': promo_code.duration_hours,
                    'created_at': promo_code.created_at.isoformat(),
                    'is_active': promo_code.is_active
                }
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/promo/send-email', methods=['POST'])
@admin_required
def send_promo_email():
    """Enviar código promocional por correo electrónico"""
    try:
        data = request.json
        
        required_fields = ['code', 'email', 'type', 'duration_hours']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Campo {field} es requerido'}), 400
        
        code = data['code']
        recipient_email = data['email']
        promo_type = data['type']
        
        try:
            duration_hours = int(data['duration_hours'])
            if duration_hours <= 0:
                return jsonify({'success': False, 'error': 'Duración debe ser positiva'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Duración inválida'}), 400
        
        gmail_user = os.getenv('GMAIL_USER')
        gmail_password = os.getenv('GMAIL_APP_PASSWORD')
        
        if not gmail_user or not gmail_password:
            return jsonify({'success': False, 'error': 'Configuración de email no disponible'}), 500
        
        type_names = {
            'revendedor': 'Revendedor',
            'agente': 'Agente',
            'cortesia': 'Cortesía'
        }
        
        duration_days = duration_hours // 24
        duration_text = f"{duration_days} {'día' if duration_days == 1 else 'días'}" if duration_hours >= 24 else f"{duration_hours} {'hora' if duration_hours == 1 else 'horas'}"
        
        html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #ffffff;
            margin: 0;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: rgba(26, 31, 58, 0.95);
            border-radius: 20px;
            padding: 40px;
            border: 1px solid rgba(0, 245, 255, 0.3);
            box-shadow: 0 8px 32px rgba(0, 245, 255, 0.15);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .logo {{
            font-size: 48px;
            margin-bottom: 10px;
        }}
        .title {{
            font-size: 28px;
            font-weight: bold;
            background: linear-gradient(135deg, #00f5ff 0%, #0066cc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: #b0b8c1;
            font-size: 16px;
        }}
        .code-box {{
            background: rgba(0, 245, 255, 0.05);
            border: 2px solid #00f5ff;
            border-radius: 15px;
            padding: 30px;
            text-align: center;
            margin: 30px 0;
            box-shadow: 0 0 30px rgba(0, 245, 255, 0.3), inset 0 0 20px rgba(0, 245, 255, 0.1);
        }}
        .code {{
            font-size: 36px;
            font-weight: bold;
            letter-spacing: 8px;
            color: #00f5ff;
            font-family: 'Courier New', monospace;
            text-shadow: 0 0 10px rgba(0, 245, 255, 0.5);
        }}
        .info-box {{
            background: rgba(255, 255, 255, 0.02);
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid #00f5ff;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        .info-row:last-child {{
            border-bottom: none;
        }}
        .info-label {{
            color: #b0b8c1;
            font-size: 14px;
        }}
        .info-value {{
            color: #00f5ff;
            font-weight: bold;
        }}
        .instructions {{
            background: rgba(0, 102, 204, 0.1);
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
        }}
        .instructions h3 {{
            color: #00f5ff;
            margin-top: 0;
            font-size: 18px;
        }}
        .instructions ol {{
            margin: 15px 0;
            padding-left: 20px;
        }}
        .instructions li {{
            margin: 10px 0;
            color: #b0b8c1;
            line-height: 1.6;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: #6c757d;
            font-size: 14px;
        }}
        .cta-button {{
            display: inline-block;
            background: linear-gradient(135deg, #00f5ff 0%, #0066cc 100%);
            color: #000;
            text-decoration: none;
            padding: 15px 40px;
            border-radius: 10px;
            font-weight: bold;
            font-size: 16px;
            margin: 20px 0;
            box-shadow: 0 4px 15px rgba(0, 245, 255, 0.4);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">📊</div>
            <div class="title">STC Trading System</div>
            <div class="subtitle">Smart Trade Academy</div>
        </div>
        
        <p style="font-size: 18px; margin-bottom: 20px;">¡Bienvenido a STC Trading System!</p>
        
        <p style="color: #b0b8c1; line-height: 1.6;">
            Te enviamos tu código de acceso exclusivo para que puedas acceder a nuestra plataforma de trading profesional con señales en tiempo real, bots automatizados y análisis avanzado.
        </p>
        
        <div class="code-box">
            <div style="color: #b0b8c1; font-size: 14px; margin-bottom: 10px;">TU CÓDIGO DE ACCESO</div>
            <div class="code">{code}</div>
        </div>
        
        <div class="info-box">
            <div class="info-row">
                <span class="info-label">Tipo de Acceso:</span>
                <span class="info-value">{type_names.get(promo_type, promo_type)}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Duración:</span>
                <span class="info-value">{duration_text}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Estado:</span>
                <span class="info-value">Activo y Listo para Usar</span>
            </div>
        </div>
        
        <div class="instructions">
            <h3>📋 Cómo Activar tu Código:</h3>
            <ol>
                <li>Ingresa a la plataforma STC Trading System</li>
                <li>En la pantalla de acceso, introduce tu código</li>
                <li>El sistema validará y activará tu acceso inmediatamente</li>
                <li>¡Comienza a operar con señales profesionales!</li>
            </ol>
        </div>
        
        <div style="text-align: center;">
            <a href="#" class="cta-button">ACCEDER A LA PLATAFORMA</a>
        </div>
        
        <div style="background: rgba(255, 193, 7, 0.1); border-radius: 10px; padding: 15px; margin: 20px 0; border-left: 4px solid #ffc107;">
            <strong style="color: #ffc107;">⚠️ Importante:</strong>
            <p style="color: #b0b8c1; margin: 10px 0 0 0;">
                Guarda este código en un lugar seguro. El tiempo comienza a contar desde el momento de la activación.
            </p>
        </div>
        
        <div class="footer">
            <p>Este es un mensaje automático generado por STC Trading System.</p>
            <p style="margin-top: 10px;">Si tienes alguna pregunta, contacta a tu asesor.</p>
            <p style="margin-top: 20px; color: #00f5ff;">© 2025 Smart Trade Academy • STC Trading System</p>
        </div>
    </div>
</body>
</html>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'🎯 Tu Código de Acceso a STC Trading System - {code}'
        msg['From'] = f'STC Trading System <{gmail_user}>'
        msg['To'] = recipient_email
        
        plain_text = f"""
¡Bienvenido a STC Trading System!

Tu Código de Acceso: {code}

Tipo de Acceso: {type_names.get(promo_type, promo_type)}
Duración: {duration_text}
Estado: Activo y Listo para Usar

Instrucciones:
1. Ingresa a la plataforma STC Trading System
2. En la pantalla de acceso, introduce tu código
3. El sistema validará y activará tu acceso inmediatamente
4. ¡Comienza a operar con señales profesionales!

Importante: Guarda este código en un lugar seguro. El tiempo comienza a contar desde el momento de la activación.

© 2025 Smart Trade Academy • STC Trading System
        """
        
        text_part = MIMEText(plain_text, 'plain')
        html_part = MIMEText(html_content, 'html')
        msg.attach(text_part)
        msg.attach(html_part)
        
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()
        
        return jsonify({
            'success': True, 
            'message': f'Código enviado exitosamente a {recipient_email}'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error al enviar email: {str(e)}'}), 500


@admin_bp.route('/api/admin/promo/list', methods=['GET'])
@admin_required
def list_promo_codes():
    """Listar códigos promocionales (solo admin)"""
    try:
        with get_db() as db:
            promo_codes = db.query(PromoCode).order_by(PromoCode.created_at.desc()).all()
            
            codes_list = []
            for pc in promo_codes:
                user_email = None
                if pc.assigned_to:
                    user = db.query(User).filter_by(id=pc.assigned_to).first()
                    if user:
                        user_email = user.email
                
                codes_list.append({
                    'id': pc.id,
                    'code': pc.code,
                    'type': pc.type.value,
                    'duration_hours': pc.duration_hours,
                    'created_at': pc.created_at.isoformat(),
                    'activated_at': pc.activated_at.isoformat() if pc.activated_at else None,
                    'expires_at': pc.expires_at.isoformat() if pc.expires_at else None,
                    'assigned_to': user_email,
                    'is_active': pc.is_active,
                    'is_used': pc.is_used
                })
            
            return jsonify({'success': True, 'promo_codes': codes_list})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/promo/delete/<promo_id>', methods=['DELETE'])
@admin_required
def delete_promo_code(promo_id):
    """Eliminar código promocional (solo admin)"""
    try:
        with get_db() as db:
            promo_code = db.query(PromoCode).filter_by(id=promo_id).first()
            
            if not promo_code:
                return jsonify({'success': False, 'error': 'Código no encontrado'}), 404
            
            db.delete(promo_code)
            db.commit()
            
            return jsonify({'success': True, 'message': 'Código eliminado'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/promo/activate', methods=['POST'])
@login_required
def activate_promo_code():
    """Activar código promocional (usuario autenticado)"""
    try:
        data = request.json
        
        if 'code' not in data:
            return jsonify({'success': False, 'error': 'Código es requerido'}), 400
        
        code = data['code'].upper().strip()
        
        with get_db() as db:
            promo_code = db.query(PromoCode).filter_by(code=code).first()
            
            if not promo_code:
                return jsonify({'success': False, 'error': 'Código inválido'}), 404
            
            if not promo_code.is_active:
                return jsonify({'success': False, 'error': 'Código desactivado'}), 400
            
            if promo_code.is_used:
                return jsonify({'success': False, 'error': 'Código ya utilizado'}), 400
            
            now = datetime.utcnow()
            expires_at = now + timedelta(hours=promo_code.duration_hours)
            
            promo_code.assigned_to = session['user_id']
            promo_code.activated_at = now
            promo_code.expires_at = expires_at
            promo_code.is_used = True
            
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'Código activado exitosamente',
                'promo_code': {
                    'type': promo_code.type.value,
                    'duration_hours': promo_code.duration_hours,
                    'activated_at': promo_code.activated_at.isoformat(),
                    'expires_at': promo_code.expires_at.isoformat()
                }
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/promo/status', methods=['GET'])
@login_required
def get_promo_status():
    """Obtener estado del código promocional del usuario"""
    try:
        with get_db() as db:
            promo_code = db.query(PromoCode).filter_by(
                assigned_to=session['user_id'],
                is_used=True,
                is_active=True
            ).order_by(PromoCode.activated_at.desc()).first()
            
            if not promo_code or not promo_code.expires_at:
                return jsonify({'success': True, 'has_active_promo': False})
            
            now = datetime.utcnow()
            
            if now > promo_code.expires_at:
                return jsonify({'success': True, 'has_active_promo': False, 'expired': True})
            
            time_remaining = (promo_code.expires_at - now).total_seconds()
            
            return jsonify({
                'success': True,
                'has_active_promo': True,
                'promo_code': {
                    'type': promo_code.type.value,
                    'expires_at': promo_code.expires_at.isoformat(),
                    'time_remaining_seconds': int(time_remaining)
                }
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== GESTIÓN DE USUARIOS ====================

@admin_bp.route('/api/admin/users/list', methods=['GET'])
@admin_required
def list_users():
    """Listar todos los usuarios (solo admin)"""
    try:
        with get_db() as db:
            users = db.query(User).order_by(User.created_at.desc()).all()
            
            users_list = []
            for user in users:
                # Obtener suscripción activa
                active_sub = db.query(Subscription).filter_by(
                    user_id=user.id,
                    status=SubscriptionStatus.ACTIVE
                ).order_by(Subscription.end_date.desc()).first()
                
                # Obtener código promocional activo
                active_promo = db.query(PromoCode).filter_by(
                    assigned_to=user.id,
                    is_used=True,
                    is_active=True
                ).order_by(PromoCode.activated_at.desc()).first()
                
                has_promo = False
                if active_promo and active_promo.expires_at:
                    has_promo = datetime.utcnow() < active_promo.expires_at
                
                users_list.append({
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_admin': user.is_admin,
                    'is_active': user.is_active,
                    'email_verified': user.email_verified,
                    'created_at': user.created_at.isoformat(),
                    'last_login': user.last_login.isoformat() if user.last_login else None,
                    'has_subscription': active_sub is not None,
                    'subscription_plan': active_sub.plan.value if active_sub else None,
                    'subscription_expires': active_sub.end_date.isoformat() if active_sub else None,
                    'has_promo': has_promo
                })
            
            return jsonify({'success': True, 'users': users_list})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/users/<user_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    """Activar/desactivar usuario (solo admin)"""
    try:
        with get_db() as db:
            user = db.query(User).filter_by(id=user_id).first()
            
            if not user:
                return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
            
            user.is_active = not user.is_active
            db.commit()
            
            return jsonify({
                'success': True,
                'message': f'Usuario {"activado" if user.is_active else "desactivado"}',
                'is_active': user.is_active
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/users/<user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_user_admin(user_id):
    """Hacer/quitar admin (solo admin)"""
    try:
        with get_db() as db:
            user = db.query(User).filter_by(id=user_id).first()
            
            if not user:
                return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
            
            user.is_admin = not user.is_admin
            db.commit()
            
            return jsonify({
                'success': True,
                'message': f'Usuario {"promovido a admin" if user.is_admin else "quitado de admin"}',
                'is_admin': user.is_admin
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/users/<user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    """Obtener detalles de un usuario (solo admin)"""
    try:
        with get_db() as db:
            user = db.query(User).filter_by(id=user_id).first()
            
            if not user:
                return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'dni': user.dni,
                    'phone': user.phone,
                    'country': user.country,
                    'is_admin': user.is_admin,
                    'is_active': user.is_active,
                    'email_verified': user.email_verified
                }
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/users/<user_id>/edit', methods=['PUT'])
@admin_required
def edit_user(user_id):
    """Editar usuario (solo admin)"""
    try:
        data = request.json
        
        with get_db() as db:
            user = db.query(User).filter_by(id=user_id).first()
            
            if not user:
                return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
            
            # Validar email único si se cambia
            if 'email' in data and data['email'] != user.email:
                existing = db.query(User).filter_by(email=data['email']).first()
                if existing:
                    return jsonify({'success': False, 'error': 'El email ya está en uso'}), 400
            
            # Validar DNI único si se cambia
            if 'dni' in data and data['dni'] != user.dni:
                existing = db.query(User).filter_by(dni=data['dni']).first()
                if existing:
                    return jsonify({'success': False, 'error': 'El DNI ya está registrado'}), 400
            
            # Actualizar campos permitidos
            if 'email' in data:
                user.email = data['email']
            if 'first_name' in data:
                user.first_name = data['first_name']
            if 'last_name' in data:
                user.last_name = data['last_name']
            if 'dni' in data:
                user.dni = data['dni']
            if 'phone' in data:
                user.phone = data['phone']
            if 'country' in data:
                user.country = data['country']
            
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'Usuario actualizado exitosamente'
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/users/<user_id>/delete', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Eliminar usuario (solo admin)"""
    try:
        with get_db() as db:
            # Prevenir que el admin se elimine a sí mismo
            if session.get('user_id') == user_id:
                return jsonify({'success': False, 'error': 'No puedes eliminar tu propia cuenta'}), 400
            
            user = db.query(User).filter_by(id=user_id).first()
            
            if not user:
                return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
            
            # Eliminar relaciones asociadas (cascada manual si es necesario)
            # Los bots, suscripciones, etc. se eliminarán por CASCADE en la BD
            
            db.delete(user)
            db.commit()
            
            return jsonify({
                'success': True,
                'message': f'Usuario {user.email} eliminado exitosamente'
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== GESTIÓN DE PRECIOS ====================

@admin_bp.route('/api/admin/pricing/list', methods=['GET'])
@admin_required
def list_pricing():
    """Listar precios de planes (solo admin)"""
    try:
        plans = []
        for plan in SubscriptionPlan:
            plans.append({
                'plan': plan.value,
                'price': Subscription.get_plan_price(plan),
                'duration_days': Subscription.get_plan_duration_days(plan),
                'duration_label': {
                    SubscriptionPlan.MONTHLY: '1 mes',
                    SubscriptionPlan.QUARTERLY: '3 meses',
                    SubscriptionPlan.BIANNUAL: '6 meses',
                    SubscriptionPlan.ANNUAL: '12 meses'
                }[plan]
            })
        
        return jsonify({'success': True, 'pricing': plans})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/pricing/update', methods=['POST'])
@admin_required
def update_pricing():
    """Actualizar precios (solo admin)"""
    try:
        data = request.json
        
        # Nota: En producción, esto debería modificar una tabla de configuración
        # Por ahora retornamos error ya que los precios están hardcodeados
        
        return jsonify({
            'success': False,
            'error': 'Los precios están definidos en el código. Para cambiarlos, edita database.py'
        }), 501
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== GESTIÓN DE BOTS ====================

@admin_bp.route('/api/admin/bots/list', methods=['GET'])
@admin_required
def list_all_bots():
    """Listar todos los bots del sistema (solo admin)"""
    try:
        with get_db() as db:
            bots = db.query(Bot).order_by(Bot.created_at.desc()).all()
            
            bots_list = []
            for bot in bots:
                user = db.query(User).filter_by(id=bot.user_id).first()
                
                bots_list.append({
                    'id': bot.id,
                    'name': bot.name,
                    'strategy': bot.strategy,
                    'user_email': user.email if user else 'Desconocido',
                    'user_id': bot.user_id,
                    'is_active': bot.is_active,
                    'symbol': bot.symbol,
                    'timeframe': bot.timeframe,
                    'amount': bot.amount,
                    'max_gale': bot.max_gale,
                    'created_at': bot.created_at.isoformat()
                })
            
            return jsonify({'success': True, 'bots': bots_list})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/bots/<bot_id>/toggle', methods=['POST'])
@admin_required
def toggle_bot_admin(bot_id):
    """Activar/desactivar bot (solo admin)"""
    try:
        with get_db() as db:
            bot = db.query(Bot).filter_by(id=bot_id).first()
            
            if not bot:
                return jsonify({'success': False, 'error': 'Bot no encontrado'}), 404
            
            bot.is_active = not bot.is_active
            db.commit()
            
            return jsonify({
                'success': True,
                'message': f'Bot {"activado" if bot.is_active else "desactivado"}',
                'is_active': bot.is_active
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== GESTIÓN DE ESTRATEGIAS ====================

@admin_bp.route('/api/admin/strategies/list', methods=['GET'])
@admin_required
def list_strategies():
    """Listar estrategias disponibles (solo admin)"""
    try:
        strategies = []
        
        # Estrategias disponibles (hardcoded por ahora)
        available_strategies = [
            {
                'name': 'RSI Oversold/Overbought',
                'description': 'Señales basadas en RSI (sobrecompra/sobreventa)',
                'params': {
                    'rsi_period': 14,
                    'oversold': 30,
                    'overbought': 70,
                    'min_confidence': 0.7
                }
            },
            {
                'name': 'MACD Crossover',
                'description': 'Señales basadas en cruces de MACD',
                'params': {
                    'fast_period': 12,
                    'slow_period': 26,
                    'signal_period': 9,
                    'min_confidence': 0.7
                }
            },
            {
                'name': 'Bollinger Bands Bounce',
                'description': 'Señales basadas en rebotes en bandas de Bollinger',
                'params': {
                    'period': 20,
                    'std_dev': 2.0,
                    'touch_threshold': 0.0005,
                    'min_confidence': 0.7
                }
            },
            {
                'name': 'Probability + Gale System',
                'description': 'Análisis de probabilidades con sistema de Martingala',
                'params': {
                    'cantidad_velas': 100,
                    'min_confidence': 0.55,
                    'min_diff_percent': 5.0
                }
            },
            {
                'name': 'Kolmogorov-Markov',
                'description': 'Cadenas de Markov para predicción de tendencias',
                'params': {
                    'sequence_length': 3,
                    'min_samples': 20,
                    'min_confidence': 0.65
                }
            },
            {
                'name': 'Kolmogorov Complexity',
                'description': 'Análisis de complejidad algorítmica',
                'params': {
                    'window_size': 50,
                    'min_complexity_diff': 0.15
                }
            },
            {
                'name': 'SmartTradeAcademy1',
                'description': 'Estrategia propietaria con lógica inversa',
                'params': {
                    'cantidad_velas': 100,
                    'min_confidence': 0.60
                }
            },
            {
                'name': 'Tablero Binarias',
                'description': 'Análisis de probabilidades siguiendo patrón dominante',
                'params': {
                    'cantidad_velas': 100
                }
            }
        ]
        
        return jsonify({'success': True, 'strategies': available_strategies})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== ESTADÍSTICAS ====================

@admin_bp.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    """Obtener estadísticas del sistema (solo admin)"""
    try:
        with get_db() as db:
            total_users = db.query(User).count()
            active_users = db.query(User).filter_by(is_active=True).count()
            admin_users = db.query(User).filter_by(is_admin=True).count()
            
            total_subs = db.query(Subscription).filter_by(status=SubscriptionStatus.ACTIVE).count()
            total_bots = db.query(Bot).count()
            active_bots = db.query(Bot).filter_by(is_active=True).count()
            
            total_promo_codes = db.query(PromoCode).count()
            used_promo_codes = db.query(PromoCode).filter_by(is_used=True).count()
            
            total_revenue = db.query(Payment).filter_by(payment_status='completed').with_entities(
                db.func.sum(Payment.amount)
            ).scalar() or 0.0
            
            return jsonify({
                'success': True,
                'stats': {
                    'users': {
                        'total': total_users,
                        'active': active_users,
                        'admins': admin_users
                    },
                    'subscriptions': {
                        'active': total_subs
                    },
                    'bots': {
                        'total': total_bots,
                        'active': active_bots
                    },
                    'promo_codes': {
                        'total': total_promo_codes,
                        'used': used_promo_codes
                    },
                    'revenue': {
                        'total': round(total_revenue, 2),
                        'currency': 'USD'
                    }
                }
            })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== PANEL PRINCIPAL ====================

@admin_bp.route('/admin')
@admin_required
def admin_panel():
    """Panel de administración principal"""
    return render_template('admin/dashboard.html')


@admin_bp.route('/admin/users')
@admin_required
def admin_users():
    """Página de gestión de usuarios"""
    return render_template('admin/users.html')


@admin_bp.route('/admin/promo-codes')
@admin_required
def admin_promo_codes():
    """Página de gestión de códigos promocionales"""
    return render_template('admin/promo_codes.html')


@admin_bp.route('/admin/bots')
@admin_required
def admin_bots():
    """Página de gestión de bots"""
    return render_template('admin/bots.html')


@admin_bp.route('/admin/strategies')
@admin_required
def admin_strategies():
    """Página de gestión de estrategias"""
    return render_template('admin/strategies.html')


@admin_bp.route('/admin/pricing')
@admin_required
def admin_pricing():
    """Página de gestión de precios"""
    return render_template('admin/pricing.html')


@admin_bp.route('/admin/payments')
@admin_required
def admin_payments():
    """Página de pagos y suscripciones"""
    return render_template('admin/payments.html')


@admin_bp.route('/api/admin/fill-market-data', methods=['POST'])
@admin_required
def fill_market_data():
    """Llena la base de datos con datos históricos de mercado usando yfinance"""
    try:
        data = request.json or {}
        days = data.get('days', 60)
        
        if days > 60:
            return jsonify({
                'success': False,
                'error': 'Máximo 60 días para intervalo 5min en yfinance'
            }), 400
        
        def run_script():
            """Ejecuta el script en background"""
            try:
                result = subprocess.run(
                    ['python', 'fill_market_data.py', str(days)],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                print("✅ Script de carga de datos completado")
                print(result.stdout)
                if result.stderr:
                    print("Errores:", result.stderr)
            except Exception as e:
                print(f"❌ Error ejecutando script: {e}")
        
        # Ejecutar en background
        thread = threading.Thread(target=run_script)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Descargando datos históricos de mercado ({days} días)...',
            'symbols': ['GOLD (XAUUSD)', 'EURUSD', 'EURJPY'],
            'interval': 'M5 (5 minutos)'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/generate-master-backtest', methods=['POST'])
@admin_required
def generate_master_backtest():
    """Genera backtest maestro - Solo WIN/LOSS para recalculo dinámico"""
    try:
        from backtesting_engine import BacktestingEngine
        from strategy_engine import Candle as EngineCandle
        from strategies import (
            RSIStrategy, MACDStrategy, BollingerStrategy,
            ProbabilityGaleStrategy, KolmogorovMarkovStrategy,
            KolmogorovComplexityStrategy, SmartTradeAcademyStrategy,
            TableroBinariasStrategy, TendencialTradeStrategy
        )
        
        data = request.json
        
        required_fields = ['strategy_name', 'symbol', 'timeframe']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Campo {field} requerido'}), 400
        
        strategy_name = data['strategy_name']
        symbol = data['symbol']
        timeframe = data['timeframe']
        trade_duration = int(data.get('trade_duration', 5))
        
        reference_amount = float(data.get('reference_amount', 100.0))
        reference_payout = float(data.get('reference_payout', 85.0))
        
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        
        strategy_map = {
            'RSI': RSIStrategy(),
            'MACD': MACDStrategy(),
            'Bollinger Bands': BollingerStrategy(),
            'Probability + Gale System': ProbabilityGaleStrategy(),
            'Kolmogorov-Markov': KolmogorovMarkovStrategy(),
            'Kolmogorov Complexity': KolmogorovComplexityStrategy(),
            'SmartTradeAcademy1': SmartTradeAcademyStrategy(),
            'Tablero Binarias': TableroBinariasStrategy()
        }
        
        if strategy_name not in strategy_map:
            return jsonify({'success': False, 'error': f'Estrategia {strategy_name} no encontrada'}), 404
        
        strategy = strategy_map[strategy_name]
        
        with get_db() as db:
            from sqlalchemy import text
            from datetime import datetime as dt
            
            if date_from and date_to:
                date_from_ts = int(dt.strptime(date_from, '%Y-%m-%d').timestamp())
                date_to_ts = int(dt.strptime(date_to + 'T23:59:59', '%Y-%m-%dT%H:%M:%S').timestamp())
                
                query = text("""
                    SELECT timestamp, open, high, low, close, volume
                    FROM candles
                    WHERE symbol = :symbol AND timeframe = :timeframe
                      AND timestamp >= :from_ts AND timestamp <= :to_ts
                    ORDER BY timestamp ASC
                    LIMIT 10000
                """)
                
                result = db.execute(query, {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'from_ts': date_from_ts,
                    'to_ts': date_to_ts
                })
            else:
                query = text("""
                    SELECT timestamp, open, high, low, close, volume
                    FROM candles
                    WHERE symbol = :symbol AND timeframe = :timeframe
                    ORDER BY timestamp ASC
                    LIMIT 10000
                """)
                
                result = db.execute(query, {'symbol': symbol, 'timeframe': timeframe})
            
            candles_data = []
            for row in result:
                candles_data.append({
                    'time': row[0],
                    'open': float(row[1]),
                    'high': float(row[2]),
                    'low': float(row[3]),
                    'close': float(row[4]),
                    'volume': float(row[5]) if row[5] else 0.0
                })
            
            if len(candles_data) < strategy.min_candles:
                return jsonify({
                    'success': False,
                    'error': f'Necesita al menos {strategy.min_candles} velas, encontradas: {len(candles_data)}'
                }), 400
            
            candles = [
                EngineCandle(
                    time=c['time'],
                    open=c['open'],
                    high=c['high'],
                    low=c['low'],
                    close=c['close'],
                    volume=c['volume']
                ) for c in candles_data
            ]
            
            engine = BacktestingEngine(
                initial_balance=1000.0,
                trade_amount=reference_amount,
                payout_percent=reference_payout
            )
            
            backtest_result = engine.run_backtest(
                strategy=strategy,
                symbol=symbol,
                timeframe=timeframe,
                candles=candles,
                trade_duration=trade_duration
            )
            
            master_run = BacktestMasterRun(
                strategy_name=strategy_name,
                symbol=symbol,
                timeframe=timeframe,
                version='v1.0',
                start_time=candles[0].time,
                end_time=candles[-1].time,
                total_candles=len(candles),
                reference_amount=reference_amount,
                reference_payout=reference_payout,
                total_signals=backtest_result.total_trades,
                winning_signals=backtest_result.winning_trades,
                losing_signals=backtest_result.losing_trades,
                draw_signals=backtest_result.draw_trades,
                win_rate=backtest_result.win_rate,
                max_consecutive_wins=backtest_result.max_consecutive_wins,
                max_consecutive_losses=backtest_result.max_consecutive_losses,
                description=f'Backtest maestro generado con {len(candles)} velas'
            )
            
            db.add(master_run)
            db.flush()
            
            for idx, trade in enumerate(backtest_result.trades):
                signal = BacktestMasterSignal(
                    master_run_id=master_run.id,
                    signal_index=idx,
                    signal_time=trade.entry_time,
                    direction=trade.direction,
                    entry_price=trade.entry_price,
                    exit_price=trade.exit_price,
                    result=trade.result
                )
                db.add(signal)
            
            db.commit()
            
            return jsonify({
                'success': True,
                'master_backtest_id': master_run.id,
                'stats': {
                    'strategy_name': strategy_name,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'total_candles': len(candles),
                    'total_signals': master_run.total_signals,
                    'winning_signals': master_run.winning_signals,
                    'losing_signals': master_run.losing_signals,
                    'win_rate': round(master_run.win_rate, 2),
                    'max_consecutive_wins': master_run.max_consecutive_wins,
                    'max_consecutive_losses': master_run.max_consecutive_losses
                }
            })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
