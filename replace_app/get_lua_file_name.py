"""Lua文件名与中文名称的映射关系

编码生成规则：
    对中文名称按 GBK 编码计算 MD5，取第 8~24 位（共16位十六进制字符）。
    即：md5(name.encode('gbk')).hexdigest()[8:24]

    示例：
        "普累罗麻" -> GBK编码 -> MD5 = 4857e363a11f6f8b73d7927344c6aff4
                          取中间16位 -> a11f6f8b73d79273
"""
import hashlib


def generate_code(name):
    """根据中文名称生成文件名编码

    规则：对名称按GBK编码做MD5，取十六进制结果的第8~24位字符
    """
    md5_hash = hashlib.md5(name.encode('gbk')).hexdigest()
    return md5_hash[8:24]


if __name__ == '__main__':
    # 测试
    name = "太阳宫殿(超越)"
    code = generate_code(name)
    print(f"{name} -> {code}")
