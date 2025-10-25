/**
 * STC Trading System - TradingView Lightweight Charts Integration
 * Adaptado para IQ Option con soporte completo de gráficos
 */

class STCChartManager {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.chart = null;
        this.candleSeries = null;
        this.volumeSeries = null;
        this.currentSymbol = 'EURUSD-OTC';
        this.isConnected = false;
        
        // Configuración por defecto
        this.config = {
            theme: 'dark',
            locale: 'es',
            layout: {
                background: { color: '#1e1e1e' },
                textColor: '#ffffff',
            },
            autoSize: true,
            watermark: 'STC Trading',
            ...options
        };
        
        this.initChart();
    }

    /**
     * Inicializar el gráfico TradingView
     */
    initChart() {
        if (!this.container) {
            console.error('Container not found:', this.containerId);
            return;
        }

        const chartOptions = {
            width: this.container.clientWidth,
            height: this.container.clientHeight,
            layout: {
                background: { 
                    type: LightweightCharts.ColorType.Solid,
                    color: this.config.theme === 'dark' ? '#1a1a1a' : '#ffffff'
                },
                textColor: this.config.theme === 'dark' ? '#ffffff' : '#000000',
            },
            grid: {
                vertLines: {
                    color: this.config.theme === 'dark' ? '#2a2a2a' : '#e0e0e0',
                },
                horzLines: {
                    color: this.config.theme === 'dark' ? '#2a2a2a' : '#e0e0e0',
                }
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
                vertLine: {
                    width: 1,
                    color: '#9598A1',
                    style: LightweightCharts.LineStyle.Dashed,
                },
                horzLine: {
                    width: 1,
                    color: '#9598A1',
                    style: LightweightCharts.LineStyle.Dashed,
                }
            },
            timeScale: {
                borderColor: '#485c7b',
                timeVisible: true,
                secondsVisible: false,
                barSpacing: 6,            // Velas más juntas (estilo broker)
                rightOffset: 3,           // Menos espacio derecho
            },
            watermark: {
                color: 'rgba(11, 94, 29, 0.4)',
                visible: true,
                text: 'STC Trading',
                fontSize: 24,
                horzAlign: 'left',
                vertAlign: 'bottom',
            },
        };

        // Crear el gráfico
        this.chart = LightweightCharts.createChart(this.container, chartOptions);
        
        // Crear serie de velas (ESTILO BROKER ORIGINAL - IQ Option)
        this.candleSeries = this.chart.addCandlestickSeries({
            upColor: '#00D09C',           // Verde sólido IQ Option
            downColor: '#FF5B5A',         // Rojo sólido IQ Option
            borderVisible: true,
            borderUpColor: '#00D09C',     // Borde verde
            borderDownColor: '#FF5B5A',   // Borde rojo
            wickVisible: true,
            wickUpColor: '#00D09C',       // Mecha verde
            wickDownColor: '#FF5B5A',     // Mecha roja
        });

        console.log('✅ Chart initialized successfully');
        this.isConnected = true;
    }

    /**
     * Actualizar datos del gráfico
     */
    updateData(symbol, timeframe = 'M5', limit = 200) {
        if (!this.chart || !this.candleSeries) {
            console.error('Chart not initialized');
            return;
        }

        const endpoint = `/api/public/candles?symbol=${symbol}&timeframe=${timeframe}&limit=${limit}&source=twelvedata`;
        
        fetch(endpoint)
            .then(response => response.json())
            .then(data => {
                if (data && Array.isArray(data) && data.length > 0) {
                    console.log(`📊 Received ${data.length} candles for ${symbol}`);
                    
                    // Limpiar datos previos
                    this.candleSeries.setData([]);
                    
                    // Formatear datos para TradingView
                    const formattedData = data
                        .filter(candle => {
                            // CRÍTICO: Validar ANTES de parseFloat para evitar NaN
                            const isValid = 
                                candle.time != null && candle.time > 0 &&
                                candle.open != null &&
                                candle.high != null &&
                                candle.low != null &&
                                candle.close != null;
                            
                            if (!isValid) {
                                console.warn('⚠️ Vela con valores null rechazada:', {
                                    time: candle.time,
                                    open: candle.open,
                                    high: candle.high,
                                    low: candle.low,
                                    close: candle.close
                                });
                            }
                            return isValid;
                        })
                        .map(candle => ({
                            time: Math.floor(candle.time / 1000), // Convertir a segundos
                            open: parseFloat(candle.open),
                            high: parseFloat(candle.high),
                            low: parseFloat(candle.low),
                            close: parseFloat(candle.close)
                        }));

                    // Ordenar por tiempo (ascendente)
                    formattedData.sort((a, b) => a.time - b.time);
                    
                    // Cargar todas las velas
                    this.candleSeries.setData(formattedData);
                    
                    console.log(`✅ Chart updated with ${formattedData.length} candles`);
                    
                    // Ajustar vista para mostrar todas las velas
                    this.chart.timeScale().fitContent();
                    
                } else {
                    console.warn('No data received or invalid format');
                }
            })
            .catch(error => {
                console.error('Error fetching candles:', error);
            });
    }

    /**
     * Cambiar símbolo
     */
    changeSymbol(symbol) {
        this.currentSymbol = symbol;
        this.updateData(symbol);
    }

    /**
     * Actualización automática cada 5 segundos
     */
    startAutoUpdate() {
        setInterval(() => {
            this.updateData(this.currentSymbol);
        }, 5000);
    }
}

// Variable global para el chart manager
window.STCChartManager = STCChartManager;