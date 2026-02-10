import time
import pyperclip
import os
import pyautogui
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select 
from selenium.webdriver.common.action_chains import ActionChains 
from webdriver_manager.chrome import ChromeDriverManager

# 클립보드 복사 붙여넣기 함수 (보안 키보드 우회)
def copy_paste_input(driver, element, text):
    try:
        driver.execute_script("arguments[0].click();", element)
        pyperclip.copy(text)
        element.send_keys(Keys.CONTROL, 'v')
        time.sleep(0.3)
    except:
        pass

# 알림창(Alert) 처리 함수
def dismiss_alert(driver):
    try:
        WebDriverWait(driver, 0.5).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        text = alert.text
        # 보안 프로그램 설치 등 불필요한 팝업은 닫기
        if "보안" in text or "설치" in text or "프로그램" in text:
            alert.dismiss()
        else:
            alert.accept()
        return True
    except:
        return False

# iframe 내부 요소 찾기 함수
def find_element_in_frames(driver, by, value):
    try:
        element = driver.find_element(by, value)
        return element
    except:
        pass
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for frame in iframes:
        try:
            driver.switch_to.frame(frame)
            found = find_element_in_frames(driver, by, value)
            if found: return found
            driver.switch_to.parent_frame()
        except:
            driver.switch_to.parent_frame()
    return None

