import os
import requests
import time
from playwright.sync_api import sync_playwright

TOKEN = '8817280652:AAHNSL-u4fbhnM8eFuPP7bOWXjbQ7bVG3R0' 
CHAT_ID = '6321591510' 
TIKTOK_URL = 'https://www.tiktok.com/@maryta288' 

print("--- الحصّادة الخارقة: أرشيف للفيديوهات السليمة، وأرشيف للروابط المعصلجة ---")

# دالة إرسال رابط التيك توك على التليجرام لو حصل مشكلة وحفظه في أرشيف الفشل
def send_fallback_link(video_id, reason):
    tiktok_link = f"https://www.tiktok.com/@user66rae99/video/{video_id}"
    text = f"⚠️ فيديو معصلج!\nالسبب: {reason}\n\n🔗 الرابط المباشر عشان تشوفه أو تحمله براحتك:\n{tiktok_link}"
    msg_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    try:
        requests.post(msg_url, data={'chat_id': CHAT_ID, 'text': text}, timeout=60)
        print(f"📩 تم إرسال الرابط البديل للتليجرام (السبب: {reason}).")
        
        # التسجيل في الأرشيف الخاص بالفيديوهات المعصلجة (الـ ID - الرابط - السبب)
        with open('failed_archive.txt', 'a', encoding='utf-8') as f:
            f.write(f"{video_id} - {tiktok_link} - {reason}\n")
        return True
    except Exception as e:
        print(f"خطأ في إرسال رسالة الرابط: {e}")
        return False

# دالة رفع الفيديو السليم على التليجرام
def send_video_file(file_path):
    url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
    if os.path.exists(file_path):
        with open(file_path, 'rb') as video:
            try:
                response = requests.post(url, data={'chat_id': CHAT_ID}, files={'video': video}, timeout=300)
                return response.status_code == 200
            except Exception as e:
                print(f"خطأ أثناء رفع الفيديو للتليجرام: {e}")
    return False

def download_from_musicaldown(browser_context, video_url):
    try:
        page = browser_context.new_page()
        page.goto("https://musicaldown.net/en", timeout=30000)
        page.fill("input[name='q']", video_url)
        page.locator("button.btn-red").click()
        
        page.wait_for_selector("a:has-text('MP4 HD')", timeout=25000)
        hd_element = page.locator("a:has-text('MP4 HD')").first
        hd_link = hd_element.get_attribute("href")
        page.close()
        return hd_link
    except Exception as e:
        print(f"مشكلة في استخراج رابط الـ HD: {e}")
        try: page.close()
        except: pass
    return None

def start_harvesting():
    # بنجمع الـ IDs من الأرشيفين عشان نتخطاهم ومفيش حاجة تتعاد
    archive_ids = set()
    
    # 1. قراءة الفيديوهات السليمة
    if os.path.exists('bulk_archive.txt'):
        with open('bulk_archive.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip(): archive_ids.add(line.strip())
                
    # 2. قراءة الفيديوهات اللي فشلت واتبعتت كلينك
    if os.path.exists('failed_archive.txt'):
        with open('failed_archive.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    # بنسحب الـ ID بس من السطر اللي متسجل فيه الرابط عشان نتخطاه
                    vid_id = line.split(' - ')[0].strip()
                    archive_ids.add(vid_id)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
        )
        tiktok_page = context.new_page()
        tiktok_page.goto(TIKTOK_URL, timeout=60000)
        tiktok_page.wait_for_timeout(5000) 
        
        processed_ids = set()
        no_new_videos_count = 0
        
        while True:
            links = tiktok_page.locator("a[href*='/video/']").all()
            video_urls = []
            for link in links:
                href = link.get_attribute("href")
                if href and "/video/" in href and href not in video_urls:
                    video_urls.append(href)
            
            new_video_found_in_loop = False
            
            for video_url in video_urls:
                video_id = video_url.split('/')[-1].split('?')[0] 
                
                # تخطي لو الفيديو اتعمل قبل كده (سواء سليم أو معصلج)
                if video_id in processed_ids or video_id in archive_ids:
                    continue
                    
                processed_ids.add(video_id)
                new_video_found_in_loop = True
                
                print(f"\n🎯 تم رصد فيديو جديد بالترتيب: {video_id}")
                hd_link = download_from_musicaldown(context, video_url)
                
                if hd_link:
                    print("جاري التحميل بأمان (Stream)...")
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    file_name = f"bulk_{video_id}.mp4"
                    
                    try:
                        vid_response = requests.get(hd_link, headers=headers, timeout=120, stream=True)
                        with open(file_name, 'wb') as f:
                            for chunk in vid_response.iter_content(chunk_size=8192):
                                if chunk: f.write(chunk)
                                    
                        file_size_mb = os.path.getsize(file_name) / (1024 * 1024)
                        
                        # التوجيه الذكي: يمين (تحميل وأرشفة) أو شمال (رسالة تليجرام وأرشفة بايظة)
                        if file_size_mb > 49.5:
                            if send_fallback_link(video_id, f"حجمه ضخم جداً ({file_size_mb:.2f} ميجا)"):
                                archive_ids.add(video_id)
                        elif file_size_mb > 0.1:
                            print(f"✅ تم التحميل ({file_size_mb:.2f} ميجا). طيران للتليجرام...")
                            if send_video_file(file_name):
                                print("💾 وصل! بنسجله في أرشيف السليم فوراً...")
                                with open('bulk_archive.txt', 'a', encoding='utf-8') as f:
                                    f.write(f"{video_id}\n")
                                archive_ids.add(video_id)
                            else:
                                if send_fallback_link(video_id, "فشل الرفع لسيرفر تليجرام (Timeout)"):
                                    archive_ids.add(video_id)
                        else:
                            if send_fallback_link(video_id, "الملف نزل تالف أو مساحته شبه معدومة"):
                                archive_ids.add(video_id)
                                
                    except Exception as e:
                        if send_fallback_link(video_id, "الموقع قطع الاتصال أثناء التحميل"):
                            archive_ids.add(video_id)
                    
                    if os.path.exists(file_name):
                        os.remove(file_name)
                else:
                    if send_fallback_link(video_id, "موقع التحميل مقدرش يستخرج الجودة الـ HD"):
                        archive_ids.add(video_id)
                
                time.sleep(2)
            
            print("📜 بننزل لتحت في الصفحة عشان نكشف الفيديوهات اللي عليها الدور...")
            tiktok_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            tiktok_page.wait_for_timeout(3000) 
            
            if not new_video_found_in_loop:
                no_new_videos_count += 1
                if no_new_videos_count >= 3:
                    print("\n🏁 وصلنا لنهاية الصفحة تماماً!")
                    break
            else:
                no_new_videos_count = 0
                
        browser.close()

if __name__ == "__main__":
    start_harvesting()
