#!/usr/bin/env python3
"""
Probe ALADI catalog endpoints: OAI-PMH, SRU, Z39.50
Usage: python probe_aladi.py
Output: probe_aladi_results.txt
"""

import urllib.request
import urllib.error
import socket
import time
import json
from datetime import datetime

BASE = "https://aladi.diba.cat"
OUTPUT_FILE = "probe_aladi_results.txt"
TIMEOUT = 8

ENDPOINTS = {
    "OAI-PMH_base": [
        "/OAI",
        "/oai",
        "/OAI-script",
        "/cgi-bin/oai",
    ],
    "OAI-PMH_verbs": [
        "/OAI?verb=Identify",
        "/OAI?verb=ListMetadataFormats",
        "/OAI?verb=ListSets",
        "/OAI?verb=ListRecords&metadataPrefix=oai_dc",
        "/oai?verb=Identify",
    ],
    "SRU": [
        "/search?operation=explain&version=1.1",
        "/search?operation=searchRetrieve&version=1.1&query=title%3Despirits&maximumRecords=5",
        "/sru?operation=explain",
        "/sru/aladi?operation=explain",
        "/search?operation=explain",
    ],
    "WebPAC_search": [
        "/search/X?searchtype=t&searcharg=casa+de+los+espiritus&searchscope=1&SORT=D",
        "/search/X?searchtype=t&searcharg=casa+de+los+espiritus",
        "/search?/tcasa+de+los+espiritus/tcasa+de+los+espiritus/1%2C20%2C20%2CB/frameset",
    ],
    "Known_public": [
        "/screens/wwwoptions",
        "/robots.txt",
        "/version",
    ],
}

Z39_HOSTS = [
    ("aladi.diba.cat", 2200),
    ("aladi.diba.cat", 210),
    ("aladi.diba.cat", 7090),
]


def probe_http(url):
    """Probe an HTTP endpoint and return status + snippet."""
    result = {
        "url": url,
        "status": None,
        "content_type": None,
        "body_snippet": None,
        "error": None,
        "response_time_ms": None,
    }
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ALADI-TFG-Probe/1.0 (UPC academic research)"},
        )
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            elapsed = int((time.time() - t0) * 1000)
            result["status"] = resp.status
            result["content_type"] = resp.headers.get("Content-Type", "")
            result["response_time_ms"] = elapsed
            raw = resp.read(2000)
            try:
                body = raw.decode("utf-8", errors="replace")
            except Exception:
                body = str(raw)
            result["body_snippet"] = body[:800].strip()
    except urllib.error.HTTPError as e:
        result["status"] = e.code
        result["error"] = str(e)
    except urllib.error.URLError as e:
        result["error"] = str(e.reason)
    except Exception as e:
        result["error"] = str(e)
    return result


def probe_tcp(host, port):
    """Check if a TCP port is open (for Z39.50)."""
    result = {"host": host, "port": port, "open": False, "banner": None, "error": None}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        code = s.connect_ex((host, port))
        if code == 0:
            result["open"] = True
            s.settimeout(3)
            try:
                banner = s.recv(256)
                result["banner"] = banner.hex()
            except Exception:
                result["banner"] = "(no banner received)"
        else:
            result["error"] = f"Connection refused or filtered (code {code})"
        s.close()
    except Exception as e:
        result["error"] = str(e)
    return result


def fmt_http(r):
    lines = []
    lines.append(f"  URL    : {r['url']}")
    if r["status"]:
        lines.append(f"  Status : {r['status']}")
    if r["content_type"]:
        lines.append(f"  C-Type : {r['content_type']}")
    if r["response_time_ms"]:
        lines.append(f"  Time   : {r['response_time_ms']} ms")
    if r["error"]:
        lines.append(f"  Error  : {r['error']}")
    if r["body_snippet"]:
        lines.append(f"  Body   :\n    " + r["body_snippet"].replace("\n", "\n    ")[:600])
    return "\n".join(lines)


def fmt_tcp(r):
    lines = []
    lines.append(f"  Host   : {r['host']}:{r['port']}")
    lines.append(f"  Open   : {r['open']}")
    if r["banner"]:
        lines.append(f"  Banner : {r['banner']}")
    if r["error"]:
        lines.append(f"  Error  : {r['error']}")
    return "\n".join(lines)


def main():
    lines = []
    lines.append("=" * 70)
    lines.append(f"ALADI ENDPOINT PROBE — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    lines.append("=" * 70)

    all_http_results = {}

    for group, paths in ENDPOINTS.items():
        lines.append(f"\n{'─'*70}")
        lines.append(f"GROUP: {group}")
        lines.append(f"{'─'*70}")
        group_results = []
        for path in paths:
            url = BASE + path
            print(f"  Probing {url} ...")
            r = probe_http(url)
            group_results.append(r)
            lines.append(fmt_http(r))
            lines.append("")
            time.sleep(0.4)  # be polite
        all_http_results[group] = group_results

    lines.append(f"\n{'─'*70}")
    lines.append("GROUP: Z39.50 TCP ports")
    lines.append(f"{'─'*70}")
    tcp_results = []
    for host, port in Z39_HOSTS:
        print(f"  Probing TCP {host}:{port} ...")
        r = probe_tcp(host, port)
        tcp_results.append(r)
        lines.append(fmt_tcp(r))
        lines.append("")

    # Summary table
    lines.append(f"\n{'='*70}")
    lines.append("SUMMARY")
    lines.append(f"{'='*70}")
    for group, results in all_http_results.items():
        for r in results:
            status = r["status"] or "ERR"
            indicator = "✓" if r["status"] == 200 else "✗"
            lines.append(f"  {indicator} [{status}]  {r['url']}")
    lines.append("")
    for r in tcp_results:
        indicator = "✓" if r["open"] else "✗"
        lines.append(f"  {indicator} [TCP]  {r['host']}:{r['port']}  open={r['open']}")

    lines.append(f"\n{'='*70}")
    lines.append("END OF REPORT — paste this file content to Claude for analysis")
    lines.append(f"{'='*70}")

    output = "\n".join(lines)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"\n✓ Done. Results saved to: {OUTPUT_FILE}")
    print("  Paste the contents of that file to Claude for analysis.")


if __name__ == "__main__":
    main()