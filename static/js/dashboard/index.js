/**
 * STC Trading Dashboard - Punto de entrada principal
 * Dashboard moderno con arquitectura limpia y modular
 */

import state from './modules/state.js';
import apiClient from './services/apiClient.js';
import { ChartManager } from './modules/chart.js';
import { InfoPanel } from './components/infoPanel.js';
import { SymbolSelector } from './components/symbolSelector.js';
import { TimeframeSelector } from './components/timeframeSelector.js';
import { CountdownTimer } from './components/countdownTimer.js';

class Dashboard {
  constructor() {
    this.chart = null;
    this.pollIntervalId = null;
    this.components = {};
  }

  async init() {
    console.log('🚀 Initializing STC Trading Dashboard...');
    
    // Inicializar gráfico
    this.chart = new ChartManager('tradingview-chart');
    this.chart.init();
    
    // Inicializar componentes
    this.components.infoPanel = new InfoPanel('info-panel', state);
    this.components.symbolSelector = new SymbolSelector('symbol-selector', state, (symbol) => this.handleSymbolChange(symbol));
    this.components.timeframeSelector = new TimeframeSelector('timeframe-selector', state, (timeframe) => this.handleTimeframeChange(timeframe));
    this.components.countdownTimer = new CountdownTimer('countdown-panel', state);
    
    // Suscribirse a cambios de velas
    state.subscribe('candles', (candles) => {
      if (candles && candles.length > 0) {
        this.chart.setCandles(candles);
      }
    });
    
    // Cargar datos iniciales
    await this.loadCandles();
    
    // Iniciar polling
    this.startPolling();
    
    console.log('✅ Dashboard initialized successfully');
  }

  async loadCandles() {
    const { symbol, timeframe } = state.getState();
    state.setLoading(true);
    
    console.log(`📊 Loading candles: ${symbol} ${timeframe}`);
    
    const result = await apiClient.getCandles(symbol, timeframe, 40);
    
    if (result.success) {
      state.updateCandles(result.data);
      console.log(`✅ Loaded ${result.data.length} candles`);
    } else {
      state.setError(result.error);
      console.error('❌ Failed to load candles:', result.error);
    }
  }

  async handleSymbolChange(symbol) {
    console.log(`🔄 Changing symbol to: ${symbol}`);
    state.changeSymbol(symbol);
    this.stopPolling();
    await this.loadCandles();
    this.startPolling();
  }

  async handleTimeframeChange(timeframe) {
    console.log(`🔄 Changing timeframe to: ${timeframe}`);
    state.changeTimeframe(timeframe);
    this.stopPolling();
    await this.loadCandles();
    this.startPolling();
  }

  startPolling() {
    if (this.pollIntervalId) return;
    
    this.pollIntervalId = setInterval(() => {
      this.loadCandles();
    }, 5000); // Actualizar cada 5 segundos
    
    console.log('▶️ Polling started (every 5s)');
  }

  stopPolling() {
    if (this.pollIntervalId) {
      clearInterval(this.pollIntervalId);
      this.pollIntervalId = null;
      console.log('⏹️ Polling stopped');
    }
  }

  destroy() {
    this.stopPolling();
    if (this.chart) {
      this.chart.destroy();
    }
    if (this.components.countdownTimer) {
      this.components.countdownTimer.destroy();
    }
  }
}

// Inicializar dashboard cuando el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
    window.dashboard.init();
  });
} else {
  window.dashboard = new Dashboard();
  window.dashboard.init();
}
