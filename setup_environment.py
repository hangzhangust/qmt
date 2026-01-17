# -*- coding: utf-8 -*-
"""
Environment Check and Dependency Validation Script
环境检查和依赖验证脚本
"""
import sys
import importlib


def check_dependencies():
    """
    Check all required dependencies
    检查所有必需的依赖

    Returns:
        bool: True if all dependencies are installed
    """
    required = {
        'backtrader': 'Backtrader Backtesting Framework',
        'xtquant': 'XtQuant Data Interface',
        'pandas': 'Pandas Data Processing',
        'numpy': 'Numpy Numerical Computing',
        'matplotlib': 'Matplotlib Plotting Library'
    }

    missing = []
    installed = []

    for module, description in required.items():
        try:
            importlib.import_module(module)
            print(f"[OK] {module:15} - {description}")
            installed.append(module)
        except ImportError:
            print(f"[X] {module:15} - {description} (Not Installed)")
            missing.append(module)

    print(f"\nInstalled: {len(installed)}/{len(required)}")
    print(f"Missing: {len(missing)}/{len(required)}")

    if missing:
        print("\nPlease run the following command to install missing dependencies:")
        print(f"pip install -r requirements.txt")
        return False

    return True


def check_xtquant_connection():
    """
    Check XtQuant connection
    检查XtQuant连接

    Returns:
        bool: True if connection successful
    """
    try:
        from xtquant import xtdata
        # Try to connect
        result = xtdata.connect()
        if result == 0:
            print("[OK] XtQuant connection successful")
            return True
        else:
            print(f"[X] XtQuant connection failed, error code: {result}")
            return False
    except Exception as e:
        print(f"[X] XtQuant connection error: {e}")
        return False


def main():
    """Main function"""
    print("=" * 60)
    print("Environment Dependency Check")
    print("环境依赖检查")
    print("=" * 60)

    # Check dependencies
    deps_ok = check_dependencies()

    # Check XtQuant connection
    print("\n" + "=" * 60)
    print("XtQuant Connection Check")
    print("XtQuant 连接检查")
    print("=" * 60)
    xt_ok = check_xtquant_connection()

    # Summary
    print("\n" + "=" * 60)
    if deps_ok and xt_ok:
        print("[OK] Environment check passed, backtest system ready to use")
        print("[OK] 环境检查通过，可以运行回测系统")
        sys.exit(0)
    else:
        print("[X] Environment check failed, please resolve the above issues")
        print("[X] 环境检查失败，请解决上述问题")
        sys.exit(1)


if __name__ == '__main__':
    main()
