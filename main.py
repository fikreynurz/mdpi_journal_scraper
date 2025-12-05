from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import os
import random



def setup_driver():
    """
    Setup Chrome WebDriver dengan opsi anti-deteksi.
    """
    chrome_options = Options()
    
    # Opsi untuk menghindari deteksi bot
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Set user agent
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Opsi tambahan untuk stabilitas
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    
    # Uncomment baris berikut jika ingin headless (tanpa GUI)
    chrome_options.add_argument("--headless")
    
    # Jika Anda meletakkan chromedriver.exe di folder project,
    # gunakan path relatif ini untuk membuat Service.
    chromedriver_path = os.path.join(os.path.dirname(__file__), "chromedriver.exe")
    service = None
    try:
        # Jika file ada, buat Service dengan path tersebut
        if os.path.exists(chromedriver_path):
            service = Service(chromedriver_path)
        else:
            # Gunakan webdriver-manager untuk otomatis download ChromeDriver yang cocok
            service = Service(ChromeDriverManager().install())

        # Buat webdriver dengan Service (atau tanpa Service jika None)
        if service:
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)

        # Hapus flag webdriver pada navigator untuk mengurangi deteksi
        try:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            })
        except Exception:
            # fallback: eksekusi script setelah halaman terbuka
            try:
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception:
                pass

        return driver
    except Exception as e:
        print(f"[!] Error setting up Chrome driver: {e}")
        print("[!] Pastikan ChromeDriver (chromedriver.exe) ada di folder project atau di PATH dan versinya cocok dengan Chrome Anda")
        return None

def get_full_abstract(driver, article_url):
    """
    Mengambil abstract lengkap dari halaman detail artikel.
    """
    try:
        # Simpan URL saat ini
        current_url = driver.current_url
        
        # Navigate ke halaman artikel
        driver.get(article_url)
        time.sleep(2)
        
        # Tunggu halaman dimuat
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Ambil HTML
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Cari abstract di berbagai lokasi
        abstract_div = soup.find('div', class_='html-abstract')
        if not abstract_div:
            abstract_div = soup.find('div', class_='abstract')
        if not abstract_div:
            abstract_div = soup.find('section', {'id': 'abstract'})
        if not abstract_div:
            abstract_div = soup.find('div', class_='art-abstract')
        
        if abstract_div:
            abstract_text = abstract_div.get_text(strip=True)
            # Bersihkan text
            if abstract_text.lower().startswith('abstract'):
                abstract_text = abstract_text[8:].strip()
        else:
            abstract_text = "Abstract not found"
            
        # Kembali ke halaman sebelumnya
        driver.get(current_url)
        time.sleep(1)
        
        return abstract_text
        
    except Exception as e:
        print(f"    [!] Error mengambil abstract: {e}")
        return "Error retrieving abstract"

