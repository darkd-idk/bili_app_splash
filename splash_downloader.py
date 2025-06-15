#!/usr/bin/env python3
"""
Bilibili Splash Image Downloader (Stable Version)

Version: 1.1.0
Updated: 2025-06-15
Fixes: API response structure handling
"""

import argparse
import hashlib
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
import requests

# 配置日志
logger = logging.getLogger("BilibiliSplash")
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# API 端点配置
SPLASH_API = "https://api.bilibili.com/x/v2/splash/list"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}

class SplashDownloader:
    def __init__(self, output_dir="splash", url_file="splash_urls.txt", log_file="splash.log"):
        self.output_dir = Path(output_dir)
        self.url_file = Path(url_file)
        self.log_file = Path(log_file)
        
        # 创建必要的目录和文件
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.url_file.touch(exist_ok=True)
        self.log_file.touch(exist_ok=True)
        
        # 设置文件日志
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'))
        logger.addHandler(file_handler)
        
        # 初始化计数器
        self.downloaded_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.start_time = time.time()
        
        # 加载URL列表
        self.url_set = self._load_url_set()
        
        logger.info("=" * 70)
        logger.info(f"📁 Output Directory: {self.output_dir}")
        logger.info(f"🔤 URL File: {self.url_file}")
        logger.info(f"📝 Log File: {self.log_file}")
        logger.info("=" * 70)
    
    def _load_url_set(self):
        """加载URL集合"""
        url_set = set()
        try:
            if self.url_file.stat().st_size > 0:
                with open(self.url_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if '|' in line:
                            _, url = line.split('|', 1)
                            url_set.add(url.strip())
                        else:
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
            logger.info(f"🌐 Requesting splash list from API: {SPLASH_API}")
            
            # 添加随机参数避免缓存
            params = {
                "platform": "android",
                "device": "phone",
                "_": int(time.time() * 1000)  # 时间戳参数避免缓存
            }
            
            response = requests.get(
                SPLASH_API,
                headers=HEADERS,
                params=params,
                timeout=20
            )
            
            logger.info(f"📡 Received response: {response.status_code}")
            
            # 检测响应状态
            if response.status_code != 200:
                logger.error(f"API returned non-200 status: {response.status_code}")
                return None
                
            # 确保响应不为空
            if not response.text.strip():
                logger.error("API returned empty response")
                return None
                
            # 尝试解析JSON
            try:
                data = response.json()
                
                # 确保是有效的API响应
                if not isinstance(data, dict):
                    logger.error("API response is not a JSON object")
                    return None
                    
                # 检查API错误代码
                if data.get('code') != 0:
                    error_msg = data.get('message', 'Unknown error')
                    logger.error(f"API error: {error_msg}")
                    return None
                    
                # 获取开屏图列表 - 处理不同的API响应结构
                splash_list = []
                
                # 情况1: 包含多个数组
                if data.get('data') and isinstance(data['data'], list) and len(data['data']) > 0:
                    # API返回了多个数组 - 如 ["summer", "spring", ...]
                    for sublist in data['data']:
                        if isinstance(sublist, list):
                            splash_list.extend(sublist)
                        else:
                            splash_list.append(sublist)
                # 情况2: 直接是列表
                elif data.get('data') and isinstance(data['data'], list):
                    splash_list = data['data']
                # 情况3: 字典中嵌套列表
                elif data.get('data') and isinstance(data['data'], dict):
                    splash_list = list(data['data'].values())[0]
                # 情况4: 其他结构
                else:
                    logger.warning("No splash list found in expected locations")
                    return None
                
                if not splash_list:
                    logger.warning("No splash images in API response")
                    return []
                    
                logger.info(f"📚 Found {len(splash_list)} splash items")
                return splash_list
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {str(e)}")
                logger.debug(f"Response content: {response.text[:500]}...")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return None
    
    def _parse_image_url(self, item):
        """从API项中解析图片URL - 处理多种数据结构"""
        # 情况1: 项目直接是字符串格式的URL
        if isinstance(item, str):
            # 检查字符串是否符合URL格式
            if re.match(r'^https?://[^\s/$.?#].[^\s]*$', item):
                return item
            else:
                logger.warning(f"Item is string but not a valid URL: {item}")
                return None
        
        # 情况2: 项目是字典格式
        elif isinstance(item, dict):
            # 尝试多个可能的字段名
            url_fields = ['thumb', 'image', 'url', 'img_url', 'source']
            for field in url_fields:
                if item.get(field):
                    return item[field]
            
            # 检查嵌套结构
            if item.get('resources') and isinstance(item['resources'], dict):
                if item['resources'].get('image'):
                    return item['resources']['image']
            
            logger.warning(f"No image URL found in item: {item}")
            return None
        
        # 情况3: 其他无法处理的数据类型
        else:
            logger.warning(f"Unsupported item type: {type(item)}")
            return None
    
    def _download_image(self, url):
        """下载单个图片"""
        if not url or len(url) < 10:
            return False
            
        # 检查URL是否已处理
        if url in self.url_set:
            self.skipped_count += 1
            logger.info(f"⏩ URL already processed: {url}")
            return False
            
        try:
            logger.info(f"⬇️ Downloading: {url}")
            
            # 添加时间戳避免缓存
            url += ('&' if '?' in url else '?') + f"ts={int(time.time())}"
            
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            # 计算内容哈希
            content_hash = hashlib.sha256(response.content).hexdigest()
            
            # 创建文件名
            filename = f"{content_hash}.jpg"
            save_path = self.output_dir / filename
            
            # 如果文件已存在，跳过保存
            if save_path.exists():
                self.skipped_count += 1
                logger.info(f"⏩ Content already exists: {filename}")
                return True
                
            # 保存文件
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            # 记录URL
            self._save_url(content_hash, url)
            
            self.downloaded_count += 1
            file_size = len(response.content) // 1024
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
                
            # 处理每个开屏图项目
            for item in splash_list:
                try:
                    # 获取图片URL - 支持多种数据结构
                    img_url = self._parse_image_url(item)
                    
                    if img_url:
                        self._download_image(img_url)
                except Exception as e:
                    logger.error(f"Error processing item: {str(e)}")
                    self.failed_count += 1
            
            success = True
        except Exception as e:
            logger.exception(f"Critical error: {str(e)}")
            success = False
            
        # 生成总结报告
        elapsed = time.time() - self.start_time
        logger.info("=" * 60)
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
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("🐛 Debug mode enabled")
    
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
