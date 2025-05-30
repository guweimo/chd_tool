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
        print('self.file_path', self.file_path)
        self.encoding = encoding
        self.data = None

        self.diy_config = {
            "装备": 'diysuit_item',
            "超越": 'diysuit_property',
            "其他": 'diysuit_other',
            "觉醒": 'diysuit_awaken',
        }
        self.replace_paths = [
            { 'name': '白云一片去悠悠', 'path': 'C:/Users/guweimo/Desktop/心月狐/data/Config/B0D7D4C6D2BBC6ACC8A5D3C6D3C6', },
            { 'name': '丑不拉几喵', 'path': 'C:/Users/guweimo/Desktop/心月狐/data/Config/B3F3B2BBC0ADBCB8DFF7', },
            { 'name': '黑桃A', 'path': 'C:/Users/guweimo/Desktop/心月狐/data/Config/A3C16365229DA6CCD25F', },
            { 'name': '落叶丶枯萎', 'path': 'C:/Users/guweimo/Desktop/心月狐/data/Config/C2E4D2B6D8BCBFDDCEAE', },
            { 'name': '倾零丶落霞', 'path': 'C:/Users/guweimo/Desktop/心月狐/data/Config/C7E3C1E3D8BCC2E4CFBC', },
        ]

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

    def find_dict_by_name(self, data, target_name):
        if isinstance(data, list):  # 确保 data 是列表
            for item in data:  # 遍历列表中的每个字典
                if isinstance(item, dict) and item.get('name') == target_name:
                    return item  # 找到目标字典
        print(f"未找到 name 为 '{target_name}' 的字典")
        return None

    def replace_content(self, diy_name):
        try:
            diy_key = self.diy_config[diy_name]
        except KeyError:
            print(f"不存在【{diy_name}】")
            return

        for item in self.replace_paths:
            repalce_path = os.path.join(item['path'], self.filename)
            with open(repalce_path, 'r', encoding=self.encoding) as file:
                content = file.read()
            repalce_data = json.loads(content)

            if diy_name == '装备':
                repalce_item = self.find_dict_by_name(repalce_data[diy_key], '存仓')
                data_item = self.find_dict_by_name(self.data[diy_key], '存仓')
                repalce_item['data'] = data_item['data']
                print(f'替换成功: {diy_name}')
            else:
                repalce_data[diy_key] = self.data[diy_key]
                print(f"替换成功: {diy_name} - {item['name']}")
            
            self.save_to_file(repalce_path, repalce_data)

    def save_to_file(self, output_file, data):
        """
        将修改后的 JSON 数据保存到文件。

        :param output_file: 输出文件路径
        """
        if data:
            try:
                with open(output_file, 'w', encoding=self.encoding) as file:
                    json.dump(data, file, ensure_ascii=False, indent=4)
                print(f"文件已保存到: {output_file}")
            except IOError as e:
                print(f"文件保存失败: {e}")
        else:
            print("没有可保存的数据")

    def run(self, diy_name):
        self.read_file()
        self.replace_content(diy_name)


def main():
    main_file = 'C:/Users/guweimo/Desktop/心月狐/data/Config/C7E3C1E3D8BCD2BBD2B6'
    config = ReplaceConfig(main_file)

    diy_name = '装备'
    config.run(diy_name)


if __name__ == "__main__":
    main()

