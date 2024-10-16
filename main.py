from seleniumwire import webdriver  # Import from seleniumwire
import time
import os
import re
import requests
import subprocess


def download_ublock_extension():
    extension_path = './ublock_origin.xpi'

    if os.path.exists(extension_path):
        print(f"uBlock Origin already exists at: {extension_path}")
        return extension_path

    url = "https://addons.mozilla.org/firefox/downloads/file/4359936/ublock_origin-1.60.0.xpi"
    response = requests.get(url)
    response.raise_for_status()  # Ensure the request was successful

    # Save the extension to the local directory
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
    response.raise_for_status()  # Ensure the request was successful

    # Save the yt-dlp executable to the local directory
    with open(yt_dlp_path, 'wb') as file:
        file.write(response.content)

    # Make the yt-dlp executable
    os.chmod(yt_dlp_path, 0o755)
    print(f"Downloaded yt-dlp to: {yt_dlp_path}")
    return yt_dlp_path


def download_and_convert_m3u8(m3u8_url, output_path):
    command = [
        './yt-dlp',  # Use the downloaded yt-dlp executable
        '-o', output_path,  # Output path for the MP4 file
        m3u8_url  # The URL of the m3u8 file
    ]

    try:
        subprocess.run(command, check=True)
        print(f"Converted and downloaded: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error downloading {m3u8_url}: {e}")


def download_vtt(vtt_url, output_path):
    try:
        response = requests.get(vtt_url)
        response.raise_for_status()  # Raise an error for bad responses

        with open(output_path, 'wb') as vtt_file:
            vtt_file.write(response.content)
        print(f"Downloaded subtitle: {output_path}")
    except requests.HTTPError as e:
        print(f"Error downloading {vtt_url}: {e}")


def log_requests(browser_choice):
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

    driver.get('https://www.hianime.to')
    print("Logging network requests in real-time. Close the browser to stop...")

    processed_requests = set()
    downloads_folder = './downloads'
    os.makedirs(downloads_folder, exist_ok=True)

    try:
        while True:
            time.sleep(1)
            current_url = driver.current_url
            episode_id = re.search(r'ep=(\d+)', current_url)

            if episode_id:
                episode_folder = os.path.join(downloads_folder, f"episode_{episode_id.group(1)}")
                os.makedirs(episode_folder, exist_ok=True)

            for request in driver.requests:
                if request.response and request.url.lower().endswith('.m3u8'):
                    if request.url not in processed_requests:
                        referrer_url = request.headers.get('Referer', current_url)

                        print(
                            f"Request URL: {request.url}, "
                            f"Status Code: {request.response.status_code}, "
                            f"Content-Type: {request.response.headers.get('Content-Type', 'N/A')}, "
                            f"Referring Page: {referrer_url}, "
                            f"Current Episode Folder: {episode_folder}"
                        )

                        # Define the output path for the MP4 file
                        output_mp4_path = os.path.join(episode_folder, f"episode_{episode_id.group(1)}.mp4")

                        # Download and convert the m3u8 file to MP4
                        download_and_convert_m3u8(request.url, output_mp4_path)

                        processed_requests.add(request.url)

                elif request.response and request.url.lower().endswith('.vtt'):
                    if request.url not in processed_requests:
                        referrer_url = request.headers.get('Referer', current_url)

                        print(
                            f"Subtitle Request URL: {request.url}, "
                            f"Status Code: {request.response.status_code}, "
                            f"Content-Type: {request.response.headers.get('Content-Type', 'N/A')}, "
                            f"Referring Page: {referrer_url}, "
                            f"Current Episode Folder: {episode_folder}"
                        )

                        # Define the output path for the VTT file
                        output_vtt_path = os.path.join(episode_folder, f"episode_{episode_id.group(1)}.vtt")

                        # Download the VTT file directly
                        download_vtt(request.url, output_vtt_path)

                        processed_requests.add(request.url)

            if len(driver.window_handles) == 0:
                break

    except Exception as e:
        print("An error occurred:", e)

    driver.quit()


if __name__ == "__main__":
    download_yt_dlp()  # Download yt-dlp if it doesn't exist
    log_requests('firefox')  # Change to 'chrome' if needed
