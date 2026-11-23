"""采集工具的唯一配置。修改后运行同目录的 collect.py。"""

SETTINGS = {
    # 任务类型：keywords 单查或批采，fashion 采集后清洗，clean 清洗自己指定的文件。
    "task": "keywords",
    "country": "fr",              # de、fr、uk 等两位站点代码

    # 文件路径相对于本目录，也支持绝对路径。基础词库在 base_words/。
    # 英国服装采集设 task="fashion"、country="uk"，input 和 keyword 留空。
    # 英国关键词批采可将 input 设为 "base_words/uk/fashion_base.md"。
    # 两种清洗共用 rules/brands.md。common 适用所有站点，de、fr、uk 小节为站点补充。
    # 服装词根在 rules/<国家>/。
    "input": "",                  # 批采默认 keywords.md；离线清洗必须指定文件
    "out": "",                    # .md 文件，默认写入 output/<国家>/keywords/ 或 output/<国家>/fashion/

    # 联网采集
    "category": "",               # Top3 品类，不填则不限
    "attempts": 5,                # 每项请求最多尝试次数，默认 5
    "timeout": 30,                # 请求超时秒数
    "interval": 2,                # 请求间隔秒数
    "page_size": 200,             # 每页请求条数

    # 关键词单查与批采
    "keyword": "",                # 留空批采；填词单查；填 "*" 单次查全站；单查时不填 input
    "sort": "fluctuation",        # new_rank、fluctuation、both；留空时单查按排名，批采按涨幅
    "fluctuation_below": -90000,  # 原始涨幅值必须低于此阈值，默认 -90000；填 False 取消筛选
    "rank_below": 200000,          # 默认 200000；可填 [40–159 条时的阈值, 160 条及以上的阈值] 或 False

    # 服装采集与清洗
    "pages": 5,                   # 采集页数
    "min_gain": "",               # 最小涨幅，在线清洗默认 1，离线不限；False 表示不限
    "limit": 0,                   # 最多保留多少条，0 表示不限
    "keep_attributes": True,      # 是否保留可独立命中的强属性
    "use_excludes": True,         # 是否启用黑名单
    "plain": False,               # True 只输出词，False 附涨幅和筛选备注
}
