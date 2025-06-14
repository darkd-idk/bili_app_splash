#!/usr/bin/env python3
"""
Bilibili 开屏图下载脚本 - 自动化获取 Bilibili 应用启动画面图片

功能：
1. 从 Bilibili API 获取开屏图列表
2. 下载开屏图片到本地目录
3. 生成下载报告和元数据
4. 提供详细的错误处理和日志记录

参数：
无需命令行参数，所有配置在脚本内定义

使用：
python get_app_splash.py

作者：GitHub Actions 工作流
版本：1.2.0
最后更新：2024-06-15
"""

import sys
import os
import json
import time
import logging
import hashlib
import requests
from typing import Dict, List, Tuple, Any
from urllib.parse import urlparse
from dataclasses import dataclass

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('BilibiliSplash')

# 常量定义
API_URL = "https://app.bilibili.com/x/v2/splash/brand/list"
APP_KEY = "1d8b6e7d45233436"
APP_SECRET = "560c52ccd288fed045859ed18bffd973"
DOWNLOAD_DIR = "app_splash"
REPORT_JSON = "download_report.json"
METADATA_JSON = "splash_metadata.json"
TIMEOUT = 15  # 请求超时时间（秒）
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 2  # 重试延迟（秒）

# 全局请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.bilibili.com/"
}


@dataclass
class SplashItem:
    """开屏图数据模型"""
    id: int
    url: str
    name: str
    mode: str
    source: str
    show_logo: bool
    thumbnail_hash: str
    thumbnail_size: int
    logo_url: str
    logo_hash: str
    logo_size: int
    filename: str = ""
    status: str = "pending"
    error: str = ""


