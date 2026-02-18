import os
# 도커 내부에서 xclip을 사용하도록 강제 설정
os.environ['PYPERCLIP_BACKEND'] = 'xclip'

import time
import pyperclip
import pyautogui
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select 
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException, NoAlertPresentException

def set_chrome_options():
    """크롬 브라우저 옵션 설정"""
    chrome_options = Options()
    
    # ★ [필수] 도커 루트 계정 실행 및 리소스 제한 해제
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # 해상도 설정 (VNC 환경에 맞춰 넉넉하게)
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 팝업 차단 해제
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.set_capability("unhandledPromptBehavior", "accept")
    
    # User-Agent 설정
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    # 자동화 탐지 방지
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    return chrome_options

def copy_input_secure(driver, element, text):
    """
    [수정됨] 입력 함수: 클립보드 오류 시 JS로 강제 주입
    1순위: JS Value Injection (가장 강력, 보안 키패드 무시)
    2순위: Send Keys (일반 입력)
    """
    if not text:
        return

    try:
        # 1. JS로 값 강제 주입 (보안 프로그램 우회 최강)
        driver.execute_script("arguments[0].value = arguments[1];", element, text)
        time.sleep(0.2)
    except Exception:
        try:
            # 2. 실패 시 일반 입력 시도
            element.clear()
            element.send_keys(text)
        except Exception as e:
            print(f"⚠️ 입력 실패: {e}")

def force_accept_alert(driver):
    """알림창(Alert) 강제 수락 함수"""
    for _ in range(3):
        pyautogui.press('enter')
        time.sleep(0.2)
    
    try:
        driver.switch_to.alert.accept()
        print("✅ Alert 창 수락 완료")
    except:
        pass

def handle_extension_install(driver, wait):
    """
    보안 프로그램(TouchEn nxKey) 설치 로직
    - 전략: [등록하기] 클릭 -> [새 창] -> [탭 5번] -> [엔터] -> [설치 승인]
    """
    print("🕵️ 보안 프로그램 설치 로직 가동 (탭 5번 전략)...")
    time.sleep(2)
    force_accept_alert(driver)

    try:
        print("🖱️ '등록하기' 버튼 (ID: btn_ex_download) 찾는 중...")
        register_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn_ex_download")))
        main_window = driver.current_window_handle
        driver.execute_script("arguments[0].click();", register_btn)
        print("🖱️ [JS] '등록하기' 버튼 클릭 완료")
        
        print("⏳ 웹 스토어 창 열림 대기...")
        wait.until(lambda d: len(d.window_handles) > 1)
        
        for handle in driver.window_handles:
            if handle != main_window:
                driver.switch_to.window(handle)
                print(f"🔀 [Switch] 웹 스토어 창으로 이동 완료: {handle}")
                break
        
        time.sleep(5) 

        print("⌨️ [Key] 탭 5번 입력 시작 (Add to Chrome 타겟팅)...")
        for i in range(5):
            pyautogui.press('tab')
            time.sleep(0.2) 
            print(f"   -> Tab {i+1}")
        
        print("⌨️ [Key] 엔터 입력 (버튼 클릭 시도)")
        pyautogui.press('enter')

        print("⌨️ 설치 승인 팝업 대기 (3초)...")
        time.sleep(3) 
        
        print("⌨️ [Key] Left -> Enter (설치 승인)")
        pyautogui.press('left')
        time.sleep(0.5)
        pyautogui.press('enter')
        
        time.sleep(7) 

        print("🔄 웹 스토어 창 닫기 및 메인 창으로 복귀")
        driver.close()
        driver.switch_to.window(main_window)
        time.sleep(2)
        force_accept_alert(driver)

        return True

    except Exception as e:
        print(f"⚠️ 설치 로직 수행 중 오류 발생: {e}")
        try:
            driver.switch_to.window(main_window)
        except:
            pass
        return False

