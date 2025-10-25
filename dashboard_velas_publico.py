#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard PÚBLICO de Velas Japonesas - Sin Autenticación
Puerto 5001 para no interferir con backtest (puerto 5000)
"""

from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route("/")
def dashboard_velas():
    """Dashboard público de velas japonesas - Sin login requerido"""
    api_key = os.getenv("BOT_API_KEY", "stc_default_key_2025")
    return render_template("signals_panel.html", api_key=api_key)

@app.route("/favicon.ico")
def favicon():
    return '', 204

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 DASHBOARD VELAS JAPONESAS PÚBLICO")
    print("=" * 60)
    print("📊 URL: http://localhost:5001")
    print("✅ Sin autenticación requerida")
    print("💹 Velas japonesas en tiempo real")
    print("=" * 60)
    
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True
    )
