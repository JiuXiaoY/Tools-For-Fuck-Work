"""亚马逊搜索建议采集配置。关键词填写在对应站点的 keywords_<站点>.txt。"""

SETTINGS = {
    "markets": ["uk"],  # de=德国，fr=法国，uk=英国。只采集一站时填一个
    "category": "aps",       # 亚马逊搜索类别，aps=全部类别
    "expand": "none",        # none=原词；letters=字母扩展；letters-digits=字母和数字
    "interval": 1.2,         # 请求间隔秒数，不得小于 0.5
    "timeout": 15,           # 单次请求超时秒数
    "retries": 2,            # 失败后的额外重试次数，范围 0~5
    "cache_hours": 24,       # 仅保存过程文件时生效：成功缓存有效小时数
    "save_process_files": False,  # False=只保存结果词表，不保存缓存、日志和明细
}
