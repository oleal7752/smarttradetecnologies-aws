import os
import uuid
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from database import (
    get_db, User, BrokerAccount, Subscription, PasswordReset,
    BrokerType, SubscriptionStatus, ValidationStatus
)
from functools import wraps
from email_service import email_service

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    """Decorador para rutas que requieren autenticación
    - Si es petición de API (/api/* o JSON): retorna JSON 401
    - Si es petición de navegador (HTML): redirige a /auth/login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            is_api_request = request.path.startswith('/api/') or request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_api_request:
                return jsonify({'success': False, 'error': 'No autorizado'}), 401
            else:
                return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorador para rutas que requieren permisos de administrador"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'No autorizado'}), 401
        
        with get_db() as db:
            user = db.query(User).filter_by(id=session['user_id']).first()
            if not user or not user.is_admin:
                return jsonify({'success': False, 'error': 'Permisos insuficientes'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def requires_active_access(f):
    """Decorador que requiere suscripción activa O código promocional válido
    - Si es petición de API (/api/* o JSON): retorna JSON 401/403
    - Si es petición de navegador (HTML): redirige a /access-validation"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"🔐 VERIFICANDO ACCESO - Sesión: {session.get('user_id', 'NO_SESSION')}")
        is_api_request = request.path.startswith('/api/') or request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if 'user_id' not in session:
            print("❌ ACCESO DENEGADO: Sin sesión")
            if is_api_request:
                return jsonify({'success': False, 'error': 'No autorizado. Inicia sesión.'}), 401
            else:
                return redirect(url_for('login_page'))
        
        with get_db() as db:
            from database import Subscription, PromoCode, SubscriptionStatus
            
            user_id = session['user_id']
            
            has_subscription = db.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.end_date > datetime.utcnow()
            ).first() is not None
            
            if has_subscription:
                return f(*args, **kwargs)
            
            promo_code = db.query(PromoCode).filter(
                PromoCode.assigned_to == user_id,
                PromoCode.is_used == True,
                PromoCode.is_active == True,
                PromoCode.expires_at > datetime.utcnow()
            ).order_by(PromoCode.activated_at.desc()).first()
            
            if promo_code:
                return f(*args, **kwargs)
            
            if is_api_request:
                return jsonify({
                    'success': False, 
                    'error': 'Acceso denegado. Necesitas una suscripción activa o código promocional válido.',
                    'requires_subscription': True
                }), 403
            else:
                return redirect(url_for('access_validation_page'))
    
    return decorated_function


@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    """Registro de nuevo usuario"""
    try:
        data = request.json
        
        # Validar campos requeridos
        required_fields = ['email', 'password', 'first_name', 'last_name', 
                          'dni', 'birth_date', 'phone', 'country', 'broker_type', 'broker_account_id']
        
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'Campo {field} es requerido'}), 400
        
        with get_db() as db:
            # Verificar si el email ya existe
            if db.query(User).filter_by(email=data['email']).first():
                return jsonify({'success': False, 'error': 'El email ya está registrado'}), 400
            
            # Verificar si el DNI ya existe
            if db.query(User).filter_by(dni=data['dni']).first():
                return jsonify({'success': False, 'error': 'El DNI ya está registrado'}), 400
            
            # Crear usuario
            verification_token = secrets.token_urlsafe(32)
            user = User(
                id=str(uuid.uuid4()),
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                dni=data['dni'],
                birth_date=datetime.strptime(data['birth_date'], '%Y-%m-%d'),
                phone=data['phone'],
                country=data['country'],
                email_verification_token=verification_token,
                email_verification_sent_at=datetime.utcnow(),
                email_verified=False  # REQUIERE VERIFICACIÓN POR EMAIL
            )
            user.set_password(data['password'])
            
            # Verificar que sea mayor de edad
            if not user.is_adult():
                return jsonify({'success': False, 'error': 'Debes ser mayor de 18 años'}), 400
            
            db.add(user)
            db.flush()
            
            # Crear cuenta de broker
            broker_account = BrokerAccount(
                user_id=user.id,
                broker_type=BrokerType(data['broker_type']),
                broker_account_id=data['broker_account_id'],
                validation_status=ValidationStatus.PENDING
            )
            db.add(broker_account)
            
            db.commit()
            
            # Enviar email de verificación
            try:
                email_sent = email_service.send_verification_email(
                    to_email=user.email,
                    token=verification_token,
                    user_name=f"{user.first_name} {user.last_name}"
                )
                
                if email_sent:
                    print(f"✅ Usuario {user.email} registrado - Email de verificación enviado")
                    return jsonify({
                        'success': True,
                        'message': 'Usuario registrado exitosamente. Revisa tu email para verificar tu cuenta.',
                        'user_id': user.id,
                        'email_sent': True
                    }), 201
                else:
                    print(f"⚠️ Usuario {user.email} registrado - Error al enviar email")
                    return jsonify({
                        'success': True,
                        'message': 'Usuario registrado pero hubo un problema al enviar el email de verificación. Contacta a soporte.',
                        'user_id': user.id,
                        'email_sent': False
                    }), 201
                    
            except Exception as e:
                print(f"❌ Error enviando email a {user.email}: {e}")
                return jsonify({
                    'success': True,
                    'message': 'Usuario registrado pero hubo un problema al enviar el email de verificación. Contacta a soporte.',
                    'user_id': user.id,
                    'email_sent': False
                }), 201
            
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error en el registro: {str(e)}'}), 500


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """Inicio de sesión"""
    try:
        data = request.json
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'success': False, 'error': 'Email y contraseña requeridos'}), 400
        
        with get_db() as db:
            user = db.query(User).filter_by(email=data['email']).first()
            
            if not user:
                print(f"❌ Login fallido: Usuario {data['email']} no encontrado")
                return jsonify({'success': False, 'error': 'Email o contraseña incorrecta'}), 401
            
            if not user.check_password(data['password']):
                print(f"❌ Login fallido: Contraseña incorrecta para {data['email']}")
                return jsonify({'success': False, 'error': 'Email o contraseña incorrecta'}), 401
            
            if not user.is_active:
                print(f"❌ Login fallido: Usuario {data['email']} desactivado")
                return jsonify({'success': False, 'error': 'Cuenta desactivada'}), 403
            
            if not user.email_verified:
                print(f"❌ Login fallido: Email {data['email']} no verificado")
                return jsonify({'success': False, 'error': 'Por favor verifica tu email primero. Revisa tu bandeja de entrada.'}), 403
            
            # Crear sesión
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['is_admin'] = user.is_admin
            
            # Actualizar último login
            user.last_login = datetime.utcnow()
            db.commit()
            
            # Determinar redirección segura en el servidor
            next_url = '/admin' if user.is_admin else '/trading-charts'
            
            return jsonify({
                'success': True,
                'next_url': next_url,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_admin': user.is_admin
                }
            }), 200
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error en login: {str(e)}'}), 500


@auth_bp.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    """Cerrar sesión"""
    session.clear()
    return jsonify({'success': True, 'message': 'Sesión cerrada'}), 200


@auth_bp.route('/api/auth/verify-email/<token>', methods=['GET'])
def verify_email(token):
    """Verificar email con token - Redirige a página HTML"""
    try:
        with get_db() as db:
            user = db.query(User).filter_by(email_verification_token=token).first()
            
            if not user:
                return render_template('auth/verify_result.html', 
                    success=False, 
                    message='Token inválido o expirado'), 400
            
            if user.email_verified:
                return render_template('auth/verify_result.html', 
                    success=True, 
                    message='Tu email ya estaba verificado. Puedes iniciar sesión.'), 200
            
            # Verificar que el token no haya expirado (24 horas)
            if user.email_verification_sent_at:
                expiry = user.email_verification_sent_at + timedelta(hours=24)
                if datetime.utcnow() > expiry:
                    return render_template('auth/verify_result.html', 
                        success=False, 
                        message='El enlace de verificación ha expirado. Por favor solicita uno nuevo.'), 400
            
            user.email_verified = True
            user.email_verification_token = None
            db.commit()
            
            return render_template('auth/verify_result.html', 
                success=True, 
                message=f'¡Email verificado exitosamente! Ya puedes iniciar sesión con {user.email}'), 200
            
    except Exception as e:
        return render_template('auth/verify_result.html', 
            success=False, 
            message=f'Error verificando email: {str(e)}'), 500


@auth_bp.route('/api/auth/request-password-reset', methods=['POST'])
def request_password_reset():
    """Solicitar reset de contraseña"""
    try:
        data = request.json
        
        if not data.get('email'):
            return jsonify({'success': False, 'error': 'Email requerido'}), 400
        
        with get_db() as db:
            user = db.query(User).filter_by(email=data['email']).first()
            
            if not user:
                # Por seguridad, no revelar si el email existe
                return jsonify({'success': True, 'message': 'Si el email existe, recibirás instrucciones'}), 200
            
            # Crear token de reset
            token = secrets.token_urlsafe(32)
            reset = PasswordReset(
                user_id=user.id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            db.add(reset)
            db.commit()
            
            # Enviar email de recuperación de contraseña
            email_sent = email_service.send_password_reset_email(
                to_email=user.email,
                token=token,
                user_name=user.first_name
            )
            
            if not email_sent:
                print(f"⚠️ No se pudo enviar email de recuperación a {user.email}")
            
            return jsonify({
                'success': True,
                'message': 'Si el email existe, recibirás instrucciones para recuperar tu contraseña'
            }), 200
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@auth_bp.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """Resetear contraseña con token"""
    try:
        data = request.json
        
        if not data.get('token') or not data.get('new_password'):
            return jsonify({'success': False, 'error': 'Token y nueva contraseña requeridos'}), 400
        
        with get_db() as db:
            reset = db.query(PasswordReset).filter_by(
                token=data['token'],
                used=False
            ).first()
            
            if not reset:
                return jsonify({'success': False, 'error': 'Token inválido'}), 400
            
            if datetime.utcnow() > reset.expires_at:
                return jsonify({'success': False, 'error': 'Token expirado'}), 400
            
            user = db.query(User).filter_by(id=reset.user_id).first()
            if not user:
                return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
            
            # Cambiar contraseña
            user.set_password(data['new_password'])
            reset.used = True
            db.commit()
            
            return jsonify({'success': True, 'message': 'Contraseña actualizada exitosamente'}), 200
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@auth_bp.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    """Obtener información del usuario actual"""
    try:
        with get_db() as db:
            user = db.query(User).filter_by(id=session['user_id']).first()
            
            if not user:
                return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
            
            # Obtener suscripción activa
            active_subscription = db.query(Subscription).filter_by(
                user_id=user.id,
                status=SubscriptionStatus.ACTIVE
            ).first()
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'phone': user.phone,
                    'is_admin': user.is_admin,
                    'has_active_subscription': active_subscription is not None,
                    'subscription': {
                        'plan': active_subscription.plan.value,
                        'days_remaining': active_subscription.get_days_remaining(),
                        'end_date': active_subscription.end_date.isoformat() if active_subscription.end_date else None
                    } if active_subscription else None
                }
            }), 200
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@auth_bp.route('/api/auth/check-access', methods=['GET'])
@login_required
def check_access():
    """Verificar si el usuario tiene acceso activo (suscripción o código promocional)"""
    try:
        with get_db() as db:
            from database import PromoCode
            
            user = db.query(User).filter_by(id=session['user_id']).first()
            
            if not user:
                return jsonify({'success': False, 'has_access': False}), 404
            
            # Verificar suscripción activa
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user.id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.end_date > datetime.utcnow()
            ).first()
            
            if subscription:
                return jsonify({
                    'success': True,
                    'has_access': True,
                    'access_via': 'subscription',
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name
                    },
                    'subscription': {
                        'plan': subscription.plan.value,
                        'end_date': subscription.end_date.isoformat()
                    }
                }), 200
            
            # Verificar código promocional activo
            promo_code = db.query(PromoCode).filter(
                PromoCode.assigned_to == user.id,
                PromoCode.is_used == True,
                PromoCode.is_active == True,
                PromoCode.expires_at > datetime.utcnow()
            ).order_by(PromoCode.activated_at.desc()).first()
            
            if promo_code:
                return jsonify({
                    'success': True,
                    'has_access': True,
                    'access_via': 'promo_code',
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name
                    },
                    'promo_code': {
                        'code': promo_code.code,
                        'expires_at': promo_code.expires_at.isoformat()
                    }
                }), 200
            
            # Sin acceso
            return jsonify({
                'success': True,
                'has_access': False,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                }
            }), 200
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@auth_bp.route('/api/auth/validate-promo-code', methods=['POST'])
@login_required
def validate_promo_code():
    """Validar código promocional SIN activarlo (solo verificar si es válido)"""
    try:
        data = request.json
        
        if not data.get('code'):
            return jsonify({'success': False, 'error': 'Código requerido'}), 400
        
        code = data['code'].strip().upper()
        
        with get_db() as db:
            from database import PromoCode
            
            # Buscar código
            promo_code = db.query(PromoCode).filter_by(code=code).first()
            
            if not promo_code:
                return jsonify({'success': False, 'error': 'Código no encontrado'}), 404
            
            # Verificar estado
            if not promo_code.is_active:
                return jsonify({'success': False, 'error': 'Código desactivado'}), 400
            
            # Verificar si ya está usado
            if promo_code.is_used:
                return jsonify({'success': False, 'error': 'Código ya utilizado'}), 400
            
            # Verificar expiración
            if promo_code.expires_at and datetime.utcnow() > promo_code.expires_at:
                return jsonify({'success': False, 'error': 'Código expirado'}), 400
            
            # Código válido
            return jsonify({
                'success': True,
                'message': 'Código válido',
                'code': {
                    'code': promo_code.code,
                    'type': promo_code.type.value,
                    'duration_hours': promo_code.duration_hours,
                    'expires_at': promo_code.expires_at.isoformat() if promo_code.expires_at else None
                }
            }), 200
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@auth_bp.route('/api/auth/activate-promo-code', methods=['POST'])
@login_required
def activate_promo_code():
    """Activar código promocional para el usuario actual"""
    try:
        data = request.json
        
        if not data.get('code'):
            return jsonify({'success': False, 'error': 'Código requerido'}), 400
        
        code = data['code'].strip().upper()
        
        with get_db() as db:
            from database import PromoCode
            
            # Buscar código
            promo_code = db.query(PromoCode).filter_by(code=code).first()
            
            if not promo_code:
                return jsonify({'success': False, 'error': 'Código no encontrado'}), 404
            
            # Verificar estado
            if not promo_code.is_active:
                return jsonify({'success': False, 'error': 'Código desactivado'}), 400
            
            # Verificar si ya está usado
            if promo_code.is_used:
                return jsonify({'success': False, 'error': 'Código ya utilizado'}), 400
            
            # Verificar expiración
            if promo_code.expires_at and datetime.utcnow() > promo_code.expires_at:
                return jsonify({'success': False, 'error': 'Código expirado'}), 400
            
            # Activar código
            promo_code.is_used = True
            promo_code.assigned_to = session['user_id']
            promo_code.activated_at = datetime.utcnow()
            
            # Calcular nueva fecha de expiración
            new_expiration = datetime.utcnow() + timedelta(hours=promo_code.duration_hours)
            promo_code.expires_at = new_expiration
            
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'Código activado exitosamente',
                'access_granted': True,
                'expires_at': new_expiration.isoformat()
            }), 200
            
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@auth_bp.route('/api/auth/broker-status', methods=['GET'])
@login_required
def get_broker_status():
    """Obtener estado de validación de cuenta de broker del usuario"""
    try:
        with get_db() as db:
            broker_account = db.query(BrokerAccount).filter_by(
                user_id=session['user_id']
            ).first()
            
            if not broker_account:
                return jsonify({
                    'success': True,
                    'broker_account': None
                }), 200
            
            return jsonify({
                'success': True,
                'broker_account': {
                    'id': broker_account.id,
                    'broker_type': broker_account.broker_type.value,
                    'broker_account_id': broker_account.broker_account_id,
                    'validation_status': broker_account.validation_status.value,
                    'validated_at': broker_account.validated_at.isoformat() if broker_account.validated_at else None,
                    'validation_notes': broker_account.validation_notes,
                    'created_at': broker_account.created_at.isoformat()
                }
            }), 200
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@auth_bp.route('/api/admin/broker-validations', methods=['GET'])
@admin_required
def get_pending_broker_validations():
    """Obtener todas las solicitudes de validación de broker (admin)"""
    try:
        with get_db() as db:
            status_filter = request.args.get('status', 'pending')
            
            query = db.query(BrokerAccount, User).join(User)
            
            if status_filter == 'pending':
                query = query.filter(BrokerAccount.validation_status == ValidationStatus.PENDING)
            elif status_filter == 'approved':
                query = query.filter(BrokerAccount.validation_status == ValidationStatus.APPROVED)
            elif status_filter == 'rejected':
                query = query.filter(BrokerAccount.validation_status == ValidationStatus.REJECTED)
            
            query = query.order_by(BrokerAccount.created_at.desc())
            results = query.all()
            
            validations = []
            for broker, user in results:
                validations.append({
                    'id': broker.id,
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'phone': user.phone
                    },
                    'broker_type': broker.broker_type.value,
                    'broker_account_id': broker.broker_account_id,
                    'validation_status': broker.validation_status.value,
                    'validated_at': broker.validated_at.isoformat() if broker.validated_at else None,
                    'validation_notes': broker.validation_notes,
                    'created_at': broker.created_at.isoformat()
                })
            
            return jsonify({
                'success': True,
                'validations': validations,
                'total': len(validations)
            }), 200
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@auth_bp.route('/api/admin/broker-validate/<int:broker_id>', methods=['POST'])
@admin_required
def validate_broker_account(broker_id):
    """Aprobar o rechazar validación de broker (admin)"""
    try:
        data = request.json
        
        if 'action' not in data or data['action'] not in ['approve', 'reject']:
            return jsonify({'success': False, 'error': 'Acción inválida'}), 400
        
        with get_db() as db:
            broker_account = db.query(BrokerAccount).filter_by(id=broker_id).first()
            
            if not broker_account:
                return jsonify({'success': False, 'error': 'Cuenta de broker no encontrada'}), 404
            
            admin_user = db.query(User).filter_by(id=session['user_id']).first()
            
            if data['action'] == 'approve':
                broker_account.validation_status = ValidationStatus.APPROVED
                broker_account.validated_at = datetime.utcnow()
                broker_account.validated_by_admin = admin_user.email
                broker_account.validation_notes = data.get('notes', '')
                
                user = db.query(User).filter_by(id=broker_account.user_id).first()
                
                email_service.send_broker_validation_notification(
                    user.email,
                    user.first_name,
                    broker_account.broker_type.value,
                    status="validated",
                    admin_comment=broker_account.validation_notes
                )
                
                message = f'Cuenta de {broker_account.broker_type.value} aprobada exitosamente'
                
            else:
                broker_account.validation_status = ValidationStatus.REJECTED
                broker_account.validated_at = datetime.utcnow()
                broker_account.validated_by_admin = admin_user.email
                broker_account.validation_notes = data.get('notes', 'No especificado')
                
                user = db.query(User).filter_by(id=broker_account.user_id).first()
                
                email_service.send_broker_validation_notification(
                    user.email,
                    user.first_name,
                    broker_account.broker_type.value,
                    status="rejected",
                    admin_comment=broker_account.validation_notes
                )
                
                message = f'Cuenta de {broker_account.broker_type.value} rechazada'
            
            db.commit()
            
            return jsonify({
                'success': True,
                'message': message,
                'broker_account': {
                    'id': broker_account.id,
                    'validation_status': broker_account.validation_status.value,
                    'validated_at': broker_account.validated_at.isoformat(),
                    'validation_notes': broker_account.validation_notes
                }
            }), 200
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@auth_bp.route('/api/subscriptions/current', methods=['GET'])
@login_required
def get_current_subscription():
    """Obtiene la suscripción activa del usuario"""
    try:
        with get_db() as db:
            subscription = db.query(Subscription).filter_by(
                user_id=session['user_id'],
                status=SubscriptionStatus.ACTIVE
            ).first()
            
            if subscription:
                return jsonify({
                    'success': True,
                    'subscription': {
                        'id': subscription.id,
                        'plan': subscription.plan.value,
                        'status': subscription.status.value,
                        'start_date': subscription.start_date.isoformat() if subscription.start_date else None,
                        'end_date': subscription.end_date.isoformat() if subscription.end_date else None,
                        'amount': subscription.amount,
                        'available_bots': subscription.available_bots
                    }
                }), 200
            else:
                return jsonify({'success': True, 'subscription': None}), 200
                
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@auth_bp.route('/api/subscriptions/purchase', methods=['POST'])
@login_required
def purchase_subscription():
    """Procesa la compra de una suscripción (pago simulado)"""
    try:
        data = request.json
        plan_str = data.get('plan')
        
        if not plan_str:
            return jsonify({'success': False, 'error': 'Plan no especificado'}), 400
        
        try:
            plan = SubscriptionPlan(plan_str)
        except ValueError:
            return jsonify({'success': False, 'error': 'Plan inválido'}), 400
        
        with get_db() as db:
            user = db.query(User).filter_by(id=session['user_id']).first()
            
            if not user:
                return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
            
            # Verificar que el broker esté aprobado
            broker_account = db.query(BrokerAccount).filter_by(
                user_id=user.id,
                validation_status=ValidationStatus.APPROVED
            ).first()
            
            if not broker_account:
                return jsonify({
                    'success': False,
                    'error': 'Debe tener una cuenta de broker aprobada antes de suscribirse'
                }), 403
            
            # Expirar TODAS las suscripciones activas previas (previene duplicados)
            existing_subscriptions = db.query(Subscription).filter_by(
                user_id=user.id,
                status=SubscriptionStatus.ACTIVE
            ).all()
            
            for existing_sub in existing_subscriptions:
                # Marcar cada suscripción anterior como expirada
                existing_sub.status = SubscriptionStatus.EXPIRED
                existing_sub.end_date = datetime.utcnow()
            
            # Calcular precio y duración
            amount = Subscription.get_plan_price(plan)
            duration_days = Subscription.get_plan_duration_days(plan)
            
            # Crear nueva suscripción
            subscription_id = str(uuid.uuid4())
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=duration_days)
            
            subscription = Subscription(
                id=subscription_id,
                user_id=user.id,
                plan=plan,
                status=SubscriptionStatus.ACTIVE,
                start_date=start_date,
                end_date=end_date,
                amount=amount,
                available_bots=['RSI Oversold/Overbought', 'MACD Crossover', 'Bollinger Bands Bounce']
            )
            
            db.add(subscription)
            db.flush()  # Flush para validar antes de commit
            
            # Validación de seguridad: verificar que solo hay 1 suscripción ACTIVE
            active_count = db.query(Subscription).filter_by(
                user_id=user.id,
                status=SubscriptionStatus.ACTIVE
            ).count()
            
            if active_count > 1:
                db.rollback()
                return jsonify({
                    'success': False,
                    'error': 'Error de integridad: múltiples suscripciones activas detectadas'
                }), 500
            
            # Crear registro de pago (simulado)
            from database import Payment
            import uuid as payment_uuid
            
            invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{payment_uuid.uuid4().hex[:6].upper()}"
            
            payment = Payment(
                id=str(payment_uuid.uuid4()),
                user_id=user.id,
                subscription_id=subscription.id,
                amount=amount,
                currency="USD",
                payment_method="simulated",
                transaction_id=f"TXN-{payment_uuid.uuid4().hex[:8].upper()}",
                status="completed",
                invoice_number=invoice_number,
                payment_date=datetime.utcnow()
            )
            
            db.add(payment)
            db.commit()
            
            # Enviar email de factura
            email_service.send_payment_invoice(
                user.email,
                user.first_name,
                invoice_number,
                plan.value,
                amount,
                start_date.strftime('%Y-%m-%d')
            )
            
            return jsonify({
                'success': True,
                'message': 'Suscripción activada exitosamente',
                'subscription_id': subscription.id,
                'invoice_number': invoice_number,
                'end_date': end_date.isoformat()
            }), 200
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@auth_bp.route('/api/admin/check-renewals', methods=['POST'])
@admin_required
def check_subscription_renewals():
    """Verifica suscripciones próximas a vencer y envía notificaciones (7 días antes)"""
    try:
        with get_db() as db:
            # Buscar suscripciones que vencen en 7 días
            seven_days_from_now = datetime.utcnow() + timedelta(days=7)
            tomorrow = datetime.utcnow() + timedelta(days=1)
            
            expiring_subscriptions = db.query(Subscription, User).join(User).filter(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.end_date >= seven_days_from_now,
                Subscription.end_date <= seven_days_from_now + timedelta(days=1)
            ).all()
            
            notifications_sent = 0
            
            for subscription, user in expiring_subscriptions:
                days_remaining = (subscription.end_date - datetime.utcnow()).days
                
                # Enviar email de renovación
                email_service.send_subscription_renewal_notification(
                    user.email,
                    user.first_name,
                    subscription.plan.value,
                    subscription.end_date.strftime('%Y-%m-%d'),
                    days_remaining
                )
                
                # Crear notificación en la BD
                from database import Notification
                notification = Notification(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    type="subscription_renewal",
                    title=f"Renovación de suscripción",
                    message=f"Tu suscripción {subscription.plan.value} vence en {days_remaining} días",
                    read=False,
                    created_at=datetime.utcnow()
                )
                db.add(notification)
                notifications_sent += 1
            
            db.commit()
            
            return jsonify({
                'success': True,
                'notifications_sent': notifications_sent,
                'message': f'{notifications_sent} notificaciones enviadas'
            }), 200
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@auth_bp.route('/api/user/notifications', methods=['GET'])
@login_required
def get_user_notifications():
    """Obtiene notificaciones del usuario"""
    try:
        with get_db() as db:
            from database import Notification
            notifications = db.query(Notification).filter_by(
                user_id=session['user_id']
            ).order_by(Notification.created_at.desc()).limit(20).all()
            
            unread_count = db.query(Notification).filter_by(
                user_id=session['user_id'],
                read=False
            ).count()
            
            return jsonify({
                'success': True,
                'notifications': [{
                    'id': n.id,
                    'type': n.type,
                    'title': n.title,
                    'message': n.message,
                    'read': n.read,
                    'created_at': n.created_at.isoformat()
                } for n in notifications],
                'unread_count': unread_count
            }), 200
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@auth_bp.route('/forgot-password', methods=['GET'])
def forgot_password_page():
    """Página para recuperar contraseña"""
    return render_template('forgot_password.html')


@auth_bp.route('/reset-password', methods=['GET'])
def reset_password_page():
    """Página para restablecer contraseña"""
    return render_template('reset_password.html')
