/**
 * STC Trading System - TradingView LightWeight Charts Integration
 * Adaptador para IQ Option con soporte completo de gráficos
 */

window.STCChartFix = (function() {
    
    let chart = null;
    let candleSeries = null;
    let config = {};
    let intervalId = null;
    let realtimeIntervalId = null; // Intervalo para vela actual en tiempo real
    let lastCandles = []; // Guardar últimas velas para comparar
    let isInitialLoad = true; // Flag para carga inicial
    let isLoggedIn = false; // Flag para saber si hay conexión a IQ Option
    let signalMarkers = []; // Almacenar marcadores de señales
    let signalsPollingId = null; // Intervalo para polling de señales
    let currentBotId = null; // ID del bot activo

    /**
     * Inicializar el sistema de gráficos
     */
    function init(options = {}) {
        config = {
            containerId: 'chart',
            endpoint: '/api/public/candles?symbol=EURUSD&timeframe=M5&limit=80&source=twelvedata',
            timeframe: 'M5',
            pollMs: 2000,  // Actualizar cada 2 segundos para velas tick a tick
            max: 80,
            ...options
        };

        console.log('🎯 Inicializando STCChartFix con config:', config);
        
        initChart();
        loadInitialData();
        startPolling();
    }

    /**
     * Crear el gráfico con LightweightCharts
     */
    function initChart() {
        const container = document.getElementById(config.containerId);
        if (!container) {
            console.error('❌ Container no encontrado:', config.containerId);
            return;
        }

        // Crear gráfico
        chart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: container.clientHeight || 400,
            layout: {
                background: { type: 'solid', color: '#131722' },
                textColor: '#d1d4dc',
            },
            grid: {
                vertLines: { color: '#1f2937' },
                horzLines: { color: '#1f2937' },
            },
            rightPriceScale: {
                borderColor: '#1f2937',
                autoScale: true,
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.1,
                },
            },
            timeScale: {
                borderColor: '#1f2937',
                timeVisible: true,
                secondsVisible: false,
                rightOffset: 5,
                barSpacing: 8,
                fixLeftEdge: false,
                fixRightEdge: false,
                lockVisibleTimeRangeOnResize: true,
                rightBarStaysOnScroll: true,
                allowBoldLabels: true,
                visible: true,
                borderVisible: true,
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
            },
        });

        // Crear serie de velas (ESTILO BROKER ORIGINAL - IQ Option)
        candleSeries = chart.addCandlestickSeries({
            upColor: '#00D09C',           // Verde sólido IQ Option
            downColor: '#FF5B5A',         // Rojo sólido IQ Option
            borderVisible: true,
            borderUpColor: '#00D09C',     // Borde verde
            borderDownColor: '#FF5B5A',   // Borde rojo
            wickVisible: true,
            wickUpColor: '#00D09C',       // Mecha verde
            wickDownColor: '#FF5B5A',     // Mecha roja
        });

        // Auto-resize
        new ResizeObserver(entries => {
            if (entries.length === 0 || entries[0].target !== container) return;
            const newRect = entries[0].contentRect;
            chart.applyOptions({ 
                width: newRect.width, 
                height: newRect.height 
            });
        }).observe(container);

        console.log('✅ Gráfico LightweightCharts inicializado');
    }

    /**
     * Cargar datos iniciales
     */
    async function loadInitialData() {
        try {
            console.log('📊 Cargando datos iniciales desde:', config.endpoint);
            
            const response = await fetch(config.endpoint);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('📈 Datos recibidos:', data);
            
            if (Array.isArray(data) && data.length > 0) {
                updateChart(data);
                console.log(`✅ Cargadas ${data.length} velas iniciales`);
            } else {
                console.warn('⚠️ No hay datos de velas disponibles');
            }
            
        } catch (error) {
            console.error('❌ Error cargando datos iniciales:', error);
        }
    }

    /**
     * Actualizar el gráfico con velas
     */
    function updateChart(candles) {
        if (!candleSeries || !Array.isArray(candles)) {
            console.warn('⚠️ Serie no inicializada o datos inválidos');
            return;
        }

        try {
            // Preparar datos para el gráfico
            const chartData = candles
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
                    time: candle.time,
                    open: parseFloat(candle.open),
                    high: parseFloat(candle.high),
                    low: parseFloat(candle.low),
                    close: parseFloat(candle.close)
                }))
                .sort((a, b) => a.time - b.time); // Ordenar siempre

            console.log('🎨 Pintando velas en el gráfico...');
            console.log('📊 Primera vela:', chartData[0]);
            console.log('📊 Última vela:', chartData[chartData.length - 1]);
            console.log('📊 Total velas:', chartData.length);
            
            // ESTRATEGIA MEJORADA: Usar setData() solo en carga inicial, update() para actualizaciones
            if (isInitialLoad) {
                candleSeries.setData(chartData);
                isInitialLoad = false;
                console.log(`✅ Gráfico LISTO con ${chartData.length} velas pintadas`);
                
                // CRÍTICO: Forzar autoescalado para que las velas sean visibles
                chart.timeScale().fitContent();
                chart.priceScale('right').applyOptions({
                    autoScale: true
                });
            } else {
                // Actualizar solo las últimas velas para animación suave
                // Si hay nuevas velas o la última cambió, actualizar
                const lastCandle = chartData[chartData.length - 1];
                if (lastCandle) {
                    candleSeries.update(lastCandle);
                    console.log(`⚡ Actualización suave: última vela ${lastCandle.time}`);
                }
            }
            
        } catch (error) {
            console.error('❌ Error actualizando gráfico:', error);
        }
    }

    /**
     * Iniciar polling para actualizaciones
     */
    function startPolling() {
        // NO iniciar polling histórico si el streaming en tiempo real está activo
        if (realtimeIntervalId) {
            console.log('⏭️ Polling histórico omitido - streaming en tiempo real activo');
            return;
        }
        
        if (intervalId) {
            clearInterval(intervalId);
        }
        
        intervalId = setInterval(async () => {
            try {
                const response = await fetch(config.endpoint);
                if (response.ok) {
                    const data = await response.json();
                    if (Array.isArray(data) && data.length > 0) {
                        updateChart(data);
                    }
                }
            } catch (error) {
                console.error('❌ Error en polling:', error);
            }
        }, config.pollMs);
        
        console.log(`🔄 Polling iniciado cada ${config.pollMs}ms`);
    }

    /**
     * Detener polling
     */
    function stopPolling() {
        if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
            console.log('⏹️ Polling detenido');
        }
    }

    /**
     * Iniciar polling en tiempo real de la vela actual (cada 1 segundo)
     * Solo funciona si el usuario está conectado a IQ Option
     */
    function startRealtimePolling(symbol, timeframe = 'M5') {
        if (realtimeIntervalId) {
            clearInterval(realtimeIntervalId);
        }
        
        // IMPORTANTE: Detener polling histórico para evitar que sobrescriba la vela actual
        // El polling histórico hace setData() cada 3s, pero nosotros usamos update() cada 1s
        stopPolling();
        console.log('⏸️ Polling histórico detenido - usando solo streaming en tiempo real');
        
        let consecutiveErrors = 0;
        const MAX_ERRORS = 5;
        
        realtimeIntervalId = setInterval(async () => {
            try {
                const response = await fetch(`/api/iq/current-candle?symbol=${symbol}&timeframe=${timeframe}`);
                
                if (response.ok) {
                    const data = await response.json();
                    
                    if (data.success && data.candle && candleSeries) {
                        // Usar update() para actualizar la última vela en tiempo real
                        const candle = data.candle;
                        const chartCandle = {
                            time: candle.time,
                            open: parseFloat(candle.open),
                            high: parseFloat(candle.high),
                            low: parseFloat(candle.low),
                            close: parseFloat(candle.close)
                        };
                        
                        candleSeries.update(chartCandle);
                        console.log('⚡ Vela actual actualizada:', chartCandle);
                        consecutiveErrors = 0; // Reset error counter on success
                    } else if (!data.success) {
                        // Stream iniciándose, buffer llenándose
                        console.log('⏳ Esperando datos del stream...');
                    }
                } else if (response.status === 401) {
                    // Usuario no conectado - detener polling en tiempo real
                    console.log('⚠️ No hay conexión a IQ Option - deteniendo streaming en tiempo real');
                    stopRealtimePolling();
                } else if (response.status === 404) {
                    // Sin datos aún, el stream se está iniciando
                    consecutiveErrors++;
                    if (consecutiveErrors === 1) {
                        console.log('⏳ Stream iniciándose, esperando datos...');
                    }
                    if (consecutiveErrors >= MAX_ERRORS) {
                        console.warn('⚠️ No se reciben datos del stream después de varios intentos');
                        consecutiveErrors = 0; // Reset to avoid spam
                    }
                } else {
                    consecutiveErrors++;
                    console.warn(`⚠️ Error HTTP ${response.status} en streaming`);
                }
            } catch (error) {
                consecutiveErrors++;
                if (consecutiveErrors === 1 || consecutiveErrors % 10 === 0) {
                    console.error('❌ Error en polling de vela actual:', error);
                }
                
                // Si hay demasiados errores consecutivos, detener
                if (consecutiveErrors >= MAX_ERRORS * 3) {
                    console.error('❌ Demasiados errores consecutivos - deteniendo streaming');
                    stopRealtimePolling();
                }
            }
        }, 1000); // Cada 1 segundo
        
        console.log(`⚡ Polling de vela actual iniciado cada 1s para ${symbol}`);
        isLoggedIn = true;
    }

    /**
     * Detener polling en tiempo real
     */
    function stopRealtimePolling() {
        if (realtimeIntervalId) {
            clearInterval(realtimeIntervalId);
            realtimeIntervalId = null;
            isLoggedIn = false;
            console.log('⏹️ Polling de vela actual detenido');
            
            // Reiniciar polling histórico cuando se detenga el streaming
            startPolling();
            console.log('▶️ Polling histórico reiniciado');
        }
    }

    /**
     * Destruir el gráfico
     */
    function destroy() {
        stopPolling();
        stopRealtimePolling();
        if (chart) {
            chart.remove();
            chart = null;
            candleSeries = null;
        }
    }

    /**
     * Cargar velas para un símbolo específico usando la fuente de datos actual
     */
    async function loadCandles(symbol, timeframe = 'M5') {
        // Determinar endpoint según fuente de datos
        const source = window.dataSource || 'finnhub';
        
        let endpoint;
        if (source === 'finnhub') {
            endpoint = `/api/finnhub/candles?symbol=${symbol}&timeframe=${timeframe}&limit=80`;
            console.log(`📊 Cargando velas desde: Finnhub (Real)`);
        } else if (source === 'iq') {
            endpoint = `/api/iq/candles?symbol=${symbol}&timeframe=${timeframe}&limit=80`;
            console.log(`📊 Cargando velas desde: IQ Option`);
        } else if (source === 'olymptrade') {
            endpoint = `/api/olymptrade/candles?symbol=${symbol}&timeframe=${timeframe}&limit=80`;
            console.log(`📊 Cargando velas desde: OlympTrade`);
        } else {
            endpoint = `/api/iq/candles?symbol=${symbol}&timeframe=${timeframe}&limit=80`;
            console.log(`📊 Cargando velas desde: IQ Option (default)`);
        }
        
        // Actualizar config
        config.endpoint = endpoint;
        config.timeframe = timeframe;
        
        // Detener polling anterior
        stopPolling();
        
        // Cargar nuevos datos
        isInitialLoad = true; // Resetear flag para fitContent
        await loadInitialData();
        
        // Reiniciar polling con nuevo endpoint
        startPolling();
        
        console.log(`✅ Gráfico actualizado: ${symbol} (${timeframe}) desde ${source}`);
    }

    /**
     * Refrescar datos del gráfico
     */
    function refresh() {
        console.log('🔄 Refrescando datos del gráfico...');
        isInitialLoad = true;
        return loadInitialData();
    }

    /**
     * Configurar bot para mostrar señales
     */
    function setBotId(botId) {
        currentBotId = botId;
        if (botId) {
            startSignalsPolling();
        } else {
            stopSignalsPolling();
        }
    }

    /**
     * Iniciar polling de señales del bot
     */
    function startSignalsPolling() {
        if (!currentBotId) {
            console.warn('⚠️ No hay bot configurado para señales');
            return;
        }

        if (signalsPollingId) {
            clearInterval(signalsPollingId);
        }

        signalsPollingId = setInterval(async () => {
            try {
                const response = await fetch(`/api/bots/signals/${currentBotId}`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.success && data.has_signal) {
                        addSignalMarker(data.signal);
                    }
                }
            } catch (error) {
                console.error('❌ Error obteniendo señales:', error);
            }
        }, 3000); // Cada 3 segundos

        console.log(`📡 Polling de señales iniciado para bot ${currentBotId}`);
    }

    /**
     * Detener polling de señales
     */
    function stopSignalsPolling() {
        if (signalsPollingId) {
            clearInterval(signalsPollingId);
            signalsPollingId = null;
            console.log('⏹️ Polling de señales detenido');
        }
    }

    /**
     * Agregar marcador de señal en el gráfico
     */
    function addSignalMarker(signal) {
        if (!candleSeries) return;

        const timestamp = Math.floor(signal.timestamp);
        const direction = signal.direction.toUpperCase();
        const indicators = signal.indicators || {};

        // Verificar si ya existe un marcador en este timestamp
        const existingIndex = signalMarkers.findIndex(m => m.time === timestamp);
        if (existingIndex !== -1) {
            // Ya existe, actualizar si es necesario
            return;
        }

        // Crear marcador según tipo de señal
        let marker = {
            time: timestamp,
            position: direction === 'CALL' ? 'belowBar' : 'aboveBar',
            color: direction === 'CALL' ? '#00ff88' : '#ff4757',
            shape: direction === 'CALL' ? 'arrowUp' : 'arrowDown',
            text: direction
        };

        // Detectar indicadores de reversión R/V
        const isReversal = indicators.reversal_indicator;
        if (isReversal === 'R' || isReversal === 'V') {
            marker.text = `${direction} (${isReversal})`;
        }

        signalMarkers.push(marker);
        candleSeries.setMarkers(signalMarkers);

        console.log(`📍 Señal ${direction} agregada en timestamp ${timestamp}`, marker);

        // Disparar evento personalizado para actualizar panel de señales
        window.dispatchEvent(new CustomEvent('signalUpdate', { detail: signal }));
    }

    /**
     * Limpiar todos los marcadores
     */
    function clearMarkers() {
        signalMarkers = [];
        if (candleSeries) {
            candleSeries.setMarkers([]);
        }
        console.log('🧹 Marcadores limpiados');
    }

    // Exponer API pública
    return {
        init,
        destroy,
        startPolling,
        stopPolling,
        startRealtimePolling,
        stopRealtimePolling,
        updateChart,
        loadCandles,
        refresh,
        setBotId,
        startSignalsPolling,
        stopSignalsPolling,
        clearMarkers
    };
})();
