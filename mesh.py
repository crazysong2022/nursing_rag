import requests
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def mesh_search(keyword, endpoint="https://id.nlm.nih.gov/mesh/lookup/term",
                match="exact", year="current", limit=10):
    """
    进行 MeSH 检索
    :param keyword: 检索关键词
    :param endpoint: API 端点，默认为术语查找端点
    :param match: 匹配方式，可选值为 "exact", "contains", "startswith"，默认为 "exact"
    :param year: 查询年份，可选值为 "current", "2025", "2024", "2023" 等，默认为 "current"
    :param limit: 最大返回结果数量，默认为 10
    :return: 检索到的 MeSH 标签列表
    """
    # 参数验证
    valid_match_values = ["exact", "contains", "startswith"]
    if match not in valid_match_values:
        logging.error(f"无效的匹配方式 '{match}'，可选值为 {valid_match_values}")
        return []

    params = {
        "label": keyword,
        "match": match,
        "year": year,
        "limit": limit
    }
    try:
        # 发送 HTTP 请求
        response = requests.get(endpoint, params=params)
        # 检查响应状态码
        response.raise_for_status()
        # 解析 JSON 数据
        results = response.json()
        if results:
            # 提取标签
            labels = [result["label"] for result in results]
            return labels
        else:
            logging.info(f"未找到与关键词 '{keyword}' 匹配的 MeSH 标签。")
            return []
    except requests.RequestException as e:
        logging.error(f"请求 MeSH API 时发生错误: {e}")
        return []
    except (KeyError, ValueError) as e:
        logging.error(f"解析 MeSH API 响应时发生错误: {e}")
        return []

if __name__ == "__main__":
    # 输入检索关键词
    keyword = input("请输入要检索的关键词: ")

    # 让用户选择匹配方式
    valid_match_values = ["exact", "contains", "startswith"]
    while True:
        match = input(f"请选择匹配方式 ({', '.join(valid_match_values)}), 默认为 'exact': ")
        if not match:
            match = "exact"
        if match in valid_match_values:
            break
        else:
            print(f"无效的匹配方式，请选择 {', '.join(valid_match_values)} 中的一个。")

    # 让用户选择查询年份
    while True:
        year = input("请输入查询年份 (如 '2025', '2024' 等), 默认为 'current': ")
        if not year:
            year = "current"
        break

    # 让用户选择最大返回结果数量
    while True:
        try:
            limit_str = input("请输入最大返回结果数量, 默认为 10: ")
            if not limit_str:
                limit = 10
            else:
                limit = int(limit_str)
            break
        except ValueError:
            print("输入无效，请输入一个整数。")

    # 调用 mesh_search 函数进行检索
    labels = mesh_search(keyword, match=match, year=year, limit=limit)
    if labels:
        print("检索到的 MeSH 标签如下:")
        for label in labels:
            print(label)