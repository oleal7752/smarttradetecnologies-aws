import time
import requests

def post_candles_batch(server_base, symbol, timeframe, candles):
    url = f"{server_base}/api/iq/candles?symbol={symbol}&timeframe={timeframe}"
    # El backend normaliza; pasamos los campos tal como los da iqoptionapi
    payload = {"candles": candles}
    r = requests.post(url, json=payload, timeout=5)
    r.raise_for_status()
    return r.json()

def backfill_200(iq, server_base, symbol, timeframe="M5"):
    tf_sec = 300
    end = int(time.time())
    # iqoptionapi devuelve lista de dicts con keys: open, close, min, max, from, to, volume
    data = iq.get_candles(symbol, tf_sec, 200, end)
    # Marca cerradas las que ya pasaron su 'to'
    now = int(time.time())
    for c in data:
        c["high"] = c.get("max", c.get("high", 0))
        c["low"]  = c.get("min", c.get("low", 0))
        if "time" not in c:  # normaliza campo time
            c["time"] = int(c.get("from", 0))
        c["closed"] = bool(now >= int(c.get("to", c["time"] + tf_sec)))
        c["symbol"] = symbol
    return post_candles_batch(server_base, symbol, timeframe, data)

def publish_on_close(iq, server_base, symbol, timeframe="M5", sleep_sec=2):
    tf_sec = 300
    last_sent_ts = None
    while True:
        end = int(time.time())
        arr = iq.get_candles(symbol, tf_sec, 2, end)  # últimas 2
        arr.sort(key=lambda x: int(x.get("from", 0)))
        now = int(time.time())
        for c in arr:
            c["high"] = c.get("max", c.get("high", 0))
            c["low"]  = c.get("min", c.get("low", 0))
            if "time" not in c:
                c["time"] = int(c.get("from", 0))
            c["closed"] = bool(now >= int(c.get("to", c["time"] + tf_sec)))
            c["symbol"] = symbol

        # La cerrada es la penúltima si la última aún está en curso
        closed_candidates = [c for c in arr if c["closed"]]
        if closed_candidates:
            last_closed = closed_candidates[-1]
            ts = int(last_closed["time"])
            if last_sent_ts is None or ts > last_sent_ts:
                post_candles_batch(server_base, symbol, timeframe, [last_closed])
                last_sent_ts = ts
        time.sleep(sleep_sec)