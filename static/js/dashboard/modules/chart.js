/**
 * Chart Module - Gestor del gráfico TradingView Lightweight Charts
 */

export class ChartManager {
  constructor(containerId) {
    this.containerId = containerId;
    this.chart = null;
    this.candleSeries = null;
    this.lastCandles = [];
  }

  init() {
    const container = document.getElementById(this.containerId);
    if (!container) {
      console.error(`Container #${this.containerId} not found`);
      return;
    }

    this.chart = LightweightCharts.createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
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
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: '#1f2937',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 5,
        barSpacing: 8,
        fixLeftEdge: true,
        fixRightEdge: true,
      },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
        vertLine: {
          color: 'rgba(0, 245, 255, 0.3)',
          width: 1,
          style: LightweightCharts.LineStyle.Dashed,
        },
        horzLine: {
          color: 'rgba(0, 245, 255, 0.3)',
          width: 1,
          style: LightweightCharts.LineStyle.Dashed,
        },
      },
    });

    this.candleSeries = this.chart.addCandlestickSeries({
      upColor: '#00D09C',
      downColor: '#FF5B5A',
      borderUpColor: '#00D09C',
      borderDownColor: '#FF5B5A',
      wickUpColor: '#00D09C',
      wickDownColor: '#FF5B5A',
      priceFormat: {
        type: 'price',
        precision: 5,
        minMove: 0.00001,
      },
    });

    window.addEventListener('resize', () => this.handleResize());
    
    console.log('📊 Chart initialized successfully');
  }

  handleResize() {
    if (!this.chart) return;
    
    const container = document.getElementById(this.containerId);
    if (container) {
      this.chart.applyOptions({
        width: container.clientWidth,
        height: container.clientHeight,
      });
    }
  }

  setCandles(candles) {
    if (!this.candleSeries || !candles || candles.length === 0) {
      return;
    }

    const formattedCandles = candles.map(c => ({
      time: c.time,
      open: parseFloat(c.open),
      high: parseFloat(c.high),
      low: parseFloat(c.low),
      close: parseFloat(c.close),
    }));

    this.candleSeries.setData(formattedCandles);
    this.chart.timeScale().fitContent();
    this.lastCandles = formattedCandles;
    
    console.log(`✅ Chart updated with ${formattedCandles.length} candles`);
  }

  updateLastCandle(candle) {
    if (!this.candleSeries || !candle) return;

    const formattedCandle = {
      time: candle.time,
      open: parseFloat(candle.open),
      high: parseFloat(candle.high),
      low: parseFloat(candle.low),
      close: parseFloat(candle.close),
    };

    this.candleSeries.update(formattedCandle);
  }

  destroy() {
    if (this.chart) {
      this.chart.remove();
      this.chart = null;
      this.candleSeries = null;
    }
  }
}
