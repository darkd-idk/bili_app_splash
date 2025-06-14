import requests, os, json, time, hashlib

# 创建存储目录
if not os.path.exists('app_splash'):
    os.makedirs('app_splash')

# 使用正确的签名算法
appkey = '1d8b6e7d45233436'
appsec = '560c52ccd288fed045859ed18bffd973'  # 这是与 appkey 配对的密钥
ts = int(time.time())

# 计算正确的签名
def calculate_sign(params, appsec):
    # 按字典序排序参数
    sorted_params = sorted(params.items())
    # 拼接参数字符串
    param_str = '&'.join([f'{k}={v}' for k, v in sorted_params])
    # 添加 appsec 并计算 MD5
    sign_str = param_str + appsec
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest()

# 构建参数字典
params = {
    'appkey': appkey,
    'ts': ts,
    # 先不包含 sign，后面计算
}

# 计算签名
sign = calculate_sign(params, appsec)
params['sign'] = sign

url = 'https://app.bilibili.com/x/v2/splash/brand/list'

try:
    # 设置请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bilibili.com/'
    }

    # 发送请求
    print("正在请求API...")
    print(f"请求参数: {params}")
    response = requests.get(url, params=params, headers=headers, timeout=15)
    print(f"HTTP状态码: {response.status_code}")
    
    # 检查响应内容
    if not response.text:
        print("错误：API返回了空响应！")
        exit(1)
        
    if not response.text.startswith('{'):
        print("错误：API返回的不是JSON格式！")
        print(f"响应开头内容: {response.text[:200]}")
        exit(1)
    
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        print("原始响应内容:")
        print(response.text[:1000])
        exit(1)
    
    # 检查API返回代码
    code = data.get('code')
    if code != 0:
        print(f"API错误: 代码={code}, 消息={data.get('message')}")
        print(f"ttl={data.get('ttl', '未知')}")
        print(f"数据字段存在: {'data' in data}")
        
        # 显示可能的额外错误信息
        if 'data' in data and isinstance(data['data'], dict):
            error_info = data['data'].get('error_info', '无额外错误信息')
            print(f"详细错误: {error_info}")
        
        exit(1)
    
    splash_list = data.get('data', {}).get('list', [])
    if not splash_list:
        print("警告：没有获取到启动图数据！")
        # 尝试保存可能存在的其他数据
        print(f"获取到数据字段: {list(data.get('data', {}).keys())}")
        exit(0)
    
    print(f"成功获取到 {len(splash_list)} 张启动图信息")
    
    # 处理图片数据
    result = {
        'lastSync': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        'pull_interval': data.get('data', {}).get('pull_interval', 1800),
        'list': []
    }
    
    # 下载所有图片
    for item in splash_list:
        img_id = item['id']
        img_url = item['thumb']
        img_name = item.get('thumb_name', f'未命名_{img_id}')
        
        # 获取图片格式
        img_format = img_url.split('.')[-1].split('?')[0]
        if img_format not in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
            img_format = 'jpg'
        
        filename = f'{img_id}.{img_format}'
        filepath = os.path.join('app_splash', filename)
        
        # 添加到结果列表
        result['list'].append({
            'id': img_id,
            'name': img_name,
            'url': filename,
            'source': item.get('source', ''),
            'mode': item.get('mode', 'full'),
            'hash': item.get('thumb_hash', ''),
            'show_logo': item.get('show_logo', True)
        })
        
        # 如果文件已存在，跳过下载
        if os.path.exists(filepath):
            print(f"图片已存在: {filename}，跳过下载")
            continue
            
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
    json_path = os.path.join('app_splash', 'images.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print("="*50)
    print(f"成功处理 {len(result['list'])} 张启动图")
    print(f"列表已保存至: {json_path}")
    print(f"下次刷新间隔: {result['pull_interval']} 秒")
    print("="*50)

except requests.exceptions.RequestException as e:
    print(f"网络请求失败: {str(e)}")
    exit(1)
except Exception as e:
    print(f"程序错误: {str(e)}")
    exit(1)
