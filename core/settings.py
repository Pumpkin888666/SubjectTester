"""设置相关"""
def settings(console,print,log):
    print("[reverse blue]设置页")
    while True:
        print("[bold blue]请输入菜单前面的数字，进行操作：")

        menus = {
            0: "上一页",
            1: "设置模型配置",
        }

        for key, values in menus.items():
            print(f"{key}: {values}")

        act = input(":")

        match act:
            case "1":
                pass

            case "0":
                break

            case _:
                pass