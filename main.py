"""
Author: Pumpkin
Date: 2026 -09 -25
"""
from rich.panel import Panel
from funcs.create_logger import create_logger
from rich.console import Console
from rich import traceback
from rich import print
from funcs.dbf import *

traceback.install(show_locals=True)
console = Console()

log = create_logger()


def main():
    # database = dbf("./subject_tester.db")
    while True:
        print("[bold blue]请输入菜单前面的数字，进行操作：")

        menus = {
            1: "设置",
            99: "退出",
        }

        for key, values in menus.items():
            print(f"{key}: {values}")

        act = input(":")

        match act:
            case "1":
                pass

            case "99":
                print("[bold red reverse]感谢使用")
                exit(0)

            case _:
                pass


if __name__ == "__main__":
    console.print(Panel.fit(
        "[bold blue]Subject Tester - AI学科水平测试[/]\n"
        "[dim]通过描述你的思维想法，免去不必要的计算，使用AI高效、快速的计算你的学科水平。[/dim]",
        border_style="red",
    ))

    main()
