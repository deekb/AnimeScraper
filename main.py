from seleniumwire import webdriver  # Import from seleniumwire
from selenium.webdriver.common.by import By  # Import By for locating elements
import time
import os
import re
import requests
import subprocess

SUBTITLE_LANG = "en"
processed_requests = set()  # Track unique downloads for each episode

def download_ublock_extension():
    extension_path = './ublock_origin.xpi'

    if os.path.exists(extension_path):
        print(f"uBlock Origin already exists at: {extension_path}")
        return extension_path

    url = "https://addons.mozilla.org/firefox/downloads/file/4359936/ublock_origin-1.60.0.xpi"
    response = requests.get(url)
    response.raise_for_status()

    with open(extension_path, 'wb') as file:
        file.write(response.content)
    print(f"Downloaded uBlock Origin to: {extension_path}")
    return extension_path


def download_yt_dlp():
    yt_dlp_path = './yt-dlp'

    if os.path.exists(yt_dlp_path):
        print(f"yt-dlp already exists at: {yt_dlp_path}")
        return yt_dlp_path

    url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
    response = requests.get(url)
    response.raise_for_status()

    with open(yt_dlp_path, 'wb') as file:
        file.write(response.content)

    os.chmod(yt_dlp_path, 0o755)
    print(f"Downloaded yt-dlp to: {yt_dlp_path}")
    return yt_dlp_path


def download_and_convert_m3u8(m3u8_url, output_path):
    command = [
        './yt-dlp',
        '--quiet',
        '-o', output_path,
        m3u8_url
    ]

    try:
        subprocess.run(command, check=True)
        print(f"Converted and downloaded: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error downloading {m3u8_url}: {e}")


def download_vtt(vtt_url, output_path):
    try:
        response = requests.get(vtt_url)
        response.raise_for_status()

        with open(output_path, 'wb') as vtt_file:
            vtt_file.write(response.content)
        print(f"Downloaded subtitle: {output_path}")
    except requests.HTTPError as e:
        print(f"Error downloading {vtt_url}: {e}")


def extract_episode_number(driver):
    """Extract the episode number using Selenium."""
    try:
        episode_info_element = driver.find_element(By.XPATH, "//div[@class='server-notice']/strong/b")
        episode_text = episode_info_element.text
        episode_number = re.search(r'\d+', episode_text)
        if episode_number:
            return episode_number.group(0)
    except Exception as e:
        print(f"Error extracting episode number: {e}")
    return None


def wait_for_user_confirmation():
    """Prompt the user to start the download process."""
    input("Navigate to the episode page, then press Enter to start downloading...")


def download_episode(driver, show_name, downloads_folder):
    """Download the current episode's video and subtitles."""
    episode_number = extract_episode_number(driver)

    if episode_number:
        episode_folder = os.path.join(downloads_folder, show_name, f"episode_{episode_number}")
        os.makedirs(episode_folder, exist_ok=True)

        # First, process the requests for the current episode
        for request in driver.requests:
            if request.url in processed_requests:
                continue

            if request.response and request.url.lower().endswith('.m3u8') and "master" in request.url.lower():
                output_mp4_path = os.path.join(episode_folder, f"episode_{episode_number}.mp4")
                download_and_convert_m3u8(request.url, output_mp4_path)
                processed_requests.add(request.url)

            elif request.response and request.url.lower().endswith('.vtt') and "en" in request.url.lower():
                output_vtt_path = os.path.join(episode_folder, f"episode_{episode_number}.vtt")
                download_vtt(request.url, output_vtt_path)
                processed_requests.add(request.url)

        print(f"Episode {episode_number} downloaded.")

        # Clear the requests after processing the current episode
        driver.requests.clear()  # Clear the requests list

    else:
        print("Unable to determine episode number.")

def next_episode(driver):
    """Navigate to the next episode."""
    try:
        driver.execute_script("nextEpisode()")
        driver.refresh()
        time.sleep(5)
        driver.implicitly_wait(10)
    except Exception as e:
        print(f"Error navigating to the next episode: {e}")

def log_requests(browser_choice):
    """Main function to handle browser setup and downloading."""
    if browser_choice == 'chrome':
        driver = webdriver.Chrome()
    else:
        profile_path = os.path.expanduser("firefox-profile")
        options = webdriver.FirefoxOptions()
        options.set_preference('profile', profile_path)
        driver = webdriver.Firefox(options=options)

        # Load uBlock Origin extension
        ublock_extension_path = download_ublock_extension()
        driver.install_addon(ublock_extension_path, temporary=True)

    # Ask the user for the name of the show
    show_name = input("Enter the name of the show (subfolder): ")

    # Create downloads folder for the show
    downloads_folder = './downloads'
    os.makedirs(os.path.join(downloads_folder, show_name), exist_ok=True)

    driver.get('https://www.hianime.to')
    print("Browser loaded. Please navigate to the first episode.")
    wait_for_user_confirmation()  # Wait for user to confirm when to start

    try:
        while True:
            # Download the current episode
            download_episode(driver, show_name, downloads_folder)

            # Ask user if they want to download the next episode
            next_episode(driver)
            # Clear requests again before the next episode's processing starts
            driver.requests.clear()  # Clear requests for the next episode


    except Exception as e:
        print(f"An error occurred: {e}")

    driver.quit()



if __name__ == "__main__":
    download_yt_dlp()  # Download yt-dlp if it doesn't exist
    log_requests('firefox')