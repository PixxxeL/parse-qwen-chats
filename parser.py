import json
import os
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


HEADLESS = False
RENEW_PROJECTS_CACHE = False
LOAD_CHATS = False
LOAD_PROJECTS = True

SITE_URLS = {
    'home': 'https://chat.qwen.ai/',
    'login': 'https://chat.qwen.ai/auth',
}

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
CHATS_DIR = os.path.join(DATA_DIR, 'chats')

def save_json(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=4, ensure_ascii=False)

def load_json(filepath):
    with open(filepath, encoding='utf-8') as fh:
        return json.load(fh)

def check_login(fn):
    def wrapper(*args):
        self = args[0]
        cookies_file = f'{DATA_DIR}\\cookies.json'
        cookies = None
        try:
            cookies = load_json(cookies_file)
        except Exception as e:
            print('No cookies: ', e)
        driver = self.driver or self.get_driver(headless=HEADLESS)
        if not cookies:
            self.login()
        elif not self.is_cookies:
            print('Get home page...')
            driver.get(SITE_URLS['home'])
            for cookie in cookies:
                #print('Add cookie', cookie['name'])
                driver.add_cookie({'name': cookie['name'], 'value': cookie['value']})
            self.is_cookies = True
            time.sleep(2)
        return fn(*args)
    return wrapper

