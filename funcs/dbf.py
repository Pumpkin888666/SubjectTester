import os
import sqlite3
from funcs.create_logger import create_logger

log = create_logger()


class dbf:
    conn = None

    def __init__(self, path):
        """链接并初始化数据库文件"""
        log.info("正在检测本地数据库文件")

        if path is None or path == '':
            log.error("[reverse red bold]请传入数据库文件路径")
            exit(-1)

        if os.path.exists(path):
            log.info(f"发现数据库文件'{path}'")

        try:
            self.conn = sqlite3.connect(path)
            self.init_table()
            log.info("数据库链接并初始化成功")
        except Exception as e:
            log.error(f"[reverse red bold]{e}")
            exit(-1)

    def init_table(self):
        """初始化表内容（如果表是空的）"""
        if self.conn is None:
            log.error("[reverse red bold]错误：未链接数据库就调用init_table()函数")
            exit(-1)