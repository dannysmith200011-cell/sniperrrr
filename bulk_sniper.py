import os
import subprocess
import requests
import time
from playwright.sync_api import sync_playwright

TOKEN = '8817280652:AAHNSL-u4fbhnM8eFuPP7bOWXjbQ7bVG3R0' 
CHAT_ID = '6321591510' 
# حط لينك اليوزر التاني هنا 👇
TIKTOK_URL = 'https://www.tiktok.com/@maryta288' 

print("--- الحصّادة شغالة: سحب كل الفيديوهات بالترتيب ---")

def send_video(file_path):
    url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
    if os.path.exists(file_path):
        with open(file_path, 'rb') as video:
            requests.post(url, data={'chat_id': CHAT_ID}, files={'video': video})
        os.remove(file_path)

# الدالة دي بتجيب كلللل الروابط اللي على الصفحة
def get_all_video_urls():
    print("جاري فحص الصفحة وسحب كل الروابط...")
    try:
        result = subprocess.run(
            ['yt-dlp', '--print', 'webpage_url', TIKTOK_URL],
            capture_output=True, text=True
        )
        urls = [line.strip() for line in result.stdout.split('\n') if 'tiktok.com' in line]
        return urls
    except Exception as e:
        print(f"مشكلة في سحب الروابط: {e}")
    return []

def process_all_videos():
    urls = get_all_video_urls()
    if not urls:
        print("ملقيناش أي فيديوهات على الصفحة!")
        return

    print(f"لقينا {len(urls)} فيديو! هنبدأ الشغل...")
    
    # بنقرأ أرشيف اليوزر التاني
    archive = []
    if os.path.exists('bulk_archive.txt'):
        with open('bulk_archive.txt', 'r') as f:
            archive = f.read().splitlines()

    # بنفتح المتصفح مرة واحدة بس عشان نوفر وقت السيرفر
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for video_url in urls:
            video_id = video_url.split('/')[-1]
            
            # لو الفيديو متحمل قبل كده، هيتجاهله ويدخل عاللي بعده
            if video_id in archive:
                print(f"فيديو {video_id} متحمل قبل كده، تخطي...")
                continue
                
            print(f"\n--- بنعالج فيديو: {video_url} ---")
            try:
                page.goto("https://musicaldown.net/en", timeout=30000)
                page.fill("input[name='q']", video_url)
                page.locator("button.btn-red").click()
                
                page.wait_for_selector("a:has-text('MP4 HD')", timeout=20000)
                hd_element = page.locator("a:has-text('MP4 HD')").first
                hd_link = hd_element.get_attribute("href")
                
                if hd_link:
                    print("لقينا رابط الـ HD! جاري التحميل...")
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    vid_response = requests.get(hd_link, headers=headers)
                    file_name = f"bulk_{video_id}.mp4"
                    
                    with open(file_name, 'wb') as f:
                        f.write(vid_response.content)
                        
                    file_size = os.path.getsize(file_name)
                    
                    if file_size > 100000:
                        print(f"تم! الحجم: {file_size / (1024*1024):.2f} ميجا. جاري الإرسال للتليجرام...")
                        send_video(file_name)
                        
                        # بنسجل في الأرشيف الجديد فوراً
                        with open('bulk_archive.txt', 'a') as f:
                            f.write(f"{video_id}\n")
                        archive.append(video_id)
                        
                        # بنريح السكريبت 3 ثواني عشان الموقع ميعملناش بلوك من كتر الطلبات
                        time.sleep(3)
                    else:
                        print("الملف مساحته صغيرة، فشل التحميل.")
                        os.remove(file_name)
            except Exception as e:
                print(f"مشكلة في الفيديو ده (هنتخطاه): {e}")
                
        browser.close()
        print("\nخلصنا فحص كل الفيديوهات!")

if __name__ == "__main__":
    process_all_videos()
