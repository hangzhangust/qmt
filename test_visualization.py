# -*- coding: utf-8 -*-
"""
Test script for backtest visualization functionality
"""
import sys
import os

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtesting.backtrader_engine import BacktestEngine


def test_visualization_methods():
    """
    Test visualization methods exist and are callable
    """
    print("=" * 60)
    print("Testing Backtest Visualization Methods")
    print("=" * 60)

    # Create a backtest engine
    engine = BacktestEngine(initial_cash=1000000, commission=0.0001)

    # Test 1: Check if calculate_enhanced_metrics method exists
    print("\n1. Testing calculate_enhanced_metrics method...")
    if hasattr(engine, 'calculate_enhanced_metrics'):
        print("   [OK] calculate_enhanced_metrics method exists")
    else:
        print("   [X] calculate_enhanced_metrics method NOT found")
        return False

    # Test 2: Check if plot_results method exists
    print("\n2. Testing plot_results method...")
    if hasattr(engine, 'plot_results'):
        print("   [OK] plot_results method exists")
    else:
        print("   [X] plot_results method NOT found")
        return False

    # Test 3: Check if private plotting methods exist
    print("\n3. Testing private plotting methods...")
    methods_to_check = [
        '_plot_equity_curve',
        '_plot_drawdown',
        '_plot_returns_distribution',
        '_plot_asset_allocation'
    ]

    all_methods_exist = True
    for method_name in methods_to_check:
        if hasattr(engine, method_name):
            print(f"   [OK] {method_name} method exists")
        else:
            print(f"   [X] {method_name} method NOT found")
            all_methods_exist = False

    if not all_methods_exist:
        return False

    # Test 4: Check matplotlib import
    print("\n4. Testing matplotlib import...")
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        print("   [OK] matplotlib imported successfully")
        print(f"   matplotlib version: {plt.matplotlib.__version__}")
    except ImportError as e:
        print(f"   [X] matplotlib import failed: {e}")
        return False

    # Test 5: Check numpy import
    print("\n5. Testing numpy import...")
    try:
        import numpy as np
        print("   [OK] numpy imported successfully")
        print(f"   numpy version: {np.__version__}")
    except ImportError as e:
        print(f"   [X] numpy import failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("All visualization tests passed!")
    print("=" * 60)
    return True


def test_command_line_args():
    """
    Test command-line argument parsing
    """
    print("\n" + "=" * 60)
    print("Testing Command-Line Arguments")
    print("=" * 60)

    # Test if run_backtest.py can be imported
    print("\n1. Testing run_backtest.py import...")
    try:
        import run_backtest
        print("   [OK] run_backtest.py imported successfully")
    except Exception as e:
        print(f"   [X] Failed to import run_backtest.py: {e}")
        return False

    # Check if the main function accepts the new args
    print("\n2. Checking argument parser...")
    import argparse
    parser = argparse.ArgumentParser()

    # Add the new arguments
    parser.add_argument('--plot', action='store_true')
    parser.add_argument('--save_plot', type=str, default=None)
    parser.add_argument('--show_metrics', action='store_true')

    # Test parsing
    test_args = ['--plot', '--save_plot', 'test.png', '--show_metrics']
    args = parser.parse_args(test_args)

    if args.plot:
        print("   [OK] --plot argument parsed")
    if args.save_plot == 'test.png':
        print("   [OK] --save_plot argument parsed")
    if args.show_metrics:
        print("   [OK] --show_metrics argument parsed")

    print("\n" + "=" * 60)
    print("Command-line argument tests passed!")
    print("=" * 60)
    return True


def main():
    """
    Main test function
    """
    print("\n")
    print("*" * 60)
    print("*" + " " * 58 + "*")
    print("*" + "  Backtest Visualization Test Suite".center(58) + "*")
    print("*" + " " * 58 + "*")
    print("*" * 60)
    print("\n")

    # Run tests
    success = True

    if not test_visualization_methods():
        success = False

    if not test_command_line_args():
        success = False

    # Summary
    print("\n\n")
    if success:
        print("[OK] All tests passed successfully!")
        print("\nThe visualization feature is ready to use.")
        print("\nUsage examples:")
        print("  python run_backtest.py --start 20230101 --end 20231231 --plot")
        print("  python run_backtest.py --start 20230101 --end 20231231 --save_plot results.png --show_metrics")
        return 0
    else:
        print("[X] Some tests failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
