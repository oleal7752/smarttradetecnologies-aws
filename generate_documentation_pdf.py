import os
import sys
from datetime import datetime
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.graphics import renderPDF
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("⚠️ ReportLab no está instalado. Instalando...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    # Re-importar después de instalar
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.graphics import renderPDF
    REPORTLAB_AVAILABLE = True

def create_stc_documentation_pdf():
    """Genera la documentación completa del Sistema STC Trading en PDF"""
    
    # Configuración del documento
    doc = SimpleDocTemplate(
        "STC_Trading_Sistema_Completo.pdf",
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=HexColor('#0f172a'),
        fontName='Helvetica-Bold'
    )
    
    heading1_style = ParagraphStyle(
        'CustomHeading1',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        spaceBefore=20,
        textColor=HexColor('#2563eb'),
        fontName='Helvetica-Bold'
    )
    
    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=15,
        textColor=HexColor('#0f172a'),
        fontName='Helvetica-Bold'
    )
    
    heading3_style = ParagraphStyle(
        'CustomHeading3',
        parent=styles['Heading3'],
        fontSize=12,
        spaceAfter=8,
        spaceBefore=12,
        textColor=HexColor('#374151'),
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    )
    
    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Courier',
        backColor=HexColor('#f3f4f6'),
        borderColor=HexColor('#e5e7eb'),
        borderWidth=1,
        leftIndent=20,
        rightIndent=20,
        spaceAfter=10
    )
    
    # Contenido del documento
    story = []
    
    # === PORTADA ===
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("🏛️ SISTEMA STC TRADING", title_style))
    story.append(Paragraph("Plataforma Profesional de Trading Automatizado", styles['Heading3']))
    story.append(Paragraph("IQ Option • Mercados OTC • Dashboard Web", styles['Normal']))
    story.append(Spacer(1, 1*inch))
    
    # Información del sistema
    info_data = [
        ["📊 Versión", "Dashboard Pro v1.0"],
        ["🗓️ Fecha", "30 Septiembre 2025"],
        ["🔧 Arquitectura", "3 Capas (Frontend + API + Cliente)"],
        ["🌐 Acceso Web", "http://localhost:5001"],
        ["⚡ Trading", "OTC 24/7 - CALL/PUT Binario"],
        ["📈 Gráficos", "TradingView Lightweight Charts"],
        ["🎯 Mercados", "EURUSD, GBPUSD, USDJPY, EURJPY OTC"]
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), HexColor('#f8fafc')),
        ('TEXTCOLOR', (0,0), (-1,-1), black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(info_table)
    story.append(PageBreak())
    
    # === ÍNDICE ===
    story.append(Paragraph("📋 ÍNDICE", heading1_style))
    
    toc_data = [
        ["1.", "Arquitectura del Sistema", "3"],
        ["2.", "Flujo de Inicio y Arranque", "4"],
        ["3.", "Flujo de Credenciales", "5"],
        ["4.", "Flujo de Velas M5", "6"],
        ["5.", "Flujo de Órdenes de Trading", "7"],
        ["6.", "Diccionario de Archivos", "8"],
        ["7.", "Bondades del Sistema", "9"],
        ["8.", "Puertos y Servicios", "10"],
        ["9.", "Requerimientos del Sistema", "11"],
        ["10.", "Guía de Instalación", "12"],
        ["11.", "Configuración y Setup", "13"],
        ["12.", "Troubleshooting", "14"]
    ]
    
    toc_table = Table(toc_data, colWidths=[0.5*inch, 4*inch, 0.5*inch])
    toc_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    
    story.append(toc_table)
    story.append(PageBreak())
    
    # === 1. ARQUITECTURA DEL SISTEMA ===
    story.append(Paragraph("1. 🏗️ ARQUITECTURA DEL SISTEMA", heading1_style))
    
    story.append(Paragraph("Componentes Principales", heading2_style))
    story.append(Paragraph("""
    El sistema STC Trading está construido con una arquitectura de 3 capas independientes que se comunican 
    a través de APIs REST y protocolos HTTP. Esta separación garantiza escalabilidad, mantenibilidad y 
    robustez del sistema completo.
    """, body_style))
    
    arch_data = [
        ["Componente", "Puerto", "Tecnología", "Función Principal"],
        ["Dashboard Frontend", "5001", "Flask + HTML/JS", "Interface web de usuario"],
        ["API Backend", "5002", "Flask + Redis", "Gestión de datos y órdenes"],
        ["Cliente IQ Option", "-", "Python + IQ API", "Conexión real con broker"],
    ]
    
    arch_table = Table(arch_data, colWidths=[1.8*inch, 0.8*inch, 1.5*inch, 2.2*inch])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#2563eb')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor('#f8fafc'), white]),
    ]))
    
    story.append(arch_table)
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("Flujo de Comunicación", heading3_style))
    story.append(Paragraph("""
    <b>Usuario</b> → <b>Dashboard (5001)</b> → <b>API (5002)</b> → <b>Cliente IQ</b> → <b>IQ Option Servers</b>
    """, code_style))
    
    # === 2. FLUJO DE INICIO Y ARRANQUE ===
    story.append(PageBreak())
    story.append(Paragraph("2. 🚀 FLUJO DE INICIO Y ARRANQUE", heading1_style))
    
    story.append(Paragraph("Secuencia de Arranque Obligatoria", heading2_style))
    story.append(Paragraph("""
    El sistema debe iniciarse en un orden específico para garantizar que todos los componentes se conecten 
    correctamente y los servicios estén disponibles cuando se necesiten.
    """, body_style))
    
    startup_data = [
        ["Orden", "Archivo", "Puerto", "Función", "Tiempo Espera"],
        ["1º", "iq_routes_redis_patch.py", "5002", "API Backend + Redis Cache", "5 segundos"],
        ["2º", "dashboard_server.py", "5001", "Servidor Web Dashboard", "4 segundos"],
        ["3º", "iq_client.py", "-", "Cliente IQ Option", "5 segundos"],
    ]
    
    startup_table = Table(startup_data, colWidths=[0.6*inch, 2.2*inch, 0.8*inch, 2.2*inch, 1.2*inch])
    startup_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#10b981')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(startup_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Script de Inicio Automático", heading3_style))
    story.append(Paragraph("""
    start_dashboard_pro.bat
    ├── Detiene procesos previos
    ├── Inicia API Backend (puerto 5002)
    ├── Inicia Dashboard Web (puerto 5001)
    ├── Inicia Cliente IQ Option
    └── Verifica que todos los servicios estén activos
    """, code_style))
    
    # === 3. FLUJO DE CREDENCIALES ===
    story.append(PageBreak())
    story.append(Paragraph("3. 🔐 FLUJO DE CREDENCIALES", heading1_style))
    
    story.append(Paragraph("Ruta de Autenticación", heading2_style))
    story.append(Paragraph("""
    Las credenciales de IQ Option viajan de forma segura a través de la arquitectura del sistema, 
    desde la interface web hasta la conexión real con los servidores de IQ Option.
    """, body_style))
    
    creds_data = [
        ["Etapa", "Componente", "Acción", "Datos Procesados"],
        ["1", "dashboard_pro.html", "Captura formulario", "Email + Password + Balance Type"],
        ["2", "dashboard_server.py", "Proxy HTTP POST", "Redirige a puerto 5002"],
        ["3", "iq_routes_redis_patch.py", "Procesa /api/iq/login", "Valida y encola credenciales"],
        ["4", "iq_client.py", "Conexión IQ Option", "Login real + cambio de balance"],
        ["5", "Respuesta", "Confirmación", "Session ID + Estado conexión"],
    ]
    
    creds_table = Table(creds_data, colWidths=[0.6*inch, 2*inch, 1.8*inch, 2.6*inch])
    creds_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#f59e0b')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(creds_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Seguridad y Almacenamiento", heading3_style))
    story.append(Paragraph("""
    • <b>Almacenamiento:</b> Memoria Redis + localStorage del navegador<br/>
    • <b>Transmisión:</b> HTTP POST (local network)<br/>
    • <b>Validación:</b> IQ Option servers via HTTPS<br/>
    • <b>Sesión:</b> Persistente hasta logout manual
    """, body_style))
    
    # === 4. FLUJO DE VELAS M5 ===
    story.append(PageBreak())
    story.append(Paragraph("4. 📈 FLUJO DE VELAS M5", heading1_style))
    
    story.append(Paragraph("Origen y Destino de Datos de Velas", heading2_style))
    story.append(Paragraph("""
    Las velas de 5 minutos (M5) son la base del análisis técnico en el sistema. Estos datos viajan 
    desde los servidores de IQ Option hasta el dashboard web para visualización en tiempo real.
    """, body_style))
    
    candles_flow = """
    IQ Option API → iq_client.py → Memory Redis → iq_routes_redis_patch.py → dashboard_pro.html → TradingView Charts
    """
    story.append(Paragraph(candles_flow, code_style))
    
    candles_data = [
        ["Etapa", "Componente", "Función", "Datos"],
        ["Obtención", "iq_client.py", "get_candles() cada 2s", "OHLCV + timestamp"],
        ["Cache", "MemoryRedis", "Almacén temporal", "Últimas 200 velas"],
        ["API", "ruta /api/iq/candles", "GET endpoint", "JSON con velas filtradas"],
        ["Frontend", "ChartManager class", "Fetch automático", "Renderizado TradingView"],
        ["Visualización", "Lightweight Charts", "Gráfico interactivo", "Velas + línea BID"],
    ]
    
    candles_table = Table(candles_data, colWidths=[1.2*inch, 1.8*inch, 1.8*inch, 2.2*inch])
    candles_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#8b5cf6')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(candles_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Características de las Velas", heading3_style))
    story.append(Paragraph("""
    • <b>Timeframe:</b> M5 (5 minutos) - Optimizado para trading binario<br/>
    • <b>Símbolos OTC:</b> EURUSD-OTC, GBPUSD-OTC, USDJPY-OTC, EURJPY-OTC<br/>
    • <b>Disponibilidad:</b> 24/7 (mercados OTC siempre abiertos)<br/>
    • <b>Actualización:</b> Cada 2 segundos con nuevos datos<br/>
    • <b>Histórico:</b> Últimas 200 velas en memoria para análisis
    """, body_style))
    
    # === 5. FLUJO DE ÓRDENES DE TRADING ===
    story.append(PageBreak())
    story.append(Paragraph("5. 💸 FLUJO DE ÓRDENES DE TRADING", heading1_style))
    
    story.append(Paragraph("Envío de Orden CALL/PUT", heading2_style))
    story.append(Paragraph("""
    El proceso de envío de órdenes es crítico para el trading. El sistema garantiza que cada orden 
    sea procesada de forma segura y eficiente desde el dashboard hasta IQ Option.
    """, body_style))
    
    order_flow = """
    Usuario (CALL/PUT) → Dashboard → API → Cola Redis → IQ Client → IQ Option → Confirmación
    """
    story.append(Paragraph(order_flow, code_style))
    
    orders_data = [
        ["Paso", "Componente", "Acción", "Datos", "Tiempo"],
        ["1", "dashboard_pro.html", "Clic botón CALL/PUT", "Symbol + Amount + Duration", "Inmediato"],
        ["2", "JavaScript fetch()", "POST /api/iq/trade", "JSON con parámetros orden", "< 100ms"],
        ["3", "dashboard_server.py", "Proxy a puerto 5002", "Forward request", "< 50ms"],
        ["4", "iq_routes_redis_patch.py", "Procesa y encola", "Orden en cola Redis", "< 200ms"],
        ["5", "iq_client.py", "Ejecuta en IQ Option", "api.buy() real", "1-3 segundos"],
        ["6", "Confirmación", "Resultado al dashboard", "Order ID + Status", "< 500ms"],
    ]
    
    orders_table = Table(orders_data, colWidths=[0.5*inch, 1.6*inch, 1.4*inch, 1.8*inch, 1*inch])
    orders_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#ef4444')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(orders_table)
    
    # === 6. DICCIONARIO DE ARCHIVOS ===
    story.append(PageBreak())
    story.append(Paragraph("6. 🗂️ DICCIONARIO DE ARCHIVOS Y FUNCIONES", heading1_style))
    
    story.append(Paragraph("Backend Core", heading2_style))
    
    backend_data = [
        ["Archivo", "Puerto", "Líneas", "Función Principal", "Dependencias Clave"],
        ["iq_routes_redis_patch.py", "5002", "~400", "API REST + Cache Redis", "Flask, MemoryRedis"],
        ["dashboard_server.py", "5001", "~120", "Servidor web + Proxy", "Flask, requests"],
        ["iq_client.py", "-", "~450", "Cliente IQ Option", "iqoptionapi, httpx"],
    ]
    
    backend_table = Table(backend_data, colWidths=[2.2*inch, 0.8*inch, 0.8*inch, 1.8*inch, 1.4*inch])
    backend_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#0f172a')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(backend_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Frontend y Templates", heading2_style))
    
    frontend_data = [
        ["Archivo", "Tamaño", "Función", "Tecnologías"],
        ["dashboard_pro.html", "~1200 líneas", "Interface moderna trading", "HTML5 + CSS3 + JavaScript ES6"],
        ["dashboard.html", "~1200 líneas", "Interface original (backup)", "HTML5 + TradingView Charts"],
    ]
    
    frontend_table = Table(frontend_data, colWidths=[2*inch, 1.5*inch, 2*inch, 1.5*inch])
    frontend_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#059669')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
    ]))
    
    story.append(frontend_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Scripts de Automatización", heading2_style))
    
    scripts_data = [
        ["Script", "Función", "Orden de Ejecución"],
        ["start_dashboard_pro.bat", "Inicio sistema completo nuevo", "Recomendado principal"],
        ["start_system_final.bat", "Inicio sistema anterior", "Backup alternativo"],
        ["restart_fixed_system.bat", "Reinicio con correcciones", "Para troubleshooting"],
        ["test_trading_routes.bat", "Pruebas de endpoints API", "Para desarrollo"],
    ]
    
    scripts_table = Table(scripts_data, colWidths=[2.2*inch, 2.5*inch, 2.3*inch])
    scripts_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#7c3aed')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
    ]))
    
    story.append(scripts_table)
    
    # === 7. BONDADES DEL SISTEMA ===
    story.append(PageBreak())
    story.append(Paragraph("7. 🌟 BONDADES Y VENTAJAS DEL SISTEMA", heading1_style))
    
    story.append(Paragraph("Arquitectura Modular", heading2_style))
    story.append(Paragraph("""
    • <b>Separación de responsabilidades:</b> Frontend, API y Cliente independientes<br/>
    • <b>Escalabilidad:</b> Cada componente puede escalar individualmente<br/>
    • <b>Mantenibilidad:</b> Modificaciones aisladas sin afectar otros módulos<br/>
    • <b>Testabilidad:</b> Cada capa puede probarse por separado
    """, body_style))
    
    story.append(Paragraph("Trading 24/7 OTC", heading2_style))
    story.append(Paragraph("""
    • <b>Mercados OTC:</b> Disponibles las 24 horas, 7 días de la semana<br/>
    • <b>Símbolos principales:</b> EURUSD-OTC, GBPUSD-OTC, USDJPY-OTC, EURJPY-OTC<br/>
    • <b>Sin restricciones horarias:</b> Opera en cualquier momento<br/>
    • <b>Latencia optimizada:</b> Cache en memoria para ejecución rápida
    """, body_style))
    
    story.append(Paragraph("Interface Profesional", heading2_style))
    story.append(Paragraph("""
    • <b>Dashboard moderno:</b> Diseño elegante inspirado en plataformas profesionales<br/>
    • <b>Gráficos TradingView:</b> Velas M5 interactivas con indicadores<br/>
    • <b>Trading integrado:</b> Botones CALL/PUT con un solo clic<br/>
    • <b>Estadísticas en vivo:</b> Balance, operaciones y rendimiento actualizados<br/>
    • <b>Responsive design:</b> Compatible con desktop y móvil
    """, body_style))
    
    story.append(Paragraph("Robustez y Confiabilidad", heading2_style))
    story.append(Paragraph("""
    • <b>Manejo inteligente de errores:</b> Reconexión automática y recuperación<br/>
    • <b>Cache eficiente:</b> Datos persistentes en memoria para velocidad<br/>
    • <b>Fallbacks múltiples:</b> CDNs de respaldo para librerías externas<br/>
    • <b>Logs detallados:</b> Sistema completo de debugging y monitoreo<br/>
    • <b>Validaciones:</b> Verificación de datos en cada etapa
    """, body_style))
    
    # === 8. PUERTOS Y SERVICIOS ===
    story.append(PageBreak())
    story.append(Paragraph("8. 📡 PUERTOS Y SERVICIOS", heading1_style))
    
    story.append(Paragraph("Mapa de Conectividad", heading2_style))
    
    connectivity_map = """
    Internet (IQ Option API) ← HTTPS → iq_client.py
                                           ↓ Redis Queue
    localhost:5001 (Dashboard) ← HTTP → localhost:5002 (API Backend)
                   ↓ Navegador Web              ↓ REST Endpoints
               Usuario Final                   Cache + Órdenes
    """
    story.append(Paragraph(connectivity_map, code_style))
    
    ports_data = [
        ["Puerto", "Servicio", "Protocolo", "Función", "Acceso"],
        ["5001", "Dashboard Web", "HTTP", "Interface usuario", "http://localhost:5001"],
        ["5002", "API Backend", "HTTP", "REST API + Cache", "http://localhost:5002"],
        ["-", "Cliente IQ", "HTTPS", "Conexión externa", "Proceso background"],
        ["443", "IQ Option", "HTTPS", "Broker real", "Internet (external)"],
    ]
    
    ports_table = Table(ports_data, colWidths=[0.8*inch, 1.5*inch, 1*inch, 1.8*inch, 1.9*inch])
    ports_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#dc2626')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(ports_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("URLs Principales del Sistema", heading2_style))
    
    urls_data = [
        ["Endpoint", "Método", "Función", "Respuesta"],
        ["/", "GET", "Dashboard principal", "HTML interface"],
        ["/health", "GET", "Estado del sistema", "JSON status"],
        ["/api/iq/balance", "GET", "Saldo actual", "JSON balance"],
        ["/api/iq/candles", "GET", "Velas M5", "JSON array"],
        ["/api/iq/trade", "POST", "Enviar orden", "JSON result"],
        ["/api/iq/login", "POST", "Autenticación", "JSON session"],
    ]
    
    urls_table = Table(urls_data, colWidths=[1.8*inch, 0.8*inch, 1.8*inch, 1.6*inch])
    urls_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#1f2937')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
    ]))
    
    story.append(urls_table)
    
    # === 9. REQUERIMIENTOS DEL SISTEMA ===
    story.append(PageBreak())
    story.append(Paragraph("9. 💻 REQUERIMIENTOS DEL SISTEMA", heading1_style))
    
    story.append(Paragraph("Sistema Operativo", heading2_style))
    
    os_data = [
        ["OS", "Versión Mínima", "Recomendado", "Notas"],
        ["Windows", "Windows 10", "Windows 11", "Tested y optimizado"],
        ["Linux", "Ubuntu 18.04+", "Ubuntu 22.04", "Compatible"],
        ["macOS", "macOS 10.14+", "macOS 12+", "Compatible"],
    ]
    
    os_table = Table(os_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 2.5*inch])
    os_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#0891b2')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
    ]))
    
    story.append(os_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Hardware", heading2_style))
    
    hw_data = [
        ["Componente", "Mínimo", "Recomendado", "Observaciones"],
        ["CPU", "Dual Core 2.0 GHz", "Quad Core 3.0 GHz", "Para múltiples procesos"],
        ["RAM", "4 GB", "8 GB", "Python + Flask + Chrome"],
        ["Disco", "2 GB libres", "5 GB libres", "Logs y cache"],
        ["Red", "Banda ancha", "Fibra óptica", "Latencia crítica trading"],
    ]
    
    hw_table = Table(hw_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 2.5*inch])
    hw_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#7c2d12')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
    ]))
    
    story.append(hw_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Software Base", heading2_style))
    
    sw_data = [
        ["Software", "Versión", "Propósito", "Instalación"],
        ["Python", "3.9+", "Runtime principal", "python.org"],
        ["Navegador Web", "Chrome 90+", "Interface dashboard", "Pre-instalado"],
        ["Terminal/CMD", "Nativo", "Ejecutar scripts", "Sistema"],
    ]
    
    sw_table = Table(sw_data, colWidths=[1.5*inch, 1.2*inch, 2*inch, 2.3*inch])
    sw_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#15803d')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
    ]))
    
    story.append(sw_table)
    
    # === 10. GUÍA DE INSTALACIÓN ===
    story.append(PageBreak())
    story.append(Paragraph("10. 🔧 GUÍA DE INSTALACIÓN", heading1_style))
    
    story.append(Paragraph("Paso 1: Instalación de Python", heading2_style))
    story.append(Paragraph("""
    1. Descargar Python 3.9+ desde <b>python.org</b><br/>
    2. Ejecutar instalador y marcar "Add to PATH"<br/>
    3. Verificar: abrir CMD y escribir <b>python --version</b><br/>
    4. Debe mostrar: Python 3.9.x o superior
    """, body_style))
    
    story.append(Paragraph("Paso 2: Descargar Sistema STC", heading2_style))
    story.append(Paragraph("""
    1. Extraer archivos en <b>C:\\STC_Trading_System</b><br/>
    2. Abrir CMD como Administrador<br/>
    3. Navegar: <b>cd C:\\STC_Trading_System</b><br/>
    4. Verificar archivos: <b>dir</b> (debe mostrar iq_client.py, etc.)
    """, body_style))
    
    story.append(Paragraph("Paso 3: Crear Entorno Virtual", heading2_style))
    install_commands = """
cd C:\\STC_Trading_System
python -m venv .venv311
.venv311\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
    """
    story.append(Paragraph(install_commands, code_style))
    
    story.append(Paragraph("Paso 4: Configurar Variables", heading2_style))
    story.append(Paragraph("""
    1. Abrir archivo <b>.env</b> con Notepad<br/>
    2. Configurar símbolos OTC (ya preconfigurado)<br/>
    3. Ajustar timeouts si es necesario<br/>
    4. Guardar cambios
    """, body_style))
    
    story.append(Paragraph("Paso 5: Primer Arranque", heading2_style))
    startup_commands = """
cd C:\\STC_Trading_System
start_dashboard_pro.bat
    """
    story.append(Paragraph(startup_commands, code_style))
    
    story.append(Paragraph("Verificación de Instalación", heading3_style))
    story.append(Paragraph("""
    ✅ Abrir navegador en <b>http://localhost:5001</b><br/>
    ✅ Ver dashboard con interface moderna<br/>
    ✅ Verificar que muestra "Sistema iniciando..."<br/>
    ✅ No debe haber errores en ventanas de CMD
    """, body_style))
    
    # === 11. CONFIGURACIÓN Y SETUP ===
    story.append(PageBreak())
    story.append(Paragraph("11. ⚙️ CONFIGURACIÓN Y SETUP", heading1_style))
    
    story.append(Paragraph("Paquetes Python Requeridos", heading2_style))
    
    packages_data = [
        ["Paquete", "Versión", "Propósito", "Crítico"],
        ["Flask", "2.3.x", "Servidor web framework", "Sí"],
        ["iqoptionapi", "6.8.9.1", "Conexión IQ Option", "Sí"],
        ["requests", "2.31.x", "HTTP client", "Sí"],
        ["httpx", "0.24.x", "Async HTTP client", "Sí"],
        ["python-dotenv", "1.0.x", "Variables entorno", "Sí"],
        ["reportlab", "4.0.x", "Generación PDF", "No"],
    ]
    
    packages_table = Table(packages_data, colWidths=[1.8*inch, 1*inch, 2*inch, 1.2*inch])
    packages_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#b91c1c')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(packages_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Archivo requirements.txt", heading3_style))
    requirements_content = """
Flask==2.3.3
iqoptionapi==6.8.9.1
requests==2.31.0
httpx==0.24.1
python-dotenv==1.0.0
reportlab==4.0.4
    """
    story.append(Paragraph(requirements_content, code_style))
    
    story.append(Paragraph("Variables de Entorno (.env)", heading2_style))
    
    env_data = [
        ["Variable", "Valor Por Defecto", "Descripción"],
        ["IQ_SYMBOLS", "EURUSD-OTC,GBPUSD-OTC,...", "Símbolos para trading"],
        ["MAX_BUFFER_SIZE", "2000", "Tamaño cache velas"],
        ["FRONTEND_CLOSED_LIMIT", "300", "Límite velas dashboard"],
        ["ACTIVE_SOURCE", "iq", "Fuente de datos principal"],
    ]
    
    env_table = Table(env_data, colWidths=[2*inch, 2.2*inch, 2.8*inch])
    env_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#059669')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
    ]))
    
    story.append(env_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Configuración de Red", heading2_style))
    story.append(Paragraph("""
    • <b>Puertos locales:</b> 5001 y 5002 deben estar libres<br/>
    • <b>Firewall:</b> Permitir conexiones locales Python<br/>
    • <b>Antivirus:</b> Excluir carpeta STC_Trading_System<br/>
    • <b>Internet:</b> Conexión estable para IQ Option API
    """, body_style))
    
    # === 12. TROUBLESHOOTING ===
    story.append(PageBreak())
    story.append(Paragraph("12. 🔍 TROUBLESHOOTING Y SOLUCIÓN DE PROBLEMAS", heading1_style))
    
    story.append(Paragraph("Problemas Comunes", heading2_style))
    
    troubleshooting_data = [
        ["Problema", "Causa", "Solución"],
        ["Puerto ocupado", "Otro proceso usa 5001/5002", "taskkill /f /im python.exe"],
        ["Gráficos no cargan", "LightweightCharts no disponible", "Refrescar navegador (Ctrl+F5)"],
        ["IQ no conecta", "Credenciales incorrectas", "Verificar email/password"],
        ["Velas no actualizan", "Cliente IQ desconectado", "Reiniciar iq_client.py"],
        ["Órdenes fallan", "Mercado cerrado", "Usar símbolos OTC únicamente"],
        ["Dashboard no abre", "Servidor no iniciado", "Ejecutar start_dashboard_pro.bat"],
    ]
    
    troubleshooting_table = Table(troubleshooting_data, colWidths=[2.2*inch, 2.2*inch, 2.6*inch])
    troubleshooting_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor('#dc2626')),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    
    story.append(troubleshooting_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Comandos de Diagnóstico", heading2_style))
    diagnostic_commands = """
# Verificar Python instalado
python --version

# Verificar puertos ocupados
netstat -an | findstr "5001\\|5002"

# Verificar procesos Python
tasklist | findstr python

# Probar conectividad API
curl http://localhost:5002/health

# Probar dashboard
curl http://localhost:5001/health

# Reinicio completo sistema
cd C:\\STC_Trading_System
start_dashboard_pro.bat
    """
    story.append(Paragraph(diagnostic_commands, code_style))
    
    story.append(Paragraph("Logs y Debugging", heading2_style))
    story.append(Paragraph("""
    • <b>Logs del sistema:</b> Se muestran en ventanas CMD abiertas<br/>
    • <b>Logs del navegador:</b> F12 → Console para errores JavaScript<br/>
    • <b>Archivos de log:</b> Carpeta logs/ (se crean automáticamente)<br/>
    • <b>Nivel de detalle:</b> INFO por defecto, cambiar a DEBUG si necesario
    """, body_style))
    
    story.append(Paragraph("Contacto y Soporte", heading2_style))
    story.append(Paragraph("""
    • <b>Documentación:</b> Archivos README.md en el proyecto<br/>
    • <b>Logs detallados:</b> Activar DEBUG en archivos Python<br/>
    • <b>Backup dashboard:</b> http://localhost:5001/dashboard_old<br/>
    • <b>Reset completo:</b> Eliminar .venv311 y reinstalar
    """, body_style))
    
    # === PIE DE PÁGINA ===
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("─" * 80, styles['Normal']))
    story.append(Paragraph(f"""
    <b>Sistema STC Trading - Documentación Completa</b><br/>
    Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}<br/>
    Versión: Dashboard Pro v1.0<br/>
    Plataforma: Windows / Linux / macOS Compatible
    """, styles['Normal']))
    
    # Generar PDF
    print("📄 Generando documentación PDF...")
    doc.build(story)
    print("✅ PDF generado: STC_Trading_Sistema_Completo.pdf")
    return "STC_Trading_Sistema_Completo.pdf"

if __name__ == "__main__":
    try:
        pdf_file = create_stc_documentation_pdf()
        print(f"🎉 Documentación completa generada en: {pdf_file}")
        print("📖 El archivo PDF contiene:")
        print("   • Arquitectura del sistema")
        print("   • Flujos de datos completos")
        print("   • Diccionario de archivos")
        print("   • Guía de instalación")
        print("   • Requerimientos de sistema")
        print("   • Troubleshooting")
    except Exception as e:
        print(f"❌ Error generando PDF: {e}")
        print("💡 Instalar ReportLab: pip install reportlab")
