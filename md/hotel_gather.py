import os
import re
import asyncio
import httpx

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
    """查询 IP 归属地"""
    try:
        resp = await client.get(IP_API.format(ip), timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                region = data.get("regionName", "")
                city = data.get("city", "")
                return region if region == city else f"{region}{city}"
    except:
        pass
    return "未知"

async def process_sources():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR, exist_ok=True)

    # 增加模拟浏览器的 Headers，防止部分网站拦截请求
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}

    async with httpx.AsyncClient(follow_redirects=True, verify=False, headers=headers) as client:
        # 1. 汇总所有 URL
        all_urls = set()
        for src in SOURCES:
            try:
                print(f"正在下载源文件: {src}")
                r = await client.get(src)
                # 【关键修正】：修改正则，允许匹配包含路径、参数的完整 URL
                # 匹配 http/rtp 直到行尾或空格或引号
                found = re.findall(r'(?:http|rtp)://[0-9\.]+(?::\d+)?[^ \r\n\t"\'<>]*', r.text)
                all_urls.update(found)
            except Exception as e:
                print(f"下载失败 {src}: {e}")

        print(f"共发现 {len(all_urls)} 个原始链接，开始处理归属地...")

        # 2. 准备任务
        tasks_info = []
        for url in all_urls:
            # 提取 IP 和 端口用于归属地查询和命名
            match = re.search(r'//([0-9\.]+):(\d+)', url)
            if match:
                ip, port = match.groups()
                tasks_info.append((ip, port, url))

        # 3. 批量处理（每10个一组）
        for i in range(0, len(tasks_info), 10):
            batch = tasks_info[i:i+10]
            for ip, port, url in batch:
                loc = await get_location(client, ip)
                # 清洗归属地字符串，只保留中文
                loc_clean = re.sub(r'[^\u4e00-\u9fa5]+', '', loc)
                if not loc_clean: loc_clean = "未知"
                
                # 文件名包含地点、IP和端口
                filename = f"{loc_clean}_{ip}_{port}.m3u"
                filepath = os.path.join(SAVE_DIR, filename)
                
                # 写入完整 URL
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write("#EXTM3U\n")
                    f.write(f"#EXTINF:-1,{loc_clean}_{ip}\n")
                    f.write(f"{url}\n") # 这里现在会写入完整的路径，如 /hls/1/index.m3u8
            
            print(f"已处理进度: {min(i+10, len(tasks_info))}/{len(tasks_info)}")
            await asyncio.sleep(0.5) 

if __name__ == "__main__":
    asyncio.run(process_sources())
