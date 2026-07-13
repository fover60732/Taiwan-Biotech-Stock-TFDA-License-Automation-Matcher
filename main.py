import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# =========================================================================
# STEP 1: 抓取生技股成分股，並建立【名稱與代碼】的對照字典
# =========================================================================
def get_biotech_companies_dict():
    print("正在從玩股網獲取【上市+上櫃+興櫃】生技股清單與代碼...")
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    urls = {
        "上市生技": "https://www.wantgoo.com/index/%5E018/stocks",
        "上櫃生技": "https://www.wantgoo.com/index/%5E048/stocks",
        "興櫃生技": "https://www.wantgoo.com/index/%5E576/stocks"
    }
    
    # 建立一個字典，用來存放 {"清洗後中文名稱": "股票代碼"}
    company_code_dict = {}
    
    for market_type, url in urls.items():
        try:
            print(f" 正在抓取 [{market_type}] 類股列表...")
            driver.get(url)
            time.sleep(2)  
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            table = soup.find('table')
            
            if table:
                rows = table.find_all('tr')[1:]  
                for row in rows:
                    cols = row.find_all('td')
                    if cols:
                        # 玩股網的第一欄通常同時包含名稱與代碼，例如 "漢康-KY創\n7827"
                        text_lines = cols[0].text.strip().split('\n')
                        full_name = text_lines[0].strip()
                        
                        # 擷取股票代碼（通常在第二行，或是文字中的純數字）
                        stock_code = ""
                        if len(text_lines) > 1:
                            stock_code = text_lines[1].strip()
                        else:
                            # 保險起見，如果沒分行，用殘留的數字當代碼
                            stock_code = ''.join([c for c in full_name if c.isdigit()]).strip()
                        
                        # 完美清洗中文名稱邏輯
                        clean_name = full_name.upper()
                        clean_name = clean_name.replace('-KY', '').replace('KY', '').replace('-', '')
                        clean_name = clean_name.replace('創', '').replace('*', '').strip()
                        clean_name = ''.join([c for c in clean_name if not c.isdigit()]).strip()
                        
                        # 存入對照表
                        if clean_name and stock_code:
                            company_code_dict[clean_name] = stock_code
                            
        except Exception as e:
            print(f"抓取 [{market_type}] 時發生異常: {e}")
            continue
                        
    driver.quit()
    print(f"\n【統計】總共取得 {len(company_code_dict)} 家生技醫藥公司對照資料。")
    return company_code_dict

# =========================================================================
# STEP 2: 比對 37_2.csv，並將結果分裝成兩個 Sheet 匯出 Excel
# =========================================================================
def filter_and_save_sheets(company_dict):
    print("\n正在讀取政府許可證 CSV 資料庫 (37_2.csv)...")
    
    try:
        df = pd.read_csv('37_2.csv', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv('37_2.csv', encoding='big5')

    print(f"資料庫讀取成功！總共有 {len(df)} 筆原始許可證資料。")
    print("正在進行名稱模糊匹配篩選...")

    # 取出所有清洗後的公司名稱清單
    company_names = list(company_dict.keys())
    search_pattern = '|'.join(company_names)
    
    # 篩選出所有含有這些公司名稱的藥證詳細資料 (對應第一個 Sheet)
    filtered_df = df[df['申請商名稱'].str.contains(search_pattern, na=False, case=False)].copy()

    # 🎯 【關鍵核心】：找出到底有哪些公司「成功過關」被比對到藥證了
    matched_companies = []
    for clean_name in company_names:
        # 如果政府資料的「申請商名稱」裡，有包含這家公司的名字
        if filtered_df['申請商名稱'].str.contains(clean_name, na=False).any():
            matched_companies.append({
                "股票代碼": company_dict[clean_name],
                "公司名稱": clean_name
            })
            
    # 把成功比對到的公司做成一個新的表格 (對應第二個 Sheet)
    matched_companies_df = pd.DataFrame(matched_companies)
    
    print(f"🎯 篩選完成！查到藥證的詳細資料共 {len(filtered_df)} 筆。")
    print(f"📊 其中，共有 {len(matched_companies_df)} 家生技公司成功比對到藥證！")

    # 💡 匯出成含有兩個 Sheet 的 Excel 檔案
    output_filename = '生技股藥證比對總表.xlsx'
    
    with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
        # Sheet 1: 藥證詳細資料
        filtered_df.to_excel(writer, sheet_name='藥證詳細資料', index=False)
        # Sheet 2: 只有成功比對到的股票代碼與名稱清單（供你後續與其他檔案 VLOOKUP 比較）
        matched_companies_df.to_excel(writer, sheet_name='有藥證公司代碼', index=False)
        
    print(f"🎉 檔案已成功生成！檔名為: {output_filename}")

# =========================================================================
# 主程式執行
# =========================================================================
if __name__ == "__main__":
    biotech_dict = get_biotech_companies_dict()
    filter_and_save_sheets(biotech_dict)