def handle_file_upload_navigation(driver, wait):
    """
    파일 탐색기(OS Native Window) 제어 로직
    - 전략: [탭 3번 진입] -> [Ctrl+L] -> [경로+슬래시 입력] -> [Down(파일선택)] -> [Enter(선택)] -> [Alt+O(열기)]
    """
    print("📂 [File Upload] 파일 업로드 네비게이션 시작...")
    
    try:
        current_path = os.getcwd()
        save_path = os.path.join(current_path, "debug_page_source.html")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"📝 [Debug] 페이지 소스 저장 완료: {save_path}")
    except Exception as e:
        print(f"⚠️ 소스 저장 실패: {e}")

    try:
        print("⌨️ [Key] 탭 3번 입력 시작 (파일 추가 버튼으로 이동)...")
        for i in range(3):
            pyautogui.press('tab')
            time.sleep(0.5) 
            print(f"   -> Tab {i+1}")
        
        print("⌨️ [Key] 엔터 입력 (파일 탐색기 호출)")
        pyautogui.press('enter')
        
        print("⏳ 파일 탐색기 열림 대기...")
        time.sleep(3)
        
        print("⌨️ [Key] Ctrl+L (경로 입력창 열기)")
        pyautogui.hotkey('ctrl', 'l') 
        time.sleep(1)
        
        target_path = "/app/backend-ai/temp_videos/"
        print(f"⌨️ [Key] 경로 입력: {target_path}")
        pyautogui.write(target_path, interval=0.1) 
        time.sleep(2.0) 
        
        print("⌨️ [Key] Down (첫 번째 파일 선택)")
        pyautogui.press('down')
        time.sleep(0.5)
        
        print("⌨️ [Key] Enter (파일 선택 확정)")
        pyautogui.press('enter')
        time.sleep(0.5)
        
        print("⌨️ [Key] Alt+O (Open 버튼 클릭)")
        pyautogui.hotkey('alt', 'o')
        
        print("✅ 파일 업로드 동작 완료!")
        
    except Exception as e:
        print(f"⚠️ 파일 업로드 네비게이션 실패: {e}")
        driver.save_screenshot("/app/backend-ai/upload_nav_fail.png")

def handle_location_search(driver, wait, location_text):
    """
    [수정됨] 위치 찾기 로직 (NoSuchWindowException 해결판)
    1. 위치찾기 버튼 클릭 -> 팝업 전환
    2. Iframe 진입 -> 검색어 JS 주입 -> 검색
    3. ★수정됨★ button.link_post 클릭 (PM님 제공 태그)
    """
    # ★ DB에 위치 정보가 없으면 서울역으로 기본 설정 (봇 멈춤 방지)
    if not location_text:
        print("⚠️ [WARNING] DB에 위치 정보가 없습니다. '서울역'으로 진행합니다.")
        location_text = "서울역" 
        
    print(f"📍 [Location] 위치 찾기 프로세스 시작: '{location_text}'")
    
    main_window = driver.current_window_handle
    
    try:
        # 1. 위치 찾기 버튼 스크롤 및 클릭
        print("📜 '위치 찾기' 버튼 클릭...")
        loc_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '위치 찾기')] | //a[contains(text(), '위치 찾기')]")))
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", loc_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", loc_btn)
        
        # 2. 팝업 창 전환
        wait.until(lambda d: len(d.window_handles) > 1)
        for handle in driver.window_handles:
            if handle != main_window:
                driver.switch_to.window(handle)
                # (주의) 여기서 driver.close() 절대 금지 -> 팝업 닫힘
                print(f"🔀 주소 검색 팝업으로 전환 완료")
                break
        
        time.sleep(3) # 팝업 로딩 대기
        
        # 3. Iframe 진입
        try:
            print("🔲 Iframe 탐색 및 진입 시도...")
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if len(iframes) > 0:
                driver.switch_to.frame(iframes[0]) 
                print("   -> Iframe 내부 진입 성공")
        except:
            print("   -> Iframe 없음, 메인 프레임에서 진행")

        # 4. 검색어 입력 (ID: region_name)
        print("⌨️ 검색어 입력 시도 (JS Injection)...")
        search_input = wait.until(EC.presence_of_element_located((By.ID, "region_name")))
        driver.execute_script("arguments[0].value = arguments[1];", search_input, location_text)
        time.sleep(0.5)
        
        # 5. 검색 버튼 클릭
        try:
            search_btn = driver.find_element(By.CLASS_NAME, "btn_search")
            driver.execute_script("arguments[0].click();", search_btn)
            print("🖱️ 검색 버튼(btn_search) 클릭 (JS)")
        except:
            search_input.send_keys(Keys.ENTER)

        time.sleep(3) # 검색 결과 로딩
        
        # 6. ★ 핵심 수정 ★ <button class="link_post"> 클릭 (PM님 지시사항)
        print("🖱️ 상세 주소(button.link_post) 클릭 시도...")
        
        first_result = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.link_post")))
        
        driver.execute_script("arguments[0].click();", first_result)
        print("✅ 위치 정보 선택 완료! (link_post 버튼 클릭됨)")
        
        time.sleep(2)
        
        # 7. 메인 창으로 복귀
        driver.switch_to.window(main_window)
        print("🔄 메인 윈도우로 복귀")
        
    except Exception as e:
        print(f"⚠️ 위치 찾기 실패: {e}")
        driver.save_screenshot("/app/backend-ai/location_error.png")
        try:
            driver.switch_to.window(main_window)
        except:
            pass

