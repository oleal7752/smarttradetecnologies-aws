/**
 * API Client - Servicio para comunicación con el backend
 */

export class APIClient {
  constructor(baseURL = '') {
    this.baseURL = baseURL;
  }

  async getCandles(symbol, timeframe, limit = 40) {
    try {
      const response = await fetch(
        `${this.baseURL}/api/public/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&limit=${limit}&source=twelvedata`
      );
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      return { success: true, data };
    } catch (error) {
      console.error('Error fetching candles:', error);
      return { success: false, error: error.message };
    }
  }

  async getServerTime() {
    try {
      const response = await fetch(`${this.baseURL}/api/server_time`);
      if (!response.ok) throw new Error('Failed to get server time');
      const data = await response.json();
      return { success: true, data };
    } catch (error) {
      console.error('Error fetching server time:', error);
      return { success: false, error: error.message };
    }
  }
}

export default new APIClient();
