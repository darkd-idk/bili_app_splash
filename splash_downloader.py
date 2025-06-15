#!/usr/bin/env python3
"""
Bilibili Splash Image Downloader (Optimized Single Job Version)

Version: 5.1.0
Updated: 2025-06-15
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
import random
import requests
from datetime import datetime
from pathlib import Path

# 配置根日志器
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# 控制台日志处理
console_handler = logging.StreamHandler()
log_formatter = logging.Formatter(
    '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)

logger = logging.getLogger("BilibiliSplash")

# API 端点配置
SPLASH_API = "https://app.bilibili.com/x/v2/splash/show"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://www.bilibili.com/",
    "Origin": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
DEFAULT_PARAMS = {
    "appkey": "1d8b6e7d45233436",
    "build": "100000",
    "platform": random.choice(["android", "ios", "web"]),
    "device": random.choice(["phone", "tablet"]),
    "channel": random.choice(["xiaomi", "huawei", "samsung"])
}

class SplashDownloader:
    def __init__(self, output_dir="splash", url_file="splash_urls.txt", log_file="splash.log", use_proxy=False):
        self.output_dir = Path(output_dir).resolve()
        self.url_file = Path(url_file).resolve()
        self.log_file = Path(log_file).resolve()
        self.use_proxy = use_proxy
        
        # 创建必要的目录和文件
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.url_file.touch(exist_ok=True)
        self.log_file.touch(exist_ok=True)
        
        # 设置文件日志处理器
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(log_formatter)
        root_logger.addHandler(file_handler)
        
        # 记录初始化信息
        logger.info("=" * 70)
        logger.info(f"⚙️ Splash Downloader Initialized at {datetime.now()}")
        logger.info(f"📁 Output Directory: {self.output_dir}")
        logger.info(f"🔤 URL File: {self.url_file}")
        logger.info(f"📝 Log File: {self.log_file}")
        logger.info(f"🌐 API: {SPLASH_API}")
        logger.info(f"🔌 Proxy Enabled: {use_proxy}")
        logger.info("=" * 70)
        
        # 初始化计数器
        self.downloaded_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.start_time = time.time()
        
        # 加载URL列表
        self.url_set = self._load_url_set()
    
    def _load_url_set(self):
        """加载URL集合"""
        url_set = set()
        try:
            with open(self.url_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '|' in line:
                        _, url = line.split('|', 1)
                        url_set.add(url.strip())
                    elif line:
                        url_set.add(line.strip())
            logger.info(f"Loaded {len(url_set)} URLs from URL list")
        except Exception as e:
            logger.error(f"Error loading URL set: {str(e)}")
        return url_set
    
    def _save_url(self, content_hash, url):
        """保存URL到文件"""
        try:
            with open(self.url_file, 'a', encoding='utf-8') as f:
                f.write(f"{content_hash}|{url}\n")
            self.url_set.add(url)
        except Exception as e:
            logger.error(f"Error saving URL: {str(e)}")
    
    def _fetch_splash_list(self):
        """获取开屏图列表"""
        try:
            logger.info("🌐 Requesting splash list from API...")
            start_time = time.time()
            
            # 添加缓存破坏者
            params = DEFAULT_PARAMS.copy()
            params["ts"] = int(time.time())
            
            response = requests.get(
                SPLASH_API,
                headers=HEADERS,
                params=params,
                timeout=20
            )
            elapsed = time.time() - start_time
            
            logger.info(f"📡 Received response in {elapsed:.2f}s: HTTP {response.status_code}")
            logger.debug(f"Request URL: {response.url}")
            
            # 保存原始响应用于调试
            with open("api_response.json", "w", encoding="utf-8") as f:
                json.dump({
                    "url": response.url,
                    "status": response.status_code,
                    "headers": dict(response.headers),
                    "content": response.text
                }, f, ensure_ascii=False, indent=2)
            
            if response.status_code != 200:
                logger.error(f"API request failed with status: {response.status_code}")
                return None
                
            data = response.json()
            
            # 检查API响应状态码
            if data.get('code') != 0:
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"API error: {error_msg}")
                return None
                
            # 尝试不同的数据路径
            splash_list = data.get('data', {}).get('list', [])
            if not splash_list:
                splash_list = data.get('data', [])
            
            if not splash_list:
                logger.warning("No splash images found in API response")
                return []
                
            logger.info(f"📚 Found {len(splash_list)} splash items")
            return splash_list
        except Exception as e:
            logger.exception(f"Failed to fetch splash list: {str(e)}")
            return None
    
    def _download_image(self, url):
        """下载单个图片"""
        if not url or len(url) < 10:
            return False
            
        # 检查URL是否已处理
        if url in self.url_set:
            self.skipped_count += 1
            logger.debug(f"Skipping already processed URL: {url}")
            return False
            
        try:
            logger.info(f"⬇️ Downloading: {url}")
            
            # 添加缓存破坏者
            url_with_ts = f"{url}{'&' if '?' in url else '?'}ts={int(time.time())}"
            
            response = requests.get(url_with_ts, headers=HEADERS, timeout=30, stream=True)
            response.raise_for_status()
            
            # 计算内容哈希
            hash_sha256 = hashlib.sha256()
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    hash_sha256.update(chunk)
                    content += chunk
            
            content_hash = hash_sha256.hexdigest()
            
            # 检查文件是否已存在
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"{content_hash}_{timestamp}_splash.jpg"
            save_path = self.output_dir / filename
            
            if save_path.exists():
                self.skipped_count += 1
                logger.info(f"⏩ Content already exists: {filename}")
                self._save_url(content_hash, url)
                return True
                
            # 保存文件
            with open(save_path, 'wb') as f:
                f.write(content)
            
            # 记录URL
            self._save_url(content_hash, url)
            
            self.downloaded_count += 1
            file_size = len(content) // 1024
            logger.info(f"✅ Saved: {filename} ({file_size} KB)")
            return True
        except Exception as e:
            self.failed_count += 1
            logger.error(f"❌ Download failed: {str(e)}")
            return False
    
    def run(self):
        """执行下载流程"""
        logger.info("🚀 Starting splash image download")
        success = False
        
        try:
            splash_list = self._fetch_splash_list()
            
            if splash_list is None:
                logger.error("❌ Failed to fetch splash list")
                return False
                
            # 处理每个开屏图
            for item in splash_list:
                try:
                    # 尝试可能的URL字段
                    thumb_url = item.get('thumb') or item.get('image') or item.get('url')
                    if thumb_url:
                        self._download_image(thumb_url)
                except Exception as e:
                    logger.error(f"Error processing item: {str(e)}")
            
            # 即使没有下载到新图片也视为成功
            success = True
        except Exception as e:
            logger.exception(f"Critical error: {str(e)}")
            success = False
        finally:
            # 生成总结报告
            elapsed = time.time() - self.start_time
            logger.info("\n" + "=" * 60)
            logger.info(f"🚀 Download Summary - {elapsed:.2f} seconds")
            logger.info(f"✅ Downloaded: {self.downloaded_count}")
            logger.info(f"⏩ Skipped: {self.skipped_count}")
            logger.info(f"❌ Failed: {self.failed_count}")
            logger.info(f"🏁 Status: {'Success' if success else 'Failed'}")
            logger.info("=" * 60)
            
            return success

def main():
    parser = argparse.ArgumentParser(description="Bilibili Splash Image Downloader")
    parser.add_argument("--output", default="splash", help="Output directory for images")
    parser.add_argument("--url-file", default="splash_urls.txt", help="File to track downloaded URLs")
    parser.add_argument("--log-file", default="splash.log", help="Path to log file")
    parser.add_argument("--proxy", action="store_true", help="Use proxy for requests")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        root_logger.setLevel(logging.DEBUG)
    
    # 创建下载器实例
    downloader = SplashDownloader(
        output_dir=args.output,
        url_file=args.url_file,
        log_file=args.log_file,
        use_proxy=args.proxy
    )
    
    # 执行下载
    success = downloader.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