def fill_report_details(driver, wait, data):
    """
    [수정됨] 상세 정보 입력 로직 
    ★ 수정 사항 1: 제목/내용 입력 후 스크롤 다운 추가 (PM 요청)
    ★ 수정 사항 2: 날짜 포맷 변환 (YYYY-MM-DD -> YYYY. MM. DD.)
    ★ 수정 사항 3: 날짜 ID 'DEVEL_DATE'로 변경 및 입력 방식 개선
    ★ 수정 사항 4: [삭제됨] 휴대전화 입력 로직 삭제 (자동완성 되므로)
    ★ 수정 사항 5: [최종] '신청' 버튼(fnGoNext(2)) 클릭 및 팝업 수락
    """
    print("📝 상세 정보 입력 시작...")
    
    # 키 이름 매핑 (서버 Snake Case 대응)
    title = data.get('title', '교통법규 위반 신고')
    content = data.get('content', '')
    
    # 차량번호
    car_num = data.get('carNum') or data.get('car_num') or '식별불가'
    
    # 날짜 (DB에서 온 값, 예: 2026-02-11)
    occur_date_raw = data.get('occurDate') or data.get('occur_date') or ''
    
    # 시간
    occur_hh = data.get('occurTimeHh') or data.get('occur_time_hh') or '00'
    occur_mm = data.get('occurTimeMm') or data.get('occur_time_mm') or '00'
    
    # 전화번호 (입력은 안하지만 로그용으로 남김)
    user_phone = data.get('userPhone') or data.get('user_phone') or ''

    print(f"   [Data Check] 시간: {occur_hh}시 {occur_mm}분, 차량: {car_num}, 날짜(Raw): {occur_date_raw}")

    try:
        # 1. 제목 입력
        print(f"   -> 제목 입력: {title}")
        title_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='최소 2자, 최대 150자 작성 가능']")))
        copy_input_secure(driver, title_input, title)
        
        # 2. 내용 입력
        print("   -> 내용 입력")
        content_input = driver.find_element(By.XPATH, "//textarea")
        copy_input_secure(driver, content_input, content)
        
        # ★ [추가됨] 내용 입력 후 스크롤 다운 (날짜/차량번호가 보이도록)
        print("📜 내용 입력 완료. 화면 스크롤 다운 (500px)...")
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(1.0)
        
        # 3. 차량번호
        print(f"   -> 차량번호 처리: {car_num}")
        if not car_num or "식별불가" in car_num or "unknown" in str(car_num).lower():
            try:
                print("      [!] 차량번호 식별불가 -> 체크박스(ID: chkNoVhrNo) 클릭 시도")
                no_plate_chk = wait.until(EC.presence_of_element_located((By.ID, "chkNoVhrNo")))
                driver.execute_script("arguments[0].click();", no_plate_chk)
                print("      [V] '차량 번호 없음' 체크완료")
            except Exception as e:
                print(f"      [X] 체크박스 클릭 실패: {e}")
        else:
            car_input = driver.find_element(By.XPATH, "//input[contains(@placeholder, '차량 번호')]")
            copy_input_secure(driver, car_input, car_num)
        
        # 4. 날짜 입력 (DEVEL_DATE ID 사용 + 포맷 변환 + Ctrl+A)
        # ★ 포맷 변환: 2026-02-11 -> 2026. 02. 11. (점과 띄어쓰기 주의)
        formatted_date = occur_date_raw
        if occur_date_raw and "-" in occur_date_raw:
            formatted_date = occur_date_raw.replace("-", ". ") + "."
        
        print(f"   -> 날짜 입력 시작 (타겟 ID: DEVEL_DATE, 변환값: {formatted_date})")
        
        try:
            # ★ ID 수정됨: occurDate -> DEVEL_DATE
            date_input = wait.until(EC.element_to_be_clickable((By.ID, "DEVEL_DATE")))
            
            # (1) 클릭해서 포커스
            date_input.click()
            time.sleep(0.5)
            
            # (2) Ctrl + A 로 전체 선택
            date_input.send_keys(Keys.CONTROL, 'a')
            time.sleep(0.2)
            
            # (3) Backspace로 지우기
            date_input.send_keys(Keys.BACKSPACE)
            time.sleep(0.2)
            
            # (4) 포맷팅된 날짜 입력 (2026. 02. 11.)
            date_input.send_keys(formatted_date)
            time.sleep(0.5)
            
            # (5) 엔터 쳐서 달력 닫기
            date_input.send_keys(Keys.ENTER)
            print("      [V] 날짜 직접 입력 성공")
            
        except Exception as e:
            print(f"      [X] 날짜 입력 실패 (JS 시도): {e}")
            # 실패 시 기존 JS 방식 fallback (ID는 DEVEL_DATE로 맞춰야 함)
            try:
                fallback_input = driver.find_element(By.ID, "DEVEL_DATE")
                driver.execute_script("arguments[0].removeAttribute('readonly');", fallback_input)
                driver.execute_script("arguments[0].value = arguments[1];", fallback_input, formatted_date)
            except:
                pass
        
        # 5. 시간 (ID: DEVEL_TIME_HH / DEVEL_TIME_MM)
        hh_str = str(int(occur_hh)).zfill(2)
        mm_str = str(int(occur_mm)).zfill(2)
        print(f"   -> 시간 설정: {hh_str}시 {mm_str}분")
        
        try:
            hour_select_elem = wait.until(EC.presence_of_element_located((By.ID, "DEVEL_TIME_HH")))
            Select(hour_select_elem).select_by_value(hh_str)
            
            min_select_elem = wait.until(EC.presence_of_element_located((By.ID, "DEVEL_TIME_MM")))
            Select(min_select_elem).select_by_value(mm_str)
            print("      [V] 시간/분 선택 성공")
        except Exception as e:
            print(f"      [X] 시간 선택 실패: {e}")
        
        # ★ [삭제됨] 6. 휴대전화 입력 부분 삭제 (자동완성 사용)
        print("   -> 전화번호 입력: (자동완성 사용하므로 건너뜀)")
        
        # ====================================================================
        # ★ [NEW] 7. '신청' 버튼(fnGoNext(2)) 클릭 및 팝업(Alert) 수락
        # ====================================================================
        print("🚀 '신청' 프로세스 시작...")
        
        # (1) 스크롤 맨 아래로 내려서 버튼 보이게 함 (가장 확실한 방법)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
        
        try:
            # onclick 속성에 'fnGoNext(2)'가 포함된 버튼 찾기
            print("   -> '신청' 버튼(fnGoNext(2)) 찾는 중...")
            
            # XPATH로 안전하게 찾기
            submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@onclick, 'fnGoNext(2)')]")))
            
            # 버튼이 화면 중앙에 오도록 스크롤 (이중 안전장치)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
            time.sleep(1)
            
            # 확실하게 클릭 (JS 사용)
            driver.execute_script("arguments[0].click();", submit_btn)
            print("   [V] 신청 버튼 클릭 완료. 팝업 대기...")
            
            # (2) 팝업(Alert) 수락
            time.sleep(2.0) # 팝업 뜨는 딜레이 (넉넉하게)
            try:
                WebDriverWait(driver, 10).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                print(f"   -> 팝업 감지됨: {alert.text}")
                alert.accept() # 확인 버튼 클릭
                print("   ✅ 팝업 수락 완료 (최종 신청 성공!)")
            except TimeoutException:
                print("   ⚠️ 팝업이 뜨지 않음 (이미 처리되었거나 오류)")
            except Exception as e:
                print(f"   ⚠️ 팝업 처리 중 오류: {e}")

        except Exception as e:
            print(f"❌ 신청 버튼 클릭 실패: {e}")
            # 혹시 모르니 클래스(button big blue)로 한번 더 시도 (fallback)
            try:
                submit_btn_fallback = driver.find_element(By.CLASS_NAME, "button.big.blue")
                driver.execute_script("arguments[0].click();", submit_btn_fallback)
            except: pass
        
        print("✅ 모든 상세 정보 입력 및 신청 시도 완료!")
        
    except Exception as e:
        print(f"⚠️ 상세 정보 입력 중 오류: {e}")

