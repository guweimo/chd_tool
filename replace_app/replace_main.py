import os
import json

class ReplaceConfig:
    def __init__(self, directory, encoding='gb2312'):
        """
        初始化文件处理器。
        :param file_path: 文件路径
        :param encoding: 文件编码，默认为 gb2312
        """
        self.filename = 'diy.suit'
        self.file_path = os.path.join(directory, self.filename)
        self.diy_name = 'diysuit_item'
        print('self.file_path', self.file_path)
        self.encoding = encoding
        self.data = None

    def read_file(self):
        """
        读取文件并解析为 JSON 数据。
        """
        try:
            with open(self.file_path, 'r', encoding=self.encoding) as file:
                content = file.read()
            self.data = json.loads(content)
            print("文件读取并解析成功")
        except FileNotFoundError:
            print(f"文件未找到: {self.file_path}")
        except UnicodeDecodeError:
            print(f"文件编码错误: {self.file_path}")
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")

    def replace_content(self, old_value, new_value):
        """
        替换 JSON 数据中的内容。

        :param old_value: 需要替换的值
        :param new_value: 替换后的值
        """
        data = self.data['diysuit_item']
        if data and isinstance(data, list):  # 确保 data 是列表
            for item in data:  # 遍历列表中的每个字典
                if isinstance(item['data'], dict):  # 确保每个元素是字典
                    for key, value in item['data'].items():  # 遍历字典的键值对
                        if value == old_value:  # 如果值等于需要替换的值
                            item['data'][key] = new_value  # 替换为新的值
                            print(f"替换成功: {old_value} -> {new_value}")
        else:
            print("数据格式不正确，无法替换")

    def save_to_file(self):
        if self.data:
            try:
                with open(self.file_path, 'w', encoding='gb2312') as file:
                    json.dump(self.data, file, ensure_ascii=False, indent=4)
                print(f"文件已保存到: {self.file_path}")
            except IOError as e:
                print(f"文件保存失败: {e}")
        else:
            print("没有可保存的数据")

    def run(self, old_value, new_value):
        self.read_file()
        self.replace_content(old_value, new_value)
        self.save_to_file()

def main():
    main_file = 'C:/Users/guweimo/Desktop/心月狐/data/Config/C7E3C1E3D8BCD2BBD2B6'
    config = ReplaceConfig(main_file)
    old_value = '清醒者的奥丁勋章+4'
    new_value = '清醒者的奥丁勋章+5'
    config.run(old_value, new_value)

if __name__ == "__main__":
    main()

