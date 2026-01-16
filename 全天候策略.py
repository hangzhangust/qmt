# encoding:utf-8
import pandas as pd
import numpy as np
import datetime
import json
import os

"""
全天候资产配置策略 - 从配置文件读取仓位比例
25% 商品: 黄金、原油（或豆粕）
25% 股票: A股ETF、纳斯达克ETF、标普500
25% 长债: 长期国债+长期企业债
25% 短债: 短期国债+短期企业债
"""


class a():
    pass


A = a()  # 全局唯一的实例 用于记录委托状态


def init(C):
    # ================== 全天候配置参数 ==================
    A.all_weather_config = {
        # 商品类 (25%)
        'commodities': {
            'target_weight': 0.25,
            'etfs': [
                "518660.SH",  # 黄金
                "160416.SZ",  # 原油ETF
                "159985.SZ",  # 豆粕ETF
            ],
            'names': {
                "518660.SH": "黄金9999",
                "160416.SZ": "原油ETF",
                "159985.SZ": "豆粕ETF"
            }
        },
        # 股票类 (25%)
        'stocks': {
            'target_weight': 0.25,
            'etfs': [
                "159380.SZ",  # A500
                "513030.SH",  # 纳斯达克指数
                "513650.SH",  # 标普500
            ],
            'names': {
                "159380.SZ": "A500",
                "513030.SH": "纳斯达克指数ETF",
                "513650.SH": "标普500"
            }
        },
        # 长债类 (25%)
        'long_bonds': {
            'target_weight': 0.25,
            'etfs': [
                "511160.SH",  # 国债ETF
                "501300.SH",  # 长债
            ],
            'names': {
                "511160.SH": "国债ETF",
                "501300.SH": "长债",
            }
        },
        # 短债类 (25%)
        'short_bonds': {
            'target_weight': 0.25,
            'etfs': [
                "511010.SH",  # 国债ETF-短
                "511880.SH",  # 银华日利
            ],
            'names': {
                "511010.SH": "国债ETF-短",
                "511880.SH": "银华日利"
            }
        }
    }

    A.acct = account  # 账号为模型交易接口选择账号
    A.acct_type = accountType  # 账户类型为模型交易接口选择账号

    # ================== 从配置文件读取参数 ==================
    A.config = load_config()
    A.position_ratio = A.config.get("all_weather_position_ratio", 0.5)  # 全天候策略仓位比例
    A.rebalance_threshold = A.config.get("rebalance_threshold", 0.05)
    A.rebalance_period = A.config.get("rebalance_period", 60)

    print(f"从配置文件读取仓位比例: {A.position_ratio * 100:.1f}%")

    # ================== 交易控制 ==================
    A.waiting_list = []  # 未查到委托列表
    A.buy_code = 23 if A.acct_type == 'STOCK' else 33
    A.sell_code = 24 if A.acct_type == 'STOCK' else 34

    # ================== 状态记录 ==================
    A.all_weather_last_rebalance = None  # 上次再平衡日期
    A.all_weather_holdings = {}  # 全天候策略持仓
    A.all_weather_days_since_rebalance = 0  # 距离上次再平衡天数

    # ================== 配置文件路径 ==================
    home_dir = os.path.expanduser("~")
    qmt_data_dir = os.path.join(home_dir, "QMT_Strategy_Data")

    if not os.path.exists(qmt_data_dir):
        os.makedirs(qmt_data_dir)
        print(f"创建数据目录: {qmt_data_dir}")

    A.state_file = os.path.join(qmt_data_dir, f'all_weather_state_{A.acct}.json')
    A.trade_records_file = os.path.join(qmt_data_dir, f'all_weather_trades_{A.acct}.json')

    print(f"状态文件路径: {A.state_file}")
    print(f"交易记录文件路径: {A.trade_records_file}")

    # ================== 订阅所有品种 ==================
    all_etfs = set()
    for category in A.all_weather_config.values():
        all_etfs.update(category['etfs'])

    C.set_universe(list(all_etfs))

    # ================== 恢复状态 ==================
    restore_state_from_file()

    print("=" * 80)
    print(f"全天候资产配置策略")
    print(f"仓位比例: {A.position_ratio * 100:.1f}%")
    print(f"账号:{A.acct} 类型:{A.acct_type}")
    print("=" * 80)


