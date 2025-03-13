import base64
import hmac
import json
import os
import queue
import threading
import time
import tkinter as tk
import traceback
from datetime import datetime
from tkinter import scrolledtext, ttk, font
from typing import Optional
from urllib.parse import urlencode

import requests
from eth_account import Account
from web3 import Web3


class ConfigApp:
    def __init__(self, root):
        self.log_text = None
        self.is_selling = None
        self.adv_entries = None
        self.ca_entry = None
        self.is_buying = None
        self.sell_button = None
        self.root = root
        self.root.title("OKX Evm Swap Helper")
        self.root.geometry("950x900")
        self.root.configure(bg="#f0f0f0")

        # 设置窗口最小尺寸
        self.root.resizable(False, False)

        # 将窗口居中显示
        self.center_window()

        # 设置字体
        self.title_font = font.Font(family="Microsoft YaHei", size=14, weight="bold")
        self.label_font = font.Font(family="Microsoft YaHei", size=10)
        self.button_font = font.Font(family="Microsoft YaHei", size=10, weight="bold")
        self.header_font = font.Font(family="Microsoft YaHei", size=15, weight="bold")  # 添加大标题字体
        self.author_font = font.Font(family="Microsoft YaHei", size=10)  # 添加大标题字体

        # 初始化entries列表
        self.entries = []

        # 创建主框架
        main_frame = tk.Frame(root, bg="#f0f0f0", padx=20, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建一个框架来容纳标题和作者信息
        header_frame = tk.Frame(main_frame, bg="#f0f0f0")
        header_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))

        # 添加大标题，靠左显示
        header_label = tk.Label(header_frame, text=" OKX Evm Swap Helper - Based on OKX", font=self.header_font, bg="#f0f0f0", fg="#333333")
        header_label.pack(side=tk.LEFT, anchor=tk.W)

        # 添加作者信息，靠右显示
        author_label = tk.Label(header_frame, text="   Author: @sky_887766", font=self.author_font, bg="#f0f0f0", fg="#333333")
        author_label.pack(side=tk.LEFT, anchor=tk.E)

        # 创建自定义样式
        style = ttk.Style()

        # 配置未选中标签的样式
        style.configure("TNotebook.Tab", font=('Microsoft YaHei', 10))

        # 配置选中标签的样式
        style.map("TNotebook.Tab", foreground=[('selected', 'Purple')])

        # 创建标签页控件
        self.notebook = ttk.Notebook(main_frame, style="TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        # 创建基本配置标签页
        self.basic_config_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.basic_config_tab, text="交易操作")

        # 创建高级配置标签页
        self.advanced_config_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.advanced_config_tab, text="基本配置")

        # 设置基本配置标签页内容
        self.setup_basic_config_tab()

        # 设置高级配置标签页内容
        self.setup_advanced_config_tab()

        # 创建一个队列用于线程间通信 - 移到这里，在使用log方法之前
        self.log_queue = queue.Queue()

        # 尝试加载现有配置
        self.load_config()

        # 初始日志
        self.log("程序已启动")

        # 启动一个定时器来处理日志队列
        self.root.after(100, self.process_log_queue)

    def center_window(self):
        """将窗口居中显示在屏幕上"""
        # 更新窗口信息，确保获取正确的尺寸
        self.root.update_idletasks()

        # 获取屏幕宽度和高度
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 获取窗口宽度和高度 - 使用winfo_width和winfo_height获取当前窗口大小
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()

        # 如果窗口尚未渲染，使用geometry中设置的值
        if window_width <= 1:
            window_width = 880
        if window_height <= 1:
            window_height = 900

        # 计算窗口应该显示的位置
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        # 设置窗口位置，保持大小不变
        self.root.geometry(f"+{x}+{y}")

    def setup_basic_config_tab(self):
        """设置基本配置标签页内容"""
        # 创建交易参数框架
        trade_frame = tk.LabelFrame(self.basic_config_tab, text="交易参数", font=self.label_font, padx=15, pady=10)
        trade_frame.pack(fill=tk.X, padx=5, pady=5)

        # 操作的链和RPC在一行
        row1 = tk.Frame(trade_frame)
        row1.pack(fill=tk.X, pady=3)

        # 操作的链 - 标签和下拉框在同一行
        chain_select_label = tk.Label(row1, text="操作的链:", font=self.label_font, width=8, anchor="e")
        chain_select_label.pack(side=tk.LEFT, padx=(5, 2))

        self.chain_combobox = ttk.Combobox(row1, width=18, font=self.label_font, state="readonly")
        self.chain_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.chain_combobox.bind("<<ComboboxSelected>>", self.on_chain_selected)

        # RPC - 标签和输入框在同一行
        rpc_label = tk.Label(row1, text="RPC:", font=self.label_font, width=8, anchor="e")
        rpc_label.pack(side=tk.LEFT, padx=(5, 2))

        self.rpc_entry = ttk.Entry(row1, width=20, font=self.label_font)
        self.rpc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entries.append(self.rpc_entry)  # 现在这是entries[0]

        # 滑点和链ID在一行
        row2 = tk.Frame(trade_frame)
        row2.pack(fill=tk.X, pady=3)

        # 滑点 - 标签和输入框在同一行
        slippage_label = tk.Label(row2, text="滑点:", font=self.label_font, width=8, anchor="e")
        slippage_label.pack(side=tk.LEFT, padx=(5, 2))

        slippage_entry = ttk.Entry(row2, width=20, font=self.label_font)
        slippage_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.entries.append(slippage_entry)  # 现在这是entries[1]

        # 链ID - 标签和输入框在同一行
        chain_id_label = tk.Label(row2, text="链ID:", font=self.label_font, width=8, anchor="e")
        chain_id_label.pack(side=tk.LEFT, padx=(5, 2))

        self.chain_id_entry = ttk.Entry(row2, width=20, font=self.label_font)
        self.chain_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entries.append(self.chain_id_entry)  # 现在这是entries[2]

        # 买入金额和卖出比例在一行
        row3 = tk.Frame(trade_frame)
        row3.pack(fill=tk.X, pady=3)

        # 买入金额 - 标签和输入框在同一行
        buy_amount_label = tk.Label(row3, text="买入金额:", font=self.label_font, width=8, anchor="e")
        buy_amount_label.pack(side=tk.LEFT, padx=(5, 2))

        buy_amount_entry = ttk.Entry(row3, width=20, font=self.label_font)
        buy_amount_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.entries.append(buy_amount_entry)  # 现在这是entries[3]

        # 卖出比例 - 标签和输入框在同一行
        sell_ratio_label = tk.Label(row3, text="卖出比例:", font=self.label_font, width=8, anchor="e")
        sell_ratio_label.pack(side=tk.LEFT, padx=(5, 2))

        sell_ratio_entry = ttk.Entry(row3, width=20, font=self.label_font)
        sell_ratio_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entries.append(sell_ratio_entry)  # 现在这是entries[4]

        # 保存信息按钮单独一行
        save_frame = tk.Frame(trade_frame)
        save_frame.pack(fill=tk.X, pady=3)

        save_rpc_button = ttk.Button(
            save_frame,
            text="保存信息",
            command=self.save_config,
            width=20,
            style="Accent.TButton"
        )
        save_rpc_button.pack(side=tk.TOP, pady=3, anchor=tk.CENTER)

        # 创建单独的交易操作框架
        action_frame_container = tk.LabelFrame(self.basic_config_tab, text="交易操作", font=self.label_font, padx=15, pady=10)
        action_frame_container.pack(fill=tk.X, padx=5, pady=5)

        # CA、一键买入和一键卖出在一行
        action_frame = tk.Frame(action_frame_container)
        action_frame.pack(fill=tk.X, pady=5)

        # CA - 标签和输入框
        ca_label = tk.Label(action_frame, text="购买的CA:", font=self.label_font, width=8, anchor="e")
        ca_label.pack(side=tk.LEFT, padx=(5, 2))

        self.ca_entry = ttk.Entry(action_frame, width=30, font=self.label_font)
        self.ca_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 70))

        # 创建一键买入和一键卖出按钮
        self.buy_button = ttk.Button(
            action_frame,
            text="一键买入",
            command=self.buy_token,
            width=20,
            style="Accent.TButton"
        )
        self.buy_button.pack(side=tk.LEFT, padx=5)

        self.sell_button = ttk.Button(
            action_frame,
            text="一键卖出",
            command=self.sell_token,
            width=20,
            style="Accent.TButton"
        )
        self.sell_button.pack(side=tk.LEFT, padx=5)

        # 添加操作状态标志
        self.is_buying = False
        self.is_selling = False

        # 创建自定义样式
        style = ttk.Style()
        style.configure("Accent.TButton", font=self.button_font)
        style.configure("Action.TButton", font=self.button_font)

        # 添加日志输出框 - 修改字体以支持emoji
        log_frame = tk.LabelFrame(self.basic_config_tab, text="系统日志", font=self.label_font, padx=15, pady=15)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        log_font = ("Consolas", 11)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            width=50,
            height=15,
            font=log_font,
            bg="#ffffff",
            fg="#333333"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text.config(state=tk.DISABLED)  # 设置为只读

        # 创建不同颜色的标签
        self.log_text.tag_config("info", foreground="#000000")  # 黑色 - 普通信息
        self.log_text.tag_config("success", foreground="#008800")  # 绿色 - 成功信息
        self.log_text.tag_config("warning", foreground="#FF8800")  # 橙色 - 警告信息
        self.log_text.tag_config("error", foreground="#FF0000")  # 红色 - 错误信息
        self.log_text.tag_config("highlight", foreground="#0000FF")  # 蓝色 - 高亮信息

    def setup_advanced_config_tab(self):
        """设置高级配置标签页内容"""
        # 创建输入框架
        adv_input_frame = tk.LabelFrame(self.advanced_config_tab, text="高级参数", font=self.label_font, padx=15, pady=10)
        adv_input_frame.pack(fill=tk.X, padx=5, pady=5)

        # 创建标签和输入框
        self.adv_labels = ["API Key:", "API Secret:", "Passphrase:", "Private Key:"]
        self.adv_entries = []

        # 第一行: API Key 和 API Secret
        adv_row1 = tk.Frame(adv_input_frame)
        adv_row1.pack(fill=tk.X, pady=3)

        # API Key - 标签和输入框在同一行
        api_key_label = tk.Label(adv_row1, text=self.adv_labels[0], font=self.label_font, width=10, anchor="e")
        api_key_label.pack(side=tk.LEFT, padx=(5, 2))

        api_key_entry = ttk.Entry(adv_row1, width=20, font=self.label_font)
        api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.adv_entries.append(api_key_entry)

        # API Secret - 标签和输入框在同一行
        api_secret_label = tk.Label(adv_row1, text=self.adv_labels[1], font=self.label_font, width=10, anchor="e")
        api_secret_label.pack(side=tk.LEFT, padx=(5, 2))

        api_secret_entry = ttk.Entry(adv_row1, width=20, font=self.label_font)
        api_secret_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.adv_entries.append(api_secret_entry)

        # 第二行: Passphrase 和 Private Key
        adv_row2 = tk.Frame(adv_input_frame)
        adv_row2.pack(fill=tk.X, pady=3)

        # Passphrase - 标签和输入框在同一行
        passphrase_label = tk.Label(adv_row2, text=self.adv_labels[2], font=self.label_font, width=10, anchor="e")
        passphrase_label.pack(side=tk.LEFT, padx=(5, 2))

        passphrase_entry = ttk.Entry(adv_row2, width=20, font=self.label_font)
        passphrase_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.adv_entries.append(passphrase_entry)

        # Private Key - 标签和输入框在同一行
        private_key_label = tk.Label(adv_row2, text=self.adv_labels[3], font=self.label_font, width=10, anchor="e")
        private_key_label.pack(side=tk.LEFT, padx=(5, 2))

        private_key_entry = ttk.Entry(adv_row2, width=20, font=self.label_font)
        private_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.adv_entries.append(private_key_entry)

        # 创建保存按钮
        adv_button_frame = tk.Frame(adv_input_frame, pady=5)
        adv_button_frame.pack(fill=tk.X)

        self.adv_save_button = ttk.Button(
            adv_button_frame,
            text="保存高级配置",
            command=self.save_advanced_config,
            width=15,
            style="Accent.TButton"
        )
        self.adv_save_button.pack(pady=5)

        # 创建独立的RPC信息框架
        rpc_input_frame = tk.LabelFrame(self.advanced_config_tab, text="添加RPC信息", font=self.label_font, padx=15, pady=10)
        rpc_input_frame.pack(fill=tk.X, padx=5, pady=5)

        # RPC单独一行
        rpc_row = tk.Frame(rpc_input_frame)
        rpc_row.pack(fill=tk.X, pady=3)

        # RPC - 标签和输入框在同一行
        rpc_label = tk.Label(rpc_row, text="RPC:", font=self.label_font, width=10, anchor="e")
        rpc_label.pack(side=tk.LEFT, padx=(5, 2))

        self.adv_rpc_entry = ttk.Entry(rpc_row, width=40, font=self.label_font)
        self.adv_rpc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # RPC名称和链ID一行
        name_chain_row = tk.Frame(rpc_input_frame)
        name_chain_row.pack(fill=tk.X, pady=3)

        # RPC名称 - 标签和输入框在同一行
        rpc_name_label = tk.Label(name_chain_row, text="RPC名称:", font=self.label_font, width=10, anchor="e")
        rpc_name_label.pack(side=tk.LEFT, padx=(5, 2))

        self.adv_rpc_name_entry = ttk.Entry(name_chain_row, width=20, font=self.label_font)
        self.adv_rpc_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # 链ID - 标签和输入框在同一行
        chain_id_label = tk.Label(name_chain_row, text="链ID:", font=self.label_font, width=10, anchor="e")
        chain_id_label.pack(side=tk.LEFT, padx=(5, 2))

        self.adv_chain_id_entry = ttk.Entry(name_chain_row, width=20, font=self.label_font)
        self.adv_chain_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # 添加RPC信息按钮和更新RPC列表按钮在同一行
        rpc_button_frame = tk.Frame(rpc_input_frame, pady=5)
        rpc_button_frame.pack(fill=tk.X)

        self.add_rpc_button = ttk.Button(
            rpc_button_frame,
            text="添加RPC信息",
            command=self.add_rpc_info,
            width=30,
            style="Accent.TButton"
        )
        self.add_rpc_button.pack(side=tk.LEFT, padx=(170, 100), pady=5)

        # 添加更新RPC列表按钮
        self.update_rpc_list_button = ttk.Button(
            rpc_button_frame,
            text="更新RPC列表",
            command=self.update_rpc_list,
            width=30,
            style="Accent.TButton"
        )
        self.update_rpc_list_button.pack(side=tk.LEFT, padx=0, pady=5)

        # 添加高级设置说明
        info_frame = tk.LabelFrame(self.advanced_config_tab, text="参数说明", font=self.label_font, padx=15, pady=15)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        info_text = tk.Text(
            info_frame,
            width=50,
            height=15,
            font=("Microsoft YaHei", 9),
            bg="#ffffff",
            fg="#333333",
            wrap=tk.WORD
        )
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 添加说明文本
        info_text.insert(tk.END, "\n\nAPI Key / API Secret / Passphrase\n\n以上三个在这里申请 > https://www.okx.com/zh-hans-sg/web3/build/dev-portal ")
        info_text.insert(tk.END, "\n\n\nPrivate Key: 自己账号的私钥。")
        info_text.insert(tk.END, "\n\n\nRPC / 链ID: 添加新的RPC信息到基本配置中。")
        info_text.config(state=tk.DISABLED)  # 设置为只读

    def add_rpc_info(self):
        """将RPC信息添加到基本配置中并保存到config.json"""
        rpc_name = self.adv_rpc_name_entry.get()
        rpc = self.adv_rpc_entry.get()
        chain_id = self.adv_chain_id_entry.get()

        if not rpc or not chain_id or not rpc_name:
            # self.log("错误: RPC或链ID或名称不能为空")
            return

        # # 更新基本配置中的RPC和链ID
        # self.entries[0].delete(0, tk.END)
        # self.entries[0].insert(0, rpc)
        #
        # self.entries[2].delete(0, tk.END)
        # self.entries[2].insert(0, chain_id)

        # 清空高级配置中的RPC和链ID输入框
        self.adv_rpc_name_entry.delete(0, tk.END)
        self.adv_rpc_entry.delete(0, tk.END)
        self.adv_chain_id_entry.delete(0, tk.END)

        # 保存RPC信息到config.json
        try:
            # 读取现有配置
            config_data = {}
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config_data = json.load(f)

            # 添加或更新RPC信息
            rpc_key = f"RPC/{rpc_name}"
            rpc_value = f"{rpc}?{chain_id}"
            config_data[rpc_key] = rpc_value

            # 保存回文件
            with open("config.json", "w") as f:
                json.dump(config_data, f, indent=4)

            # 显示成功消息
            self.log(f"RPC信息 '{rpc_name}' 已成功添加到配置文件")

            # 更改按钮文本为"添加成功"
            self.add_rpc_button.config(text="添加成功")

            # 1秒后恢复按钮文本
            self.root.after(500, self._reset_add_rpc_button_text)
        except Exception as e:
            error_msg = f"保存RPC信息失败: {str(e)}"
            self.log(error_msg)

    def _reset_add_rpc_button_text(self):
        """恢复添加RPC信息按钮的文本"""
        self.add_rpc_button.config(text="添加RPC信息")

    def process_log_queue(self):
        """处理日志队列中的消息"""
        try:
            # 尝试从队列中获取所有消息
            while True:
                message = self.log_queue.get_nowait()
                self._log_direct(message)
                self.log_queue.task_done()
        except queue.Empty:
            pass
        finally:
            # 无论如何，继续定时检查队列
            self.root.after(100, self.process_log_queue)

    def log(self, message, level="info"):
        """向日志队列添加消息，可以指定级别（info, success, warning, error, highlight）"""
        # 将消息和级别放入队列
        self.log_queue.put((message, level))

    def _log_direct(self, message_data):
        """直接更新日志UI（仅在主线程中调用）"""
        # 如果消息为特殊标记"EMPTY_LINE"，则添加一个完全空白的行
        if message_data == "EMPTY_LINE":
            self.log_text.config(state=tk.NORMAL)  # 临时允许编辑
            self.log_text.insert(tk.END, "\n")
            self.log_text.see(tk.END)  # 滚动到最新内容
            self.log_text.config(state=tk.DISABLED)  # 恢复只读状态
            return

        # 解包消息和级别
        if isinstance(message_data, tuple) and len(message_data) == 2:
            message, level = message_data
        else:
            message, level = message_data, "info"  # 默认为info级别

        # 正常消息添加时间戳
        current_time = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{current_time}] {message}"

        self.log_text.config(state=tk.NORMAL)  # 临时允许编辑
        self.log_text.insert(tk.END, log_message + "\n", level)  # 使用对应的标签
        self.log_text.see(tk.END)  # 滚动到最新内容
        self.log_text.config(state=tk.DISABLED)  # 恢复只读状态

    def load_config(self):
        """尝试加载现有的config.json文件"""
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config_data = json.load(f)

                # 将读取的数据填充到基本配置输入框
                if "rpc" in config_data:
                    self.entries[0].insert(0, config_data["rpc"])
                if "slippage" in config_data:
                    self.entries[1].insert(0, config_data["slippage"])
                if "chain_id" in config_data:
                    self.entries[2].insert(0, config_data["chain_id"])
                if "buy_amount" in config_data:
                    self.entries[3].insert(0, config_data["buy_amount"])
                if "sell_ratio" in config_data:
                    self.entries[4].insert(0, config_data["sell_ratio"])
                if "ca" in config_data:
                    self.ca_entry.insert(0, config_data["ca"])

                # 将读取的数据填充到高级配置输入框
                if "api_key" in config_data:
                    self.adv_entries[0].insert(0, config_data["api_key"])
                if "api_secret" in config_data:
                    self.adv_entries[1].insert(0, config_data["api_secret"])
                if "passphrase" in config_data:
                    self.adv_entries[2].insert(0, config_data["passphrase"])
                if "private_key" in config_data:
                    self.adv_entries[3].insert(0, config_data["private_key"])

            # 加载RPC链选项到下拉框
            self.load_rpc_chains(config_data)

            self.log("成功加载配置文件")
        except Exception as e:
            # 如果读取失败，不做任何操作，输入框保持为空
            self.load_rpc_chains({})
            self.log(f"加载配置文件失败: {str(e)}")
            self.log('如果是第一次使用,请看参数配置页面的操作说明!')

    def load_rpc_chains(self, config_data):
        """从配置数据中加载RPC链到下拉框"""
        chain_options = []

        # 添加默认选项
        default_option = "请在基本配置添加RPC，并下拉选择操作的链"
        chain_options.append(default_option)

        # 遍历配置数据，查找以"RPC/"开头的键
        for key in config_data:
            if key.startswith("RPC/"):
                # 提取RPC名称（"RPC/"后面的部分）
                chain_name = key[4:]  # 跳过"RPC/"前缀
                chain_options.append(chain_name)

        # 更新下拉框选项
        self.chain_combobox['values'] = chain_options

        # 检查是否有默认链设置
        default_index = 0  # 默认选择第一个选项
        if "default_chain" in config_data and config_data["default_chain"] in chain_options:
            default_index = chain_options.index(config_data["default_chain"])
            # 如果找到默认链，自动触发选择事件
            self.chain_combobox.current(default_index)
            # 手动触发链选择事件
            self.on_chain_selected(None)
        else:
            self.chain_combobox.current(0)  # 默认选择第一个选项

    def on_chain_selected(self, event):
        """当用户从下拉框选择链时触发"""
        selected_chain = self.chain_combobox.get()
        # 确保选择了有效的链（不是默认提示文本）
        default_text = "请在基本配置添加RPC，并下拉选择操作的链"

        if selected_chain and selected_chain != default_text:
            try:
                # 读取配置文件
                if os.path.exists("config.json"):
                    with open("config.json", "r") as f:
                        config_data = json.load(f)

                # 获取选中链的RPC信息
                rpc_key = f"RPC/{selected_chain}"
                if rpc_key in config_data:
                    rpc_value = config_data[rpc_key]
                    # 解析RPC值，格式为"rpc/chain_id"
                    rpc_parts = rpc_value.split('?')
                    # print(rpc_parts)
                    if len(rpc_parts) >= 2:
                        rpc = rpc_parts[0]
                        chain_id = rpc_parts[1]

                        # 打印调试信息到日志
                        self.log(f"已加载 {selected_chain} 的RPC信息")

                        # 更新RPC和链ID输入框
                        self.entries[0].delete(0, tk.END)
                        self.entries[0].insert(0, rpc)

                        self.entries[2].delete(0, tk.END)
                        self.entries[2].insert(0, chain_id)

                        # 更新config_data中的rpc和chain_id值
                        config_data["rpc"] = rpc
                        config_data["chain_id"] = chain_id

                        # 保存更新后的配置
                        with open("config.json", "w") as f:
                            json.dump(config_data, f, indent=4)

                        # self.log(f"已加载 {selected_chain} 的RPC信息")
                    else:
                        self.log(f"错误: RPC值格式不正确: {rpc_value}")
                else:
                    self.log(f"错误: 找不到链 {selected_chain} 的RPC信息")
            except Exception as e:
                self.log(f"加载链信息失败: {str(e)}")
                import traceback
                self.log(traceback.format_exc())

    def save_config(self):
        # 获取所有输入框的值
        config_data = {
            "rpc": self.entries[0].get(),
            "slippage": self.entries[1].get(),
            "chain_id": self.entries[2].get(),
            "buy_amount": self.entries[3].get(),
            "sell_ratio": self.entries[4].get(),
            "ca": self.ca_entry.get(),  # 保存CA值
            "api_key": self.adv_entries[0].get(),
            "api_secret": self.adv_entries[1].get(),
            "passphrase": self.adv_entries[2].get(),
            "private_key": self.adv_entries[3].get(),
        }

        # 检查当前选择的链
        selected_chain = self.chain_combobox.get()
        default_text = "请在基本配置添加RPC，并下拉选择操作的链"

        # 保存为JSON文件
        try:
            # 读取现有配置以保留RPC信息
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    old_config = json.load(f)
                    # 保留所有以RPC/开头的键
                    for key in old_config:
                        if key.startswith("RPC/"):
                            config_data[key] = old_config[key]

            # 如果用户选择了一个有效的链（不是默认提示文本），则将其设置为默认链
            if selected_chain and selected_chain != default_text:
                config_data["default_chain"] = selected_chain
                self.log(f"已将 {selected_chain} 设置为默认链")

            with open("config.json", "w") as f:
                json.dump(config_data, f, indent=4)
            self.log("配置已成功保存到config.json")
        except Exception as e:
            error_msg = f"保存失败: {str(e)}"
            self.log(error_msg)

    def buy_token(self):
        """一键买入功能 - 使用线程执行"""
        # 如果已经在执行操作，则不再启动新线程
        if self.is_buying or self.is_selling:
            return

        # 设置买入状态为True
        self.is_buying = True

        # 禁用买入和卖出按钮
        self.buy_button.config(state="disabled")
        self.sell_button.config(state="disabled")

        # 创建一个新线程来执行买入操作
        buy_thread = threading.Thread(target=self._buy_token_thread)
        buy_thread.daemon = True  # 设置为守护线程，这样主程序退出时线程也会退出
        buy_thread.start()

    def _buy_token_thread(self):
        """在单独的线程中执行买入操作"""
        try:
            # 获取所有输入框的值 - 在主线程中获取UI值
            # 注意：这里可能需要使用线程安全的方式获取UI值
            rpc = self.entries[0].get()
            slippage = self.entries[1].get()
            chain_id = self.entries[2].get()
            buy_amount = self.entries[3].get()
            sell_ratio = self.entries[4].get()
            ca = self.ca_entry.get()
            api_key = self.adv_entries[0].get()
            api_secret = self.adv_entries[1].get()
            passphrase = self.adv_entries[2].get()
            private_key = self.adv_entries[3].get()

            # 检查必要参数
            if not ca or not buy_amount:
                self.log("错误: CA和买入金额不能为空")
                return

            if not api_key or not api_secret or not passphrase or not private_key:
                self.log("错误: API Key、API Secret、Passphrase和Private Key不能为空")
                return

            if not slippage:
                self.log("错误: 滑点不能为空")
                return

            # 输出所有参数到日志，添加完全空白的行
            self.log_queue.put("EMPTY_LINE")  # 添加完全空白的行
            self.log("===== 买入操作参数 =====", "highlight")
            self.log(f"CA: {ca}")
            self.log(f"滑点: {slippage}")
            self.log(f"买入金额: {buy_amount}")
            # self.log("========================")

            # 调用OKX买入功能
            self.log("开始执行OKX买入操作...")

            # 创建OKXDexSwap实例
            dex = OKXDexSwap(api_key, api_secret, passphrase, private_key)

            # 代币地址
            BNB_ADDRESS = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"

            # 转换买入金额为wei
            amount_wei = str(int(float(buy_amount) * 1e18))

            # 获取报价
            self.log("买入获取报价中...")
            quote = dex.get_quote(BNB_ADDRESS, ca, float(slippage) / 100, amount_wei, chain_id)

            if quote is None:
                self.log("获取买入报价失败")
                return

            if quote.get("code") == "0":
                # 显示预计收到的代币数量
                expected_amount = quote["data"][0]["toTokenAmount"]
                self.log(f"预计收到的代币 {float(expected_amount) / 1e18:.8f} {quote['data'][0]['toToken']['tokenSymbol']}")
                self.log(f"价格影响: {quote['data'][0]['priceImpactPercentage']}%")
                self.log(f"使用DEX: {quote['data'][0]['quoteCompareList'][0]['dexName']}")

                # 执行交换
                swap_result = dex.swap(quote["data"], float(slippage) / 100)
                if swap_result and swap_result.get("code") == "0":
                    # 从响应中提取交易数据
                    tx_data = swap_result["data"][0]["tx"]
                    self.log("买入交易数据已获取!")

                    # 发送交易
                    self.log('准备发送买入交易...')
                    tx_result = dex.send_transaction(tx_data, rpc, chain_id)
                    if tx_result:
                        tx_hash = tx_result['tx_hash']
                        receipt = tx_result['receipt']

                        self.log(f"等待买入哈希确认:{tx_hash}")

                        # 检查交易是否成功
                        if receipt['status'] == 1:
                            self.log(">> 买入交易成功! 后台进行预授权方便卖出...", "success")
                            dex.check_and_approve(ca, rpc, chain_id, wait=False)
                        else:
                            self.log('[ 买入交易失败 ]', "error")
                    else:
                        self.log("发送买入交易失败", "error")
                else:
                    self.log(f"获取买入交易数据失败: {swap_result}", "error")
            else:
                self.log(f"获取买入报价失败: {quote}", "error")
        except Exception as e:
            error_msg = f"买入失败: {str(e)}"
            self.log(error_msg, "error")
            self.log(traceback.format_exc())
        finally:
            # 操作完成，设置买入状态为False
            self.is_buying = False
            # 检查是否可以恢复按钮状态
            self.root.after(0, self._check_and_enable_buttons)
        # self.log("========================")
        self.log_queue.put("EMPTY_LINE")  # 添加完全空白的行

    def sell_token(self):
        """一键卖出功能 - 使用线程执行"""
        # 如果已经在执行操作，则不再启动新线程
        if self.is_buying or self.is_selling:
            return

        # 设置卖出状态为True
        self.is_selling = True

        # 禁用买入和卖出按钮
        self.buy_button.config(state="disabled")
        self.sell_button.config(state="disabled")

        # 创建一个新线程来执行卖出操作
        sell_thread = threading.Thread(target=self._sell_token_thread)
        sell_thread.daemon = True
        sell_thread.start()

    def _sell_token_thread(self):
        """在单独的线程中执行卖出操作"""
        try:
            # 获取所有输入框的值 - 在主线程中获取UI值
            # 注意：这里可能需要使用线程安全的方式获取UI值
            rpc = self.entries[0].get()
            slippage = self.entries[1].get()
            chain_id = self.entries[2].get()
            buy_amount = self.entries[3].get()
            sell_ratio = self.entries[4].get()
            ca = self.ca_entry.get()
            api_key = self.adv_entries[0].get()
            api_secret = self.adv_entries[1].get()
            passphrase = self.adv_entries[2].get()
            private_key = self.adv_entries[3].get()

            # 验证卖出比例是整数且在0-100之间
            try:
                sell_ratio_value = float(sell_ratio)
                # 检查是否为整数
                if sell_ratio_value != int(sell_ratio_value):
                    self.log("错误: 卖出比例必须是整数")
                    return
                # 转换为整数
                sell_ratio_int = int(sell_ratio_value)
                # 检查范围
                if sell_ratio_int <= 0 or sell_ratio_int > 100:
                    self.log("错误: 卖出比例必须大于0且小于或等于100")
                    return
                # 更新sell_ratio为整数值
                sell_ratio = str(sell_ratio_int)
            except ValueError:
                self.log("错误: 卖出比例必须是有效的数字")
                return

            # 检查必要参数
            if not ca or not sell_ratio:
                self.log("错误: CA和卖出比例不能为空")
                return

            if not api_key or not api_secret or not passphrase or not private_key:
                self.log("错误: API Key、API Secret、Passphrase和Private Key不能为空")
                return

            if not slippage:
                self.log("错误: 滑点不能为空")
                return

            # 输出所有参数到日志，添加完全空白的行
            self.log_queue.put("EMPTY_LINE")  # 添加完全空白的行
            self.log("===== 卖出操作参数 =====", "highlight")
            self.log(f"CA: {ca}")
            self.log(f"滑点: {slippage}")
            self.log(f"卖出比例: {sell_ratio}%")

            # 创建OKXDexSwap实例
            dex = OKXDexSwap(api_key, api_secret, passphrase, private_key)

            # 代币地址
            BNB_ADDRESS = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"

            # 获取代币余额
            self.log("获取代币余额...")
            token_balance = dex.get_token_balance(ca, rpc)
            # print(token_balance)
            # print(sell_ratio)

            if token_balance <= 100000000:
                self.log(f"错误: 没有可用或太少的代币余额 {token_balance / 10 ** 18}", "warning")
                return

            self.log(f"代币余额: {float(token_balance) / 1e18:.8f}")

            # 计算要卖出的数量（根据百分比）
            if int(sell_ratio) == 100:
                sell_amount = token_balance
            else:
                # 否则计算百分比
                sell_amount = int(token_balance * int(sell_ratio) / 100)

            if sell_amount <= 0:
                self.log("错误: 计算的卖出数量为零")
                return

            self.log(f"将卖出 {float(sell_amount) / 1e18:.8f} 代币 ({sell_ratio}%)")

            # 检查并执行授权
            self.log("检查并进行代币授权...")
            if not dex.check_and_approve(ca, rpc, chain_id):
                self.log("授权失败，交易终止", "error")
                return

            self.log("代币已授权，准备卖出")

            # 获取卖出报价 - 注意这里slippage需要除以100转换为小数
            self.log("获取卖出报价...")
            quote = dex.get_quote(ca, BNB_ADDRESS, float(slippage) / 100, str(sell_amount), chain_id)
            # print(quote)
            if quote is None:
                self.log("获取报价失败", "error")
                return

            if quote.get("code") == "0":
                # 显示预计收到的BNB数量
                expected_amount = quote["data"][0]["toTokenAmount"]
                self.log(f"预计收到的代币: {float(expected_amount) / 1e18:.8f}")
                self.log(f"价格影响: {quote['data'][0]['priceImpactPercentage']}%")
                self.log(f"使用DEX: {quote['data'][0]['quoteCompareList'][0]['dexName']}")

                # 执行交换 - 这里slippage也需要除以100
                self.log("执行卖出交易...")
                swap_result = dex.swap(quote["data"], float(slippage) / 100)
                if swap_result and swap_result.get("code") == "0":
                    # 从响应中提取交易数据
                    tx_data = swap_result["data"][0]["tx"]
                    self.log("卖出交易数据已获取!")
                    # 发送交易
                    self.log('准备发送卖出交易...')
                    tx_result = dex.send_transaction(tx_data, rpc, chain_id)
                    if tx_result:
                        tx_hash = tx_result['tx_hash']
                        receipt = tx_result['receipt']

                        self.log(f"等待卖出哈希确认:{tx_hash}")

                        # 检查交易是否成功
                        if receipt['status'] == 1:
                            self.log(">> 卖出交易成功!", "success")
                        else:
                            # print(receipt)
                            self.log('[ 卖出交易失败 ]', "error")
                    else:
                        self.log(f'发送卖出交易出错...', "error")
                else:
                    self.log(f"获取卖出交易数据失败: {swap_result}", "error")
            else:
                self.log(f"获取卖出报价失败: {quote}", "error")
        except Exception as e:
            error_msg = f"卖出失败: {str(e)}"
            self.log(error_msg, "error")
            self.log(traceback.format_exc())
        finally:
            # 操作完成，设置卖出状态为False
            self.is_selling = False
            # 检查是否可以恢复按钮状态
            self.root.after(0, self._check_and_enable_buttons)
        # self.log("========================")
        self.log_queue.put("EMPTY_LINE")  # 添加完全空白的行

    def _check_and_enable_buttons(self):
        """检查操作状态并决定是否恢复按钮状态"""
        # 只有当买入和卖出操作都没有在运行时，才恢复按钮状态
        if not self.is_buying and not self.is_selling:
            self.buy_button.config(state="normal")
            self.sell_button.config(state="normal")

    def save_advanced_config(self):
        """保存高级配置并显示临时成功消息"""
        # 先调用原来的保存配置方法
        self.save_config()

        # 更改按钮文本为"保存成功"
        self.adv_save_button.config(text="保存成功")

        # 1秒后恢复按钮文本
        self.root.after(500, self._reset_adv_button_text)

    def _reset_adv_button_text(self):
        """恢复高级配置保存按钮的文本"""
        self.adv_save_button.config(text="保存高级配置")

    def update_rpc_list(self):
        """更新RPC列表"""
        try:
            # 加载配置文件
            config_data = {}
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config_data = json.load(f)

            # 清空下拉框选项
            self.chain_combobox['values'] = []

            # 重新加载RPC链选项到下拉框
            self.load_rpc_chains(config_data)

            # 检查是否有默认链设置
            default_index = 0  # 默认选择第一个选项
            if "default_chain" in config_data and config_data["default_chain"] in self.chain_combobox['values']:
                default_index = self.chain_combobox['values'].index(config_data["default_chain"])
                # 如果找到默认链，自动触发选择事件
                self.chain_combobox.current(default_index)
                # 手动触发链选择事件
                self.on_chain_selected(None)
            else:
                self.chain_combobox.current(0)  # 默认选择第一个选项

            # 更新按钮文本为"更新成功"
            self.update_rpc_list_button.config(text="更新成功")
            # 1秒后恢复按钮文本
            self.root.after(500, lambda: self.update_rpc_list_button.config(text="更新RPC列表"))

            self.log("RPC列表已更新")
        except Exception as e:
            self.log(f"更新RPC列表失败: {str(e)}")


