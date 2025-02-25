import requests

def mesh_search(keyword, match="exact", year="current", limit=10):
    """
    进行 MeSH 检索
    :param keyword: 检索关键词
    :param match: 匹配方式，可选值为 "exact", "contains", "startswith"，默认为 "exact"
    :param year: 查询年份，可选值为 "current", "2025", "2024", "2023" 等，默认为 "current"
    :param limit: 最大返回结果数量，默认为 10
    :return: 检索到的 MeSH 描述符列表
    """
    base_url = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    params = {
        "label": keyword,
        "match": match,
        "year": year,
        "limit": limit
    }
    try:
        # 发送 HTTP 请求
        response = requests.get(base_url, params=params)
        # 检查响应状态码
        response.raise_for_status()
        # 解析 JSON 数据
        results = response.json()
        if results:
            # 提取描述符标签
            descriptors = [result["label"] for result in results]
            return descriptors
        else:
            print(f"未找到与关键词 '{keyword}' 匹配的 MeSH 描述符。")
            return []
    except requests.RequestException as e:
        print(f"请求 MeSH API 时发生错误: {e}")
        return []
    except (KeyError, ValueError) as e:
        print(f"解析 MeSH API 响应时发生错误: {e}")
        return []

if __name__ == "__main__":
    # 输入检索关键词
    keyword = input("请输入要检索的关键词: ")
    # 调用 mesh_search 函数进行检索
    descriptors = mesh_search(keyword)
    if descriptors:
        print("检索到的 MeSH 描述符如下:")
        for descriptor in descriptors:
            print(descriptor)