class SiteReader:

    driver = None
    is_cookies = False
    chat_names = []
    project_chat_names = {}

    def get_driver(self, headless=True):
        firefox_location = os.getenv('FIREFOX_BINARY')
        gecko_location = os.getenv('GECKO_BINARY')
        options = Options()
        if headless:
            options.headless = True
            options.add_argument('-headless')
        options.binary_location = firefox_location
        service = Service(executable_path=gecko_location)
        self.driver = webdriver.Firefox(service=service, options=options)
        return self.driver

    def quit(self):
        if self.driver:
            self.driver.quit()

    def wait_for(self, timeout=1, message=None):
        if message:
            print(message)
        time.sleep(timeout)

    def login(self):
        user = os.getenv('QWEN_USER')
        password = os.getenv('QWEN_PASSWORD')
        print('Get login page...')
        self.driver.get(SITE_URLS['login'])
        self.wait_for(4, 'Ожидаем загрузки страницы...')
        username = self.driver.find_element(By.CSS_SELECTOR, 'input[name=email]')
        username.clear()
        username.send_keys(user)
        password = self.driver.find_element(By.CSS_SELECTOR, 'input[name=password]')
        password.send_keys(password)
        #password.send_keys(Keys.RETURN)
        self.driver.find_element(By.CSS_SELECTOR, 'button.qwenchat-auth-pc-submit-button').click()
        print('Logged in...')
        self.wait_for(6, 'Ожидаем редиректа после логина...')
        save_json(self.driver.get_cookies(), os.path.join(DATA_DIR, 'cookies.json'))

    @check_login
    def get_chats(self):
        page_url = SITE_URLS['home']
        print(f'Get page {page_url} ...')
        self.driver.get(page_url)
        self.wait_for(4, 'Ожидаем загрузки страницы...')
        # собрать контейнеры без проектов и групп
        if LOAD_CHATS:
            try:
                self.chat_names = load_json(os.path.join(DATA_DIR, 'chats.json'))
            except:
                pass
            if not self.chat_names:
                self._harvest_chat_names()
                save_json(self.chat_names, os.path.join(DATA_DIR, 'chats.json'))
            self._start_chat_loading()
        # собрать контейнеры проектов
        if LOAD_PROJECTS:
            try:
                self.project_chat_names = load_json(os.path.join(DATA_DIR, 'projects.json'))
            except:
                pass
            if RENEW_PROJECTS_CACHE or not self.project_chat_names:
                self._harvest_projects_chat_names()
                save_json(self.project_chat_names, os.path.join(DATA_DIR, 'projects.json'))
            self._start_project_loading()

    def _harvest_chat_names(self):
        self._scroll_sidebar()
        chats = self.driver.find_elements(By.CSS_SELECTOR, '.chat-item-drag-link-content')
        for chat in chats:
            name = None
            first_children = chat.find_elements(By.XPATH, './*[1]')
            if first_children:
                name = first_children[0].text
            if not name:
                print(f'ERROR element {chat}')
                continue
            self.chat_names.append(name)
        print(f'Harvested {len(self.chat_names)} chats...')

    def _scroll_sidebar(self):
        script = 'arguments[0].scrollTop = arguments[0].scrollHeight;'
        scrollable = self.driver.find_element(By.CSS_SELECTOR, '.sidebar-new-list-content')
        for idx in range(4):
            self.driver.execute_script(script, scrollable)
            self.wait_for(4, f'Ожидаем подгрузки прошлых чатов ({idx + 1}/4)...')
    
    def _start_chat_loading(self):
        for name in self.chat_names:
            el = self.driver.find_element(By.XPATH, f"//*[text()='{name}']")
            if not el:
                print(f'ERROR element for name: {name}')
                continue
            try:
                parent = el.find_element(By.XPATH, '..')
                parent = parent.find_element(By.XPATH, '..')
                parent.click()
            except Exception as e:
                print(f'ERROR {e} click for name: {name}')
                continue
            self.wait_for(4, f'Ожидаем подгрузки чата `{name}`...')
            self._click_download(name)

    def _click_download(self, name):
        self.driver.find_element(By.CSS_SELECTOR, '.chat-extension-modal').click()
        self.wait_for(2)
        try:
            el = self.driver.find_element(By.XPATH, "//*[text()='Download']")
            parent = el.find_element(By.XPATH, '..')
            #ActionChains(self.driver).move_to_element(parent).perform()
            parent.click()
            self.wait_for(2)
            self.driver.find_element(By.XPATH, "//*[text()='Export chat (.json)']").click()
            self.wait_for(2)
            return True
        except Exception as e:
            print(f'ERROR {e} download click for name: {name}')

    def _harvest_projects_chat_names(self):
        projects = self._projects_list()
        for idx, project in enumerate(projects):
            if not idx: # skip New Project
                continue
            if idx + 1 == len(projects): # more projects
                subprojects = self._more_projects(project)
                for subp in subprojects:
                    self._harvest_project_chat_names(subp, '.project-panel-item-text')
                continue
            self._harvest_project_chat_names(project, '.project-item-text')

    def _harvest_project_chat_names(self, project_el, name_selector):
        if not project_el:
            print(f'ERROR project element {project_el}')
            return
        project_name = project_el.find_element(By.CSS_SELECTOR, name_selector).text
        self.project_chat_names[project_name] = []
        project_el.click()
        self.wait_for(4, f'Ожидаем загрузки чатов проекта `{project_name}`...')
        selector = ' '.join([
            '.desktop-layout-content', '.project-content-chats',
            '.project-chats', '.chat-item-drag.project-chat-list'
        ])
        chats = self.driver.find_elements(By.CSS_SELECTOR, selector)
        for chat in chats:
            chat_name = chat.find_element(By.CSS_SELECTOR, '.project-chat-item-title').text
            self.wait_for(.1)
            self.project_chat_names[project_name].append(chat_name)
    
    def _start_project_loading(self):
        for project_name in list(self.project_chat_names.keys()):
            el = self.driver.find_element(By.XPATH, f"//*[text()='{project_name}']")
            if not el:
                # try to load more
                #projects = self._projects_list()
                #if projects:
                #    subprojects = self._more_projects(project)
                #for subp in subprojects:
                #    ...
                print(f'ERROR element for project: {project_name}')
                continue
            el.click()
            print(f'Ожидаем загрузки чатов проекта `{project_name}`...')
            selector = ' '.join([
                '.desktop-layout-content', '.project-content-chats',
                '.project-chats'
            ])
            root = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            try:
                chat_name = self.project_chat_names[project_name].pop()
            except:
                msg = (
                    'Project names is finished. '
                    'Replace from download folder and press Enter...'
                )
                input(msg)
                del self.project_chat_names[project_name]
                continue
            el = root.find_element(By.XPATH, f"//*[text()='{chat_name}']")
            parent = el.find_element(By.XPATH, '../../..')
            parent.click()
            self.wait_for(6, f'Ожидаем загрузки чата {project_name}:{chat_name}...')
            self._click_download(chat_name)
            self.driver.back()
            self.wait_for(2)
            if self.project_chat_names.keys():
                self._start_project_loading()

    def _projects_list(self):
        selector = ' '.join([
            '#sidebar', '.sidebar-new-list-content', '.project-list-wrapper',
            '.project-container', '.project-list', '.project-item'
        ])
        return self.driver.find_elements(By.CSS_SELECTOR, selector)

    def _more_projects(self, more_projects):
        more_projects.click()
        self.wait_for(1)
        return more_projects.find_elements(By.CSS_SELECTOR, '.project-panel-item')

def main():
    reader = SiteReader()
    try:
        reader.get_chats()
    except Exception as e:
        print(f'ERROR {e}')
    finally:
        reader.quit()


if __name__ == '__main__':
    main()