def scrape_mdpi(topic, years_back, limit):
    """
    Melakukan scraping jurnal MDPI berdasarkan topik dan rentang tahun.
    Menggunakan Selenium Chrome WebDriver untuk menghindari deteksi bot.
    """
    
    # 1. Konfigurasi Tanggal
    current_year = datetime.now().year
    year_from = current_year - years_back
    year_to = current_year
    
    print(f"[*] Memulai scraping MDPI dengan Selenium...")
    print(f"[*] Topik: {topic}")
    print(f"[*] Rentang Tahun: {year_from} - {year_to}")
    print(f"[*] Target Jumlah: {limit} artikel")
    print("-" * 50)

    # Setup WebDriver
    driver = setup_driver()
    if not driver:
        return
    
    articles_data = []

    page = 1
    
    try:
        while len(articles_data) < limit:
            # Buat URL pencarian dengan parameter
            search_url = f"https://www.mdpi.com/search?q={topic.replace(' ', '+')}&year_from={year_from}&year_to={year_to}&sort=pubdate&page_count=50&page_no={page}&featured=&subjects=&journals=&article_types=&countries="
            
            print(f"[*] Mengakses halaman {page}...")
            print(f"    URL: {search_url}")
            
            # Navigate ke halaman pencarian
            driver.get(search_url)
            
            # Tunggu halaman dimuat
            time.sleep(random.uniform(3, 6))
            
            # Tunggu sampai artikel dimuat
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "generic-item"))
                )
            except Exception as e:
                print(f"[!] Timeout waiting for articles: {e}")
                break
            
            # Ambil HTML setelah JavaScript dimuat
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Mencari artikel berdasarkan struktur yang ditemukan
            article_items = soup.find_all('div', class_='generic-item article-item')
            
            if not article_items:
                print("[!] Tidak ada artikel ditemukan di halaman ini.")
                break
                
            print(f"[*] Ditemukan {len(article_items)} artikel di halaman {page}")
            
            for item in article_items:
                if len(articles_data) >= limit:
                    break
                    
                try:
                    # Ambil title dan link
                    title_link = item.find('a', class_='title-link')
                    if not title_link:
                        continue
                        
                    title = title_link.get_text(strip=True)
                    link = "https://www.mdpi.com" + title_link.get('href', '')
                    
                    # Ambil authors
                    authors_div = item.find('div', class_='authors')
                    authors = authors_div.get_text(strip=True) if authors_div else "No Authors"
                    
                    # Ambil journal info
                    journal_div = item.find('div', class_='color-grey-dark')
                    journal_info = journal_div.get_text(strip=True) if journal_div else "Unknown Journal"
                    
                    # Ambil abstract dari halaman list (abstract-cropped atau abstract-full)
                    abstract_full = item.find('div', class_='abstract-full')
                    abstract_cropped = item.find('div', class_='abstract-cropped')
                    
                    if abstract_full:
                        abstract = abstract_full.get_text(strip=True)
                    elif abstract_cropped:
                        abstract = abstract_cropped.get_text(strip=True)
                    else:
                        # Coba ambil abstract lengkap dari halaman detail
                        abstract = get_full_abstract(driver, link)
                    
                    # Clean abstract text
                    if abstract and '[...] Read more.' in abstract:
                        abstract = abstract.replace('[...] Read more.', '').strip()
                    
                    article_data = {
                        "title": title,
                        "authors": authors,
                        "journal": journal_info,
                        "abstract": abstract,
                        "link": link,
                        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    articles_data.append(article_data)
                    print(f"    ✓ [{len(articles_data)}] {title[:60]}...")
                    
                except Exception as e:
                    print(f"    [!] Error parsing artikel: {e}")
                    continue
            
            page += 1
            
            # Break jika sudah mencapai limit
            if len(articles_data) >= limit:
                break
                
    except Exception as e:
        print(f"[!] Error umum: {e}")
    finally:
        # Tutup browser
        print("[*] Menutup browser...")
        driver.quit()

 

    # 4. Membuat folder output jika belum ada
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[*] Folder '{output_dir}' berhasil dibuat.")
    
    # 5. Menyimpan ke JSON di folder output
    filename = f"mdpi_{topic.replace(' ', '_')}_{year_from}-{year_to}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(articles_data, f, ensure_ascii=False, indent=4)

    print("-" * 50)
    print(f"[✓] Selesai! {len(articles_data)} artikel berhasil disimpan ke '{filepath}'")

# --- KONFIGURASI PENGGUNAAN ---
if __name__ == "__main__":
    # Ubah parameter di sini sesuai keinginan
    TOPIK = "computer science"  # Topik pencarian
    TAHUN_KEBELAKANG = 5        # Rentang tahun (misal: 5 tahun terakhir)
    JUMLAH_AMBIL = 1000            # Jumlah jurnal yang ingin diambil (testing dengan jumlah kecil dulu)
    
    scrape_mdpi(TOPIK, TAHUN_KEBELAKANG, JUMLAH_AMBIL)