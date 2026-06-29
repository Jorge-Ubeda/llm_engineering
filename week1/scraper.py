import asyncio
import threading
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import requests
import os


# Standard headers to fetch a website
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}

def fetch_website_contents(url):
    """
    Return the title and contents of the website at the given url;
    truncate to 2,000 characters as a sensible limit
    """
    certs = os.getenv("PEM_BUNDLE_PATH")

    response = requests.get(url, headers=headers, verify=certs)
    return response

def fetch_website_contents_with_js(url):
    """
    Return the title and contents of the website at the given url that contains JavaScript;
    truncate to 2,000 characters as a sensible limit
    """
    html_result = []
    error_result = []

    async def fetch():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            content = await page.content()
            html_result.append(content)
            await browser.close()
    def run_in_thread():
        try:
            loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(fetch())
            loop.close()
        except Exception as e:
            error_result.append(e)
    
    t = threading.Thread(target=run_in_thread)
    t.start()
    t.join()

    if error_result:
        raise error_result[0]
    
    return html_result[0]

def parse_letterboxd_rss(url):
    """
    Return the first 10 reviewed films from a Letterboxd RSS feed,
    formatted as label: value pairs, truncated to 2,000 characters.
    """
    response = fetch_website_contents(url)
    soup = BeautifulSoup(response.content, "xml")
    title = soup.title.string if soup.title else "No title found"
    items = soup.find_all("item")[:10]
    item_texts = []
    for item in items:
        lines = []
        for tag_name in ["tmdb:movieId", "letterboxd:memberLike"]:
            tag = item.find(tag_name)
            if tag:
                tag.decompose()
        for child in item.find_all(recursive=False):
            label = child.name
            if label == "description":
                desc_soup = BeautifulSoup(child.get_text(), "html.parser")
                for img in desc_soup.find_all("img"):
                    img.decompose()
                value = desc_soup.get_text(separator="\n", strip=True)
            else:
                value = child.get_text(strip=True)
            if value:
                lines.append(f"{label}: {value}")
        item_texts.append("\n".join(lines))
    text = "\n\n".join(item_texts)
    return (title + "\n\n" + text)

def parse_website_contents(url, contains_js=False):
    """
    Return the title and text body of the website at the given url;
    truncated to 2,000 characters.
    """
    if contains_js:
        soup = BeautifulSoup(fetch_website_contents_with_js(url), "html.parser")
    else:
        soup = BeautifulSoup(fetch_website_contents(url).content, "html.parser")

    title = soup.title.string if soup.title else "No title found"
    if soup.body:
        for irrelevant in soup.body(["script", "style", "img", "input"]):
            irrelevant.decompose()
        text = soup.body.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)
    return (title + "\n\n" + text)[:2_000]

def fetch_website_links(url):
    """
    Return the links on the webiste at the given url
    I realize this is inefficient as we're parsing twice! This is to keep the code in the lab simple.
    Feel free to use a class and optimize it!
    """
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    links = [link.get("href") for link in soup.find_all("a")]
    return [link for link in links if link]
