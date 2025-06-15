#!/usr/bin/env python3
"""
Bilibili Splash Image Downloader (Content Hash Deduplication)

Version: 4.0.0
Updated: 2025-06-15
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
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

# API 端点
SPLASH_API = "https://app.bilibili.com/x/v2/splash/show"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://www.bilibili.com/",
    "Origin": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
}

class SplashDownloader:
    def __init__(self, output_dir="splash", url_file="splash_urls.txt", log_file="splash.log"):
        # 解析输出目录为绝对路径
        self.output_dir = Path(output_dir).resolve()
        self.url_file = Path(url_file).resolve()
        self.log_file = Path(log_file).resolve()
        
        # 确保所有目录和文件存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.url_file.touch(exist_ok=True)
        self.log_file.touch(exist_ok=True)
        
        # 初始化文件日志
        self.setup_file_logger()
        
        # 初始化计数器
        self.downloaded_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.start_time = time.time()
        
        # 加载URL列表
        self.url_list = self.load_url_list()
        
        logger.info("=" * 70)
        logger.info(f"⚙️ Splash Downloader Initialized")
        logger.info(f"📁 Output Directory: {self.output_dir}")
        logger.info(f"📝 URL File: {self.url_file} ({len(self.url_list)} URLs)")
        logger.info(f"📋 Log File: {self.log_file}")
        logger.info(f"🌐 API Endpoint: {SPLASH_API}")
        logger.info("=" * 70)
    
    def setup_file_logger(self):
        """设置文件日志记录器"""
        file_handler = logging.FileHandler(self.log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        
        # 记录初始化信息
        logging.info("\n" + "=" * 70)
        logging.info(f"{' Bilibili Splash Downloader ':^70}")
        logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^70}")
        logging.info("=" * 70)
    
    def load_url_list(self):
        """加载已处理的URL列表"""
        url_set = set()
        try:
            with open(self.url_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        # 格式：hash|url 或 url
                        parts = line.split('|')
                        if len(parts) == 2:
                            url_set.add(parts[1])  # 提取URL
                        else:
                            url_set.add(line)
            logger.info(f"Loaded {len(url_set)} URLs from {self.url_file}")
        except Exception as e:
            logger.error(f"Failed to load URL list: {str(e)}")
        return url_set
    
    def save_url_to_list(self, content_hash, url):
        """将URL保存到文件"""
        with open(self.url_file, 'a', encoding='utf-8') as f:
            f.write(f"{content_hash}|{url}\n")
    
    def download_image(self, url, metadata=None):
        """下载单个开屏图 - 使用内容哈希避免重复"""
        if not url or len(url) < 10:
            logger.warning("Skipping invalid URL")
            return None
            
        # 检查URL是否已处理
        if url in self.url_list:
            self.skipped_count += 1
            logger.debug(f"URL already processed: {url}")
            return None
            
        # 下载图像
        try:
            logger.info(f"🌐 Downloading: {url}")
            response = requests.get(url, headers=HEADERS, timeout=30, stream=True)
            response.raise_for_status()
            
            # 计算内容哈希
            hash_sha256 = hashlib.sha256()
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    hash_sha256.update(chunk)
                    content += chunk
                    
            content_hash = hash_sha256.hexdigest()
            
            # 检查是否已有相同内容的文件
            existing_file = None
            for file in self.output_dir.iterdir():
                if file.is_file() and file.stem.startswith(content_hash):
                    existing_file = file
                    break
            
            # 如果相同内容已存在
            if existing_file:
                logger.info(f"🎯 Identical content found: {existing_file.name}")
                self.skipped_count += 1
                # 记录URL以防下次重新下载
                self.url_list.add(url)
                self.save_url_to_list(content_hash, url)
                return existing_file
                
            # 创建文件名：哈希值 + 日期 + 时间
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"{content_hash}_{timestamp}_splash.jpg"
            save_path = self.output_dir / filename
            
            # 保存文件
            with open(save_path, 'wb') as f:
                f.write(content)
            
            # 记录URL
            self.url_list.add(url)
            self.save_url_to_list(content_hash, url)
            
            self.downloaded_count += 1
            file_size = len(content) // 1024
            logger.info(f"✅ Downloaded: {save_path.name} ({file_size} KB)")
            
            return save_path
        except Exception as e:
            self.failed_count += 1
            logger.error(f"❌ Failed to download {url}: {str(e)}")
            return None
    
    def run(self):
        """执行下载过程"""
        logger.info("🏁 Starting splash image download")
        success = False
        
        try:
            splash_list = self.fetch_splash_list()
            
            if splash_list is None:
                logger.error("❌ Failed to fetch splash list")
                return False
                
            # 处理每个开屏图
            for splash in splash_list:
                try:
                    thumb_url = splash.get('thumb')
                    if thumb_url:
                        self.download_image(thumb_url, splash)
                except Exception as e:
                    logger.error(f"Error processing splash item: {str(e)}")
            
            # 即使为空也视为成功
            success = True
        except Exception as e:
            logger.exception(f"Critical error: {str(e)}")
            success = False
        finally:
            # 生成总结报告
            elapsed = time.time() - self.start_time
            summary = [
                "",
                "=" * 60,
                f"🚀 Splash Download Summary - {elapsed:.2f} seconds",
                f"✅ Downloaded: {self.downloaded_count}",
                f"⏩ Skipped: {self.skipped_count}",
                f"❌ Failed: {self.failed_count}",
                f"🏁 Status: {'Success' if success else 'Failed'}",
                "=" * 60,
                ""
            ]
            
            # 将摘要写入日志文件
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write("\n".join(summary))
            
            return success

    def fetch_splash_list(self):
        """获取开屏图列表"""
        try:
            logger.info(f"🌍 Requesting splash list from API: {SPLASH_API}")
            response = requests.get(SPLASH_API, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            logger.info(f"📡 Received response: {response.status_code}")
            
            data = response.json()
            
            # 验证API响应
            if data.get('code') != 0:
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"API error: {error_msg}")
                return None
                
            splash_list = data.get('data', {}).get('list', [])
            if not splash_list:
                logger.warning("No splash images in API response")
                return []
                
            logger.info(f"📚 Found {len(splash_list)} splash items")
            return splash_list
        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            return None

def main():
    """命令行入口点"""
    parser = argparse.ArgumentParser(description="Bilibili Splash Image Downloader")
    parser.add_argument("--output", default="splash", help="Output directory for images")
    parser.add_argument("--url-file", default="splash_urls.txt", help="File to record downloaded URLs")
    parser.add_argument("--log-file", default="splash.log", help="Path to log file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # 设置调试级别
    if args.debug:
        root_logger.setLevel(logging.DEBUG)
        logger.debug("🚧 Debug mode enabled")
    
    # 创建下载器实例
    downloader = SplashDownloader(
        output_dir=args.output,
        url_file=args.url_file,
        log_file=args.log_file
    )
    
    # 执行下载
    success = downloader.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
