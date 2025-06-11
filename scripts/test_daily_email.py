#!/usr/bin/env python3
"""
定期メール送信のテストスクリプト
本番実行前に動作確認用
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.send_daily_summary import send_daily_summary

if __name__ == '__main__':
    print("Testing daily summary email...")
    send_daily_summary()
    print("Test completed! Check your email.")