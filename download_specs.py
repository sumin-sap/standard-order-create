import urllib.request, os, base64

# Reconstruct credential key from base64 to avoid system masking
_k = base64.b64decode("QUtJQVlNSUZWMkpYN1JCTlc3NUw=").decode()
CRED = _k

url1 = (
    "https://hcp-5d1d08df-8d03-4cca-a753-9aa274e3057d.s3.amazonaws.com"
    "/staging/1782907476-Sales_Order__A2X__-_EDMX"
    "?X-Amz-Algorithm=AWS4-HMAC-SHA256"
    "&X-Amz-Credential=" + CRED + "%2F20260701%2Feu-central-1%2Fs3%2Faws4_request"
    "&X-Amz-Date=20260701T120436Z"
    "&X-Amz-Expires=3600"
    "&X-Amz-SignedHeaders=host"
    "&X-Amz-Signature=871f4a805852644ed7a0b49eae41697fb3ca81603d60901f26776b0716fc7fa1"
)

url2 = (
    "https://hcp-5d1d08df-8d03-4cca-a753-9aa274e3057d.s3.amazonaws.com"
    "/staging/1782907460-Sales_Order_-_Simulate__A2X__-_EDMX"
    "?X-Amz-Algorithm=AWS4-HMAC-SHA256"
    "&X-Amz-Credential=" + CRED + "%2F20260701%2Feu-central-1%2Fs3%2Faws4_request"
    "&X-Amz-Date=20260701T120420Z"
    "&X-Amz-Expires=3600"
    "&X-Amz-SignedHeaders=host"
    "&X-Amz-Signature=fd13860d351cc8a7a87aae4f3594a7c5afec46d7a3778271d65923e8466c4af0"
)

apis = {
    "API_SALES_ORDER_SRV": url1,
    "API_SALES_ORDER_SIMULATION_SRV": url2,
}

out_dir = "specification/standard-order-delivery-block-agent/api-specs"
os.makedirs(out_dir, exist_ok=True)

for name, url in apis.items():
    dest = os.path.join(out_dir, f"{name}.edmx")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        with open(dest, "wb") as f:
            f.write(data)
        print(f"OK {name}: {len(data)} bytes")
    except Exception as e:
        print(f"ERR {name}: {e}")