class OKXDexSwap:
    def __init__(self, api_key, api_secret, passphrase, private_key):
        self.base_url = "https://www.okx.com"
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.private_key = private_key

        # 验证参数
        if not all([self.api_key, self.api_secret, self.passphrase, self.private_key]):
            raise ValueError("请确保所有API参数都已正确设置")

        try:
            self.account = Account.from_key(self.private_key)
        except Exception as e:
            raise ValueError(f"私钥格式错误: {e}")

    def generate_sign(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """生成OKX API签名"""
        if str(body) == '{}' or str(body) == 'None':
            body = ''
        message = timestamp + method + request_path + str(body)

        try:
            mac = hmac.new(
                bytes(self.api_secret, encoding='utf8'),
                bytes(message, encoding='utf-8'),
                digestmod='sha256'
            )
            d = mac.digest()
            return base64.b64encode(d).decode('utf-8')
        except Exception as e:
            # print(f"生成签名时发生错误: {e}")
            raise

    def get_quote(self, from_token: str, to_token: str, slippage, amount: str, chain_id) -> Optional[dict]:
        """获取Swap报价"""
        endpoint = "/api/v5/dex/aggregator/quote"
        timestamp = str(int(time.time() * 1000))
        method = 'GET'

        params = {
            "chainId": chain_id,
            "fromTokenAddress": from_token,
            "toTokenAddress": to_token,
            "amount": amount,
            "slippage": str(slippage),
            "userAddr": self.account.address
        }

        # 使用urlencode确保参数正确编码
        query_string = urlencode(sorted(params.items()))
        full_path = f"{endpoint}?{query_string}"
        # print(full_path)
        try:
            signature = self.generate_sign(timestamp, method, full_path)
        except Exception as e:
            # print(f"生成签名失败: {e}")
            return None

        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json"
        }

        try:
            url = self.base_url + full_path
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                return None

            return response.json()

        except requests.exceptions.RequestException as e:
            # print(f"请求发生错误: {e}")
            return None
        except json.JSONDecodeError as e:
            # print(f"解析响应JSON时发生错误: {e}")
            return None

    def swap(self, quote_data: list, slippage) -> Optional[dict]:
        """执行Swap交易"""
        endpoint = "/api/v5/dex/aggregator/swap"
        timestamp = str(int(time.time() * 1000))
        method = 'GET'  # 使用GET请求

        # 构建交易参数
        params = {
            "chainId": quote_data[0]["chainId"],
            "fromTokenAddress": quote_data[0]["fromToken"]["tokenContractAddress"],
            "toTokenAddress": quote_data[0]["toToken"]["tokenContractAddress"],
            "amount": quote_data[0]["fromTokenAmount"],
            "userWalletAddress": self.account.address,
            "slippage": str(slippage),
            "dexId": quote_data[0]["quoteCompareList"][0]["dexName"].replace(" ", "")
        }

        # print(f"交易参数: {json.dumps(params, indent=2)}")
        # 使用urlencode确保参数正确编码
        query_string = urlencode(sorted(params.items()))
        full_path = f"{endpoint}?{query_string}"

        # 生成签名
        signature = self.generate_sign(timestamp, method, full_path)

        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json"
        }

        try:
            url = self.base_url + full_path
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                return None

            return response.json()

        except Exception as e:
            # print(f"执行Swap时发生错误: {e}")
            return None

    def send_transaction(self, tx_data: dict, rpc_url: str, chain_id) -> Optional[dict]:
        """发送交易到区块链并返回交易收据"""
        try:
            # 连接到区块链
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            gas_price = w3.eth.gas_price
            gas_limit = int(tx_data['gas']) * 2  # 增加gas限制
            # 创建交易对象
            transaction = {
                'from': self.account.address,
                'to': tx_data['to'],
                'value': int(tx_data['value']),
                'gas': gas_limit,  # 增加gas限制
                'gasPrice': int(gas_price * 1.01),  # 增加20%的gas价格
                'nonce': w3.eth.get_transaction_count(self.account.address),
                'data': tx_data['data'],
                'chainId': int(chain_id)  # 确保chainId是整数
            }
            # print(transaction)

            # 签名交易
            signed_txn = w3.eth.account.sign_transaction(transaction, self.private_key)

            # 发送交易
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            # 等待交易收据
            # print(f"等待交易确认，交易哈希: {w3.to_hex(tx_hash)}")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            # 返回交易哈希和收据
            return {
                'tx_hash': w3.to_hex(tx_hash),
                'receipt': receipt
            }

        except Exception as e:
            # print(f"发送交易时发生错误: {e}")
            return None

    def get_token_balance(self, token_address: str, rpc):
        """获取代币余额"""
        try:
            w3 = Web3(Web3.HTTPProvider(rpc))

            abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                }
            ]

            contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=abi)
            balance = contract.functions.balanceOf(self.account.address).call()
            return int(balance)
        except Exception as e:
            # print(f"获取代币余额时发生错误: {e}")
            return 0

    def check_and_approve(self, token_address: str, rpc_url: str, chain_id, wait=True):
        """检查并执行代币授权"""
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            # 首先通过OKX API获取授权交易信息
            endpoint = "/api/v5/dex/aggregator/approve-transaction"
            timestamp = str(int(time.time() * 1000))
            method = 'GET'
            # 构建参数
            params = {
                "chainId": chain_id,
                "tokenContractAddress": token_address,
                "approveAmount": "10"  # 2^256-1
            }

            # 使用urlencode确保参数正确编码
            query_string = urlencode(sorted(params.items()))
            full_path = f"{endpoint}?{query_string}"

            # 生成签名
            signature = self.generate_sign(timestamp, method, full_path)

            headers = {
                "OK-ACCESS-KEY": self.api_key,
                "OK-ACCESS-SIGN": signature,
                "OK-ACCESS-TIMESTAMP": timestamp,
                "OK-ACCESS-PASSPHRASE": self.passphrase,
                "Content-Type": "application/json"
            }

            url = self.base_url + full_path
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                return False

            approve_data = response.json()

            if approve_data.get("code") != "0":
                return False

            # 获取DEX合约地址作为授权接收方
            spender_address = approve_data["data"][0]["dexContractAddress"]

            # ERC20代币ABI
            abi = [
                # balanceOf
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                },
                # allowance
                {
                    "constant": True,
                    "inputs": [
                        {"name": "_owner", "type": "address"},
                        {"name": "_spender", "type": "address"}
                    ],
                    "name": "allowance",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "type": "function"
                },
                # approve
                {
                    "constant": False,
                    "inputs": [
                        {"name": "_spender", "type": "address"},
                        {"name": "_value", "type": "uint256"}
                    ],
                    "name": "approve",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                }
            ]

            # 创建合约实例
            contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=abi)

            # 检查当前授权额度
            allowance = contract.functions.allowance(
                self.account.address,
                Web3.to_checksum_address(spender_address)
            ).call()

            # 最大授权额度
            max_amount = 2 ** 256 - 1

            # 如果授权额度小于最大值，则需要重新授权
            if allowance < max_amount:
                # print(f"\n当前授权额度: {allowance / 1e18:.8f}")
                # print(f"代币余额: {balance / 1e18:.8f}")
                # print("需要最大授权，准备发送授权交易...")

                # 构建授权交易
                transaction = contract.functions.approve(
                    Web3.to_checksum_address(spender_address),
                    max_amount
                ).build_transaction({
                    'from': self.account.address,
                    'gas': 2100000,
                    'gasPrice': w3.eth.gas_price,
                    'nonce': w3.eth.get_transaction_count(self.account.address),
                    'chainId': int(chain_id)
                })

                # 签名并发送交易
                signed_txn = w3.eth.account.sign_transaction(transaction, self.private_key)
                tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

                # # 等待交易确认
                # print(f"授权交易已发送，交易哈希: {w3.to_hex(tx_hash)}")
                # print("等待交易确认...")
                if not wait:
                    return

                try:
                    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                    if tx_receipt['status'] == 1:
                        return True
                except Exception as e:
                    # print(f"等待授权交易确认时发生错误: {e}")
                    pass
                return False
            else:
                return True

        except Exception as e:
            # print(f"检查授权时发生错误: {e}")
            return False


if __name__ == "__main__":
    root = tk.Tk()
    app = ConfigApp(root)
    root.mainloop()
