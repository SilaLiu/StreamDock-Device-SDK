import threading
import time
import os
import logging
from typing import Dict, Optional, Callable
from PIL import Image, ImageEnhance, ImageOps
from functools import partial
from StreamDock.DeviceManager import DeviceManager
from StreamDock.Devices.StreamDockN1 import StreamDockN1

# --------------------- 全局常量与函数定义 ---------------------

# 三页的按键映射（物理按键与逻辑功能编号的映射）
KEY_MAPPING = {
    1: {
        1: 1,
        2: 2,
        3: 3,
        4: 4,
        5: 5,
        6: 6,
        7: 7,
        8: 8,
        9: 9,
        56: 56,  # 下一页
        57: 57,  # 上一页
        64: 64,
        65: 65,
        66: 66,
        67: 67,
        160: 160,
        161: 161,
        80: 80,
        81: 81,
        144: 144,
        145: 145,
        112: 112,
        113: 113
    },
    2: {
        1: 11,
        2: 12,
        3: 13,
        4: 14,
        5: 15,
        6: 16,
        7: 17,
        8: 18,
        9: 19,
        10: 20,
        56: 56,  # 下一页
        57: 57,  # 上一页
        64: 64,
        65: 65,
        66: 66,
        67: 67,
        160: 160,
        161: 161,
        80: 80,
        81: 81,
        144: 144,
        145: 145,
        112: 112,
        113: 113
    },
    3: {
        1: 21,
        2: 22,
        3: 23,
        4: 24,
        5: 25,
        6: 26,
        7: 27,
        8: 28,
        9: 29,
        10: 30,
        56: 56,  # 下一页
        57: 57,  # 上一页
        64: 64,
        65: 65,
        66: 66,
        67: 67,
        160: 160,
        161: 161,
        80: 80,
        81: 81,
        144: 144,
        145: 145,
        112: 112,
        113: 113
    }
}

def get_key_function(key_num: int, page: int):
    """
    获取按键功能描述，根据当前页返回对应描述
    :param key_num: 按键编号
    :param page: 当前页号(1~3)
    :return: (按键编号, 功能描述) 元组
    """
    key_function_map = {
        1: {  # 第一页功能
            1: "R档",
            2: "N档",
            3: "S档",
            4: "AC开关",
            5: "除雾功能",
            6: "D档",
            7: "P档",
            8: "logo",
            9: "内循环",
            10: "外循环",
            56: "下一页",         
            57: "上一页",         
            64: "触摸屏第1个按压",         
            65: "触摸屏第2个按压",         
            66: "触摸屏第3个按压",         
            67: "触摸屏第4个按压",        
            160: "温度降低(左旋)",
            161: "温度升高(右旋)",
            80: "风速降低(左旋)",
            81: "风速增加(右旋)",
            144: "左车窗下降(左旋)",
            145: "左车窗上升(右旋)",
            112: "右车窗下降(左旋)",
            113: "右车窗上升(右旋)"
        },
        2: {  # 第二页功能
            1: "尾门开关",
            2: "ECO1",
            3: "ECO2",
            4: "ECO3",
            5: "向上吹",
            6: "左车门开关",
            7: "右车门开关",
            8: "logo",
            9: "向前吹",
            10: "向下吹",
            56: "下一页",         
            57: "上一页",         
            64: "触摸屏第1个按压",         
            65: "触摸屏第2个按压",         
            66: "触摸屏第3个按压",         
            67: "触摸屏第4个按压",        
            160: "温度降低(左旋)",
            161: "温度升高(右旋)",
            80: "风速降低(左旋)",
            81: "风速增加(右旋)",
            144: "左车窗下降(左旋)",
            145: "左车窗上升(右旋)",
            112: "右车窗下降(左旋)",
            113: "右车窗上升(右旋)"
        },
        3: {  # 第三页功能
            1: "自定义1",
            2: "自定义2",
            3: "自定义3",
            4: "自定义4",
            5: "自定义5",
            6: "自定义6",
            7: "自定义7",
            8: "自定义8",
            9: "自定义9",
            10: "自定义10",
            56: "下一页",         
            57: "上一页",         
            64: "触摸屏第1个按压",         
            65: "触摸屏第2个按压",         
            66: "触摸屏第3个按压",         
            67: "触摸屏第4个按压",        
            160: "温度降低(左旋)",
            161: "温度升高(右旋)",
            80: "风速降低(左旋)",
            81: "风速增加(右旋)",
            144: "左车窗下降(左旋)",
            145: "左车窗上升(右旋)",
            112: "右车窗下降(左旋)",
            113: "右车窗上升(右旋)"
        }
    }
    description = key_function_map.get(page, {}).get(key_num, "未知功能")
    print(f"按键 {key_num} 功能: {description}")
    return (key_num, description)

# --------------------- 全局函数定义结束 ---------------------


