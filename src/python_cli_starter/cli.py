# cli.py
import typer
from typing import Optional
import json
from rich.console import Console
from rich.table import Table
from pathlib import Path
import logging

from .logger_config import setup_logging
from .models import SessionLocal
from . import services, schemas
from .scheduler import update_all_nav_history, update_today_estimate
from .crud import get_holdings 

# 将Typer实例命名为 cli_app，以示区分
cli_app = typer.Typer()
console = Console()
logger = logging.getLogger(__name__)

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
    logger.info(f"开始执行 add-holding 命令, code: {code}, amount: {amount}")
    db = SessionLocal()
    try:
        holding_data = schemas.HoldingCreate(code=code, name=name or "", holding_amount=amount)
        new_holding = services.create_new_holding(db=db, holding_data=holding_data)
        
        # 使用 rich console 打印给用户的最终结果
        table = Table("属性", "值", title="🎉 基金添加成功！")
        table.add_row("基金代码 (Code)", new_holding.code)
        table.add_row("基金名称 (Name)", new_holding.name)
        table.add_row("买入金额 (Amount)", f"{new_holding.holding_amount:,.2f}")
        table.add_row("买入时净值 (NAV)", f"{new_holding.yesterday_nav:.4f}")
        table.add_row("计算份额 (Shares)", f"{new_holding.shares:.4f}")
        table.add_row("-" * 15, "-" * 20)
        table.add_row("[bold]当前估算净值[/bold]", f"{new_holding.today_estimate_nav:.4f}" if new_holding.today_estimate_nav else "-")
        table.add_row("[bold]当前估算金额[/bold]", f"{new_holding.today_estimate_amount:,.2f}" if new_holding.today_estimate_amount else "-")
        
        pct_str = "-"
        if new_holding.percentage_change is not None:
            color = "red" if new_holding.percentage_change > 0 else "green"
            pct_str = f"[{color}]{new_holding.percentage_change:+.2f}%[/{color}]"
        table.add_row("[bold]当前估算涨跌[/bold]", pct_str)
        console.print(table)
        
    except services.HoldingExistsError as e:
        logger.warning(f"添加基金失败，因为已存在: {e.code}")
        console.print(f"[bold red]错误: {e}[/bold red]")
    except Exception as e:
        logger.exception(f"在 add-holding 命令中发生未知错误, code: {code}")
        console.print(f"[bold red]发生未知错误: {e}[/bold red]")
    finally:
        db.close()

@cli_app.command(name="list-holdings")
def list_holdings_command():
    """以表格形式列出所有持仓的基金。"""
    logger.info("开始执行 list-holdings 命令。")
    db = SessionLocal()
    try:
        holdings = get_holdings(db)
        
        if not holdings:
            console.print("🤷‍ 您当前没有任何持仓记录。")
            return

        table = Table(title="我的基金持仓组合", caption=f"共 {len(holdings)} 只基金", show_header=True, header_style="bold magenta")
        table.add_column("代码 (Code)", style="dim", width=12)
        table.add_column("名称 (Name)", min_width=20)
        table.add_column("持有金额 (Amount)", justify="right", style="green")
        table.add_column("昨日净值 (NAV)", justify="right")
        table.add_column("今日估值 (Estimate)", justify="right")
        table.add_column("估算涨跌幅 (%)", justify="right")
        table.add_column("估值更新时间", justify="right", style="dim")

        total_amount = 0.0
        total_estimate_value = 0.0

        for holding in holdings:
            estimate_nav = holding.today_estimate_nav
            yesterday_nav = holding.yesterday_nav
            
            estimate_change_pct_str = "-"
            if estimate_nav is not None and yesterday_nav > 0:
                change_pct = ((estimate_nav / float(yesterday_nav)) - 1) * 100
                if change_pct > 0:
                    estimate_change_pct_str = f"[bold red]+{change_pct:.2f}%[/bold red]"
                elif change_pct < 0:
                    estimate_change_pct_str = f"[bold green]{change_pct:.2f}%[/bold green]"
                else:
                    estimate_change_pct_str = f"{change_pct:.2f}%"
            
            total_amount += float(holding.holding_amount)
            if estimate_nav is not None:
                total_estimate_value += (float(holding.holding_amount) / float(yesterday_nav)) * estimate_nav
            else:
                total_estimate_value += float(holding.holding_amount)

            table.add_row(holding.code, holding.name, f"{holding.holding_amount:,.2f}", f"{holding.yesterday_nav:.4f}",
                          f"{estimate_nav:.4f}" if estimate_nav is not None else "-", estimate_change_pct_str,
                          f"{holding.today_estimate_update_time}" if holding.today_estimate_update_time else "-")
        
        console.print(table)
        
        total_change = total_estimate_value - total_amount
        total_change_pct = (total_change / total_amount) * 100 if total_amount > 0 else 0.0
        total_change_color = "bold green" if total_change < 0 else "bold red"
        
        console.print(f"\n[bold]持仓总成本[/bold]: [cyan]{total_amount:,.2f}[/cyan]")
        console.print(f"[bold]预估总市值[/bold]: [cyan]{total_estimate_value:,.2f}[/cyan]")
        console.print(f"[bold]预估总盈亏[/bold]: [{total_change_color}]{total_change:+.2f}[/{total_change_color}] ([{total_change_color}]{total_change_pct:+.2f}%[/{total_change_color}])")

    except Exception as e:
        logger.exception("在 list-holdings 命令中发生未知错误。")
        console.print(f"[bold red]查询持仓时发生错误: {e}[/bold red]")
    finally:
        db.close()

