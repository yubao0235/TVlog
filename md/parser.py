import os
import re
from bs4 import BeautifulSoup

# 配置路径
SOURCE_FILE = "md/index.html"
FULL_DIR = "Full"        # 存放完整内容的文件夹
AV_DIR = "Only"    # 存放纯净可用内容的文件夹

def parse_and_split():
    if not os.path.exists(SOURCE_FILE):
        print(f"❌ 找不到源文件: {SOURCE_FILE}")
        return

    # 创建输出目录
    for d in [FULL_DIR, AV_DIR]:
        if not os.path.exists(d): 
            os.makedirs(d)
            print(f"📁 已创建目录: {d}")

    # 读取抓取到的 HTML
    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, 'html.parser')

    # 提取所有数据行
    rows = soup.find_all('tr')
    print(f"📊 扫描完成：共发现 {len(rows)} 条原始记录。")

    # 分类存储字典
    groups = {}

    for row in rows:
        cells = row.find_all('td')
        # 基础校验，确保行数据完整
        if len(cells) < 5: 
            continue
        
        try:
            # 1. 提取频道名 (在第二个 td 里的 small 标签)
            name_tag = cells[1].find('small')
            name = name_tag.get_text(strip=True) if name_tag else cells[1].get_text(strip=True)
            
            # 2. 提取分类 (在第三个 td 里的 category-tag 标签)
            cat_tag = cells[2].find('span', class_='category-tag')
            category = cat_tag.get_text(strip=True) if cat_tag else "其他频道"
            
            # 3. 提取链接 (在 url-cell 里的 a 标签)
            url_cell = row.find('td', class_='url-cell')
            url_a = url_cell.find('a') if url_cell else None
            url = url_a['href'].strip() if url_a else ""
            
            # 4. 判定状态 (寻找包含 ok 的 tag)
            status_tag = row.find('span', class_='tag-ok')
            is_available = True if status_tag and "可用" in status_tag.get_text() else False

            if not url: continue # 跳过没有链接的行

            # 归类
            if category not in groups: 
                groups[category] = []
            
            groups[category].append({
                "name": name,
                "url": url,
                "available": is_available
            })
        except:
            continue

    # --- 写入文件逻辑 ---
    for cat, items in groups.items():
        # 清理文件名非法字符
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', cat)
        
        full_file = os.path.join(FULL_DIR, f"{safe_name}.m3u")
        av_file = os.path.join(AV_DIR, f"{safe_name}.m3u")

        # 写入 Full_Data (全部收录)
        with open(full_file, "w", encoding="utf-8") as f_full:
            f_full.write("#EXTM3U\n")
            # 写入 Available_Only (仅收录可用)
            with open(av_file, "w", encoding="utf-8") as f_av:
                f_av.write("#EXTM3U\n")
                
                for item in items:
                    # 统一格式：不带任何状态文字后缀
                    line = f'#EXTINF:-1 group-title="{cat}",{item["name"]}\n{item["url"]}\n'
                    
                    # 总是写入全部文件夹
                    f_full.write(line)
                    
                    # 只有可用的才写入可用文件夹
                    if item["available"]:
                        f_av.write(line)

    print(f"✅ 处理完毕：分类源已分发至 {FULL_DIR} 和 {AV_DIR} 文件夹。")

if __name__ == "__main__":
    parse_and_split()