def load_config():
    """
    加载配置文件加载参数
    """
    home_dir = os.path.expanduser("~")
    config_file = os.path.join(home_dir, "QMT_Strategy_Data", "strategy_config.json")

    default_config = {
        "momentum_position_ratio": 0.5,
        "all_weather_position_ratio": 0.5,
        "max_drawdown_threshold": 10,
        "rebalance_threshold": 0.05,
        "rebalance_period": 60,
        "lookback_period": 20,
        "hold_period": 20
    }

    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"加载配置文件加载参数: {config_file}")
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
            return config
        else:
            print(f"配置文件不存在，使用默认参数: {config_file}")
            return default_config
    except Exception as e:
        print(f"读取配置文件失败: {e}, 使用默认参数")
        return default_config


def handlebar(C):
    # 仅在历史k线
    if not C.is_last_bar():
        return

    now = datetime.datetime.now()
    now_date = now.strftime('%Y%m%d')
    now_time = now.strftime('%H%M%S')

    # 判断是否交易时间
    if now_time < '093000' or now_time > "150000":
        return

    # 获取账户信息
    account_info = get_trade_detail_data(A.acct, A.acct_type, 'account')
    if len(account_info) == 0:
        print(f'账号{A.acct} 未登录 退出')
        return

    account_info = account_info[0]
    total_assets = int(account_info.m_dBalance)  # 总资产

    # 根据仓位比例计算全天候策略的目标市值
    all_weather_target_value = total_assets * A.position_ratio

    # 处理未查到委托，查询委托状态
    if A.waiting_list:
        found_list = []
        orders = get_trade_detail_data(A.acct, A.acct_type, 'order')
        for order in orders:
            if order.m_strRemark in A.waiting_list:
                found_list.append(order.m_strRemark)
        A.waiting_list = [i for i in A.waiting_list if i not in found_list]

    if A.waiting_list:
        print(f"当前有未查到委托 {A.waiting_list} ，暂停策略")
        return

    # 获取当前持仓
    holdings = get_trade_detail_data(A.acct, A.acct_type, 'position')
    holdings_dict = {}

    for position in holdings:
        stock_code = position.m_strInstrumentID + '.' + position.m_strExchangeID
        holdings_dict[stock_code] = {
            'volume': position.m_nCanUseVolume,
            'total_volume': position.m_nVolume,
            'market_value': position.m_dInstrumentValue,
            'cost_price': position.m_dOpenPrice,
        }

    print(f"\n{'=' * 60}")
    print(f"全天候策略执行")
    print(f"总资产: {total_assets:,.2f}")
    print(f"目标市值: {all_weather_target_value:,.2f} (仓位比例: {A.position_ratio * 100:.1f}%)")

    # 执行全天候策略
    execute_all_weather_strategy(C, holdings_dict, all_weather_target_value, now_date)

    # 保存状态
    save_state_to_file()


def execute_all_weather_strategy(C, holdings_dict, target_value, current_date):
    """
    执行全天候策略
    """
    # 判断是否需要再平衡
    need_rebalance = check_rebalance_condition(current_date)

    if not need_rebalance:
        print("未满足再平衡条件，保持当前全天候策略的配置")
        return

    print("执行全天候策略再平衡...")

    # 计算每个ETF的目标市值
    target_allocations = calculate_all_weather_targets(target_value)

    # 执行再平衡
    rebalance_all_weather(C, holdings_dict, target_allocations)


def calculate_all_weather_targets(target_value):
    """
    计算全天候策略各ETF的目标市值
    """
    target_allocations = {}

    for category_name, category_config in A.all_weather_config.items():
        category_weight = category_config['target_weight']
        category_target = target_value * category_weight

        # 每个类别内的ETF等权配置
        etfs_in_category = category_config['etfs']
        etf_count = len(etfs_in_category)

        for etf in etfs_in_category:
            etf_target = category_target / etf_count
            target_allocations[etf] = etf_target

    return target_allocations


def check_rebalance_condition(current_date):
    """
    判断是否需要再平衡
    """
    # 如果是第一次运行，需要再平衡
    if A.all_weather_last_rebalance is None:
        return True

    # 计算距离上次再平衡的天数
    try:
        last_date = datetime.datetime.strptime(A.all_weather_last_rebalance, '%Y%m%d')
        current_date_obj = datetime.datetime.strptime(current_date, '%Y%m%d')
        days_diff = (current_date_obj - last_date).days

        A.all_weather_days_since_rebalance = days_diff

        # 如果超过再平衡周期，需要再平衡
        if days_diff >= A.rebalance_period:
            print(f"距离上次再平衡: {days_diff}天 > {A.rebalance_period}天")
            return True

    except Exception as e:
        print(f"计算再平衡周期失败: {e}")

    return False


