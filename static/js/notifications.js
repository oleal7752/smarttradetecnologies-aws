/**
 * Sistema de notificaciones glassmorphism para STC Trading System
 * Reemplaza alert() con notificaciones transparentes rojas/verdes
 */

class STCNotification {
    constructor() {
        this.container = null;
        this.ready = false;
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    init() {
        if (!document.body) {
            setTimeout(() => this.init(), 100);
            return;
        }
        
        if (!document.getElementById('stc-notification-container')) {
            this.container = document.createElement('div');
            this.container.id = 'stc-notification-container';
            this.container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                gap: 10px;
                pointer-events: none;
            `;
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('stc-notification-container');
        }
        this.ready = true;
    }

    show(message, type = 'success', duration = 4000) {
        if (!this.ready || !this.container) {
            console.warn('⚠️ Sistema de notificaciones no está listo aún');
            return;
        }
        
        const notification = document.createElement('div');
        notification.className = 'stc-notification';
        
        const isError = type === 'error' || type === 'danger';
        const bgColor = isError ? 'rgba(255, 0, 102, 0.15)' : 'rgba(0, 255, 102, 0.15)';
        const borderColor = isError ? '#ff0066' : '#00ff66';
        const textColor = isError ? '#ff3388' : '#00ff88';
        const icon = isError ? '⚠️' : '✓';
        
        notification.style.cssText = `
            background: ${bgColor};
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid ${borderColor};
            border-radius: 12px;
            padding: 16px 20px;
            color: ${textColor};
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 8px 32px ${isError ? 'rgba(255, 0, 102, 0.3)' : 'rgba(0, 255, 102, 0.3)'};
            min-width: 300px;
            max-width: 500px;
            pointer-events: auto;
            animation: slideInRight 0.3s ease-out;
            display: flex;
            align-items: center;
            gap: 12px;
            position: relative;
        `;
        
        notification.innerHTML = `
            <span style="font-size: 20px;">${icon}</span>
            <span style="flex: 1;">${message}</span>
            <button onclick="this.parentElement.remove()" style="
                background: transparent;
                border: none;
                color: ${textColor};
                font-size: 18px;
                cursor: pointer;
                padding: 0;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                opacity: 0.7;
                transition: opacity 0.2s;
            " onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.7'">×</button>
        `;
        
        this.container.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 300);
        }, duration);
    }

    success(message, duration = 4000) {
        this.show(message, 'success', duration);
    }

    error(message, duration = 4000) {
        this.show(message, 'error', duration);
    }

    info(message, duration = 4000) {
        this.show(message, 'info', duration);
    }
}

const notify = new STCNotification();

const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

window.notify = notify;
