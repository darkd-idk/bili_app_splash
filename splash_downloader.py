#!/usr/bin/env python3
"""
Bilibili Splash Image Downloader (Robust API Handling)

Version: 7.0.0
Updated: 2025-06-15
"""

import argparse
import hashlib
import json
import logging
import os
import random
import re
import sys
import time
import requests
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

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
SPLASH_API = "https://api.bilibili.com/x/v2/splash/show"
ALTERNATE_API = "https://api.bilibili.com/x/v2/splash/list"
BACKUP_API = "https://api.bilibili.com/x/v2/splash"
DEVICE_MODELS = ["iPhone15,3", "Xiaomi Mi 10", "Huawei P40 Pro", "Samsung Galaxy S23"]

# 创建真实的用户代理列表
USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "Mozilla/5.0 (Linux; Android 13; SM-S901U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1"
]

class SplashDownloader:
    def __init__(self, output_dir="splash", url_file="splash_urls.txt", log_file="splash.log", use_proxy=False):
        # 解析输出目录为绝对路径
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
        logger.info(f"🌐 Proxy Enabled: {use_proxy}")
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
            if self.url_file.stat().st_size > 0:
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
    
    def _get_headers(self):
        """创建真实的请求头"""
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "DNT": "1",
            "Origin": "https://www.bilibili.com",
            "Referer": "https://www.bilibili.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "User-Agent": random.choice(USER_AGENTS)
        }
        
        # 添加设备相关信息
        if "Android" in headers["User-Agent"]:
            headers["X-Bili-Device-Name"] = random.choice(DEVICE_MODELS)
            headers["X-Bili-Device-Type"] = "phone"
        elif "iPhone" in headers["User-Agent"] or "iPad" in headers["User-Agent"]:
            headers["X-Bili-Device-Name"] = "iPhone"
            headers["X-Bili-Device-Type"] = "ios"
        
        return headers
    
    def _make_api_request(self, api_url):
        """发送API请求并返回响应内容"""
        try:
            # 创建请求参数
            params = {
                "appkey": "1d8b6e7d45233436",
                "build": "100000",
                "platform": "android" if "Android" in self._get_headers()["User-Agent"] else "ios",
                "device": "phone",
                "channel": random.choice(["xiaomi", "huawei", "samsung", "apple"]),
                "ts": str(int(time.time()))
            }
            
            logger.info(f"🌐 Requesting: {api_url}")
            logger.debug(f"Headers: {json.dumps(self._get_headers(), indent=2)}")
            logger.debug(f"Params: {json.dumps(params, indent=2)}")
            
            # 发送请求
            response = requests.get(
                api_url,
                headers=self._get_headers(),
                params=params,
                timeout=20,
                verify=not self.use_proxy  # 使用代理时跳过SSL验证
            )
            
            # 保存原始响应
            response_timestamp = int(time.time())
            response_file = f"api_response_{response_timestamp}.txt"
            with open(response_file, "w", encoding="utf-8") as f:
                f.write(f"URL: {response.url}\n")
                f.write(f"Status Code: {response.status_code}\n")
                f.write(f"Headers: {json.dumps(dict(response.headers), indent=2)}\n")
                f.write("\nResponse Body:\n")
                f.write(response.text)
            
            logger.info(f"📡 Response saved to {response_file}")
            logger.info(f"🔄 Status Code: {response.status_code}")
            
            return response
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return None
    
    def _process_api_response(self, response):
        """处理API响应并提取开屏图列表"""
        if not response or response.status_code != 200:
            return None
            
        content_type = response.headers.get("Content-Type", "").lower()
        
        # 处理JSON响应
        if "application/json" in content_type:
            try:
                return response.json()
            except json.JSONDecodeError:
                logger.warning("JSON decode failed, trying to extract from text")
                return self._extract_json(response.text)
        
        # 处理可能的错误响应
        if response.text.strip() == "":
            logger.error("Empty API response")
            return None
        
        # 尝试提取JSON
        return self._extract_json(response.text)
    
    def _extract_json(self, text):
        """从响应文本中提取JSON"""
        try:
            # 尝试直接解析
            return json.loads(text)
        except:
            # 尝试查找JSON对象
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    logger.error("Failed to extract JSON from response")
            return None
    
    def _get_splash_items(self, api_data):
        """从API数据中获取开屏图列表"""
        if not api_data or not isinstance(api_data, dict):
            return None
            
        # 检查错误代码
        if api_data.get("code") != 0:
            error_msg = api_data.get("message", "Unknown error")
            logger.error(f"API error: {error_msg}")
            return None
            
        # 尝试所有可能的路径
        possible_paths = [
            api_data.get("data", {}).get("list", []),
            api_data.get("data", {}).get("splash_list", []),
            api_data.get("data", []),
            api_data.get("list", []),
            api_data.get("splash", []),
            api_data.get("images", [])
        ]
        
        for path in possible_paths:
            if isinstance(path, list) and path:
                return path
        
        logger.warning("No splash items found in API response")
        return []
    
    def _fetch_splash_list(self):
        """获取开屏图列表，支持多个API端点"""
        endpoints = [
            SPLASH_API,
            ALTERNATE_API,
            BACKUP_API,
            "https://app.bilibili.com/x/v2/splash/show"
        ]
        
        # 随机打乱端点顺序
        random.shuffle(endpoints)
        
        for api_url in endpoints:
            # 添加唯一参数避免缓存
            parsed = urlparse(api_url)
            query = parse_qs(parsed.query)
            query["_t"] = str(int(time.time() * 1000))
            api_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                urlencode(query, doseq=True),
                parsed.fragment
            ))
            
            response = self._make_api_request(api_url)
            api_data = self._process_api_response(response)
            
            if not api_data:
                continue
                
            splash_items = self._get_splash_items(api_data)
            
            if splash_items is not None:
                return splash_items
        
        logger.error("All API endpoints failed")
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
            
            # 添加随机参数避免CDN缓存
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            query["_"] = str(int(time.time() * 1000))
            url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                urlencode(query, doseq=True),
                parsed.fragment
            ))
            
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            
            # 计算内容哈希
            content_hash = hashlib.sha256(response.content).hexdigest()
            
            # 检查文件是否已存在
            existing_files = list(self.output_dir.glob(f"{content_hash}_*"))
            if existing_files:
                self.skipped_count += 1
                logger.info(f"⏩ Content already exists: {existing_files[0].name}")
                self._save_url(content_hash, url)
                return True
                
            # 创建文件名
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"{content_hash}_{timestamp}_splash.jpg"
            save_path = self.output_dir / filename
            
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
                logger.error("❌ Failed to fetch splash list from all APIs")
                return False
                
            logger.info(f"📚 Found {len(splash_list)} splash items")
                
            # 处理每个开屏图
            for item in splash_list:
                try:
                    # 尝试多种可能的字段
                    image_fields = ["thumb", "image", "url", "image_url", "splash", "cover"]
                    for field in image_fields:
                        if item.get(field):
                            self._download_image(item[field])
                            break
                    else:
                        logger.warning(f"⚠️ No valid image URL found in item: {json.dumps(item)[:200]}")
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
        logger.debug("🐛 Debug mode enabled")
    
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
