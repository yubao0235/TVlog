import os
import re
import asyncio
import httpx
import shutil

# --- 配置区 ---
SOURCES = [
    "https://yuxx.de5.net/4d2e30e5.m3u",
    "https://yuxx.de5.net/edcab778.m3u",
    "https://yuxx.de5.net/33fc12a0.m3u",
    "https://yuxx.de5.net/3c1f32b7.m3u",
    "https://yuxx.de5.net/97d6e00d.m3u"
]
SAVE_DIR = "hotel"
# 使用 API 归属地查询
IP_API = "http://ip-api.com/json/{}?fields=status,regionName,city,query&lang=zh-CN"

async def get_location(client, ip):
    """异步查询归属地"""
    try:
        resp = await client.get(IP_API.format(ip), timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                region = data.get("regionName", "")
                city = data.get("city", "")
                return region if region == city else f"{region}{city}"
    except: pass
    return "Unknown"

async def process_single_task(client, ip, port, url):
    """单个 URL 的完整处理逻辑"""
    loc = await get_location(client, ip)
    # 清洗地点名，只保留中文，防止文件名非法
    loc_clean = re.sub(r'[^\u4e00-\u9fa5]+', '', loc) or "Unknown"
    
    filename = f"{loc_clean}_{ip}_{port}.m3u"
    filepath = os.path.join(SAVE_DIR, filename)
    
    # 写入文件，确保使用 w 模式覆盖
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"#EXTM3U\n#EXTINF:-1,{loc_clean}_{ip}\n{url}\n")
    except Exception as e:
        print(f"写入失败 {filename}: {e}")
    return True

async def process_sources():
    # 1. 强制清空旧文件夹，确保残缺文件消失
    if os.path.exists(SAVE_DIR):
        shutil.rmtree(SAVE_DIR)
    os.makedirs(SAVE_DIR, exist_ok=True)

    # 【核心修正】：Headers 必须是 ASCII 字符，去掉了中文
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(follow_redirects=True, verify=False, headers=headers) as client:
        # 1. 抓取源码
        all_urls = set()
        for src in SOURCES:
            try:
                print(f"📡 Downloading: {src}", flush=True)
                r = await client.get(src)
                # 修正后的正则：确保抓取完整路径
                found = re.findall(r'(?:http|rtp)://[0-9\.]+(?::\d+)?[^ \r\n\t"\'<>]*', r.text)
                all_urls.update(found)
            except Exception as e:
                print(f"❌ Failed to download {src}: {e}", flush=True)


        # --- 修改后：按 IP+端口 去重（每个酒店只生成一个文件） ---
        tasks_data = []
        seen_hosts = set() # 用来记录处理过的 IP:Port
        for url in all_urls:
            match = re.search(r'//([0-9\.]+):(\d+)', url)
            if match:
                ip, port = match.groups()
                host = f"{ip}:{port}"
                if host not in seen_hosts:
                    tasks_data.append((ip, port, url))
                    seen_hosts.add(host)

        print(f"📊 Total links: {len(tasks_data)}. Processing...", flush=True)

        # 3. 并发处理（每 5 个一组，防止被 API 封锁）
        batch_size = 5 
        for i in range(0, len(tasks_data), batch_size):
            batch = tasks_data[i:i+batch_size]
            await asyncio.gather(*(process_single_task(client, *item) for item in batch))
            print(f"🚀 Progress: {min(i+batch_size, len(tasks_data))}/{len(tasks_data)}", flush=True)
            await asyncio.sleep(0.3) # 稍微喘口气，防止 API 报 429 错误

if __name__ == "__main__":
    asyncio.run(process_sources())