@cli_app.command(name="sync-history")
def sync_history_command():
    """手动触发一次全量/增量的历史净值同步任务。"""
    console.print("[bold yellow]🚀 开始手动执行历史净值同步任务...[/bold yellow]")
    logger.info("开始执行 sync-history 命令。")
    try:
        update_today_estimate()
        update_all_nav_history()
        console.print("[bold green]✅ 同步任务执行完毕！[/bold green]")
    except Exception as e:
        logger.exception("在 sync-history 命令中发生未知错误。")
        console.print(f"[bold red]❌ 同步任务执行失败: {e}[/bold red]")

@cli_app.command(name="update-holding")
def update_holding_command(
    code: str = typer.Option(..., "--code", "-c", help="要更新的基金代码"),
    amount: float = typer.Option(..., "--amount", "-a", help="新的持仓金额")
):
    """更新一个已持仓基金的金额。"""
    logger.info(f"开始执行 update-holding 命令, code: {code}, new_amount: {amount}")
    db = SessionLocal()
    try:
        updated_holding = services.update_holding_amount(db=db, code=code, new_amount=amount)
        console.print(f"🎉 [bold green]更新成功！[/bold green]")
        console.print(f"   - 新的持有金额: {updated_holding.holding_amount:,.2f}")
        console.print(f"   - 重新计算份额: {updated_holding.shares:.4f}")
        if updated_holding.today_estimate_nav:
            console.print(f"   - 当前估算金额: {updated_holding.today_estimate_amount:,.2f}")
    except services.HoldingNotFoundError as e:
        logger.warning(f"更新基金失败，未找到基金代码: {code}")
        console.print(f"[bold red]错误: {e}[/bold red]")
    except Exception as e:
        logger.exception(f"在 update-holding 命令中发生未知错误, code: {code}")
        console.print(f"[bold red]发生未知错误: {e}[/bold red]")
    finally:
        db.close()

@cli_app.command(name="delete-holding")
def delete_holding_command(
    code: str = typer.Argument(..., help="要删除的基金代码"),
    force: bool = typer.Option(False, "--force", "-f", help="强制删除，不进行确认提示")
):
    """删除一个持仓基金及其所有历史数据。"""
    if not force:
        if not typer.confirm(f"⚠️ 您确定要删除基金代码为 [bold red]{code}[/bold red] 的所有记录吗？此操作不可撤销！"):
            console.print("操作已取消。")
            raise typer.Abort()
    
    logger.info(f"开始执行 delete-holding 命令, code: {code}")
    db = SessionLocal()
    try:
        services.delete_holding_by_code(db=db, code=code)
        console.print(f"🗑️ [bold green]基金 {code} 已成功删除。[/bold green]")
    except services.HoldingNotFoundError as e:
        logger.warning(f"删除基金失败，未找到基金代码: {code}")
        console.print(f"[bold red]错误: {e}[/bold red]")
    except Exception as e:
        logger.exception(f"在 delete-holding 命令中发生未知错误, code: {code}")
        console.print(f"[bold red]发生未知错误: {e}[/bold red]")
    finally:
        db.close()

@cli_app.command(name="export-data")
def export_data_command(
    output_file: Path = typer.Option("fund_holdings_export.json", "--output", "-o", help="导出数据的文件路径和名称。")
):
    """将所有持仓的核心数据 (代码和份额) 导出到一个 JSON 文件。"""
    logger.info(f"开始执行 export-data 命令, output file: {output_file}")
    db = SessionLocal()
    try:
        data_to_export = services.export_holdings_data(db)
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(data_to_export, f, indent=2, ensure_ascii=False)
        console.print(f"✅ [bold green]数据已成功导出到 {output_file}！共 {len(data_to_export)} 条记录。[/bold green]")
    except Exception as e:
        logger.exception(f"在 export-data 命令中发生未知错误。")
        console.print(f"[bold red]导出数据时发生错误: {e}[/bold red]")
    finally:
        db.close()

@cli_app.command(name="import-data")
def import_data_command(
    input_file: Path = typer.Argument(..., help="要从中导入数据的 JSON 文件路径。", exists=True),
    overwrite: bool = typer.Option(False, "--overwrite", help="覆盖模式，导入前将删除所有现有数据。")
):
    """从一个 JSON 文件中导入持仓数据。"""
    logger.info(f"开始执行 import-data 命令, input file: {input_file}, overwrite: {overwrite}")
    if overwrite:
        if not typer.confirm("⚠️ 您选择了覆盖模式，所有现有的持仓和历史数据都将被删除！您确定要继续吗？"):
            console.print("操作已取消。")
            raise typer.Abort()
    
    db = SessionLocal()
    try:
        with input_file.open("r", encoding="utf-8") as f:
            data_to_import = json.load(f)

        imported, skipped = services.import_holdings_data(db, data_to_import, overwrite)

        console.print(f"✅ [bold green]数据导入完成！[/bold green]")
        console.print(f"   - 成功导入: {imported} 条")
        console.print(f"   - 跳过/失败: {skipped} 条")

    except json.JSONDecodeError:
        logger.error(f"导入数据失败，文件 '{input_file}' 不是有效的JSON。")
        console.print(f"[bold red]错误: 文件 '{input_file}' 不是一个有效的 JSON 文件。[/bold red]")
    except Exception as e:
        logger.exception(f"在 import-data 命令中发生未知错误。")
        console.print(f"[bold red]导入数据时发生错误: {e}[/bold red]")
    finally:
        db.close()

def main():
    """这是专门为命令行脚本准备的入口函数。"""
    # 在CLI应用启动时，最先配置日志
    setup_logging()
    cli_app()

if __name__ == "__main__":
    main()