def rebalance_all_weather(C, holdings_dict, target_allocations):
    """
    执行全天候策略再平衡
    """
    # 获取账户资金
    account_info = get_trade_detail_data(A.acct, A.acct_type, 'account')
    if len(account_info) == 0:
        return

    available_cash = int(account_info[0].m_dAvailable)

    # 获取所有ETF的最新价格
    all_etfs = list(target_allocations.keys())
    try:
        price_data = C.get_market_data_ex(
            ['close'],
            all_etfs,
            period='1d',
            count=1,
            dividend_type='follow',
            fill_data=True,
            subscribe=True
        )
    except Exception as e:
        print(f"获取价格数据失败: {e}")
        return

    # 计算每个ETF的当前持仓市值
    current_values = {}
    for etf in all_etfs:
        current_values[etf] = holdings_dict.get(etf, {}).get('market_value', 0)

    # 执行调仓
    for etf, target_value in target_allocations.items():
        current_value = current_values.get(etf, 0)

        if etf not in price_data or price_data[etf].empty:
            continue

        current_price = price_data[etf]['close'].iloc[-1]

        if current_price <= 0:
            continue

        # 计算目标持仓量
        target_volume = int(target_value / current_price / 100) * 100
        if target_volume < 100:
            target_volume = 0

        # 获取当前持仓量
        current_volume = holdings_dict.get(etf, {}).get('volume', 0)

        # 判断是否需要交易
        if target_volume == current_volume:
            continue

        # 执行交易
        if target_volume > current_volume:
            # 买入
            buy_volume = target_volume - current_volume
            buy_amount = buy_volume * current_price

            if buy_amount <= available_cash:
                etf_name = get_etf_name(etf)
                msg = f"全天候策略买入 {etf}({etf_name})"
                passorder(A.buy_code, 1101, A.acct, etf,
                          14, -1, buy_volume, '全天候策略', 1, msg, C)
                print(f"{msg}, 数量: {buy_volume}, 价格: {current_price:.4f}, 金额: {buy_amount:.2f}")
                A.waiting_list.append(msg)
                available_cash -= buy_amount
            else:
                print(f"可用资金不足，无法买入 {etf}，需要: {buy_amount:.2f}, 可用: {available_cash}")

        elif target_volume < current_volume:
            # 卖出
            sell_volume = current_volume - target_volume
            etf_name = get_etf_name(etf)
            msg = f"全天候策略卖出 {etf}({etf_name})"
            passorder(A.sell_code, 1101, A.acct, etf,
                      14, -1, sell_volume, '全天候策略', 1, msg, C)
            print(f"{msg}, 数量: {sell_volume}, 价格: {current_price:.4f}")
            A.waiting_list.append(msg)

    # 更新再平衡日期
    A.all_weather_last_rebalance = datetime.datetime.now().strftime('%Y%m%d')


def get_etf_name(etf_code):
    """
    获取ETF名称
    """
    for category in A.all_weather_config.values():
        if etf_code in category['names']:
            return category['names'][etf_code]
    return "未知"


def restore_state_from_file():
    """
    从文件恢复策略状态
    """
    try:
        if not os.path.exists(A.state_file):
            print(f"状态文件不存在: {A.state_file}")
            return

        with open(A.state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)

        if 'all_weather' in state:
            all_weather_state = state['all_weather']
            A.all_weather_last_rebalance = all_weather_state.get('last_rebalance')
            A.all_weather_holdings = all_weather_state.get('holdings', {})
            A.all_weather_days_since_rebalance = all_weather_state.get('days_since_rebalance', 0)

        print("全天候策略状态恢复成功")

    except Exception as e:
        print(f"从文件恢复策略状态失败: {e}")


def save_state_to_file():
    """
    保存策略状态到文件
    """
    try:
        state = {
            'all_weather': {
                'last_rebalance': A.all_weather_last_rebalance,
                'holdings': A.all_weather_holdings,
                'days_since_rebalance': A.all_weather_days_since_rebalance,
                'last_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }

        with open(A.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        print(f"全天候策略状态已保存到文件: {A.state_file}")

    except Exception as e:
        print(f"保存策略状态到文件失败: {e}")
