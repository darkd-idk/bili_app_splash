#!/usr/bin/env python3
"""
Bilibili Wallpaper Girl Downloader - Optimized and Fixed Version

Version: 1.4.2
Fixed: 2025-06-15
"""

import argparse
import concurrent.futures
import json
import logging
import math
import os
import sys
import time
from datetime import datetime
from urllib.parse import urlparse

import requests

# 创建根日志记录器
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# 控制台日志处理
console_handler = logging.StreamHandler()
log_formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)

logger = logging.getLogger("BilibiliWallpaper")

# 全局常量
WALLPAPER_UID = 6823116  # Wallpaper Girl account UID
API_URL = "https://api.vc.bilibili.com/link_draw/v1/doc/others"
DEFAULT_PAGE_SIZE = 45
MAX_RETRIES = 5  # 增加重试次数
RETRY_DELAY = 2  # seconds
REQUEST_TIMEOUT = 45  # 增加超时时间
MAX_CONCURRENT_DOWNLOADS = 8  # 防止限流
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://www.bilibili.com/",
    "Accept": "application/json",
    "Origin": "https://www.bilibili.com",
    "DNT": "1",
}
URLS_FILE = "urls.txt"

class WallpaperDownloader:
    def __init__(self, sessdata: str, output_dir: str = "bizhiniang", page_size: int = DEFAULT_PAGE_SIZE):
        self.sessdata = sessdata
        self.output_dir = os.path.abspath(output_dir)
        self.page_size = page_size
        self.downloaded_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.album_counts = {}
        self.start_time = time.time()
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化URL跟踪文件
        with open(URLS_FILE, "w", encoding="utf-8") as f:
            f.write("# Wallpaper URL Record\n")
            f.write(f"# Generated at {datetime.utcnow().isoformat()}Z\n\n")
        
        logger.info(f"Initialized Wallpaper Downloader (Output: {self.output_dir})")
        logger.debug(f"Using SESSDATA: {sessdata[:4]}...{sessdata[-4:]}")

    def _is_valid_response(self, response_data: dict) -> bool:
        """验证API响应是否有效"""
        if not response_data:
            logger.error("API response is empty")
            return False
            
        if response_data.get("code") != 0:
            logger.error(f"API returned non-zero code: {response_data.get('code')}, message: {response_data.get('message')}")
            return False
            
        if "data" not in response_data:
            logger.error("API response missing 'data' field")
            return False
            
        return True

    def _api_request(self, page: int = 0) -> dict:
        """获取壁纸数据API请求"""
        params = {
            "biz": 0,
            "poster_uid": WALLPAPER_UID,
            "page_num": page,
            "page_size": self.page_size,
        }
        cookies = {"SESSDATA": self.sessdata}
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(
                    API_URL,
                    params=params,
                    headers=HEADERS,
                    cookies=cookies,
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                
                # 检查响应内容是否为JSON
                if "application/json" not in response.headers.get("Content-Type", ""):
                    logger.warning(f"API response is not JSON (attempt {attempt+1}/{MAX_RETRIES})")
                    continue
                
                data = response.json()
                
                # 验证响应有效性
                if self._is_valid_response(data):
                    return data
                else:
                    logger.warning(f"Invalid API response (attempt {attempt+1}/{MAX_RETRIES})")
                
            except requests.RequestException as e:
                status_code = getattr(e.response, 'status_code', None) if e.response else None
                logger.warning(f"API request failed (attempt {attempt+1}/{MAX_RETRIES}): {e} (Status: {status_code})")
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON response (attempt {attempt+1}/{MAX_RETRIES})")
            
            # 等待后重试
            time.sleep(RETRY_DELAY * (attempt + 1))
        
        logger.error("Failed to get valid API response after multiple attempts")
        return {}

    def _download_image(self, url: str, album_path: str) -> None:
        """下载单张图片"""
        image_name = os.path.basename(urlparse(url).path)
        save_path = os.path.join(album_path, image_name)
        
        # 如果已存在则跳过
        if os.path.exists(save_path):
            self.skipped_count += 1
            logger.debug(f"Skipped existing image: {image_name}")
            return
        
        # 下载图片
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(
                    url,
                    headers=HEADERS,
                    timeout=REQUEST_TIMEOUT,
                    stream=True  # 使用流式下载节省内存
                )
                response.raise_for_status()
                
                # 写入文件
                with open(save_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:  # 过滤保活块
                            f.write(chunk)
                
                # 记录URL
                with open(URLS_FILE, "a", encoding="utf-8") as url_file:
                    url_file.write(f"{os.path.basename(album_path)},{image_name},{url}\n")
                
                self.downloaded_count += 1
                logger.info(f"Downloaded: {image_name}")
                return
            except Exception as e:
                logger.warning(f"Download failed (attempt {attempt+1}/{MAX_RETRIES}): {url} - {e}")
                time.sleep(RETRY_DELAY * (attempt + 1))
        
        self.failed_count += 1
        logger.error(f"Failed to download: {url}")

    def _process_album(self, album_data: dict) -> None:
        """处理相册中的图片"""
        if not album_data or "upload_time" not in album_data or "pictures" not in album_data:
            logger.warning("Invalid album data, skipping")
            return
        
        # 创建相册目录
        album_name = album_data["upload_time"].replace(":", "")
        album_path = os.path.join(self.output_dir, album_name)
        os.makedirs(album_path, exist_ok=True)
        
        # 获取所有图片URL
        image_urls = []
        for pic in album_data["pictures"]:
            if pic.get("img_src"):
                image_urls.append(pic["img_src"])
        
        # 记录相册统计
        self.album_counts[album_name] = len(image_urls)
        
        # 跳过没有图片的相册
        if not image_urls:
            logger.info(f"Skipping empty album: {album_name}")
            return
            
        logger.info(f"Processing album: {album_name} ({len(image_urls)} images)")
        
        # 使用线程池处理图片
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(MAX_CONCURRENT_DOWNLOADS, len(image_urls))
        ) as executor:
            futures = []
            for url in image_urls:
                future = executor.submit(self._download_image, url, album_path)
                futures.append(future)
            
            # 等待所有下载完成
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Download exception: {e}")
                    self.failed_count += 1

    def get_total_albums(self) -> int:
        """获取相册总数"""
        api_data = self._api_request()
        if not api_data:
            logger.error("API request failed, no data returned")
            return 0
            
        if "data" not in api_data or "total_count" not in api_data["data"]:
            logger.error(f"API response missing 'total_count'. API data: {api_data}")
            return 0
            
        return api_data["data"]["total_count"]

    def run(self) -> None:
        """主执行方法"""
        logger.info("Starting wallpaper sync process")
        
        # 获取相册总数并计算页数
        total_albums = self.get_total_albums()
        if total_albums <= 0:
            logger.error("No albums found, exiting")
            return
            
        pages = math.ceil(total_albums / self.page_size)
        logger.info(f"Found {total_albums} albums across {pages} pages")
        
        # 处理每一页
        for page in range(pages):
            logger.info(f"Processing page {page+1}/{pages}")
            api_data = self._api_request(page)
            
            if not api_data or "data" not in api_data or "items" not in api_data["data"]:
                logger.error(f"Page {page} returned invalid data")
                continue
                
            # 处理相册
            for album_data in api_data["data"]["items"]:
                self._process_album(album_data)
            
            # 限制请求频率
            time.sleep(1)
        
        # 生成最终报告
        elapsed = time.time() - self.start_time
        logger.info("\n" + "=" * 60)
        logger.info(f"Wallpaper Sync Completed - {elapsed:.1f} seconds")
        logger.info(f"- Downloaded: {self.downloaded_count} new images")
        logger.info(f"- Skipped: {self.skipped_count} existing images")
        logger.info(f"- Failed: {self.failed_count} downloads")
        logger.info(f"- Albums processed: {len(self.album_counts)}")
        if self.album_counts:
            latest_album = max(self.album_counts, key=self.album_counts.get)
            logger.info(f"- Largest album: {latest_album} ({self.album_counts[latest_album]} images)")
        logger.info("=" * 60)

def setup_logging(log_file: str = None, debug: bool = False):
    """配置日志系统"""
    # 设置日志级别
    log_level = logging.DEBUG if debug else logging.INFO
    root_logger.setLevel(log_level)
    console_handler.setLevel(log_level)
    
    # 配置文件日志
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)

def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description="Bilibili Wallpaper Girl Downloader")
    parser.add_argument("--sessdata", required=True, help="Bilibili session cookie (SESSDATA)")
    parser.add_argument("--output", default="bizhiniang", help="Output directory for images")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--log-file", default=None, help="Path to log file")
    args = parser.parse_args()
    
    # 配置日志
    setup_logging(args.log_file, args.debug)
    
    try:
        downloader = WallpaperDownloader(
            sessdata=args.sessdata,
            output_dir=args.output
        )
        downloader.run()
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Critical error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
