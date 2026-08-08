"""Lua文件名编码与中文名称的映射表

映射关系存储在 filename_mapping.json 配置文件中（数组形式，保证顺序）。
程序启动时若配置文件不存在，则自动生成默认配置。

可直接编辑 filename_mapping.json 修改映射：
[
    {"code": "a8473938b1adc2db", "name": "伊卡洛斯之翼"},
    ...
]
"""
import os
import sys
import json
from collections import OrderedDict


# 默认映射数据（配置文件不存在时自动生成）
_DEFAULT_MAPPING = [
    {"code": "a8473938b1adc2db", "name": "伊卡洛斯之翼"},
    {"code": "a11f6f8b73d79273", "name": "普累罗麻"},
    {"code": "e3963af32f789373", "name": "翡翠世界"},
    {"code": "80a29fdeb82317d6", "name": "智海"},
    {"code": "96d0f424b3d6a42f", "name": "残缺边界"},
    {"code": "3e5c4e25fb39dec6", "name": "葬剑幻谷"},
    {"code": "181b75c7f9bc9de7", "name": "被吞噬的魔法办公楼"},
    {"code": "854df731d996c054", "name": "归元木匣"},
    {"code": "3cc4cdda6cfb6e65", "name": "铁之考验"},
    {"code": "232d6af26e1536aa", "name": "赫利波尔要塞"},
    {"code": "6e4ca0cb0c935200", "name": "曼赤肯仓库"},
    {"code": "d29ecf143abd4460", "name": "丽西泰亚之门"},
    {"code": "8730659a18d7b4ba", "name": "蘑菇树沼泽"},
    {"code": "5d2f295ec271acdb", "name": "摩克沙"},
    {"code": "74b04b62710052ab", "name": "尼夫海姆站"},
    {"code": "54cbda403ac1e8ef", "name": "阿特拉斯庭院"},
    {"code": "14bcb0915711d136", "name": "埃吉尔遗迹"},
    {"code": "a2f9929ab4d64355", "name": "大地的考验"},
    {"code": "3b386ccf95b83396", "name": "黑月的考验"},
    {"code": "60ecc260c1312931", "name": "诺尼尔之泪"},
    {"code": "3884d4a499b541a9", "name": "神笔画卷"},
    {"code": "432f304bd27ba112", "name": "消失的星之歌"},
    {"code": "b132c14db09d8a05", "name": "黄昏教堂"},
    {"code": "f83325f755aac222", "name": "精灵树桩"},
    {"code": "edb0c2993de08c4e", "name": "生命之恩泰"},
    {"code": "b7d4b92119164d14", "name": "失魂寺"},
    {"code": "f5b6e903f08655fc", "name": "薇娅斯梦境"},
    {"code": "6f58063a8bbccba5", "name": "穆斯菲尔斯隧道"},
    {"code": "aa7fa86c91735c2c", "name": "星能之战（家族本）"},
    {"code": "000aaccac0f4305c", "name": "艾乌加蒙剧场"},
    {"code": "46d09fe1bda4c623", "name": "深渊之境"},
    {"code": "2ca09d77df84073a", "name": "龙皇殿"},
    {"code": "0e7431cf48088aad", "name": "太阳宫殿（超越）"},
]


def _get_config_path():
    """获取配置文件路径

    打包后：与 exe 同目录
    开发时：与本脚本同目录
    """
    if getattr(sys, 'frozen', False):
        # 打包后，exe 所在目录
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发时，脚本所在目录
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "filename_mapping.json")


def get_filename_mapping():
    """从配置文件加载映射关系，返回有序字典（OrderedDict）

    配置文件不存在时自动生成默认配置。
    """
    config_path = _get_config_path()

    # 配置文件不存在则自动生成
    if not os.path.exists(config_path):
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(_DEFAULT_MAPPING, f, ensure_ascii=False, indent=4)
        except Exception:
            # 生成失败则用默认数据
            pass

    mapping = OrderedDict()
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                code = item.get("code")
                name = item.get("name")
                if code and name:
                    mapping[code] = name
    except Exception:
        # 读取失败则回退到默认数据
        for item in _DEFAULT_MAPPING:
            mapping[item["code"]] = item["name"]

    return mapping
