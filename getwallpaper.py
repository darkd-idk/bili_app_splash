#!/usr/bin/env python3
"""
Bilibili Wallpaper Girl Downloader - Final Version
修复了所有类型注解问题

Version: 1.4.1
Fixed: 2025-06-15
"""

import argparse
import concurrent.futures
import logging
import math
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List  # 添加缺失的类型导入
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
API_URL = "http://api.vc.bilibili.com/link_draw/v1/doc/others"
DEFAULT_PAGE_SIZE = 45
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
REQUEST_TIMEOUT = 30  # seconds
MAX_CONCURRENT_DOWNLOADS = 8  # Limit to prevent rate limiting
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://www.bilibili.com/",
    "Accept": "application/json",
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
        self.album_counts: Dict[str, int] = {}  # 添加类型注解
        self.start_time = time.time()
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化URL跟踪文件
        with open(URLS_FILE, "w", encoding="utf-8") as f:
            f.write("# Wallpaper URL Record\n")
            f.write(f"# Generated at {datetime.utcnow().isoformat()}Z\n\n")
        
        logger.info(f"Initialized Wallpaper Downloader (Output: {self.output_dir})")

    def _api_request(self, page: int = 0) -> Dict[str, Any]:  # 修复类型注解
        """Make API request to get wallpaper data"""
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
                return response.json()
            except requests.RequestException as e:
                logger.warning(f"API request failed (attempt {attempt+1}/{MAX_RETRIES}): {e}")
                time.sleep(RETRY_DELAY * (attempt + 1))
        return {}

    def _download_image(self, url: str, album_path: str) -> None:
        """Download a single image"""
        image_name = os.path.basename(urlparse(url).path)
        save_path = os.path.join(album_path, image_name)
        
        # Skip if already downloaded
        if os.path.exists(save_path):
            self.skipped_count += 1
            logger.debug(f"Skipped existing image: {image_name}")
            return
        
        # Download the image
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                
                # Write file
                with open(save_path, "wb") as f:
                    f.write(response.content)
                
                # Record URL
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

    def _process_album(self, album_data: Dict[str, Any]) -> None:  # 添加类型注解
        """Process an album of images"""
        if not album_data or "upload_time" not in album_data or "pictures" not in album_data:
            logger.warning("Invalid album data, skipping")
            return
        
        # Create album directory
        album_name = album_data["upload_time"].replace(":", "")
        album_path = os.path.join(self.output_dir, album_name)
        os.makedirs(album_path, exist_ok=True)
        
        # 安全获取图片URL列表
        image_urls = []
        if "pictures" in album_data:
            image_urls = [pic["img_src"] for pic in album_data["pictures"] if "img_src" in pic]
        
        # Track album stats
        self.album_counts[album_name] = len(image_urls)
        
        # Skip if album has no images
        if not image_urls:
            logger.info(f"Skipping empty album: {album_name}")
            return
            
        logger.info(f"Processing album: {album_name} ({len(image_urls)} images)")
        
        # Process images with thread pool
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(MAX_CONCURRENT_DOWNLOADS, len(image_urls))
        ) as executor:
            futures = [
                executor.submit(self._download_image, url, album_path)
                for url in image_urls
            ]
            # Wait for all downloads to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Download exception: {e}")
                    self.failed_count += 1

    def get_total_albums(self) -> int:
        """Get total number of albums available"""
        api_data = self._api_request()
        if not api_data or "data" not in api_data or "total_count" not in api_data["data"]:
            logger.error("Failed to get total album count")
            return 0
        return api_data["data"]["total_count"]

    def run(self) -> None:
        """Main execution method"""
        logger.info("Starting wallpaper sync process")
        
        # Get total albums and calculate pages needed
        total_albums = self.get_total_albums()
        if total_albums <= 0:
            logger.error("No albums found, exiting")
            return
            
        pages = math.ceil(total_albums / self.page_size)
        logger.info(f"Found {total_albums} albums across {pages} pages")
        
        # Process each page
        for page in range(pages):
            logger.info(f"Processing page {page+1}/{pages}")
            api_data = self._api_request(page)
            
            if not api_data or "data" not in api_data or "items" not in api_data["data"]:
                logger.error(f"Page {page} returned invalid data")
                continue
                
            for album_data in api_data["data"]["items"]:
                self._process_album(album_data)
            
            # Throttle requests
            time.sleep(1)
        
        # Generate final report
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
    """Configure logging system"""
    # Set root log level
    log_level = logging.DEBUG if debug else logging.INFO
    root_logger.setLevel(log_level)
    console_handler.setLevel(log_level)
    
    # Configure file logging
    if log_file:
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)

def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description="Bilibili Wallpaper Girl Downloader")
    parser.add_argument("--sessdata", required=True, help="Bilibili session cookie (SESSDATA)")
    parser.add_argument("--output", default="bizhiniang", help="Output directory for images")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--log-file", default=None, help="Path to log file")
    args = parser.parse_args()
    
    # Configure logging
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
