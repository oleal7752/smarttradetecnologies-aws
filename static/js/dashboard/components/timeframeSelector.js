/**
 * Timeframe Selector Component - Selector de temporalidad
 */

export class TimeframeSelector {
  constructor(containerId, state, onTimeframeChange) {
    this.container = document.getElementById(containerId);
    this.state = state;
    this.onTimeframeChange = onTimeframeChange;
    this.timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'];
    this.init();
  }

  init() {
    this.render();
    this.state.subscribe('timeframe', () => this.render());
  }

  render() {
    const currentTimeframe = this.state.getState().timeframe;
    
    this.container.innerHTML = `
      <div class="info-panel-title">⏱️ Temporalidad</div>
      <div class="timeframe-grid">
        ${this.timeframes.map(tf => `
          <button 
            class="btn timeframe-button ${tf === currentTimeframe ? 'active' : ''}" 
            data-timeframe="${tf}"
          >
            ${tf}
          </button>
        `).join('')}
      </div>
    `;

    this.container.querySelectorAll('.timeframe-button').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const timeframe = e.target.dataset.timeframe;
        if (timeframe !== currentTimeframe) {
          this.onTimeframeChange(timeframe);
        }
      });
    });
  }
}
