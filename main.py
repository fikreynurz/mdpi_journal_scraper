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
    
    # Tambahan opsi anti-deteksi
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")  # Matikan gambar untuk loading lebih cepat
    # chrome_options.add_argument("--disable-javascript")  # Jangan matikan JS, diperlukan untuk MDPI
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    
    # Set user agent yang lebih umum
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.7444.176 Safari/537.36")
    
    # Opsi tambahan untuk stabilitas
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    
    # Uncomment baris berikut jika ingin headless (tanpa GUI)
    chrome_options.add_argument("--headless")  # Disable headless untuk debugging
    
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

def get_full_article_content(driver, article_url):
    """
    Mengambil konten lengkap artikel dari halaman detail MDPI.
    """
    try:
        # Simpan URL saat ini
        current_url = driver.current_url
        
        # Navigate ke halaman artikel
        driver.get(article_url)
        time.sleep(3)
        
        # Tunggu halaman dimuat
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Ambil HTML
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        article_content = {}
        
        # 1. Ambil Abstract
        abstract_div = soup.find('div', class_='html-abstract')
        if not abstract_div:
            abstract_div = soup.find('div', class_='abstract')
        if not abstract_div:
            abstract_div = soup.find('section', {'id': 'abstract'})
        if not abstract_div:
            abstract_div = soup.find('div', class_='art-abstract')
        
        if abstract_div:
            abstract_text = abstract_div.get_text(strip=True)
            if abstract_text.lower().startswith('abstract'):
                abstract_text = abstract_text[8:].strip()
            article_content['abstract'] = abstract_text
        else:
            article_content['abstract'] = "Abstract not found"
        
        # 2. Ambil Keywords
        keywords_section = soup.find('div', class_='art-keywords')
        if keywords_section:
            keywords = keywords_section.get_text(strip=True)
            if keywords.lower().startswith('keywords'):
                keywords = keywords[8:].strip()
            article_content['keywords'] = keywords
        else:
            article_content['keywords'] = "Keywords not found"
        
        # 3. Ambil konten utama artikel
        # MDPI biasanya menyimpan konten dalam div dengan class 'html-body' atau 'article-content'
        main_content_div = soup.find('div', class_='html-body')
        if not main_content_div:
            main_content_div = soup.find('div', class_='article-content')
        if not main_content_div:
            main_content_div = soup.find('article')
        
        if main_content_div:
            # Ambil semua section dalam artikel
            sections = {}
            
            # Cari section berdasarkan heading (h2, h3)
            headings = main_content_div.find_all(['h2', 'h3', 'h4'])
            
            for i, heading in enumerate(headings):
                section_title = heading.get_text(strip=True)
                
                # Ambil konten antara heading ini dan heading berikutnya
                content_elements = []
                next_sibling = heading.next_sibling
                
                while next_sibling:
                    # Stop jika menemukan heading berikutnya
                    if hasattr(next_sibling, 'name') and next_sibling.name in ['h2', 'h3', 'h4']:
                        break
                    
                    if hasattr(next_sibling, 'get_text'):
                        text = next_sibling.get_text(strip=True)
                        if text:  # Skip elemen kosong
                            content_elements.append(text)
                    
                    next_sibling = next_sibling.next_sibling
                
                if content_elements:
                    sections[section_title] = ' '.join(content_elements)
            
            # Jika tidak ada heading yang ditemukan, ambil semua teks
            if not sections:
                full_text = main_content_div.get_text(strip=True)
                sections['full_content'] = full_text
                
            article_content['sections'] = sections
        else:
            article_content['sections'] = {"error": "Main content not found"}
        
        # 4. Ambil References (jika ada)
        references_section = soup.find('div', class_='html-references')
        if not references_section:
            references_section = soup.find('section', {'id': 'references'})
        
        if references_section:
            references = []
            ref_items = references_section.find_all('li') or references_section.find_all('p')
            for ref in ref_items:
                ref_text = ref.get_text(strip=True)
                if ref_text:
                    references.append(ref_text)
            article_content['references'] = references
        else:
            article_content['references'] = "References not found"
        
        # Kembali ke halaman sebelumnya
        driver.get(current_url)
        time.sleep(1)
        
        return article_content
        
    except Exception as e:
        print(f"    [!] Error mengambil konten artikel: {e}")
        return {
            "abstract": "Error retrieving content",
            "keywords": "Error retrieving content", 
            "sections": {"error": str(e)},
            "references": "Error retrieving content"
        }

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
            
            # Tunggu halaman dimuat dengan lebih sabar
            time.sleep(random.uniform(5, 8))
            
            # Tunggu sampai halaman sepenuhnya dimuat
            try:
                # Tunggu sampai body dimuat dulu
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Scroll ke bawah untuk memicu loading konten
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(2)
                
                # Tunggu artikel dimuat
                WebDriverWait(driver, 20).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CLASS_NAME, "generic-item")),
                        EC.presence_of_element_located((By.CLASS_NAME, "article-item")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".generic-item.article-item"))
                    )
                )
                print("    ✓ Halaman berhasil dimuat")
                
            except Exception as e:
                print(f"[!] Timeout waiting for articles: {e}")
                print("    Mencoba dengan strategi alternatif...")
                
                # Coba refresh halaman
                time.sleep(5)
                driver.refresh()
                time.sleep(random.uniform(5, 10))
                
                # Scroll dan tunggu lagi
                try:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
                    time.sleep(3)
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.TAG_NAME, "article"))
                    )
                except Exception as e2:
                    print(f"    [!] Strategi alternatif gagal: {e2}")
                    print("    Melanjutkan ke halaman berikutnya...")
                    continue
            
            # Ambil HTML setelah JavaScript dimuat
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Mencari artikel berdasarkan berbagai kemungkinan struktur
            article_items = soup.find_all('div', class_='generic-item article-item')
            
            # Jika tidak ditemukan, coba alternatif lain
            if not article_items:
                article_items = soup.find_all('div', class_='generic-item')
                article_items = [item for item in article_items if 'article-item' in item.get('class', [])]
            
            if not article_items:
                article_items = soup.find_all('article')
            
            if not article_items:
                print("[!] Tidak ada artikel ditemukan di halaman ini.")
                print("    Mencoba menganalisis struktur halaman...")
                
                # Debug: Print beberapa elemen yang ditemukan
                all_divs = soup.find_all('div', limit=10)
                for i, div in enumerate(all_divs):
                    classes = div.get('class', [])
                    if classes:
                        print(f"    Debug {i+1}: div dengan class: {classes}")
                
                if page == 1:
                    print("    [!] Halaman pertama tidak berhasil, kemungkinkan ada masalah dengan akses MDPI")
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
                    
                    # Ambil konten lengkap dari halaman detail artikel
                    print(f"    └ Mengambil konten lengkap untuk: {title[:40]}...")
                    article_content = get_full_article_content(driver, link)
                    
                    article_data = {
                        "title": title,
                        "authors": authors,
                        "journal": journal_info,
                        "abstract": article_content.get('abstract', 'Abstract not found'),
                        "keywords": article_content.get('keywords', 'Keywords not found'),
                        "full_content": article_content.get('sections', {}),
                        "references": article_content.get('references', 'References not found'),
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
    JUMLAH_AMBIL = 5000         # Jumlah jurnal yang ingin diambil (testing dengan jumlah kecil dulu)
    
    scrape_mdpi(TOPIK, TAHUN_KEBELAKANG, JUMLAH_AMBIL)