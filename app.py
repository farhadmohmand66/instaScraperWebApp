# ########################################################################################
from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
import csv
import time

import secrets

app = Flask(__name__)

# Generate a random secret key with 32 bytes
secret_key = secrets.token_hex(8)
print("Generated Secret Key:", secret_key)
app.secret_key = secret_key

chrome_driver_path = 'chromedriver.exe'  # Update with your actual path
chrome_options = Options()
chrome_options.add_argument('--headless')  # Run Chrome in headless mode (no GUI)

driver = None  # Global variable to store the WebDriver instance

def init_driver():
    global driver
    if driver is not None:
        try:
            driver.quit()
        except Exception as e:
            print(f"Error quitting existing WebDriver instance: {str(e)}")
    driver = webdriver.Chrome(executable_path=chrome_driver_path, options=chrome_options)
    # driver = webdriver.Chrome(service=webdriver.chrome.service.Service(chrome_driver_path))
    return driver

def login_instagram(username, password, driver):
    try:
        driver.get("http://www.instagram.com")
        wait = WebDriverWait(driver, 10)

        username_elem = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='username']")))
        password_elem = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='password']")))
        username_elem.clear()
        username_elem.send_keys(username)
        password_elem.clear()
        password_elem.send_keys(password)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()
        wait.until(EC.element_to_be_clickable((By.CLASS_NAME, '_ac8f'))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Not Now")]'))).click()

    except Exception as e:
        print(f"Error logging in: {str(e)}")

    return driver

def logout_from_instagram(driver, wait):
    try:
        # Click on the profile picture
        profile_picture = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@class="x1iyjqo2 xh8yej3"]/div[8]')))
        profile_picture.click()

        # Click on the "Log Out" option
        log_out_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@class="x1q0g3np x2lah0s x8j4wrb"]')))
        log_out_button.click()

        # Click on the "Log Out" confirmation button
        log_out_confirm_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Log Out")]')))
        log_out_confirm_button.click()

    except Exception as e:
        print(f"Error logging out: {str(e)}")


def search_and_scrape(keyword, driver, wait, data_list):
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@class="x1iyjqo2 xh8yej3"]/div[2]'))).click()
        searchbox = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Search']")))
        searchbox.clear()
        searchbox.send_keys(keyword)
        my_link = wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, '/{keyword[1:]}/')]")))
        my_link.click()
        time.sleep(4)

        post_links = driver.find_elements(By.CSS_SELECTOR, 'a[href^="/p/"]')
        del post_links[3:]  # Keep the links up to index 3 and delete onward links
        post_links = [link.get_attribute('href') for link in post_links]

        for post_link in post_links:
            try:
                driver.get(post_link)
                time.sleep(4)
                post = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span.xt0psk2")))
                post.click()
                time.sleep(4)

                try:
                    time.sleep(4)
                    profile_name = driver.find_element(By.CSS_SELECTOR, 'h2').text
                except NoSuchElementException:
                    profile_name = 'none'

                try:
                    follower_count = driver.find_element(By.XPATH, "//a[contains(@href, '/followers')]").text
                except NoSuchElementException:
                    follower_count = 'none'

                try:
                    bio = driver.find_element(By.CSS_SELECTOR, 'div.x7a106z h1').text
                except NoSuchElementException:
                    bio = 'none'

                data_list.append({
                    "post_link": post_link,
                    "profile_name": profile_name,
                    "follower_count": follower_count,
                    "bio": bio
                })

            except Exception as e:
                print(f"Error scraping profile: {str(e)}")
                continue

        driver.get('https://www.instagram.com')
        time.sleep(2)

    except Exception as e:
        print(f"Error searching for keyword: {str(e)}")
        return

def write_list_to_csv(data_list, csv_file):
    with open(csv_file, 'w', newline='', encoding='utf-8') as file:
        csv_writer = csv.DictWriter(file, fieldnames=["post_link", "profile_name", "follower_count", "bio"])
        csv_writer.writeheader()
        csv_writer.writerows(data_list)


# Initialize the WebDriver
init_driver()

# Main route for the web application
@app.route('/', methods=['GET', 'POST'])
def main_page():
    global driver  # Use the global WebDriver instance
    if request.method == 'POST':
        if 'username' in session and 'password' in session:
            hashtags = request.form['hashtags'].split(',')
            data_list = []
            wait = WebDriverWait(driver, 10)

            for hashtag in hashtags:
                search_and_scrape(hashtag, driver, wait, data_list)

            csv_filename = 'output.csv'
            write_list_to_csv(data_list, csv_filename)

            return render_template('main.html', data=data_list, csv_filename=csv_filename)
        else:
            return redirect(url_for('login'))

    return render_template('main.html', data=None, csv_filename=None)

# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    global driver  # Use the global WebDriver instance
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if login_instagram(username, password, driver):
            session['username'] = username
            session['password'] = password
            flash('login successful!')
            return redirect(url_for('main_page'))
        else:
            flash('incorrect username or password!')
            return redirect(url_for('login'))

    return render_template('main.html', data=None, csv_filename=None)

# Route for logout
@app.route('/logout', methods=['GET'])
def logout():
    global driver  # Use the global WebDriver instance
    if 'username' in session and 'password' in session:
        wait = WebDriverWait(driver, 10)
        logout_from_instagram(driver, wait)
        # Clear the session data for 'username' and 'password'
        session.pop('username', None)
        session.pop('password', None)

    return render_template('main.html', data=None, csv_filename=None)

# Route to download the CSV file
@app.route('/download/<csv_filename>')
def download_csv(csv_filename):
    return send_file(csv_filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')

# #################################################################

