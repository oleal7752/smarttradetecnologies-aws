// TradingView Lightweight Charts - Configuración STC Trading
const CHART_CONFIG = {
    width: 0,
    height: 600,
    layout: {
        background: { type: 'solid', color: '#0f172a' },
        textColor: '#d6d3d1',
    },
    grid: {
        vertLines: { color: '#334155' },
        horzLines: { color: '#334155' },
    },
    crosshair: { mode: 1 },
    rightPriceScale: { borderColor: '#485563' },
    timeScale: { 
        borderColor: '#485563',
        timeVisible: true,
        secondsVisible: false,
    },
};

// Configuración para diferentes tipos de gráficos
const SERIES_CONFIG = {
    candlestick: {
        upColor: '#00ff88',
        downColor: '#ff4757',
        borderDownColor: '#ff4757',
        borderUpColor: '#00ff88',
        wickDownColor: '#ff4757',
        wickUpColor: '#00ff88',
    }
};

// Exportar configuraciones
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { CHART_CONFIG, SERIES_CONFIG };
}
