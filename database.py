import os
import enum
import logging
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, JSON, Text, ForeignKey, Enum, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
from datetime import datetime, timedelta
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable no configurada")

engine = create_engine(
    DATABASE_URL,
    pool_recycle=300,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()


# ===================== ENUMS =====================

class BrokerType(enum.Enum):
    """Tipos de broker soportados"""
    EXNOVA = "exnova"
    IQOPTION = "iqoption"
    OLYMPTRADE = "olymptrade"
    QUOTEX = "quotex"


class SubscriptionPlan(enum.Enum):
    """Planes de suscripción disponibles"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    BIANNUAL = "biannual"
    ANNUAL = "annual"


class SubscriptionStatus(enum.Enum):
    """Estados de suscripción"""
    PENDING_VALIDATION = "pending_validation"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ValidationStatus(enum.Enum):
    """Estados de validación"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PromoCodeType(enum.Enum):
    """Tipos de códigos promocionales"""
    REVENDEDOR = "revendedor"
    AGENTE = "agente"
    CORTESIA = "cortesia"


# ===================== CONTEXT MANAGER =====================

@contextmanager
def get_db():
    """Context manager para sesiones de base de datos"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ===================== MODELOS DE USUARIOS =====================

class User(Base):
    """Modelo de Usuario"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    
    # Datos personales
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    dni = Column(String, nullable=False, unique=True)
    birth_date = Column(DateTime, nullable=False)
    phone = Column(String, nullable=False)
    country = Column(String, nullable=False)
    
    # Verificación
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String, nullable=True)
    email_verification_sent_at = Column(DateTime, nullable=True)
    
    # Cuenta
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relaciones
    broker_accounts = relationship("BrokerAccount", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    bots = relationship("Bot", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    promo_codes = relationship("PromoCode", foreign_keys="[PromoCode.assigned_to]", back_populates="user", cascade="all, delete-orphan")
    
    def set_password(self, password):
        """Hashea y guarda la contraseña"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica la contraseña"""
        return check_password_hash(self.password_hash, password)
    
    def is_adult(self):
        """Verifica si el usuario es mayor de 18 años"""
        today = datetime.utcnow()
        age = today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return age >= 18


class BrokerAccount(Base):
    """Modelo de Cuenta de Broker"""
    __tablename__ = "broker_accounts"
    __table_args__ = (
        Index('idx_user_broker', 'user_id', 'broker_type', unique=True),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    broker_type = Column(Enum(BrokerType), nullable=False)
    broker_account_id = Column(String, nullable=False)
    
    validation_status = Column(Enum(ValidationStatus), default=ValidationStatus.PENDING)
    validated_at = Column(DateTime, nullable=True)
    validated_by_admin = Column(String, nullable=True)
    validation_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    user = relationship("User", back_populates="broker_accounts")


class Subscription(Base):
    """Modelo de Suscripción"""
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index('idx_user_status', 'user_id', 'status'),
    )
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    plan = Column(Enum(SubscriptionPlan), nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.PENDING_VALIDATION)
    
    # Bots disponibles (JSON array de strategy names)
    available_bots = Column(JSON, nullable=False)
    
    # Fechas
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True, index=True)
    
    # Precio
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    user = relationship("User", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription", cascade="all, delete-orphan")
    
    @staticmethod
    def get_plan_price(plan):
        """Obtiene el precio del plan"""
        prices = {
            SubscriptionPlan.MONTHLY: 200.0,
            SubscriptionPlan.QUARTERLY: 500.0,
            SubscriptionPlan.BIANNUAL: 999.0,
            SubscriptionPlan.ANNUAL: 1999.0
        }
        return prices.get(plan, 0.0)
    
    @staticmethod
    def get_plan_duration_days(plan):
        """Obtiene la duración del plan en días"""
        durations = {
            SubscriptionPlan.MONTHLY: 30,
            SubscriptionPlan.QUARTERLY: 90,
            SubscriptionPlan.BIANNUAL: 180,
            SubscriptionPlan.ANNUAL: 365
        }
        return durations.get(plan, 0)
    
    def get_days_remaining(self):
        """Calcula los días restantes de la suscripción"""
        if not self.end_date:
            return 0
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)
    
    def is_expiring_soon(self, days=7):
        """Verifica si la suscripción está por expirar"""
        return 0 < self.get_days_remaining() <= days


class Payment(Base):
    """Modelo de Pago"""
    __tablename__ = "payments"
    
    id = Column(String, primary_key=True)
    subscription_id = Column(String, ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    
    payment_method = Column(String, nullable=True)
    payment_status = Column(String, default="pending")
    transaction_id = Column(String, nullable=True)
    
    invoice_number = Column(String, unique=True, nullable=True)
    invoice_sent = Column(Boolean, default=False)
    invoice_sent_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relaciones
    subscription = relationship("Subscription", back_populates="payments")
    user = relationship("User", back_populates="payments")


class PromoCode(Base):
    """Modelo de Códigos Promocionales"""
    __tablename__ = "promo_codes"
    
    id = Column(String, primary_key=True)
    code = Column(String, unique=True, nullable=False, index=True)
    type = Column(Enum(PromoCodeType), nullable=False)
    
    # Duración y expiración
    duration_hours = Column(Integer, nullable=False)
    activated_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Asignación
    created_by = Column(String, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    assigned_to = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    
    # Estado
    is_active = Column(Boolean, default=True)
    is_used = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relaciones
    creator = relationship("User", foreign_keys=[created_by])
    user = relationship("User", foreign_keys=[assigned_to], back_populates="promo_codes")


class PasswordReset(Base):
    """Modelo de Recuperación de Contraseña"""
    __tablename__ = "password_resets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    """Modelo de Notificaciones"""
    __tablename__ = "notifications"
    __table_args__ = (
        Index('idx_user_read', 'user_id', 'read'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String, nullable=False)
    
    read = Column(Boolean, default=False)
    sent_via_email = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relaciones
    user = relationship("User", back_populates="notifications")


class BotStrategy(Base):
    """Modelo de Estrategias de Bot Disponibles"""
    __tablename__ = "bot_strategies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Métricas de rendimiento
    avg_win_rate = Column(Float, default=0.0)
    total_profit = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ===================== MODELOS DE BOTS (ACTUALIZADO) =====================

class Bot(Base):
    """Modelo de Bot - Configuración y estado"""
    __tablename__ = "bots"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    name = Column(String, nullable=False)
    strategy_name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    timeframe = Column(String, nullable=False)
    trade_amount = Column(Float, default=5.0)
    trade_duration = Column(Integer, default=5)
    max_daily_loss = Column(Float, default=100.0)
    max_daily_trades = Column(Integer, default=50)
    active = Column(Boolean, default=False, index=True)
    auto_restart = Column(Boolean, default=True)
    use_dual_gale = Column(Boolean, default=False)
    
    gale_level = Column(Integer, default=0)
    last_direction = Column(String, nullable=True)
    pending_trade = Column(JSON, nullable=True)
    last_candle_time = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    user = relationship("User", back_populates="bots")


class BotStat(Base):
    """Modelo de Estadísticas de Bot"""
    __tablename__ = "bot_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_id = Column(String, nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    daily_profit = Column(Float, default=0.0)
    total_profit = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    trades_today = Column(Integer, default=0)
    last_trade_time = Column(Integer, default=0)
    status = Column(String, default='stopped')
    error_message = Column(Text, nullable=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Trade(Base):
    """Modelo de Trade - Historial de operaciones"""
    __tablename__ = "trades"
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_id = Column(String, nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    
    direction = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    gale_level = Column(Integer, default=0)
    entry_time = Column(Integer, nullable=False)
    expiry_time = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    
    result = Column(String, nullable=True)
    profit = Column(Float, default=0.0)
    
    symbol = Column(String, nullable=False)
    timeframe = Column(String, nullable=False)
    strategy_name = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class BacktestRun(Base):
    """Modelo de Ejecución de Backtest - Almacena resultados generales"""
    __tablename__ = "backtest_runs"
    __table_args__ = (
        Index('idx_user_strategy_symbol', 'user_id', 'strategy_name', 'symbol'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Información del backtest
    strategy_name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    timeframe = Column(String, nullable=False)
    
    # Parámetros
    initial_balance = Column(Float, nullable=False)
    trade_amount = Column(Float, nullable=False)
    payout_percent = Column(Float, nullable=False)
    trade_duration = Column(Integer, nullable=False)
    
    # Período analizado
    start_time = Column(Integer, nullable=False)
    end_time = Column(Integer, nullable=False)
    
    # Resultados generales
    final_balance = Column(Float, nullable=False)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    draw_trades = Column(Integer, default=0)
    
    # Métricas de rendimiento
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    net_profit = Column(Float, default=0.0)
    return_percent = Column(Float, default=0.0)
    
    # Métricas de ganancia/pérdida
    total_profit = Column(Float, default=0.0)
    total_loss = Column(Float, default=0.0)
    gross_profit = Column(Float, default=0.0)
    gross_loss = Column(Float, default=0.0)
    average_win = Column(Float, default=0.0)
    average_loss = Column(Float, default=0.0)
    largest_win = Column(Float, default=0.0)
    largest_loss = Column(Float, default=0.0)
    
    # Métricas de riesgo
    max_drawdown = Column(Float, default=0.0)
    max_drawdown_percent = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    
    # Rachas
    max_consecutive_wins = Column(Integer, default=0)
    max_consecutive_losses = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    user = relationship("User", backref="backtest_runs")


class BacktestTrade(Base):
    """Modelo de Trade de Backtest - Trades individuales del backtest"""
    __tablename__ = "backtest_trades"
    __table_args__ = (
        Index('idx_backtest_entry', 'backtest_run_id', 'entry_time'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    backtest_run_id = Column(Integer, ForeignKey('backtest_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Información del trade
    trade_id = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    duration = Column(Integer, nullable=False)
    
    # Precios y tiempos
    entry_price = Column(Float, nullable=False)
    entry_time = Column(Integer, nullable=False)
    exit_price = Column(Float, nullable=True)
    exit_time = Column(Integer, nullable=True)
    
    # Resultado
    result = Column(String, nullable=True)
    profit = Column(Float, default=0.0)
    
    strategy_name = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    backtest_run = relationship("BacktestRun", backref="trades")


class BacktestEquityPoint(Base):
    """Modelo de Punto de Equity - Puntos de la curva de equity para gráficos"""
    __tablename__ = "backtest_equity_points"
    __table_args__ = (
        Index('idx_backtest_point', 'backtest_run_id', 'point_index'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    backtest_run_id = Column(Integer, ForeignKey('backtest_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    
    point_index = Column(Integer, nullable=False)
    balance = Column(Float, nullable=False)
    timestamp = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    backtest_run = relationship("BacktestRun", backref="equity_points")


# ===================== BACKTESTS MAESTROS =====================

class BacktestMasterRun(Base):
    """Backtest Maestro - Generado por admin, consultado por todos los usuarios"""
    __tablename__ = "backtest_master_runs"
    __table_args__ = (
        Index('idx_master_strategy_symbol', 'strategy_name', 'symbol', 'version'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Información del backtest
    strategy_name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    timeframe = Column(String, nullable=False)
    version = Column(String, default="v1.0")
    
    # Período analizado
    start_time = Column(Integer, nullable=False)
    end_time = Column(Integer, nullable=False)
    total_candles = Column(Integer, default=0)
    
    # Métricas base (con monto de referencia $100)
    reference_amount = Column(Float, default=100.0)
    reference_payout = Column(Float, default=85.0)
    
    # Estadísticas de señales
    total_signals = Column(Integer, default=0)
    winning_signals = Column(Integer, default=0)
    losing_signals = Column(Integer, default=0)
    draw_signals = Column(Integer, default=0)
    
    # Win rate (independiente del monto)
    win_rate = Column(Float, default=0.0)
    
    # Rachas
    max_consecutive_wins = Column(Integer, default=0)
    max_consecutive_losses = Column(Integer, default=0)
    
    # Metadata
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    signals = relationship("BacktestMasterSignal", back_populates="master_run", cascade="all, delete-orphan")


class BacktestMasterSignal(Base):
    """Señal individual de backtest maestro - Solo guarda WIN/LOSS sin monto"""
    __tablename__ = "backtest_master_signals"
    __table_args__ = (
        Index('idx_master_signal_time', 'master_run_id', 'signal_time'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    master_run_id = Column(Integer, ForeignKey('backtest_master_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Información de la señal
    signal_index = Column(Integer, nullable=False)
    signal_time = Column(Integer, nullable=False)
    direction = Column(String, nullable=False)
    
    # Precios (para análisis)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    
    # Resultado (WIN/LOSS/DRAW) - Sin monto para recalcular dinámicamente
    result = Column(String, nullable=False)
    
    # Indicadores adicionales (opcional)
    confidence = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    master_run = relationship("BacktestMasterRun", back_populates="signals")


# ===================== BOT DE SEÑALES =====================

class TradingPair(Base):
    """Modelo de Pares de Trading - Símbolos disponibles en el sistema"""
    __tablename__ = "trading_pairs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, unique=True, nullable=False, index=True)  # EURUSD, GBPUSD, etc.
    name = Column(String, nullable=False)  # EUR/USD, GBP/USD, etc.
    is_active = Column(Boolean, default=True, index=True)
    
    # Metadata
    description = Column(String, nullable=True)
    display_order = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    signal_configs = relationship("SignalBotSelectedPair", back_populates="trading_pair", cascade="all, delete-orphan")


class SignalBotConfig(Base):
    """Modelo de Configuración del Bot de Señales - Por usuario o global"""
    __tablename__ = "signal_bot_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=True, index=True)
    
    # Estado del bot
    scanning_active = Column(Boolean, default=False, index=True)
    
    # Configuración Martingale
    max_gales = Column(Integer, default=7)
    initial_stake = Column(Float, default=10.0)
    multiplier = Column(Float, default=2.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_started_at = Column(DateTime, nullable=True)
    last_stopped_at = Column(DateTime, nullable=True)
    
    # Relaciones
    selected_pairs = relationship("SignalBotSelectedPair", back_populates="bot_config", cascade="all, delete-orphan")


class SignalBotSelectedPair(Base):
    """Modelo de Relación: Pares seleccionados para un bot de señales"""
    __tablename__ = "signal_bot_selected_pairs"
    __table_args__ = (
        Index('idx_config_pair', 'config_id', 'pair_id'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(Integer, ForeignKey('signal_bot_configs.id', ondelete='CASCADE'), nullable=False, index=True)
    pair_id = Column(Integer, ForeignKey('trading_pairs.id', ondelete='CASCADE'), nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    bot_config = relationship("SignalBotConfig", back_populates="selected_pairs")
    trading_pair = relationship("TradingPair", back_populates="signal_configs")


# ===================== FUNCIONES =====================

def init_db():
    """Inicializa la base de datos creando todas las tablas"""
    Base.metadata.create_all(bind=engine)
    logger.info("Base de datos inicializada correctamente")


def drop_all_tables():
    """CUIDADO: Elimina todas las tablas"""
    Base.metadata.drop_all(bind=engine)
    logger.info("Todas las tablas eliminadas")


if __name__ == "__main__":
    logger.info("Inicializando base de datos...")
    init_db()
    logger.info("Listo!")
