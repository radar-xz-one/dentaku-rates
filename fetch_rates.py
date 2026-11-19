"""Fetch daily FX rates (units per 1 JPY) and write docs/rates.json. Tries several free sources in order."""
import calendar
import json
import sys
import time
import urllib.request

CRYPTO = ["BTC", "ETH", "USDT", "XRP", "BNB", "SOL", "DOGE", "ADA", "LTC", "TRX"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "dentaku-rates/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def er_api():
    j = get("https://open.er-api.com/v6/latest/JPY")
    assert j["result"] == "success"
    return j["rates"], j.get("time_last_update_unix", int(time.time()))


def fawaz():
    j = get("https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/jpy.json")
    rates = {k.upper(): v for k, v in j["jpy"].items() if len(k) == 3 and v}
    rates["CNH"] = rates.get("CNY", 0)
    return rates, int(time.time())


def fawaz_fallback():
    j = get("https://latest.currency-api.pages.dev/v1/currencies/jpy.json")
    rates = {k.upper(): v for k, v in j["jpy"].items() if len(k) == 3 and v}
    rates["CNH"] = rates.get("CNY", 0)
    return rates, int(time.time())


def crypto():
    """Crypto rates (units per 1 JPY). Optional: failure here must not fail the whole update."""
    for url in ("https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/jpy.json",
                "https://latest.currency-api.pages.dev/v1/currencies/jpy.json"):
        try:
            j = get(url)["jpy"]
            day = get(url).get("date")
            ts = calendar.timegm(time.strptime(day, "%Y-%m-%d")) if day else int(time.time())
            return {c: j[c.lower()] for c in CRYPTO if j.get(c.lower())}, ts
        except Exception as e:
            print("CRYPTO FAILED", url, e, file=sys.stderr)
    return {}, 0


for name, fn in [("open.er-api.com", er_api), ("fawazahmed0 (jsdelivr)", fawaz), ("fawazahmed0 (pages.dev)", fawaz_fallback)]:
    try:
        rates, ts = fn()
        rates = {k: v for k, v in rates.items() if isinstance(v, (int, float)) and v > 0}
        if len(rates) < 50 or "USD" not in rates:
            raise ValueError("too few rates: %d" % len(rates))
        crypto_rates, crypto_ts = crypto()
        rates.update(crypto_rates)
        out = {"source": name, "updated_unix": int(ts), "updated_unix_crypto": int(crypto_ts), "fetched_unix": int(time.time()), "base": "JPY", "rates": rates}
        with open("docs/rates.json", "w", encoding="utf-8") as f:
            json.dump(out, f, separators=(",", ":"), sort_keys=True)
        print("OK", name, len(rates), "currencies")
        sys.exit(0)
    except Exception as e:
        print("FAILED", name, e, file=sys.stderr)

print("All sources failed", file=sys.stderr)
sys.exit(1)