class StreamDockController:
    """StreamDock设备主控制器类，负责设备管理和操作，包括支持多页切换"""

    # 默认图标目录和背景图片
    DEFAULT_ICON_DIR = "../icon"
    DEFAULT_BACKGROUND = "logo.png"

    def __init__(self):
        """初始化控制器"""
        self.manager = DeviceManager()  # 设备管理器实例
        self.devices = []  # 存储已连接的设备列表
        self._running = False  # 控制线程运行的标志位
        self._key_event_callbacks = {}  # 按键回调函数字典
        self.current_page = 1  # 当前页（取值1~total_pages）
        self.total_pages = 3  # 总页数

        # 多页面图标配置（每一页各自的图标配置，按键编号: 图标文件名）
        self.icon_mapping = {
            1: {  # 第一页icon配置
                1: "r.png",
                2: "n.png",
                3: "s.png",
                4: "ac.png",
                5: "defrost.png",
                6: "d.png",
                7: "p.png",
                8: "pix.png",
                9: "recirculate.png",
                10: "fresh.png",
                11: "temp.png",
                12: "fans.png",
                13: "leftdoor.png",
                14: "rightdoor.png",
                56: "",  # 下一页
                57: "",  # 上一页
                64: "",
                65: "",
                66: "",
                67: "",
                160: "",
                161: "",
                80: "",
                81: "",
                144: "",
                145: "",
                112: "",
                113: ""
            },
            2: {  # 第二页icon配置
                1: "back.png",
                2: "eco1.png",
                3: "eco2.png",
                4: "eco3.png",
                5: "face.png",
                6: "left.png",
                7: "right.png",
                8: "pix.png",
                9: "faceandfoot.png",
                10: "foot.png",
                11: "temp.png",
                12: "fans.png",
                13: "leftdoor.png",
                14: "rightdoor.png",
                56: "",  # 下一页
                57: "",  # 上一页
                64: "",
                65: "",
                66: "",
                67: "",
                160: "",
                161: "",
                80: "",
                81: "",
                144: "",
                145: "",
                112: "",
                113: ""
            },
            3: {  # 第三页icon配置
                1: "r.png",
                2: "r.png",
                3: "r.png",
                4: "r.png",
                5: "r.png",
                6: "d.png",
                7: "d.png",
                8: "pix.png",
                9: "d.png",
                10: "d.png",
                11: "temp.png",
                12: "fans.png",
                13: "leftdoor.png",
                14: "rightdoor.png",
                56: "",  # 下一页
                57: "",  # 上一页
                64: "",
                65: "",
                66: "",
                67: "",
                160: "",
                161: "",
                80: "",
                81: "",
                144: "",
                145: "",
                112: "",
                113: ""
            }
        }

    def initialize(self) -> bool:
        """
        初始化所有连接的StreamDock设备
        :return: 初始化是否成功
        """
        try:
            # 枚举所有连接的设备
            self.devices = self.manager.enumerate()
            if not self.devices:
                logging.warning("未检测到任何StreamDock设备")
                return False

            # 启动设备监听线程（守护线程）
            self._running = True
            threading.Thread(
                target=self._device_listener,
                daemon=True
            ).start()

            # 初始化每个设备
            for device in self.devices:
                self._init_single_device(device)

            return True
        except Exception as e:
            logging.error(f"初始化失败: {str(e)}")
            return False

    def register_key_callback(self, key_num: int, callback: Callable):
        """
        注册按键回调函数
        :param key_num: 按键编号
        :param callback: 回调函数
        """
        if 1 <= key_num <= 500:
            self._key_event_callbacks[key_num] = callback
            logging.debug(f"按键 {key_num} 回调已注册")
        else:
            logging.warning(f"无效的按键编号: {key_num}")

    def _init_single_device(self, device):
        """
        初始化单个设备
        :param device: 设备实例
        """
        try:
            # 打开并初始化设备
            device.open()
            device.init()

            # 设备读取线程（处理按键事件）
            def device_read_loop():
                while self._running:
                    try:
                        data = device.read()
                        logging.debug(f"读取到设备数据: {data}")
                        
                        key_num = None
                        status = None
                        
                        if isinstance(data, tuple):
                            # 假设数据格式：(..., 'ACK', 'OK', key编号, 状态)
                            if len(data) >= 5 and data[1] == 'ACK' and data[2] == 'OK':
                                key_num = data[3]
                                status = data[4]
                                
                        if isinstance(key_num, int):
                            if key_num in self._key_event_callbacks:
                                logging.info(f"触发按键 {key_num} 的回调")
                                self._key_event_callbacks[key_num](key_num, status)
                            else:
                                logging.warning(f"未注册的按键编号: {key_num}")
                        
                    except Exception as e:
                        logging.error(f"设备读取错误: {str(e)}")
                        time.sleep(0.1)

            threading.Thread(
                target=device_read_loop,
                daemon=True
            ).start()

            # 初始显示设置：背景、清空按键、设置按键图标
            self.set_background(device, self.DEFAULT_BACKGROUND)
            time.sleep(1)
            self.clear_all_keys(device)
            time.sleep(0.5)
            self.set_all_key_icons(device)
        except Exception as e:
            logging.error(f"设备初始化失败: {str(e)}")

    def _device_listener(self):
        """设备热插拔监听线程"""
        while self._running:
            try:
                self.manager.listen()
                time.sleep(0.1)
            except Exception as e:
                logging.error(f"设备监听错误: {str(e)}")

    def set_background(self, device, bg_filename: str) -> bool:
        """
        设置设备背景图片
        :param device: 设备实例
        :param bg_filename: 背景图片文件名
        :return: 是否设置成功
        """
        bg_path = self._get_resource_path(bg_filename)
        if not bg_path:
            return False

        try:
            device.set_touchscreen_image(bg_path)
            device.refresh()  # 刷新显示
            return True
        except Exception as e:
            logging.error(f"设置背景失败: {str(e)}")
            return False

    def clear_all_keys(self, device) -> bool:
        """
        清空所有按键图标
        :param device: 设备实例
        :return: 是否成功
        """
        try:
            device.clearAllIcon()
            device.refresh()
            return True
        except Exception as e:
            logging.error(f"清空按键失败: {str(e)}")
            return False

    def set_all_key_icons(self, device, delay: float = 0.05) -> bool:
        """
        根据当前页面为所有按键设置图标
        :param device: 设备实例
        :param delay: 每个按键之间的延迟(秒)
        :return: 是否全部设置成功
        """
        try:
            success = True
            # 依据当前页面获取对应图标配置
            page_icons = self.icon_mapping.get(self.current_page, {})
            for key_num, icon_file in page_icons.items():
                if not self.set_key_icon(device, key_num, icon_file):
                    success = False
                time.sleep(delay)
            return success
        except Exception as e:
            logging.error(f"设置按键图标失败: {str(e)}")
            return False

    def set_key_icon(self, device, key_num: int, icon_filename: str) -> bool:
        """
        设置单个按键图标
        :param device: 设备实例
        :param key_num: 按键编号
        :param icon_filename: 图标文件名
        :return: 是否设置成功
        """
        if key_num not in self.icon_mapping.get(self.current_page, {}):
            logging.warning(f"当前页面无效的按键编号: {key_num}")
            return False

        icon_path = self._get_resource_path(icon_filename)
        if not icon_path:
            return False

        try:
            device.set_key_image(key_num, icon_path)
            device.refresh()
            return True
        except Exception as e:
            logging.error(f"设置按键{key_num}图标失败: {str(e)}")
            return False

    def _get_resource_path(self, filename: str) -> Optional[str]:
        """
        获取资源文件的完整路径
        :param filename: 文件名
        :return: 完整路径或 None（如果文件不存在）
        """
        if not filename:
            return None
        resource_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            self.DEFAULT_ICON_DIR,
            filename
        )
        if not os.path.exists(resource_path):
            logging.warning(f"资源文件不存在: {resource_path}")
            return None
        return resource_path

    def change_page(self, next_page: bool):
        """
        切换页面，更新当前页号并刷新所有设备的按键图标
        :param next_page: True 表示下一页，False 表示上一页
        """
        if next_page:
            self.current_page = (self.current_page % self.total_pages) + 1
        else:
            self.current_page = (self.current_page - 2 + self.total_pages) % self.total_pages + 1
        logging.info(f"切换到第 {self.current_page} 页")
        self.update_all_keys()

    def update_all_keys(self):
        """
        刷新所有设备的按键图标（依据当前页面）
        """
        for device in self.devices:
            self.clear_all_keys(device)
            self.set_all_key_icons(device)

    def shutdown(self):
        """安全关闭所有设备"""
        self._running = False
        for device in self.devices:
            try:
                self.clear_all_keys(device)
                device.close()
            except Exception as e:
                logging.error(f"设备关闭时出错: {str(e)}")


