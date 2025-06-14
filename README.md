# 🖼️ bili_app_splash - B站壁纸与开屏图自动同步

![壁纸娘同步状态](https://github.com/zjkwdy/bili_app_splash/actions/workflows/BIZHINIANG.yml/badge.svg)
![开屏图下载状态](https://github.com/zjkwdy/bili_app_splash/actions/workflows/bilibili_splash_download.yml/badge.svg)
![最新提交](https://img.shields.io/github/last-commit/zjkwdy/bili_app_splash)
![仓库大小](https://img.shields.io/github/repo-size/zjkwdy/bili_app_splash)
![许可协议](https://img.shields.io/badge/license-MIT-blue)

本项目通过GitHub Actions自动同步B站壁纸娘的美图合集和B站应用的开屏图（启动图），所有图片将保存在仓库中方便下载使用。每日自动更新，无需手动操作。

## 📦 项目目录结构

```
bili_app_splash/
├── bizhiniang/          # 壁纸娘壁纸（按时间分类的相册）
│   └── YYYYMMDDHHMMSS/  # 相册文件夹（格式：年月日时分秒）
│       ├── image1.jpg
│       └── image2.jpg
├── splash/              # B站开屏图片
│   └── splash_YYYYMMDD.jpg
├── .github/             # GitHub Actions工作流配置
│   └── workflows/
│       ├── BIZHINIANG.yml               # 壁纸娘同步任务
│       └── bilibili_splash_download.yml # 开屏图下载任务
├── getwallpaper.py      # 壁纸同步脚本
├── splash_downloader.py # 开屏图下载脚本
├── urls.txt             # 所有壁纸的原始URL记录
├── requirements.txt     # Python依赖项
└── README.md            # 项目说明文档
```

## ⚡ 主要功能

- **每日壁纸同步**：每天自动下载B站壁纸娘的最新相册
- **开屏图定时更新**：每小时检查并下载最新的B站开屏图
- **智能分类整理**：壁纸按相册上传时间分类存放
- **完整URL记录**：保存所有图片的原始B站链接
- **自动化工作流**：GitHub Actions全自动处理下载和提交
- **代理支持**：内置代理机制确保网络连接可靠性
- **详细日志**：生成完整的下载过程日志

## 🚀 快速开始

### GitHub Actions自动使用（无需配置）

项目配置了全自动任务：
1. **壁纸娘同步**：每天北京时间09:10运行
2. **开屏图下载**：每小时运行一次

自动更新后的图片可在以下目录查看：
- 壁纸：`bizhiniang/` 
- 开屏图：`splash/`

### 本地运行指南

1. **克隆仓库到本地**：
   ```bash
   git clone https://github.com/zjkwdy/bili_app_splash.git
   cd bili_app_splash
   ```

2. **安装Python依赖**：
   ```bash
   pip install -r requirements.txt
   ```

3. **同步壁纸（需要B站SESSDATA）**：
   ```bash
   python getwallpaper.py --sessdata YOUR_SESSDATA
   ```
   
   如何获取SESSDATA：
   1. 登录B站网页版
   2. 打开开发者工具（F12）
   3. 进入Application > Cookies
   4. 复制`SESSDATA`的值

4. **下载开屏图**：
   ```bash
   python splash_downloader.py
   ```

## 🔍 图片查找方法

1. **最新壁纸**：
   - 查看`bizhiniang/`目录中按时间排序的最新文件夹
   
2. **特定日期壁纸**：
   - 使用文件名格式：`YYYYMMDDHHMMSS`（年月日时分秒）
   - 例如：`bizhiniang/20230615120000/`

3. **开屏图片**：
   - 在`splash/`目录查找以日期命名的文件
   - 格式：`splash_YYYYMMDD.jpg`

4. **原始链接查询**：
   - 打开`urls.txt`文件
   - 按相册名或图片名搜索对应URL

## ⚠️ 注意事项

### 网络连接机制
1. 脚本包含智能代理系统，自动绕过网络限制
2. 内置7次重试机制应对连接失败
3. 随机延迟设计避免请求频率过高被封禁

### 错误排查
1. **同步失败处理**：
   - 检查GitHub Actions的作业日志
   - 查看Artifacts中的`wallpapers.log`文件
   - 更新可能过期的SESSDATA（有效期为1-3个月）
   
2. **常见问题**：
   ```markdown
   Q: 为什么有时看不到最新图片？
   A: 同步任务北京时间09:10运行，新建相册需要等待下次运行
   
   Q: 下载速度慢如何解决？
   A: GitHub Actions服务器位置限制，可尝试本地运行获得更好速度
   ```

### 版权声明
1. 本项目仅用于学习和技术演示目的
2. 所有图片版权归属于Bilibili及原创作者
3. 禁止用于任何商业用途
4. 下载后24小时内请自觉删除

## 📊 实时统计

| 指标 | 值 |
|------|-----|
| 最新同步时间 | ![Last Sync](https://img.shields.io/badge/dynamic/json?label=时间&query=$.last_sync&url=https%3A%2F%2Fraw.githubusercontent.com%2Fzjkwdy%2Fbili_app_splash%2Fmain%2F.stats.json) |
| 相册数量 | ![Album Count](https://img.shields.io/badge/dynamic/json?label=数量&query=$.album_count&url=https%3A%2F%2Fraw.githubusercontent.com%2Fzjkwdy%2Fbili_app_splash%2Fmain%2F.stats.json) |
| 图片总数 | ![Image Count](https://img.shields.io/badge/dynamic/json?label=总量&query=$.total_images&url=https%3A%2F%2Fraw.githubusercontent.com%2Fzjkwdy%2Fbili_app_splash%2Fmain%2F.stats.json) |

> 统计数据每小时更新一次  
> 最后更新日期：2025-06-15

## 🤝 贡献指南

欢迎通过Issues和Pull Requests贡献项目：

### 问题报告
1. 网络连接问题（失效代理等）
2. 脚本执行错误
3. API接口变更

### 功能建议
1. 添加新功能（如按主题分类）
2. 优化现有下载算法
3. 改进用户界面和文档

### 开发规范
1. 遵循PEP8 Python编码规范
2. 添加必要的代码注释
3. 保持代码清晰和模块化
4. 提交前测试所有变更

### 贡献步骤
1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/your-feature`)
3. 提交变更 (`git commit -am 'Add some feature'`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 创建Pull Request

## 📜 开源协议

本项目采用 [MIT License](LICENSE) 发行，核心条款如下：

1. 允许自由使用、复制、修改和分发软件
2. 需要保留版权声明和许可声明
3. 不提供任何担保和责任限制

```text
MIT License
Copyright (c) 2025 zjkwdy
```

## ℹ️ 项目维护

维护者：zjkwdy  
反馈邮箱：your-email@example.com（请将问题先提交至Issues）  
项目链接：https://github.com/zjkwdy/bili_app_splash