# ★★★ 핵심 함수: 데이터를 인자로 받아서 크롤링 실행 ★★★
def run_safety_report(report_data):
    """
    [인자 구조 예시]
    report_data = {
        "portal_id": "kwr518",       # user 테이블
        "portal_pw": "password!",    # user 테이블
        "user_name": "건우",         # user 테이블
        "user_phone": "010-XXXX...", # user 테이블
        "file_path": "C:/.../temp_videos/submit_video.mp4", # 로컬 다운로드 경로
        "title": "중앙선 침범 신고",
        "content": "상세 내용...",
        "car_num": "123가4567",
        "occur_date": "2026. 02. 04.", 
        "occur_time_hh": "16",
        "occur_time_mm": "29"
    }
    """
    print("🚀 [Bot] 안전신문고 자동 신고 시작...")

    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True) # 브라우저 꺼짐 방지
    chrome_options.add_argument("--start-maximized")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # [Step 1] 로그인
        driver.get("https://www.safetyreport.go.kr/#/main/login/login")
        wait = WebDriverWait(driver, 15)
        dismiss_alert(driver)

        print(f"🔑 로그인 시도 (ID: {report_data['portal_id']})...")
        try:
            id_input = wait.until(EC.element_to_be_clickable((By.ID, "username")))
            copy_paste_input(driver, id_input, report_data["portal_id"])
            
            pw_input = driver.find_element(By.ID, "password")
            copy_paste_input(driver, pw_input, report_data["portal_pw"])
            
            pw_input.send_keys(Keys.ENTER)
            wait.until(EC.url_contains("main"))
            print("✅ 로그인 성공")
        except:
            print("⚠️ 로그인 실패 또는 이미 로그인됨 (진행 시도)")

        # [Step 2] 신고 페이지 이동
        target_url = "https://www.safetyreport.go.kr/#/safereport/safereport3"
        driver.get(target_url)
        driver.refresh()
        time.sleep(5)
        
        # 팝업 정리
        for _ in range(5):
            if dismiss_alert(driver): pass
            time.sleep(0.5)

        if "safereport3" in driver.current_url:
            print("📝 신고 양식 진입 성공!")
            time.sleep(2)

            # [Step 3] 카테고리 선택 (기타 자동차 안전기준 위반)
            category = "기타 자동차 안전기준 위반"
            try:
                select_elem = wait.until(EC.presence_of_element_located((By.ID, "ReportTypeSelect")))
                driver.execute_script("arguments[0].style.display = 'block';", select_elem)
                Select(select_elem).select_by_visible_text(category)
            except Exception as e:
                print(f"카테고리 선택 실패: {e}")

            # [Step 4] 동영상 업로드 (로컬 파일 경로 사용)
            try:
                file_path = report_data["file_path"]
                if os.path.exists(file_path):
                    print(f"📂 파일 업로드 시도: {file_path}")
                    add_btn = find_element_in_frames(driver, By.ID, "button_add")
                    if add_btn:
                        try: ActionChains(driver).move_to_element(add_btn).click().perform()
                        except: driver.execute_script("arguments[0].click();", add_btn)
                        
                        time.sleep(3)
                        dismiss_alert(driver)
                        
                        # 파일 탐색기 제어 (pyautogui)
                        pyautogui.hotkey('alt', 'n')
                        time.sleep(1)
                        # 한글 경로 문제 방지를 위해 클립보드 복사 붙여넣기도 고려 가능하나, 영문 경로 권장
                        pyautogui.write(file_path, interval=0.05)
                        time.sleep(1)
                        pyautogui.press('enter')
                        
                        print("📂 파일 선택 완료")
                        driver.switch_to.default_content()
                        time.sleep(5) 
                else:
                    print(f"❌ 파일이 존재하지 않습니다: {file_path}")
            except Exception as e:
                print(f"업로드 에러: {e}")

            # [Step 5] 내용 작성 (DB 데이터 사용)
            try:
                # 제목
                title_in = driver.find_element(By.XPATH, "//input[contains(@placeholder, '최소 2자')]")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", title_in)
                copy_paste_input(driver, title_in, report_data["title"])

                # 내용
                content_in = driver.find_element(By.TAG_NAME, "textarea")
                copy_paste_input(driver, content_in, report_data["content"])
                
                # 차량번호 (식별불가면 체크박스 클릭)
                car_num = report_data.get("car_num", "")
                if car_num and car_num != "식별불가":
                     try:
                        copy_paste_input(driver, driver.find_element(By.XPATH, "//input[contains(@placeholder, '차량 번호')]"), car_num)
                     except: pass
                else:
                    try: driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "chkNoVhrNo"))
                    except: pass

                # 발생일자 (DB: YYYY-MM-DD -> Site: YYYY. MM. DD.)
                try:
                    date_input = driver.find_element(By.ID, "DEVEL_DATE")
                    driver.execute_script("arguments[0].click();", date_input)
                    date_input.send_keys(Keys.CONTROL, "a")
                    date_input.send_keys(Keys.DELETE)
                    date_input.send_keys(report_data["occur_date"]) 
                    date_input.send_keys(Keys.ESCAPE)
                except: pass

                # 발생시각 (HH, MM 분리)
                try:
                    Select(driver.find_element(By.ID, "DEVEL_TIME_HH")).select_by_value(report_data["occur_time_hh"])
                    Select(driver.find_element(By.ID, "DEVEL_TIME_MM")).select_by_value(report_data["occur_time_mm"])
                except: pass

            except Exception as e:
                print(f"내용 작성 실패: {e}")

            # [Step 6] 신고자 정보 (user 테이블 데이터)
            try:
                # 이름
                name_input = driver.find_element(By.ID, "C_NAME")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", name_input)
                driver.execute_script("arguments[0].value = arguments[1];", name_input, report_data["user_name"])

                # 전화번호
                phone_input = driver.find_element(By.ID, "C_PHONE2")
                driver.execute_script("arguments[0].value = arguments[1];", phone_input, report_data["user_phone"])
                
                # 인증 버튼 클릭
                auth_btn = driver.find_element(By.ID, "authSelectBtn")
                driver.execute_script("arguments[0].click();", auth_btn)
                print("📩 인증번호 요청 완료")
                
                time.sleep(2)
                try:
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '문자로')]"))).click()
                except: pass
                
                time.sleep(2)
                dismiss_alert(driver)

            except Exception as e:
                print(f"인증/인적사항 실패: {e}")

            # [Step 7] 동의 체크
            try:
                agree = driver.find_element(By.ID, "agreeUseMyInfo1")
                driver.execute_script("arguments[0].click();", agree)
            except: pass

            print("✅ 봇 작업 완료! (사용자가 인증번호 입력 후 제출하면 됨)")

    except Exception as e:
        print(f"❌ 봇 실행 중 오류: {e}")