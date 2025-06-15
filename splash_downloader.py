#!/usr/bin/env python3
"""
Bilibili Splash Image Downloader (Complete Solution with Enhanced API Handling)

Version: 5.0.0
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
import random
import traceback

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
ALTERNATE_API = "https://api.bilibili.com/x/v2/splash/list"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://www.bilibili.com/",
    "Origin": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}
DEFAULT_PARAMS = {
    "appkey": "1d8b6e7d45233436",
    "build": "100000",
    "platform": "android",
    "device": "phone",
    "channel": "xiaomi"
}
PROXIES = {
    "http": "socks5h://your-proxy:1080",
    "https": "socks5h://your-proxy:1080"
}

class SplashDownloader:
    def __init__(self, output_dir="splash", url_file="splash_urls.txt", log_file="splash.log", use_proxy=False):
        # 解析输出目录为绝对路径
        self.output_dir = Path(output_dir).resolve()
        self.url_file = Path(url_file).resolve()
        self.log_file = Path(log_file).resolve()
        self.use_proxy = use_proxy
        
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
        logger.info(f"🔌 Proxy Enabled: {use_proxy}")
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
            if self.url_file.is_file() and self.url_file.stat().st_size > 0:
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
    
    def request_api(self, api_url, params):
        """发送API请求，支持重试和代理"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 添加随机延迟避免限流
                time.sleep(random.uniform(0.5, 1.5))
                
                request_headers = {**HEADERS}
                request_params = {**DEFAULT_PARAMS, **params}
                
                # 记录请求详情
                logger.info(f"🌐 Request attempt {attempt+1}/{max_retries}")
                logger.debug(f"Request URL: {api_url}")
                logger.debug(f"Request Headers: {json.dumps(request_headers, indent=2)}")
                logger.debug(f"Request Params: {json.dumps(request_params, indent=2)}")
                
                # 使用代理
                proxies = PROXIES if self.use_proxy else None
                verify_ssl = not self.use_proxy  # 使用代理时不验证SSL
                
                response = requests.get(
                    api_url,
                    headers=request_headers,
                    params=request_params,
                    timeout=30,
                    proxies=proxies,
                    verify=verify_ssl
                )
                
                # 记录响应详情
                logger.info(f"📡 Received response: {response.status_code}, size: {len(response.content)} bytes")
                logger.debug(f"Response Headers: {response.headers}")
                
                # 保存原始响应
                with open("api_response.json", "w", encoding="utf-8") as f:
                    json.dump({"url": api_url, "params": request_params, "response": response.text}, f, ensure_ascii=False, indent=2)
                
                # 检查响应状态码
                if response.status_code != 200:
                    logger.warning(f"API returned non-200 status: {response.status_code}")
                    continue  # 重试
                
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {str(e)}")
                    logger.debug(f"Response content: {response.text[:500]}")
                    continue  # 重试
                
                return data
            except requests.RequestException as e:
                logger.warning(f"Request failed: {str(e)}, retrying...")
                time.sleep(2 ** attempt)  # 指数退避
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                break
        
        logger.error(f"API request failed after {max_retries} attempts")
        return None
    
    def fetch_splash_list(self):
        """获取开屏图列表，支持主备API"""
        # 尝试主API
        api_urls = [
            {"url": SPLASH_API, "params": {"plat": 0}},
            {"url": ALTERNATE_API, "params": {"plat": 1}},
            {"url": SPLASH_API, "params": {"plat": 2}}  # 尝试不同平台
        ]
        
        # 随机排序API列表
        random.shuffle(api_urls)
        
        for api in api_urls:
            data = self.request_api(api["url"], api["params"])
            if not data:
                continue
            
            # 检查API错误代码
            if data.get('code') != 0:
                error_msg = data.get('message', 'Unknown error')
                logger.warning(f"API error [{data.get('code')}]: {error_msg}")
                continue
            
            # 尝试不同数据路径
            data_paths = [
                data.get('data', {}).get('list', []),
                data.get('data', []),
                data.get('list', [])
            ]
            
            for path in data_paths:
                if isinstance(path, list) and path:
                    logger.info(f"📚 Found {len(path)} splash items at API: {api['url']}")
                    return path
            
            logger.debug(f"API response data paths: {json.dumps(data, indent=2)}")
        
        logger.error("All API endpoints failed to return valid splash items")
        return None
    
    def download_image(self, url, metadata=None):
        """下载单个开屏图 - 使用内容哈希避免重复"""
        if not url or len(url) < 10:
            logger.warning("Skipping invalid URL")
            return None
            
        # 检查URL是否已处理
        if url in self.url_list:
            self.skipped_count += 1
            logger.info(f"⏩ URL already processed: {url}")
            return None
            
        # 下载图像
        try:
            logger.info(f"⬇️ Downloading: {url}")
            # 使用代理设置
            proxies = PROXIES if self.use_proxy else None
            verify_ssl = not self.use_proxy
            
            response = requests.get(
                url, 
                headers=HEADERS,
                timeout=30, 
                stream=True,
                proxies=proxies,
                verify=verify_ssl
            )
            response.raise_for_status()
            
            # 计算内容哈希
            hash_sha256 = hashlib.sha256()
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    hash_sha256.update(chunk)
                    content += chunk
                    
            content_hash = hash_sha256.hexdigest()
            logger.debug(f"Content SHA256: {content_hash}")
            
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
                
            # 创建唯一文件名
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
            file_size = save_path.stat().st_size // 1024
            logger.info(f"✅ Downloaded: {save_path.name} ({file_size} KB)")
            
            return save_path
        except Exception as e:
            self.failed_count += 1
            logger.error(f"❌ Failed to download {url}: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
    
    def run(self):
        """执行下载过程"""
        logger.info("🚀 Starting splash image download")
        success = False
        
        try:
            splash_list = self.fetch_splash_list()
            
            if splash_list is None:
                logger.error("❌ Failed to fetch splash list from any API")
                return False
                
            if not splash_list:
                logger.warning("⚠️ API returned empty splash list")
                # 即使为空也视为成功
                return True
                
            logger.info(f"🔍 Processing {len(splash_list)} splash items")
            
            # 处理每个开屏图
            for splash in splash_list:
                try:
                    # 尝试多种可能的缩略图字段
                    thumb_fields = ['thumb', 'image', 'url', 'image_url', 'splash_url']
                    
                    for field in thumb_fields:
                        thumb_url = splash.get(field)
                        if thumb_url:
                            result = self.download_image(thumb_url, splash)
                            if result:
                                break
                    else:
                        logger.warning(f"🔍 No valid thumb URL found in item: {splash}")
                except Exception as e:
                    logger.error(f"🚨 Error processing splash item: {str(e)}")
                    logger.debug(traceback.format_exc())
            
            # 即使没有下载到新图片也视为成功（可能都是重复图片）
            success = True
        except Exception as e:
            logger.error(f"🔥 Critical error: {str(e)}")
            logger.debug(traceback.format_exc())
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

def main():
    """命令行入口点"""
    parser = argparse.ArgumentParser(description="Bilibili Splash Image Downloader")
    parser.add_argument("--output", default="splash", help="Output directory for images")
    parser.add_argument("--url-file", default="splash_urls.txt", help="File to record downloaded URLs")
    parser.add_argument("--log-file", default="splash.log", help="Path to log file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--proxy", action="store_true", help="Use proxy for requests")
    args = parser.parse_args()
    
    # 设置调试级别
    if args.debug:
        root_logger.setLevel(logging.DEBUG)
        logger.debug("🚧 Debug mode enabled")
    
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
