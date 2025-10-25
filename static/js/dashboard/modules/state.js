/**
 * State Manager - Manejador de estado global simple
 */

class StateManager {
  constructor() {
    this.state = {
      symbol: 'EURUSD',
      timeframe: 'M5',
      candles: [],
      lastUpdate: null,
      isLoading: false,
      error: null,
      dataSource: 'Twelve Data'
    };
    
    this.listeners = new Map();
  }

  getState() {
    return { ...this.state };
  }

  setState(updates) {
    const oldState = { ...this.state };
    this.state = { ...this.state, ...updates };
    
    Object.keys(updates).forEach(key => {
      if (this.listeners.has(key)) {
        this.listeners.get(key).forEach(callback => {
          callback(this.state[key], oldState[key]);
        });
      }
    });
  }

  subscribe(key, callback) {
    if (!this.listeners.has(key)) {
      this.listeners.set(key, new Set());
    }
    this.listeners.get(key).add(callback);
    
    return () => {
      this.listeners.get(key).delete(callback);
    };
  }

  updateCandles(newCandles) {
    this.setState({
      candles: newCandles,
      lastUpdate: Date.now(),
      isLoading: false,
      error: null
    });
  }

  setLoading(isLoading) {
    this.setState({ isLoading });
  }

  setError(error) {
    this.setState({ error, isLoading: false });
  }

  changeSymbol(symbol) {
    this.setState({ symbol, candles: [], isLoading: true });
  }

  changeTimeframe(timeframe) {
    this.setState({ timeframe, candles: [], isLoading: true });
  }
}

export default new StateManager();
