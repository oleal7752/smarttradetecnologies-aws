/**
 * Symbol Selector Component - Selector de símbolos
 */

export class SymbolSelector {
  constructor(containerId, state, onSymbolChange) {
    this.container = document.getElementById(containerId);
    this.state = state;
    this.onSymbolChange = onSymbolChange;
    this.symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD'];
    this.init();
  }

  init() {
    this.render();
    this.state.subscribe('symbol', () => this.render());
  }

  render() {
    const currentSymbol = this.state.getState().symbol;
    
    this.container.innerHTML = `
      <div class="info-panel-title">💱 Símbolo</div>
      <div class="symbol-grid">
        ${this.symbols.map(symbol => `
          <button 
            class="btn symbol-button ${symbol === currentSymbol ? 'active' : ''}" 
            data-symbol="${symbol}"
          >
            ${symbol}
          </button>
        `).join('')}
      </div>
    `;

    this.container.querySelectorAll('.symbol-button').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const symbol = e.target.dataset.symbol;
        if (symbol !== currentSymbol) {
          this.onSymbolChange(symbol);
        }
      });
    });
  }
}
