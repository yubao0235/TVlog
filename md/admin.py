import requests
import os

# 1. 配置
TARGET_URL = "http://117.72.167.234:8000/index.html" # 目标网页地址
SAVE_PATH = "md/index.html"    # 本地保存路径

def download_full_page():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        print(f"📡 正在抓取全量网页内容: {TARGET_URL}")
        response = requests.get(TARGET_URL, headers=headers, timeout=30)
        response.encoding = 'utf-8' # 确保中文不乱码
        
        if response.status_code == 200:
            # 创建文件夹
            os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
            
            # 整个 HTML 存入本地
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"✅ 全量数据已保存至: {SAVE_PATH}")
        else:
            print(f"❌ 抓取失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"❌ 发生异常: {e}")

if __name__ == "__main__":
    download_full_page()
