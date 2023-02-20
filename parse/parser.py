import json
import time
import pprint
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.common.by import By
# from selenium_stealth import stealth

# options = webdriver.FirefoxOptions()
# options.add_argument("start-maximized")

# options.add_argument("--headless")

# options.add_experimental_option("excludeSwitches", ["enable-logging"])
# options.add_experimental_option('useAutomationExtension', False)
driver = webdriver.Chrome()
# stealth(driver,
#         languages=["en-US", "en"],
#         vendor="Google Inc.",
#         platform="Win32",
#         webgl_vendor="Intel Inc.",
#         renderer="Intel Iris OpenGL Engine",
#         fix_hairline=True,
#         )

data = {
}
domain = "https://tabiturient.ru/"
driver.get('https://tabiturient.ru/vuzege/')
vuz = driver.find_element(By.CLASS_NAME, 'obramtop100').find_elements(By.TAG_NAME, 'a')
# Извлекаем имена Вузов
vuz = [i.get_attribute("href").split('/')[-3] for i in vuz]
for name_vuz in vuz:
    # Извлекаем все блоки CO страницы
    url = f'https://tabiturient.ru/vuzu/{name_vuz}/'
    driver.get(url)
    head = driver.find_element(By.CLASS_NAME, 'headercontent')
    """ Ищем ссылку, логотип и имя высшего учебного заведения """
    link = head.find_element(By.TAG_NAME, 'a').get_attribute("href")
    title = driver.find_elements(By.CLASS_NAME, 'font4m')[1].text
    title1 = driver.find_elements(By.CLASS_NAME, 'font4m')[0].text
    img = head.find_element(By.CLASS_NAME, 'vuzlistimg2').get_attribute('src')
    comments = []
    """ Проверяем есть ли у учебного заведения отзовы """
    try:
        blocks = driver.find_element(By.ID, "resultsliv")
        if blocks:
            posts = blocks.find_elements(By.CLASS_NAME, "mobpadd20-2")
            for ind, i in enumerate(posts):
                text = i.find_elements(By.CLASS_NAME, "font2")
                comments.append((text[0].text[:-1], ' '.join(text[3].text.split('\n'))))
                if ind == 5:
                    break
    except NoSuchElementException:
        pass
    data.update({name_vuz: {'title': title, 'img': img, 'link': link, 'coments': comments, 'title1': title1}})
with open('result.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)
