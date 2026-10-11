import os
import requests
import time
from playwright.sync_api import sync_playwright

TOKEN = '8817280652:AAHNSL-u4fbhnM8eFuPP7bOWXjbQ7bVG3R0' 
CHAT_ID = '6321591510' 
TIKTOK_URL = 'https://www.tiktok.com/@maryta288' 

print("--- الحصّادة فائقة السرعة: لقط، تحميل، وإرسال فيديو بفيديو بالترتيب ---")

def send_video(file_path):
    url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
    if os.path.exists(file_path):
        with open(file_path, 'rb') as video:
            try:
                response = requests.post(url, data={'chat_id': CHAT_ID}, files={'video': video}, timeout=60)
                return response.status_code == 200
            except Exception as e:
                print(f"خطأ أثناء الإرسال للتليجرام: {e}")
    return False

def download_from_musicaldown(browser_context, video_url):
    try:
        page = browser_context.new_page()
        page.goto("https://musicaldown.net/en", timeout=30000)
        page.fill("input[name='q']", video_url)
        page.locator("button.btn-red").click()
        
        # بنستنى زرار الـ HD يظهر
        page.wait_for_selector("a:has-text('MP4 HD')", timeout=20000)
        hd_element = page.locator("a:has-text('MP4 HD')").first
        hd_link = hd_element.get_attribute("href")
        page.close()
        return hd_link
    except Exception as e:
        print(f"⚠️ مشكلة في موقع التحميل للفيديو ده: {e}")
        try: page.close()
        except: pass
    return None

def start_harvesting():
    # 1. بنقرأ الأرشيف الحالي لليوزر التاني
    archive = []
    if os.path.exists('bulk_archive.txt'):
        with open('bulk_archive.txt', 'r') as f:
            archive = f.read().splitlines()

    with sync_playwright() as p:
        print("فتح المتصفح للبدء في مسح صفحة تيك توك...")
        browser = p.chromium.launch(headless=True)
        # بنحط User-Agent حقيقي عشان تيك توك ميقفشوش
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        tiktok_page = context.new_page()
        
        print(f"الدخول على صفحة اليوزر: {TIKTOK_URL}")
        tiktok_page.goto(TIKTOK_URL, timeout=60000)
        tiktok_page.wait_for_timeout(5000) # بنستنى 5 ثواني عشان الفيديوهات تتملي
        
        processed_ids = set()
        no_new_videos_count = 0
        
        while True:
            # بنلقط كل روابط الفيديوهات المتاحة على الشاشة حالياً
            links = tiktok_page.locator("a[href*='/video/']").all()
            video_urls = []
            for link in links:
                href = link.get_attribute("href")
                if href and "/video/" in href and href not in video_urls:
                    video_urls.append(href)
            
            new_video_found_in_loop = False
            
            for video_url in video_urls:
                video_id = video_url.split('/')[-1].split('?')[0] # تنظيف الـ ID
                
                # لو عالجناه في الـ اللوب الحالية أو متسجل في الأرشيف قبل كده هنتخطاه
                if video_id in processed_ids or video_id in archive:
                    continue
                    
                processed_ids.add(video_id)
                new_video_found_in_loop = True
                
                print(f"\n🎯 تم رصد فيديو جديد بالترتيب: {video_url}")
                
                # خطوة التحميل الفوري من خلال المتصفح
                hd_link = download_from_musicaldown(context, video_url)
                
                if hd_link:
                    print("لقينا رابط الـ HD الخارق! جاري سحب الـ 13 ميجا...")
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    try:
                        vid_response = requests.get(hd_link, headers=headers, timeout=60)
                        file_name = f"bulk_{video_id}.mp4"
                        
                        with open(file_name, 'wb') as f:
                            f.write(vid_response.content)
                            
                        file_size = os.path.getsize(file_name)
                        
                        if file_size > 100000:
                            print(f"✅ تم التحميل بنجاح (الحجم: {file_size / (1024*1024):.2f} ميجا). طيران للتليجرام...")
                            if send_video(file_name):
                                print("💾 وصل للتليجرام! بنسجله في الأرشيف فوراً...")
                                with open('bulk_archive.txt', 'a') as f:
                                    f.write(f"{video_id}\n")
                                archive.append(video_id)
                            else:
                                print("❌ فشل الإرسال، مش هنأرشفه عشان يعيد المحاولة.")
                                if os.path.exists(file_name): os.remove(file_name)
                        else:
                            print("⚠️ الملف نزل تالف أو صغير.")
                            if os.path.exists(file_name): os.remove(file_name)
                    except Exception as e:
                        print(f"خطأ أثناء تحميل الملف: {e}")
                
                # ريفريش بسيط 2 ثانية بين كل فيديو وفيديو
                time.sleep(2)
            
            # حركة النزول لتحت (Scroll Down) عشان يظهر فيديوهات جديدة
            print("📜 بننزل لتحت في الصفحة عشان نكشف الفيديوهات اللي عليها الدور...")
            tiktok_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            tiktok_page.wait_for_timeout(3000) # بنستنى 3 ثواني الفيديوهات الجديدة تفتح
            
            # شرط النهاية: لو نزلنا تحت 3 مرات ورا بعض وملقيناش أي فيديو جديد، يبقى الصفحة خلصت تماماً وصل للرقم الكلي
            if not new_video_found_in_loop:
                no_new_videos_count += 1
                if no_new_videos_count >= 3:
                    print("\n🏁 وصلنا لنهاية الصفحة تماماً وتم التأكد إن عدد الفيديوهات مطابق للكل!")
                    break
            else:
                no_new_videos_count = 0
                
        browser.close()
    print("\n🎉 انتهت العملية بنجاح كامل!")

if __name__ == "__main__":
    start_harvesting()
