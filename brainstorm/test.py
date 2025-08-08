#!/usr/bin/env python3
"""
Test script to verify all router logs are created
Run this after starting your FastAPI app
"""
import os
import time
import requests

def test_router_logs():
    print("🧪 Testing Router Log Creation...")
    print("=" * 50)
    
    # First, check what log files exist before
    log_dir = "./database/logs"
    if os.path.exists(log_dir):
        before_files = set(f for f in os.listdir(log_dir) if f.endswith('.log'))
        print(f"📄 Log files before test: {len(before_files)}")
        for file in sorted(before_files):
            print(f"   - {file}")
    
    print(f"\n⏰ Waiting 2 seconds for app startup...")
    time.sleep(2)
    
    # Check what log files exist after app startup
    if os.path.exists(log_dir):
        after_files = set(f for f in os.listdir(log_dir) if f.endswith('.log'))
        new_files = after_files - before_files
        
        print(f"\n📄 Log files after startup: {len(after_files)}")
        for file in sorted(after_files):
            file_path = os.path.join(log_dir, file)
            size = os.path.getsize(file_path)
            status = "NEW" if file in new_files else "EXISTS"
            print(f"   - {file} ({size} bytes) [{status}]")
        
        if new_files:
            print(f"\n✅ {len(new_files)} new log files created!")
        else:
            print(f"\n⚠️ No new log files created during startup")
    
    # Expected log files based on your router structure
    expected_logs = [
        "apis_regulator_organizations_api_main_process_router.log",
        "apis_regulator_organizations_api_admin_router.log", 
        "apis_regulator_organizations_api_chat_router.log",
        "apis_regulator_organizations_api_data_router.log",
        "apis_regulator_licenses_api_main_process_router.log",
        "apis_regulator_licenses_api_admin_router.log",
        "apis_regulator_licenses_api_chat_router.log", 
        "apis_regulator_licenses_api_data_router.log",
        "apis_enterprise_organizations_api_main_process_router.log",
        "apis_enterprise_organizations_api_admin_router.log",
        "apis_enterprise_organizations_api_chat_router.log",
        "apis_enterprise_organizations_api_data_router.log",
        "apis_enterprise_licenses_api_main_process_router.log",
        "apis_enterprise_licenses_api_admin_router.log",
        "apis_enterprise_licenses_api_chat_router.log",
        "apis_enterprise_licenses_api_data_router.log"
    ]
    
    print(f"\n🎯 Checking for expected router logs...")
    missing_logs = []
    for expected_log in expected_logs:
        if expected_log in after_files:
            print(f"   ✅ {expected_log}")
        else:
            print(f"   ❌ {expected_log} - MISSING")
            missing_logs.append(expected_log)
    
    if missing_logs:
        print(f"\n⚠️ {len(missing_logs)} router logs are missing!")
        print("This might happen if:")
        print("1. The router modules don't have setup_logger(__name__) at the top")
        print("2. The import is inside a function instead of at module level")
        print("3. The routers aren't being imported by main.py")
    else:
        print(f"\n🎉 All {len(expected_logs)} router logs are present!")

if __name__ == "__main__":
    test_router_logs()