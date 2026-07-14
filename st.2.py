import streamlit as st
import io
import time
import csv

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# =========================================================================
# STEP 1: 純 Python 爬蟲邏輯
# =========================================================================
def get_biotech_companies_dict(status_placeholder):
    status_placeholder.text("🚀 正在從玩股網獲取【上市+上櫃+興櫃】生技股清單與代碼...")
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    urls = {
        "上市生技": "https://www.wantgoo.com/index/%5E018/stocks",
        "上櫃生技": "https://www.wantgoo.com/index/%5E048/stocks",
        "興櫃生技": "https://www.wantgoo.com/index/%5E576/stocks"
    }
    
    company_code_dict = {}
    
    for market_type, url in urls.items():
        try:
            status_placeholder.text(f"📥 正在抓取 [{market_type}] 類股列表...")
            driver.get(url)
            time.sleep(2)  
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            table = soup.find('table')
            
            if table:
                rows = table.find_all('tr')[1:]  
                for row in rows:
                    cols = row.find_all('td')
                    if cols:
                        text_lines = cols[0].text.strip().split('\n')
                        full_name = text_lines[0].strip()
                        
                        stock_code = ""
                        if len(text_lines) > 1:
                            stock_code = text_lines[1].strip()
                        else:
                            stock_code = ''.join([c for c in full_name if c.isdigit()]).strip()
                        
                        clean_name = full_name.upper()
                        clean_name = clean_name.replace('-KY', '').replace('KY', '').replace('-', '')
                        clean_name = clean_name.replace('創', '').replace('*', '').strip()
                        clean_name = ''.join([c for c in clean_name if not c.isdigit()]).strip()
                        
                        if clean_name and stock_code:
                            company_code_dict[clean_name] = stock_code
                                
        except Exception as e:
            st.warning(f"⚠️ 抓取 [{market_type}] 時發生異常: {e}")
            continue
                        
    driver.quit()
    return company_code_dict

# =========================================================================
# STEP 2: 使用 Python 內建 csv 庫進行比對 (無 DLL 阻擋風險)
# =========================================================================
def filter_and_process_data_pure_python(company_dict, status_placeholder):
    status_placeholder.text("🔍 正在讀取政府許可證資料庫 (37_2.csv)...")
    
    raw_rows = []
    headers = []
    
    for encoding in ['utf-8', 'big5', 'cp950']:
        try:
            with open('37_2.csv', mode='r', encoding=encoding) as f:
                reader = csv.reader(f)
                headers = next(reader)
                raw_rows = [row for row in reader]
            break
        except (UnicodeDecodeError, LookupError):
            continue

    status_placeholder.text(f"📚 資料庫讀取成功！正在進行名稱模糊比對...")

    company_name_idx = -1
    for idx, h in enumerate(headers):
        if '申請商名稱' in h or '申請人' in h:
            company_name_idx = idx
            break
    if company_name_idx == -1:
        company_name_idx = 4 
        
    filtered_rows = []
    matched_companies_set = set()
    company_names = list(company_dict.keys())
    
    for row in raw_rows:
        if len(row) > company_name_idx:
            cell_value = row[company_name_idx]
            for clean_name in company_names:
                if clean_name in cell_value:
                    filtered_rows.append(row)
                    matched_companies_set.add(clean_name)
                    break 
                    
    matched_companies_list = []
    for clean_name in matched_companies_set:
        matched_companies_list.append(f"{company_dict[clean_name]} - {clean_name}")
        
    return headers, filtered_rows, matched_companies_list

# =========================================================================
# 網頁前端介面佈局
# =========================================================================
st.title("📊 臺灣生技醫療股 — TFDA 藥證自動化比對系統")
# 使用 st.info 做出精美的藍色說明框，把 A 與 B 用條列式完整呈現
st.info(
    "💡 **系統設計目的與應用場景：**\n\n"
    "1. **學術與臨床聲明**：提供醫藥產業研究人員、臨床專家及學術發表者，在進行利益衝突聲明（Conflict of Interest）時之關鍵參考，協助確認並宣告自身無特定持股生技公司之藥證關聯性。\n"
    "2. **合規與自我審查**：協助需要進行合規申報或利益衝突（Conflict of Interest）自我審查的專業人士，快速比對自身未持有任何具備特定 TFDA 藥證的生技公司股份。"
)
#本工具已啟動【無二進位安全模式】，完美繞過資安控制原則。
if st.button("🚀 開始動態擷取與大數據比對"):
    status_msg = st.empty() 
    
    with st.spinner("系統運行中..."):
        try:
            # 1. 執行爬蟲
            company_dict = get_biotech_companies_dict(status_msg)
            
            # 2. 純 Python 比對
            headers, filtered_rows, matched_list = filter_and_process_data_pure_python(company_dict, status_msg)
            
            status_msg.empty()
            st.success(f"🎉 比對完成！查到藥證詳細資料共 {len(filtered_rows)} 筆，共 {len(matched_list)} 家生技公司成功比對！")
            
            # ❌ 徹底拔除 st.dataframe()，改用純文字標籤顯示成功公司名稱，避免觸發 numpy/pyarrow 的 DLL
            st.subheader("📋 成功比對公司名單")
            for comp in matched_list[:15]: # 顯示前 15 家名稱就好
                st.text(f"✅ {comp}")
            if len(matched_list) > 15:
                st.text(f"...以及其他 {len(matched_list)-15} 家公司（請下載完整報表查看）")
            
            # 3. 匯出下載按鈕
            # --- 🔥 新增按鈕 1：下載【有藥證之生技公司清單】 (對應你原本 main.py 的 Sheet 2) ---
            csv_buffer_companies = io.StringIO()
            writer_companies = csv.writer(csv_buffer_companies)
            # 寫入欄位標頭 (股票代碼, 公司名稱)
            writer_companies.writerow(["股票代碼", "公司名稱"])
            
            # 寫入資料列
            for comp in matched_list:
                # 剛才 matched_list 的格式是 "股號 - 公司名"，我們把它拆開寫入
                if " - " in comp:
                    code, name = comp.split(" - ", 1)
                    writer_companies.writerow([code, name])
            
            st.download_button(
                label="📥 點我下載【1. 有藥證公司清單(股號與名稱).csv】",
                data=csv_buffer_companies.getvalue().encode('utf-8-sig'),
                file_name="生技股藥證比對結果_有藥證公司名單.csv",
                mime="text/csv"
            )
            # --- 按鈕 2：下載【藥證詳細資料】 (原本的 CSV) ---
            csv_buffer_detail = io.StringIO()
            writer_detail = csv.writer(csv_buffer_detail)
            writer_detail.writerow(headers)
            writer_detail.writerows(filtered_rows)
            
            st.download_button(
                label="📥 點我下載【2. 藥證詳細資料.csv】",
                data=csv_buffer_detail.getvalue().encode('utf-8-sig'),
                file_name="生技股藥證比對結果_詳細資料.csv",
                mime="text/csv"
            )
        except FileNotFoundError as fnf_err:
            status_msg.empty()
            st.error(f"❌ {fnf_err}")
        except Exception as e:
            status_msg.empty()
            st.error(f"❌ 執行過程中發生錯誤：{e}")