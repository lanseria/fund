# cli.py

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table

from .models import SessionLocal
from . import services, schemas

# 将Typer实例命名为 cli_app，以示区分
cli_app = typer.Typer()
console = Console()

# --- CLI 命令定义 (保持不变) ---
@cli_app.command()
def hello(name: Optional[str] = typer.Argument(None)):
    """简单的问候命令"""
    if name:
        console.print(f"你好 [bold green]{name}[/bold green]!")
    else:
        console.print("你好 [bold blue]世界[/bold blue]!")

@cli_app.command(name="add-holding")
def add_holding_command(
    code: str = typer.Option(..., "--code", "-c", help="基金代码"),
    amount: float = typer.Option(..., "--amount", "-a", help="持仓金额"),
    name: str = typer.Option(None, "--name", "-n", help="基金名称 (可选，会尝试自动获取)")
):
    """通过命令行添加一个新的持仓基金。"""
    console.print(f"正在尝试添加基金: [cyan]{code}[/cyan] 金额: [cyan]{amount}[/cyan]...")
    db = SessionLocal()
    try:
        # 注意：这里的name是可选的，因为我们的service层会尝试自动获取
        # 如果用户不提供，我们就传入一个空字符串或None
        holding_data = schemas.HoldingCreate(code=code, name=name or "", holding_amount=amount)
        new_holding = services.create_new_holding(db=db, holding_data=holding_data)
        
        table = Table("属性", "值", title="🎉 基金添加成功！")
        table.add_row("基金代码 (Code)", new_holding.code)
        table.add_row("基金名称 (Name)", new_holding.name)
        table.add_row("持有金额 (Amount)", f"{new_holding.holding_amount:.2f}")
        table.add_row("昨日净值 (Yesterday NAV)", f"{new_holding.yesterday_nav:.4f}")
        console.print(table)
    except services.HoldingExistsError as e:
        console.print(f"[bold red]错误: {e}[/bold red]")
    except Exception as e:
        console.print(f"[bold red]发生未知错误: {e}[/bold red]")
    finally:
        db.close()

# --- 新增的 CLI 入口函数 ---
def main():
    """
    这是专门为命令行脚本准备的入口函数。
    """
    cli_app()

if __name__ == "__main__":
    main()