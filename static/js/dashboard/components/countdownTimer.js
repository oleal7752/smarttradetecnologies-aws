/**
 * Countdown Timer Component - Contador de próxima vela
 */

export class CountdownTimer {
  constructor(containerId, state) {
    this.container = document.getElementById(containerId);
    this.state = state;
    this.intervalId = null;
    this.init();
  }

  init() {
    this.render();
    this.startCountdown();
    
    this.state.subscribe('timeframe', () => {
      this.stopCountdown();
      this.startCountdown();
    });
  }

  getTimeframeSeconds(timeframe) {
    const map = {
      'M1': 60,
      'M5': 300,
      'M15': 900,
      'M30': 1800,
      'H1': 3600,
      'H4': 14400,
      'D1': 86400
    };
    return map[timeframe] || 300;
  }

  startCountdown() {
    const updateCountdown = () => {
      const timeframe = this.state.getState().timeframe;
      const intervalSeconds = this.getTimeframeSeconds(timeframe);
      const now = Math.floor(Date.now() / 1000);
      const secondsLeft = intervalSeconds - (now % intervalSeconds);
      
      const minutes = Math.floor(secondsLeft / 60);
      const seconds = secondsLeft % 60;
      const timeString = `${minutes}:${seconds.toString().padStart(2, '0')}`;
      
      const timerEl = document.getElementById('countdown-display');
      if (timerEl) {
        timerEl.textContent = timeString;
        timerEl.className = 'countdown-timer' + (secondsLeft <= 10 ? ' warning' : '');
      }
    };

    updateCountdown();
    this.intervalId = setInterval(updateCountdown, 1000);
  }

  stopCountdown() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  render() {
    this.container.innerHTML = `
      <div class="countdown-label">Próxima vela en</div>
      <div id="countdown-display" class="countdown-timer">5:00</div>
    `;
  }

  destroy() {
    this.stopCountdown();
  }
}
