/**
 * Info Panel Component - Panel de información del dashboard
 */

export class InfoPanel {
  constructor(containerId, state) {
    this.container = document.getElementById(containerId);
    this.state = state;
    this.init();
  }

  init() {
    this.state.subscribe('symbol', () => this.render());
    this.state.subscribe('timeframe', () => this.render());
    this.state.subscribe('dataSource', () => this.render());
    this.state.subscribe('lastUpdate', () => this.render());
    this.render();
  }

  render() {
    const state = this.state.getState();
    const lastUpdateText = state.lastUpdate 
      ? new Date(state.lastUpdate).toLocaleTimeString('es-ES')
      : '-';

    this.container.innerHTML = `
      <div class="info-panel-title">📊 Información</div>
      <div class="info-panel-content">
        <div class="info-row">
          <span class="info-label">Símbolo</span>
          <span class="info-value text-primary">${state.symbol}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Timeframe</span>
          <span class="info-value">${state.timeframe}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Fuente</span>
          <span class="info-value text-success">${state.dataSource}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Última actualización</span>
          <span class="info-value text-dim">${lastUpdateText}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Velas cargadas</span>
          <span class="info-value">${state.candles.length}</span>
        </div>
      </div>
    `;
  }
}
