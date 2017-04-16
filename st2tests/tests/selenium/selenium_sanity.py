import datetime

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def navigate_to_page(page_url, page_signature_xpath):
    print "Navigating to %s" % page_url
    driver = webdriver.Firefox()
    driver.get(page_url)
    condition = EC.presence_of_element_located((By.XPATH, page_signature_xpath))
    WebDriverWait(driver, 10).until(condition)
    return driver

def wait_for_element_by_xpath(driver, xpath):
    condition = EC.presence_of_element_located((By.XPATH, xpath))
    element = WebDriverWait(driver, 10).until(condition)
    return element

def wait_for_view_to_load(driver, view_name):
    print "Wait for %s to load" % view_name
    wait_for_element_by_xpath(driver, '//div[contains(@class,"panel__toolbar-title") and contains(text(), "%s")]' % view_name)
    return

def login(driver):
    print "Login"
    condition = EC.element_to_be_clickable((By.XPATH,'//input[contains(@class,"login__button")]'))
    login_button = WebDriverWait(driver, 10).until(condition)
    login_button.click()
    wait_for_view_to_load(driver, "History")
    return

def navigate_to_view(driver, menu_name, view_name):
    print "Go to %s" % view_name
    menu_link = driver.find_element(By.XPATH, '//a[contains(@href, "%s")]' % menu_name)
    menu_link.click()
    wait_for_view_to_load(driver, view_name)
    return

def select_row_by_property(driver, column_name, value):
    print "Find the %s = %s in list" % (column_name, value)
    cell_element = wait_for_element_by_xpath(driver, '//div[contains(@class, "column-%s") and contains(@title, "%s")]' % (column_name, value))
    row_element = cell_element.find_element_by_xpath('..')
    row_element.click()
    return

def fill_payload_input_field(driver, label, value):
    print "Fill the %s with value %s" % (label, value)
    wait_for_element_by_xpath(driver, '//div[contains(@class, "form__title")]')
    title_element = driver.find_element(By.XPATH, '//div[contains(@class, "form__title") and contains(text(), "%s")]' % label)
    label_element = title_element.find_element_by_xpath('..')
    input_element = label_element.find_element_by_xpath('./input')
    input_element.send_keys(value)
    return

def run_current_action(driver):
    print "Run current action"
    run_button = driver.find_element(By.XPATH, '//button[contains(@class, "forms__button")]')
    run_button.click()
    return

def wait_for_run_result(driver):
    print "Wait for execution completion and return output"
    wait_for_element_by_xpath(driver, '//span[contains(@status, "record.status") and contains(@class, "label--succeeded")]')
    result = driver.find_element(By.XPATH, '//div[contains(@code, "execution.result.stdout")]/div/pre/code/div')
    return result.text

########################## TEST ################################

driver = navigate_to_page("http://localhost:9101/webui", '//div[contains(@class,"login")]')

try:
    login(driver)

    navigate_to_view(driver, "actions", "Actions")
    select_row_by_property(driver, 'name', 'core.local')
    fill_payload_input_field(driver, "cmd", "uname")
    run_current_action(driver)

    navigate_to_view(driver, "history", "History")
    select_row_by_property(driver, 'action', 'core.local')

    expected_result = "Linux"
    actual_result = wait_for_run_result(driver)
    if expected_result == actual_result:
        print "Test successful: the returned value is %s as expected" % actual_result
    else:
        print "Test failed: actual value (%s) is different from expected (%s)" % (actual_result, expected_result)
except:
    print "Test failed: exception before test completion"
    raise
finally:
     driver.quit()
     print "Finished test"
