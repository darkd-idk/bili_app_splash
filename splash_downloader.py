#!/usr/bin/env python3
"""
Bilibili Splash Image Downloader (Final Fix Version)

Version: 1.1.0
Updated: 2025-06-15
Fixes: JSON parsing errors and sys import
"""

import requests
import os
import json
import time
import logging
import argparse
from datetime import datetime
import hashlib
import sys  # 添加sys模块导入

# 配置日志
logger = logging.getLogger("BilibiliSplash")
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# API配置
SPLASH_API = 'https://app.bilibili.com/x/v2/splash/brand/list?appkey=1d8b6e7d45233436&ts=0&sign=78a89e153cd6231a4a4d55013aa063ce'

class SplashDownloader:
    def __init__(self, output_dir="app_splash", list_file="images.json", log_file="splash.log"):
        self.output_dir = output_dir
        self.list_file = list_file
        self.log_file = log_file
        
        # 创建必要的目录和文件
        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Created output directory: {self.output_dir}")
            
        # 设置文件日志
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # 初始化状态
        self.downloaded_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.start_time = time.time()
        
        # 加载已有的图片列表
        self.existing_images = self._load_existing_images()
        
        logger.info("=" * 60)
        logger.info(f"📁 Output Directory: {self.output_dir}")
        logger.info(f"📋 Image List File: {self.list_file}")
        logger.info(f"📝 Log File: {self.log_file}")
        logger.info(f"🔗 API: {SPLASH_API}")
        logger.info("=" * 60)
    
    def _load_existing_images(self):
        """加载已有的图片列表"""
        existing_images = {}
        list_path = os.path.join(self.output_dir, self.list_file)
        if os.path.exists(list_path):
            try:
                with open(list_path, 'r') as f:
                    data = json.load(f)
                    if 'list' in data:
                        for img in data['list']:
                            existing_images[img['id']] = img
                logger.info(f"Loaded {len(existing_images)} existing images from list")
            except Exception as e:
                logger.error(f"Error loading existing image list: {str(e)}")
        return existing_images
    
    def run(self):
        """执行下载流程"""
        logger.info("🚀 Starting splash image download")
        
        try:
            # 获取API数据
            logger.info(f"🔍 Fetching splash data from API...")
            req = requests.get(SPLASH_API, timeout=15)
            
            # 检查响应状态码
            logger.info(f"📡 API status code: {req.status_code}")
            if req.status_code != 200:
                logger.error(f"API request failed with status: {req.status_code}")
                return False
                
            # 检查响应内容类型
            content_type = req.headers.get('Content-Type', '').lower()
            logger.info(f"📄 Content-Type: {content_type}")
            
            # 尝试解析JSON
            try:
                json_req = req.json()
                logger.debug(f"API response data: {json_req}")
            except json.JSONDecodeError as e:
                # 非JSON响应 - 记录响应内容
                logger.error(f"JSON parsing failed: {str(e)}")
                
                # 检查是否为HTML内容
                if '<!DOCTYPE html>' in req.text or '<html>' in req.text:
                    logger.error("⚠️ Received HTML instead of JSON response")
                    logger.error(f"HTML snippet: {req.text[:500]}")
                else:
                    logger.error(f"Response text: {req.text[:500]}")
                
                return False
            
            # 检查API响应
            if 'code' not in json_req:
                logger.error("Invalid API response: Missing 'code' field")
                return False
                
            if json_req['code'] != 0:
                error_msg = json_req.get('message', 'Unknown error')
                logger.error(f"API error: {error_msg}")
                return False
                
            # 确保有数据列表
            if 'data' not in json_req or 'list' not in json_req['data']:
                logger.error("Invalid API response structure")
                logger.debug(f"Response keys: {list(json_req.keys())}")
                if 'data' in json_req:
                    logger.debug(f"Data keys: {list(json_req['data'].keys())}")
                return False
                
            # 初始化结果
            result = {}
            result['lastSync'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            img_list = []
            
            # 处理每个开屏图
            for img in json_req['data']['list']:
                try:
                    if 'id' not in img or 'thumb' not in img:
                        logger.warning(f"⚠️ Skipping invalid image entry: {img}")
                        continue
                        
                    img_id = str(img['id'])
                    img_url = img['thumb']
                    
                    # 获取图片扩展名
                    img_format = img_url.split('.')[-1].split('?')[0].lower()
                    
                    # 创建图片信息
                    img_info = {
                        'id': img_id,
                        'url': img_url,
                        'filename': f"{img_id}.{img_format}",
                        'download_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # 检查图片是否已存在
                    file_path = os.path.join(self.output_dir, img_info['filename'])
                    
                    if img_id in self.existing_images:
                        if os.path.exists(file_path):
                            self.skipped_count += 1
                            logger.info(f"⏩ Image already exists: {img_id}")
                            img_list.append(img_info)
                            continue
                    
                    # 下载图片
                    logger.info(f"⬇️ Downloading: {img_url}")
                    imgreq = requests.get(img_url, stream=True, timeout=20)
                    
                    # 检查图片响应状态
                    if imgreq.status_code != 200:
                        logger.error(f"❌ Image download failed (status {imgreq.status_code}): {img_url}")
                        self.failed_count += 1
                        continue
                    
                    # 验证内容类型
                    image_content_type = imgreq.headers.get('Content-Type', '')
                    if not image_content_type.startswith('image/'):
                        logger.error(f"❌ Not an image response: {image_content_type}")
                        self.failed_count += 1
                        continue
                    
                    # 保存图片
                    try:
                        with open(file_path, 'wb') as image:
                            for chunk in imgreq.iter_content(8192):
                                image.write(chunk)
                        
                        # 计算文件哈希
                        with open(file_path, 'rb') as f:
                            file_hash = hashlib.sha256(f.read()).hexdigest()
                        img_info['sha256'] = file_hash
                        
                        # 添加到列表
                        img_list.append(img_info)
                        self.downloaded_count += 1
                        file_size = os.path.getsize(file_path) // 1024
                        logger.info(f"✅ Downloaded: {img_info['filename']} ({file_size} KB)")
                        
                    except Exception as e:
                        # 删除不完整的下载
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        self.failed_count += 1
                        logger.error(f"❌ Save failed for {img_url}: {str(e)}")
                        
                except Exception as e:
                    self.failed_count += 1
                    logger.error(f"❌ Error processing image {img.get('id')}: {str(e)}")
            
            # 更新图片列表
            result['list'] = img_list
            
            # 保存图片列表文件
            with open(os.path.join(self.output_dir, self.list_file), 'w') as fp:
                json.dump(result, fp, indent=2)
            
            # 生成总结报告
            elapsed = time.time() - self.start_time
            logger.info("=" * 60)
            logger.info(f"🚀 Download Summary - {elapsed:.2f} seconds")
            logger.info(f"✅ Downloaded: {self.downloaded_count}")
            logger.info(f"⏩ Skipped: {self.skipped_count}")
            logger.info(f"❌ Failed: {self.failed_count}")
            logger.info(f"🏁 Status: Success")
            logger.info("=" * 60)
            
            return True
            
        except requests.RequestException as e:
            logger.error(f"🚫 API request failed: {str(e)}")
            return False
        except Exception as e:
            logger.exception(f"🚫 Critical error: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Bilibili Splash Image Downloader")
    parser.add_argument("--output", default="app_splash", help="Output directory for images")
    parser.add_argument("--list-file", default="images.json", help="JSON file for image list")
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
        list_file=args.list_file,
        log_file=args.log_file
    )
    
    # 执行下载
    success = downloader.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
