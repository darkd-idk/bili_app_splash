import requests, os, json, time

# 创建存储目录
if not os.path.exists('app_splash'):
    os.makedirs('app_splash')

# API配置 - 使用您提供的签名
url = 'https://app.bilibili.com/x/v2/splash/brand/list'
params = {
    'appkey': '1d8b6e7d45233436',
    'ts': int(time.time()),
    'sign': '78a89e153cd6231a4a4d55013aa063ce'
}

try:
    # 设置请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com/'
    }

    # 发送请求
    print("正在请求API...")
    response = requests.get(url, params=params, headers=headers, timeout=15)
    print(f"HTTP状态码: {response.status_code}")

    # 检查响应内容
    if not response.text.startswith('{'):
        print("错误：API返回的不是JSON格式！")
        print("响应开头内容:", response.text[:200])
        exit(1)
    
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        print("原始响应内容:")
        print(response.text[:1000])
        exit(1)
    
    # 检查API返回代码
    if data.get('code') != 0:
        print(f"API错误: 代码={data.get('code')}, 消息={data.get('message')}")
        exit(1)
    
    # 确保有数据
    splash_list = data.get('data', {}).get('list', [])
    if not splash_list:
        print("警告：没有获取到启动图数据！")
        exit(0)
    
    print(f"成功获取到 {len(splash_list)} 张启动图信息")
    
    # 处理图片数据
    result = {
        'lastSync': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        'list': []
    }
    
    # 下载所有图片
    for item in splash_list:
        img_id = item['id']
        img_url = item['thumb']
        img_name = item.get('thumb_name', f'未命名_{img_id}')
        
        # 获取图片格式
        img_format = img_url.split('.')[-1].split('?')[0]
        # 支持常见的图片格式
        if img_format not in ['jpg', 'jpeg', 'png', 'webp']:
            img_format = 'jpg'  # 默认为jpg
        
        filename = f'{img_id}.{img_format}'
        filepath = os.path.join('app_splash', filename)
        
        # 添加到结果列表
        result['list'].append({
            'id': img_id,
            'name': img_name,
            'url': filename,
            'source': item.get('source', ''),
            'mode': item.get('mode', '')
        })
        
        # 下载图片
        try:
            print(f"正在下载 [{img_name}] (ID: {img_id})...")
            img_response = requests.get(img_url, headers=headers, timeout=15)
            img_response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(img_response.content)
            print(f"成功保存: {filename}")
        except Exception as e:
            print(f"下载失败 [{img_name}]: {str(e)}")
    
    # 保存图片列表
    with open('app_splash/images.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print("="*50)
    print(f"成功处理 {len(result['list'])} 张启动图")
    print(f"列表已保存至: app_splash/images.json")
    print("="*50)

except requests.exceptions.RequestException as e:
    print(f"网络请求失败: {str(e)}")
    exit(1)
except Exception as e:
    print(f"程序错误: {str(e)}")
    exit(1)
