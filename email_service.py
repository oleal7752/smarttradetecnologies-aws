"""
Servicio de Email para STC Trading System
Envío de emails de verificación, notificaciones y recuperación de contraseñas
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime

class EmailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.environ.get('GMAIL_USER')
        self.sender_password = os.environ.get('GMAIL_APP_PASSWORD')
        
        # Detectar ambiente usando REPLIT_DEPLOYMENT
        # REPLIT_DEPLOYMENT=1 indica que estamos en producción publicada
        is_production = os.environ.get('REPLIT_DEPLOYMENT') == '1'
        
        if is_production:
            # En producción: usar URL de producción
            self.base_url = 'https://Smart-Trade-Academy-IA.replit.app'
            print(f"📧 Email Service: PRODUCCIÓN - {self.base_url}")
        else:
            # En desarrollo: usar URL de desarrollo
            dev_domain = os.environ.get('REPLIT_DEV_DOMAIN')
            if dev_domain:
                self.base_url = f'https://{dev_domain}'
            else:
                # Fallback a producción si no hay dev domain
                self.base_url = 'https://Smart-Trade-Academy-IA.replit.app'
            print(f"📧 Email Service: DESARROLLO - {self.base_url}")
        
        if not self.sender_email or not self.sender_password:
            raise ValueError("GMAIL_USER y GMAIL_APP_PASSWORD deben estar configurados")
    
    def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Envía un email HTML
        
        Args:
            to_email: Email del destinatario
            subject: Asunto del email
            html_content: Contenido HTML del email
            
        Returns:
            bool: True si se envió correctamente, False si hubo error
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"Smart Trade Academy <{self.sender_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            print(f"✅ Email enviado a {to_email}: {subject}")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando email a {to_email}: {e}")
            return False
    
    def send_verification_email(self, to_email: str, token: str, user_name: str) -> bool:
        """Envía email de verificación de cuenta"""
        
        verification_url = f"{self.base_url}/api/auth/verify-email/{token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #0a0e27;
                    color: #ffffff;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 40px 20px;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 40px;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: 700;
                    color: #00c851;
                }}
                .content {{
                    background: #1a1f3a;
                    border-radius: 15px;
                    padding: 40px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(135deg, #0066cc 0%, #00c851 100%);
                    color: white;
                    text-decoration: none;
                    padding: 15px 40px;
                    border-radius: 50px;
                    font-weight: 600;
                    margin: 30px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 40px;
                    color: #b0b8c1;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">📈 Smart Trade Academy</div>
                </div>
                <div class="content">
                    <h2>¡Bienvenido, {user_name}!</h2>
                    <p>Gracias por registrarte en Smart Trade Academy. Para activar tu cuenta, por favor verifica tu dirección de email.</p>
                    
                    <div style="text-align: center;">
                        <a href="{verification_url}" class="button">Verificar Email</a>
                    </div>
                    
                    <p style="margin-top: 30px; color: #b0b8c1; font-size: 14px;">
                        Si no puedes hacer clic en el botón, copia y pega este enlace en tu navegador:<br>
                        <span style="color: #0066cc;">{verification_url}</span>
                    </p>
                    
                    <p style="margin-top: 30px; color: #b0b8c1; font-size: 14px;">
                        Este enlace expirará en 24 horas.
                    </p>
                </div>
                <div class="footer">
                    <p>© 2024 Smart Trade Academy. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, "Verifica tu cuenta - Smart Trade Academy", html_content)
    
    def send_password_reset_email(self, to_email: str, token: str, user_name: str) -> bool:
        """Envía email de recuperación de contraseña"""
        
        reset_url = f"{self.base_url}/reset-password?token={token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #0a0e27;
                    color: #ffffff;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 40px 20px;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 40px;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: 700;
                    color: #00c851;
                }}
                .content {{
                    background: #1a1f3a;
                    border-radius: 15px;
                    padding: 40px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(135deg, #0066cc 0%, #00c851 100%);
                    color: white;
                    text-decoration: none;
                    padding: 15px 40px;
                    border-radius: 50px;
                    font-weight: 600;
                    margin: 30px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 40px;
                    color: #b0b8c1;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">📈 Smart Trade Academy</div>
                </div>
                <div class="content">
                    <h2>Recuperación de Contraseña</h2>
                    <p>Hola {user_name},</p>
                    <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta. Haz clic en el botón de abajo para crear una nueva contraseña:</p>
                    
                    <div style="text-align: center;">
                        <a href="{reset_url}" class="button">Restablecer Contraseña</a>
                    </div>
                    
                    <p style="margin-top: 30px; color: #b0b8c1; font-size: 14px;">
                        Si no puedes hacer clic en el botón, copia y pega este enlace en tu navegador:<br>
                        <span style="color: #0066cc;">{reset_url}</span>
                    </p>
                    
                    <p style="margin-top: 30px; color: #ff6b6b; font-size: 14px;">
                        ⚠️ Si no solicitaste este cambio, ignora este email. Tu contraseña permanecerá sin cambios.
                    </p>
                    
                    <p style="color: #b0b8c1; font-size: 14px;">
                        Este enlace expirará en 1 hora.
                    </p>
                </div>
                <div class="footer">
                    <p>© 2024 Smart Trade Academy. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, "Recuperación de Contraseña - Smart Trade Academy", html_content)
    
    def send_subscription_renewal_notification(
        self, 
        to_email: str, 
        user_name: str, 
        plan_name: str, 
        expiration_date: str,
        days_remaining: int
    ) -> bool:
        """Envía notificación de renovación de suscripción"""
        
        renewal_url = f"{self.base_url}/subscriptions"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #0a0e27;
                    color: #ffffff;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 40px 20px;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 40px;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: 700;
                    color: #00c851;
                }}
                .content {{
                    background: #1a1f3a;
                    border-radius: 15px;
                    padding: 40px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }}
                .alert-box {{
                    background: rgba(255, 193, 7, 0.1);
                    border-left: 4px solid #ffc107;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 5px;
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(135deg, #0066cc 0%, #00c851 100%);
                    color: white;
                    text-decoration: none;
                    padding: 15px 40px;
                    border-radius: 50px;
                    font-weight: 600;
                    margin: 30px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 40px;
                    color: #b0b8c1;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">📈 Smart Trade Academy</div>
                </div>
                <div class="content">
                    <h2>Tu Suscripción está por Vencer</h2>
                    <p>Hola {user_name},</p>
                    
                    <div class="alert-box">
                        <strong>⚠️ Recordatorio de Renovación</strong><br>
                        Tu plan <strong>{plan_name}</strong> vencerá en <strong>{days_remaining} días</strong> ({expiration_date}).
                    </div>
                    
                    <p>Para continuar disfrutando de:</p>
                    <ul>
                        <li>✅ 3 Bots activos simultáneos</li>
                        <li>✅ 8 Estrategias de trading avanzadas</li>
                        <li>✅ Sistema Dual-Gale optimizado</li>
                        <li>✅ Dashboard personalizado con estadísticas</li>
                        <li>✅ Soporte prioritario 24/7</li>
                    </ul>
                    
                    <p>Renueva tu suscripción antes de que expire:</p>
                    
                    <div style="text-align: center;">
                        <a href="{renewal_url}" class="button">Renovar Suscripción</a>
                    </div>
                    
                    <p style="margin-top: 30px; color: #b0b8c1; font-size: 14px;">
                        Si tienes alguna pregunta, nuestro equipo de soporte está disponible 24/7.
                    </p>
                </div>
                <div class="footer">
                    <p>© 2024 Smart Trade Academy. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(
            to_email, 
            f"⚠️ Tu suscripción vence en {days_remaining} días - Smart Trade Academy", 
            html_content
        )
    
    def send_payment_invoice(
        self,
        to_email: str,
        user_name: str,
        invoice_number: str,
        plan_name: str,
        amount: float,
        payment_date: str
    ) -> bool:
        """Envía factura de pago"""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #0a0e27;
                    color: #ffffff;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 40px 20px;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 40px;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: 700;
                    color: #00c851;
                }}
                .content {{
                    background: #1a1f3a;
                    border-radius: 15px;
                    padding: 40px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }}
                .invoice-box {{
                    background: rgba(0, 200, 81, 0.1);
                    border: 1px solid #00c851;
                    padding: 30px;
                    margin: 30px 0;
                    border-radius: 10px;
                }}
                .invoice-row {{
                    display: flex;
                    justify-content: space-between;
                    padding: 10px 0;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                }}
                .total-row {{
                    display: flex;
                    justify-content: space-between;
                    padding: 20px 0;
                    font-size: 24px;
                    font-weight: 700;
                    color: #00c851;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 40px;
                    color: #b0b8c1;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">📈 Smart Trade Academy</div>
                </div>
                <div class="content">
                    <h2>✅ Pago Confirmado - Factura #{invoice_number}</h2>
                    <p>Hola {user_name},</p>
                    <p>Gracias por tu pago. Tu suscripción ha sido activada exitosamente.</p>
                    
                    <div class="invoice-box">
                        <h3 style="margin-top: 0; color: #00c851;">Detalles de la Factura</h3>
                        <div class="invoice-row">
                            <span>Número de Factura:</span>
                            <strong>{invoice_number}</strong>
                        </div>
                        <div class="invoice-row">
                            <span>Fecha de Pago:</span>
                            <strong>{payment_date}</strong>
                        </div>
                        <div class="invoice-row">
                            <span>Plan Contratado:</span>
                            <strong>{plan_name}</strong>
                        </div>
                        <div class="total-row">
                            <span>Total Pagado:</span>
                            <strong>${amount:.2f}</strong>
                        </div>
                    </div>
                    
                    <p style="margin-top: 30px;">
                        Ya puedes acceder a tu dashboard y comenzar a usar tus bots de trading:
                    </p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{self.base_url}/dashboard" style="display: inline-block; background: linear-gradient(135deg, #0066cc 0%, #00c851 100%); color: white; text-decoration: none; padding: 15px 40px; border-radius: 50px; font-weight: 600;">Ir al Dashboard</a>
                    </div>
                    
                    <p style="color: #b0b8c1; font-size: 14px;">
                        Guarda esta factura para tus registros. Si tienes alguna pregunta, contáctanos en soporte@smarttradeacademy.com
                    </p>
                </div>
                <div class="footer">
                    <p>© 2024 Smart Trade Academy. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(
            to_email,
            f"Factura #{invoice_number} - Smart Trade Academy",
            html_content
        )
    
    def send_broker_validation_notification(
        self,
        to_email: str,
        user_name: str,
        broker_type: str,
        status: str,
        admin_comment: Optional[str] = None
    ) -> bool:
        """Envía notificación de validación de broker"""
        
        status_emoji = "✅" if status == "validated" else "❌"
        status_text = "Aprobada" if status == "validated" else "Rechazada"
        status_color = "#00c851" if status == "validated" else "#ff6b6b"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #0a0e27;
                    color: #ffffff;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 40px 20px;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 40px;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: 700;
                    color: #00c851;
                }}
                .content {{
                    background: #1a1f3a;
                    border-radius: 15px;
                    padding: 40px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }}
                .status-box {{
                    background: rgba(0, 200, 81, 0.1);
                    border-left: 4px solid {status_color};
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 5px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 40px;
                    color: #b0b8c1;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">📈 Smart Trade Academy</div>
                </div>
                <div class="content">
                    <h2>{status_emoji} Validación de Cuenta de Broker</h2>
                    <p>Hola {user_name},</p>
                    
                    <div class="status-box">
                        <strong>Estado de Validación: {status_text}</strong><br>
                        <strong>Broker:</strong> {broker_type.upper()}
                    </div>
                    
                    {f'<p><strong>Comentario del administrador:</strong><br>{admin_comment}</p>' if admin_comment else ''}
                    
                    {'<p>Tu cuenta de broker ha sido validada exitosamente. Ya puedes seleccionar tu plan de suscripción y comenzar a operar.</p>' if status == 'validated' else '<p>Tu cuenta de broker no pudo ser validada. Por favor, verifica los datos proporcionados o contacta a soporte.</p>'}
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{self.base_url}/{'subscriptions' if status == 'validated' else 'profile'}" style="display: inline-block; background: linear-gradient(135deg, #0066cc 0%, #00c851 100%); color: white; text-decoration: none; padding: 15px 40px; border-radius: 50px; font-weight: 600;">
                            {'Elegir Plan' if status == 'validated' else 'Ver Perfil'}
                        </a>
                    </div>
                </div>
                <div class="footer">
                    <p>© 2024 Smart Trade Academy. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(
            to_email,
            f"{status_emoji} Validación de Broker {status_text} - Smart Trade Academy",
            html_content
        )


# Instancia global del servicio
email_service = EmailService()
