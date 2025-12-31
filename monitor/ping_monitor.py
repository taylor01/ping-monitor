#!/usr/bin/env python3
"""
Distributed Ping Monitor for Datadog - Concurrent Version
"""

import json
import time
import os
import requests
from pathlib import Path
from icmplib import ping, multiping
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

CONFIG_URL = os.getenv("CONFIG_URL", "")
LOCAL_CACHE = os.getenv("LOCAL_CACHE", "/data/hosts-cache.json")
LOCAL_HOSTS = os.getenv("LOCAL_HOSTS", "/config/hosts.json")
DD_API_KEY = os.getenv("DD_API_KEY", "")
DD_SITE = os.getenv("DD_SITE", "datadoghq.com")
SITE_NAME = os.getenv("SITE_NAME", "default")
PING_INTERVAL = int(os.getenv("PING_INTERVAL", "60"))
PING_COUNT = int(os.getenv("PING_COUNT", "3"))
PING_TIMEOUT = int(os.getenv("PING_TIMEOUT", "2"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "20"))



def fetch_hosts():
    if CONFIG_URL:
        try:
            resp = requests.get(CONFIG_URL, timeout=10)
            resp.raise_for_status()
            hosts = resp.json()
            Path(LOCAL_CACHE).parent.mkdir(parents=True, exist_ok=True)
            with open(LOCAL_CACHE, "w") as f:
                json.dump(hosts, f)
            print(f"[{timestamp()}] Loaded {len(hosts)} hosts from remote config")
            return hosts
        except Exception as e:
            print(f"[{timestamp()}] Failed to fetch remote config: {e}")
    
    try:
        with open(LOCAL_CACHE) as f:
            hosts = json.load(f)
            print(f"[{timestamp()}] Loaded {len(hosts)} hosts from cache")
            return hosts
    except:
        pass
    
    try:
        with open(LOCAL_HOSTS) as f:
            hosts = json.load(f)
            print(f"[{timestamp()}] Loaded {len(hosts)} hosts from local config")
            return hosts
    except Exception as e:
        print(f"[{timestamp()}] No hosts configuration found: {e}")
        return []


def timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def send_metrics(host, result):
    ts = int(time.time())
    
    tags = [
        f"ip:{host['ip']}",
        f"site:{SITE_NAME}",
        f"device_type:{host.get('type', 'unknown')}",
    ]
    
    desc = host.get('description', '').replace(' ', '_').replace(':', '-')
    if desc:
        tags.append(f"description:{desc}")
    
    for tag in host.get("tags", []):
        tags.append(tag)
    
    series = [
        {
            "metric": "custom.ping.reachable",
            "type": "gauge",
            "points": [[ts, 1 if result.is_alive else 0]],
            "host": host["name"],
            "tags": tags
        },
        {
            "metric": "custom.ping.latency_ms",
            "type": "gauge",
            "points": [[ts, round(result.avg_rtt, 2) if result.is_alive else 0]],
            "host": host["name"],
            "tags": tags
        },
        {
            "metric": "custom.ping.packet_loss",
            "type": "gauge",
            "points": [[ts, result.packet_loss * 100]],
            "host": host["name"],
            "tags": tags
        },
        {
            "metric": "custom.ping.jitter_ms",
            "type": "gauge",
            "points": [[ts, round(result.jitter, 2) if result.is_alive else 0]],
            "host": host["name"],
            "tags": tags
        }
    ]
    
    try:
        resp = requests.post(
            f"https://api.{DD_SITE}/api/v1/series",
            headers={"DD-API-KEY": DD_API_KEY, "Content-Type": "application/json"},
            json={"series": series},
            timeout=10
        )
        if not resp.ok:
            print(f"[{timestamp()}] API Error for {host['name']}: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[{timestamp()}] Failed to send metrics for {host['name']}: {e}")


def check_hosts(hosts):
    start = time.time()
    
    # Concurrent ping using multiping
    ips = [h["ip"] for h in hosts]
    results = multiping(ips, count=PING_COUNT, timeout=PING_TIMEOUT, privileged=True)
    
    # Map results back to hosts
    ip_to_result = {r.address: r for r in results}
    
    # Send metrics concurrently
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for host in hosts:
            result = ip_to_result.get(host["ip"])
            if result:
                status = "UP" if result.is_alive else "DOWN"
                latency = f"{result.avg_rtt:.1f}ms" if result.is_alive else "N/A"
                loss = f"{result.packet_loss * 100:.0f}%"
                print(f"[{timestamp()}] {host['name']:20} ({host['ip']:15}) - {status:4} | Latency: {latency:8} | Loss: {loss}")
                
                executor.submit(send_metrics, host, result)
    
    elapsed = time.time() - start
    print(f"[{timestamp()}] Completed {len(hosts)} hosts in {elapsed:.1f}s")


def main():
    print(f"[{timestamp()}] Ping Monitor starting")
    print(f"[{timestamp()}] Site: {SITE_NAME}")
    print(f"[{timestamp()}] Interval: {PING_INTERVAL}s")
    print(f"[{timestamp()}] Datadog Site: {DD_SITE}")
    
    if not DD_API_KEY:
        print(f"[{timestamp()}] ERROR: DD_API_KEY not set")
        return
    
    while True:
        hosts = fetch_hosts()
        if hosts:
            check_hosts(hosts)
        else:
            print(f"[{timestamp()}] No hosts to monitor")
        
        time.sleep(PING_INTERVAL)


if __name__ == "__main__":
    main()