def run_safety_report(report_data):
    """
    메인 실행 함수
    """
    print(f"🔥 [DEBUG] 전달받은 데이터 확인: {report_data}")
    
    # ★ DB 데이터 체크 로직 (키 매핑 추가)
    location_data = report_data.get('location') or report_data.get('location') 
    
    if not location_data:
        print("⚠️ [WARNING] 'location' 정보가 NULL입니다. 기본값(서울역)으로 진행합니다.")
    
    print("🚀 [Bot] 안전신문고 프로세스 시작 (ID: DEVEL_DATE 수정판)...")

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=set_chrome_options())
        wait = WebDriverWait(driver, 20)

        login_url = "https://www.safetyreport.go.kr/#/main/login/login"
        print(f"🌐 접속 시도: {login_url}")
        
        try:
            driver.get(login_url)
        except:
            force_accept_alert(driver)
        
        time.sleep(2)

        # ----------------------------------------------------------------------
        # [Step 1] 보안 프로그램 설치
        # ----------------------------------------------------------------------
        is_install_page = False
        if "install" in driver.current_url.lower() or "touchen" in driver.current_url.lower():
            is_install_page = True
        elif len(driver.find_elements(By.ID, "btn_ex_download")) > 0:
            is_install_page = True

        if is_install_page:
             print("🛡️ 보안 프로그램 설치 페이지 감지됨.")
             if handle_extension_install(driver, wait):
                 print("🔄 설치 완료 후 로그인 페이지 새로고침")
                 driver.get(login_url)
                 time.sleep(3)
                 force_accept_alert(driver)

        # ----------------------------------------------------------------------
        # [Step 2] 로그인
        # ----------------------------------------------------------------------
        print("⏳ 로그인 정보 입력 중...")
        try:
            id_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='아이디']")))
        except:
            force_accept_alert(driver)
            id_input = driver.find_element(By.ID, "userId") 

        # Portal ID/PW 매핑 확인
        p_id = report_data.get('portalId') or report_data.get('portal_id')
        p_pw = report_data.get('portalPw') or report_data.get('portal_pw')

        copy_input_secure(driver, id_input, p_id)

        pw_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='비밀번호']")
        copy_input_secure(driver, pw_input, p_pw)
        
        print("🖱️ 로그인 버튼 클릭")
        pw_input.send_keys(Keys.ENTER)
        
        time.sleep(5)
        force_accept_alert(driver)

        # ----------------------------------------------------------------------
        # [Step 3] 메인 메뉴 진입
        # ----------------------------------------------------------------------
        if "login" not in driver.current_url:
            print("🎉 [성공] 로그인 성공! 메인 페이지 진입.")

            print("🖱️ '안전신고' 메뉴 클릭...")
            try:
                safe_report_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), '안전신고')] | //img[@alt='안전신고']")))
                safe_report_btn.click()
            except Exception as e:
                print(f"⚠️ 안전신고 버튼 클릭 실패 (URL 이동 시도): {e}")
                driver.get("https://www.safetyreport.go.kr/#/safereport/safereport1")
            
            time.sleep(3)
            force_accept_alert(driver)

            if len(driver.find_elements(By.ID, "btn_ex_download")) > 0:
                 print("🛡️ [재진입 감지] 설치 페이지로 이동됨. 설치 로직 재실행.")
                 handle_extension_install(driver, wait)
                 print("🔄 설치 후 다시 안전신고 페이지로 이동")
                 driver.get("https://www.safetyreport.go.kr/#/safereport/safereport1")
                 time.sleep(3)

            print("🖱️ '자동차·교통위반' 탭 클릭...")
            try:
                traffic_violation_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '자동차·교통위반')]")))
                driver.execute_script("arguments[0].click();", traffic_violation_tab)
                print("✅ [최종] 자동차·교통위반 카테고리 진입 성공!")
            except:
                print("⚠️ 탭 이동 실패, URL 강제 이동 시도")
                driver.get("https://www.safetyreport.go.kr/#/safereport/safereport3")
            
            time.sleep(3)

            # ------------------------------------------------------------------
            # [Step 4] 신고 유형 선택
            # ------------------------------------------------------------------
            print("📜 [Step 4] 신고 유형 선택 로직 시작...")
            print("📜 화면 스크롤 (0 -> 500)")
            driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(1)

            print("🖱️ 드롭다운 메뉴 클릭...")
            try:
                dropdown_trigger = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '유형을 선택해 주세요')]")))
                dropdown_trigger.click()
                print("   -> 드롭다운 메뉴 열림")
                time.sleep(1)
            except Exception as e:
                print(f"⚠️ 드롭다운 클릭 실패: {e}")

            print("🖱️ '교통위반(고속도로 포함)' 옵션 선택...")
            try:
                target_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '교통위반(고속도로 포함)')]")))
                target_option.click()
                print("✅ 신고 유형 선택 완료!")
            except Exception as e:
                print(f"⚠️ 옵션 선택 실패: {e}")

            time.sleep(2)

            # ------------------------------------------------------------------
            # [Step 5] 파일 업로드 (스크롤 보정 + 탭 3번 + Alt+O)
            # ------------------------------------------------------------------
            print("📜 [Step 5] 파일 추가 버튼을 찾기 위해 추가 스크롤 (500px)...")
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(2)

            handle_file_upload_navigation(driver, wait)
            
            time.sleep(2) # 파일 업로드 처리 대기

            # ------------------------------------------------------------------
            # [Step 6] 위치 찾기 (DB 정보 사용 - JS 주입 + ID타겟팅)
            # ------------------------------------------------------------------
            print("📜 [Step 6] 위치 찾기 로직 시작...")
            
            # 여기서 위에서 꺼낸 location_data 사용 (Snake Case 고려됨)
            handle_location_search(driver, wait, location_data)
            time.sleep(1)

            # ------------------------------------------------------------------
            # [Step 7] 상세 정보 입력 (DB 정보 사용 + ID타겟팅)
            # ------------------------------------------------------------------
            fill_report_details(driver, wait, report_data)

            print("🏁 모든 작업 완료. 10초 대기 후 종료.")
            time.sleep(10)

        else:
            print("❓ 로그인 실패: 여전히 로그인 페이지입니다.")

    except Exception as e:
        print(f"❌ [Bot] 치명적 오류 발생: {e}")
        if driver:
            driver.save_screenshot("/app/backend-ai/error_screenshot.png")
            print("📸 에러 화면 캡처 완료")

    finally:
        pass