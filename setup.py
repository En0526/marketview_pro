"""
環境設置腳本 - 用於檢查和設置交易系統環境
"""
import sys
import subprocess

def check_python_version():
    """檢查 Python 版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ 需要 Python 3.8 或更高版本")
        return False
    print(f"✅ Python 版本: {version.major}.{version.minor}.{version.micro}")
    return True

def install_requirements():
    """安裝依賴套件"""
    print("\n📦 正在安裝依賴套件...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依賴套件安裝完成")
        return True
    except subprocess.CalledProcessError:
        print("❌ 依賴套件安裝失敗")
        return False

def check_files():
    """檢查必要檔案是否存在"""
    import os
    required_files = [
        "app.py",
        "config.py",
        "requirements.txt",
        "market_data/data_fetcher.py",
        "timing/timing_selector.py",
        "strategy/strategy_matcher.py",
        "templates/index.html",
        "static/css/style.css",
        "static/js/main.js"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 缺少以下檔案: {', '.join(missing_files)}")
        return False
    else:
        print("✅ 所有必要檔案都存在")
        return True

def main():
    """主函數"""
    print("=" * 50)
    print("交易系統環境檢查")
    print("=" * 50)
    
    # 檢查 Python 版本
    if not check_python_version():
        return
    
    # 檢查檔案
    if not check_files():
        return
    
    # 詢問是否安裝依賴
    print("\n是否要安裝依賴套件? (y/n): ", end="")
    response = input().strip().lower()
    if response == 'y':
        install_requirements()
        print("\n✅ 環境設置完成！")
        print("\n下一步:")
        print("  1. 執行: python app.py")
        print("  2. 打開瀏覽器訪問: http://localhost:5001")
    else:
        print("\n請手動執行: pip install -r requirements.txt")

if __name__ == "__main__":
    main()

