import sys
import json
import hashlib
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.event import KeywordQueryEvent

# Python 3 compatibility for network requests
import urllib.request
import urllib.parse
import urllib.error

# Import BeautifulSoup for HTML parsing
from bs4 import BeautifulSoup


class HaiciDictExtension(Extension):

    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):

    def fetchAndParse(self, word):
        # Construct the URL for direct GET request
        url = 'http://apii.dict.cn/mini.php?q=' + urllib.parse.quote(word)
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36',
        }
        request = urllib.request.Request(url=url, headers=headers)
        response = None
        try:
            response = urllib.request.urlopen(request, timeout=5)
            if response.getcode() != 200:
                self.logger.error(f"HTTP error {response.getcode()} during fetchAndParse for word: {word}")
                return None

            responseData = response.read().decode('utf-8')

            # Parse the HTML content
            soup = BeautifulSoup(responseData, 'html.parser')

            result = {}

            # Extract the pronunciation (inside <span class='p'>)
            pronunciation_span = soup.find('span', class_='p')
            if pronunciation_span:
                result['p'] = pronunciation_span.get_text().strip()

            # Extract the main explanation (id="e")
            explanation_div = soup.find('div', id='e')
            if explanation_div:
                # Get text, replacing <br> with newlines, then strip leading/trailing whitespace
                result['e'] = explanation_div.get_text('\n').strip()

            return result

        except urllib.error.URLError as e:
            self.logger.error(f"Network error fetching dictionary data for '{word}': {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in fetchAndParse for '{word}': {e}")
            return None
        finally:
            if response:
                response.close()

    def on_event(self, event, _):
        word = event.get_argument()
        icon = 'images/icon.png'
        showList = []

        if not word:
            showList.append(ExtensionResultItem(icon=icon, name='Please type in some words', description='Enter a word to get its meaning', on_enter=DoNothingAction()))
            return RenderResultListAction(showList)

        # Step 1: Fetch and parse the HTML content
        parsed_data = self.fetchAndParse(word)

        if parsed_data is None:
            showList.append(ExtensionResultItem(icon=icon, name='Failed to retrieve dictionary data', description='Network error or inability to parse response. Please try again.', on_enter=HideWindowAction()))
            return RenderResultListAction(showList)

        # Step 2: Display results from parsed_data
        if 'e' not in parsed_data or not parsed_data['e']: # Check if 'e' key exists and is not empty
            showList.append(ExtensionResultItem(icon=icon, name=f'No result found for "{word}"', description='Try another word or check spelling', on_enter=HideWindowAction()))
        else:
            # Display word and pronunciation (if available)
            pronunciation = parsed_data.get('p', '').strip()
            word_and_pronunciation = f"{word} {pronunciation}" if pronunciation else word
            showList.append(ExtensionResultItem(
                icon=icon,
                name=word_and_pronunciation,
                description="Click to copy word and pronunciation",
                on_enter=CopyToClipboardAction(word_and_pronunciation)
            ))

            # Display explanations, each line as a separate item
            # The get_text('\n') in fetchAndParse already handled <br> to newlines
            explanations = parsed_data['e'].split('\n')
            for item in explanations:
                item = item.strip()
                if item: # Only add non-empty lines
                    showList.append(ExtensionResultItem(icon=icon, name=item, description='Click to copy explanation', on_enter=CopyToClipboardAction(item)))

        return RenderResultListAction(showList)

if __name__ == '__main__':
    HaiciDictExtension().run()