class SplashDownloader:
    """Bilibili 开屏图下载器"""
    
    def __init__(self):
        self.download_dir = DOWNLOAD_DIR
        self.report_file = os.path.join(DOWNLOAD_DIR, REPORT_JSON)
        self.metadata_file = os.path.join(DOWNLOAD_DIR, METADATA_JSON)
        self.splash_items: List[SplashItem] = []
        self.report_data = {
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "end_time": "",
            "execution_time": 0,
            "total_count": 0,
            "success_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "errors": []
        }
        
        # 确保工作目录存在
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """确保下载目录存在"""
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
            logger.info(f"创建下载目录: {self.download_dir}")
    
    @staticmethod
    def _generate_sign(params: Dict[str, Any], app_secret: str) -> str:
        """
        生成 API 签名
        
        Args:
            params: API 参数字典
            app_secret: 应用密钥
            
        Returns:
            MD5 签名字符串
        """
        sorted_params = sorted(params.items())
        param_str = "&".join([f"{k}={v}" for k, v in sorted_params])
        sign_str = param_str + app_secret
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest()
    
    def _get_valid_filename(self, url: str, file_id: int) -> str:
        """
        从 URL 生成有效的文件名
        
        Args:
            url: 图片 URL
            file_id: 开屏图 ID
            
        Returns:
            格式为 {file_id}.{extension} 的文件名
        """
        path = urlparse(url).path
        extension = os.path.splitext(path)[1]
        
        # 如果没有扩展名或扩展名无效，使用默认的 .jpg
        if not extension or extension not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            return f"{file_id}.jpg"
        
        # 去除问号后的参数部分
        clean_extension = extension.split('?')[0]
        return f"{file_id}{clean_extension}"
    
    def fetch_splash_list(self) -> None:
        """从 Bilibili API 获取开屏图列表"""
        logger.info("正在获取开屏图列表...")
        
        params = {"appkey": APP_KEY, "ts": int(time.time())}
        params["sign"] = self._generate_sign(params, APP_SECRET)
        
        try:
            response = requests.get(
                API_URL, 
                params=params, 
                headers=HEADERS, 
                timeout=TIMEOUT
            )
            response.raise_for_status()
            
            if not response.text.strip():
                raise ValueError("API 返回空响应")
            
            api_data = response.json()
            
            # 检查 API 返回状态码
            if api_data.get("code") != 0:
                error_msg = f"API错误: code={api_data.get('code')}, message={api_data.get('message')}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            splash_list = api_data.get("data", {}).get("list", [])
            
            if not splash_list:
                logger.warning("未获取到开屏图数据")
                return
                
            self.report_data["total_count"] = len(splash_list)
            logger.info(f"获取到 {len(splash_list)} 个开屏图")
            
            # 将 API 数据转换为 SplashItem 对象
            for item in splash_list:
                filename = self._get_valid_filename(item["thumb"], item["id"])
                splash_item = SplashItem(
                    id=item["id"],
                    url=item["thumb"],
                    name=item.get("thumb_name", f"未命名_{item['id']}"),
                    mode=item.get("mode", "full"),
                    source=item.get("source", "brand"),
                    show_logo=item.get("show_logo", True),
                    thumbnail_hash=item.get("thumb_hash", ""),
                    thumbnail_size=item.get("thumb_size", 0),
                    logo_url=item.get("logo_url", ""),
                    logo_hash=item.get("logo_hash", ""),
                    logo_size=item.get("logo_size", 0),
                    filename=filename
                )
                self.splash_items.append(splash_item)
                
        except requests.RequestException as e:
            logger.error(f"网络请求失败: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            logger.debug(f"原始响应内容: {response.text[:500]}")
            raise
        except Exception as e:
            logger.error(f"获取开屏图列表时发生错误: {str(e)}")
            raise
    
    def download_all_splash(self) -> None:
        """下载所有开屏图"""
        logger.info("开始下载开屏图...")
        
        if not self.splash_items:
            logger.warning("没有可供下载的开屏图")
            return
            
        for item in self.splash_items:
            file_path = os.path.join(self.download_dir, item.filename)
            
            # 如果文件已存在，跳过下载
            if os.path.exists(file_path):
                logger.info(f"文件已存在，跳过: {item.name} ({item.filename})")
                item.status = "skipped"
                self.report_data["skipped_count"] += 1
                continue
                
            # 尝试下载（带重试机制）
            success = False
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = requests.get(
                        item.url, 
                        headers=HEADERS, 
                        stream=True,
                        timeout=TIMEOUT
                    )
                    response.raise_for_status()
                    
                    # 写入文件
                    with open(file_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    # 验证文件大小（如果可用）
                    if item.thumbnail_size > 0:
                        file_size = os.path.getsize(file_path)
                        if abs(file_size - item.thumbnail_size) > file_size * 0.1:
                            logger.warning(f"文件大小不匹配: 期望 {item.thumbnail_size} 字节, 实际 {file_size} 字节")
                    
                    logger.info(f"下载成功: {item.name} ({item.filename})")
                    item.status = "success"
                    self.report_data["success_count"] += 1
                    success = True
                    break
                    
                except Exception as e:
                    logger.error(f"下载尝试 {attempt}/{MAX_RETRIES} 失败: {item.name} - {str(e)}")
                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_DELAY)
                    
            if not success:
                logger.error(f"下载失败: {item.name}")
                item.status = "failed"
                item.error = str(e)
                self.report_data["failed_count"] += 1
                self.report_data["errors"].append({
                    "id": item.id,
                    "name": item.name,
                    "error": str(e)
                })
    
    def save_metadata(self) -> None:
        """保存开屏图元数据到 JSON 文件"""
        try:
            metadata = {
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "pull_interval": 1800,  # 默认刷新间隔
                "items": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "filename": item.filename,
                        "url": item.url,
                        "mode": item.mode,
                        "source": item.source,
                        "show_logo": item.show_logo,
                        "thumbnail_hash": item.thumbnail_hash,
                        "thumbnail_size": item.thumbnail_size,
                        "logo_url": item.logo_url,
                        "logo_hash": item.logo_hash,
                        "logo_size": item.logo_size
                    }
                    for item in self.splash_items
                ]
            }
            
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"元数据保存至: {self.metadata_file}")
            
        except Exception as e:
            logger.error(f"保存元数据失败: {str(e)}")
    
    def save_report(self) -> None:
        """保存下载报告到 JSON 文件"""
        try:
            end_time = time.time()
            self.report_data["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.report_data["execution_time"] = round(end_time - self.report_data["start_time"], 2)
            
            with open(self.report_file, "w", encoding="utf-8") as f:
                json.dump(self.report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"报告保存至: {self.report_file}")
            
        except Exception as e:
            logger.error(f"保存报告失败: {str(e)}")
    
    def print_summary(self) -> None:
        """打印下载结果摘要"""
        duration = self.report_data.get("execution_time", 0)
        success = self.report_data.get("success_count", 0)
        skipped = self.report_data.get("skipped_count", 0)
        failed = self.report_data.get("failed_count", 0)
        total = success + skipped + failed
        
        print("\n" + "=" * 60)
        print(f"Bilibili 开屏图下载摘要 ({self.report_data['end_time']})")
        print("=" * 60)
        print(f"{'总图片数:':<20} {total}")
        print(f"{'成功下载:':<20} {success}")
        print(f"{'跳过下载:':<20} {skipped}")
        print(f"{'下载失败:':<20} {failed}")
        print(f"{'执行时间:':<20} {duration:.2f}秒")
        print("=" * 60)
        
        if failed > 0:
            print("错误详情:")
            for error in self.report_data["errors"][:5]:  # 只显示前5个错误
                print(f"- ID: {error['id']}, 名称: {error['name']}")
                print(f"  错误: {error['error']}")
            if failed > 5:
                print(f"...还有 {failed - 5} 个错误未显示")
            print("=" * 60)
    
    def run(self) -> int:
        """执行完整下载流程"""
        start_time = time.time()
        
        try:
            # 获取开屏图列表
            self.fetch_splash_list()
            
            # 下载所有开屏图
            self.download_all_splash()
            
            # 保存元数据和报告
            self.save_metadata()
            self.save_report()
            
            return 0
            
        except Exception as e:
            logger.critical(f"运行过程中发生严重错误: {str(e)}", exc_info=True)
            return 1
        finally:
            # 确保报告时间被正确记录
            end_time = time.time()
            self.report_data["execution_time"] = round(end_time - start_time, 2)
            self.report_data["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.print_summary()


if __name__ == "__main__":
    try:
        downloader = SplashDownloader()
        exit_code = downloader.run()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        sys.exit(2)
