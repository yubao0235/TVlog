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
    return "未知"

async def process_single_task(client, ip, port, url):
    """单个 URL 的完整处理逻辑"""
    loc = await get_location(client, ip)
    loc_clean = re.sub(r'[^\u4e00-\u9fa5]+', '', loc) or "未知"
    
    filename = f"{loc_clean}_{ip}_{port}.m3u"
    filepath = os.path.join(SAVE_DIR, filename)
    
    # 写入文件
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"#EXTM3U\n#EXTINF:-1,{loc_clean}_{ip}\n{url}\n")
    return True

async def process_sources():
    # 强制清空旧文件夹
    if os.path.exists(SAVE_DIR):
        shutil.rmtree(SAVE_DIR)
    os.makedirs(SAVE_DIR, exist_ok=True)

    headers = {"User-Agent": "Mozilla/5.0 (VLC播放器风格)"}
    
    async with httpx.AsyncClient(follow_redirects=True, verify=False, headers=headers) as client:
        # 1. 抓取所有源码中的完整 URL
        all_urls = set()
        for src in SOURCES:
            try:
                print(f"📡 正在拉取源: {src}", flush=True)
                r = await client.get(src)
                # 修正后的正则：抓取完整路径
                found = re.findall(r'(?:http|rtp)://[0-9\.]+(?::\d+)?[^ \r\n\t"\'<>]*', r.text)
                all_urls.update(found)
            except Exception as e:
                print(f"❌ 下载失败 {src}: {e}", flush=True)

        # 2. 提取任务信息
        tasks_data = []
        for url in all_urls:
            match = re.search(r'//([0-9\.]+):(\d+)', url)
            if match:
                tasks_data.append((match.group(1), match.group(2), url))

        print(f"📊 共提取到 {len(tasks_data)} 个有效链接，开始并发处理...", flush=True)

        # 3. 并发处理（每 5 个一组，防止被 API 封锁）
        batch_size = 5 
        for i in range(0, len(tasks_data), batch_size):
            batch = tasks_data[i:i+batch_size]
            # 使用 gather 同时启动 5 个任务
            await asyncio.gather(*(process_single_task(client, *item) for item in batch))
            print(f"🚀 已处理: {min(i+batch_size, len(tasks_data))}/{len(tasks_data)}", flush=True)
            # 缩短等待时间
            await asyncio.sleep(0.2)

if __name__ == "__main__":
    asyncio.run(process_sources())