class StreamDockApp:
    """StreamDock应用程序主类"""

    def __init__(self):
        """初始化应用"""
        self.controller = StreamDockController()
        self._setup_callbacks()

    def _setup_callbacks(self):
        """注册所有按键回调函数"""
        for key in range(1, 500):
            self.controller.register_key_callback(
                key,
                partial(self._on_key_press, key)
            )
            logging.info(f"按键 {key} 回调已注册")

    def _on_key_press(self, key, key_num, status):
        """
        按键事件处理函数
        :param key: 注册时的按键编号（由 register_key_callback 传入）
        :param key_num: 从设备数据中解析出的实际按键编号
        :param status: 按键状态
        """
        # 如果是翻页按键，直接调用页面切换
        if key_num == 56:
            self.controller.change_page(next_page=True)
            return
        elif key_num == 57:
            self.controller.change_page(next_page=False)
            return

        # 其它按键，调用获取功能描述函数（传入当前页面信息）
        key_num, description = get_key_function(key_num, self.controller.current_page)
        # 此处你可以根据 description 进一步调用具体的功能处理函数
        logging.info(f"执行功能: {description}")

    def run(self):
        """运行应用程序主循环"""
        if not self.controller.initialize():
            return

        logging.info("StreamDock控制器已启动, 按 Ctrl+C 退出...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("正在关闭...")
        finally:
            self.controller.shutdown()
            logging.info("程序已退出")


if __name__ == "__main__":
    app = StreamDockApp()
    app.run()
