import logging
import requests
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup
from quickimgurpy import ImgurClient
from datetime import datetime
from .utils import azure_translate

logger = logging.getLogger(__name__)

load_dotenv()

DISCORD_FILE_LIMIT = int(os.getenv('DISCORD_FILE_LIMIT', 10*1024**2)) - 1
DISCORD_CHARACTER_LIMIT = int(os.getenv('DISCORD_CHARACTER_LIMIT', 2000)) - 200
TRANSLATE_FROM_LANGUAGE = os.getenv('TRANSLATE_FROM_LANGUAGE')
TRANSLATE_TO_LANGUAGE = os.getenv('TRANSLATE_TO_LANGUAGE')

WORD_LIMIT_MARKER = ' ...\n-# :small_orange_diamond: Word limit'
WORD_LIMIT_MARKER_LENGTH = len(WORD_LIMIT_MARKER)

def add_line_prefix(text: str, prefix: str) -> str:
    lines = text.split('\n')
    if len(lines) == 1:
        return prefix + text
    result = []
    for line in lines:
        if line.strip():
            result.append(prefix + line)
        else:
            result.append(prefix + ' ᠎')  # do nothing for empty lines
    return '\n'.join(result)


def build_line(text: str, prefix='', line_break=True, single_line_break=False):
    if not text:
        return ''
    if prefix:
        text = add_line_prefix(text, prefix)
    if not line_break:
        return text
    if single_line_break:
        return text + '\n'
    return text + '\n\n'


def trim_text_by_length(text: str, length: int) -> str:
    if len(text) <= length:
        return text

    return text[:length - WORD_LIMIT_MARKER_LENGTH].rstrip() + WORD_LIMIT_MARKER


def parse_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    external_links = []
    for a in soup.find_all('a'):
        href = a.get('href', '')
        text = a.get_text().strip()
        if text.startswith('http'):
            text = '外部链接'
        markdown_link = f'[{text}]({href})'
        if text.startswith('@'):
            a.replace_with(markdown_link)
        else:
            external_links.append(markdown_link)
            a.replace_with('')

    paragraphs = soup.find_all('p')
    paragraph_texts = []
    quote_in_line = None
    header_card = None
    for p in paragraphs:
        spans = p.find_all('span')
        for span in spans:
            if 'h-card' in span.get('class', []):
                if header_card:
                    logger.warning(
                        f"Multiple header cards found in {html_content} Skipping...")
                else:
                    header_card = span.get_text()
                span.replace_with("")
            elif 'quote-inline' in span.get('class', []):
                if quote_in_line:
                    logger.warning(
                        f"Multiple quote in lines found in {html_content}. Skipping...")
                else:
                    url = span.get_text()
                    url = url[url.find('http'):]
                    user = url[url.find('users/')+6:url.find('/truthes')]
                    quote_in_line = f'[{user}]({url})'
                span.replace_with("")
            else:
                span.unwrap()

        for br in p.find_all('br'):
            br.replace_with('\n')

        if not header_card:
            p_text = p.get_text()
            p_text = p_text.strip()
            if p_text:
                p_text = p_text.replace('â€™', '\'').replace('Â', '').replace(
                    "â€œ", "“").replace("â€", "”").replace("â€™", "'").replace("â€¦", "...")
                paragraph_texts.append(p_text)

    logger.debug(f"Parsed HTML. Found {len(paragraph_texts)} paragraphs, {len(external_links)} external links, {quote_in_line} quote in line, {header_card} header card.")
    return {
        'paragraph_texts': paragraph_texts,
        'quote_in_line': quote_in_line,
        'header_card': header_card,
        'external_links': external_links
    }


class TruthBuilder:
    def __init__(self):
        self.imgur = ImgurClient()
        self.translation_enabled = TRANSLATE_FROM_LANGUAGE and TRANSLATE_TO_LANGUAGE

    def build_truth(self, truth: dict):
        logger.debug(f"Building truth content.")
        files, inline_links = self._convert_attachments(truth)
        content = self._build_truth_content(truth, inline_links)
        return content, files

    def _build_truth_content(self, truth: dict, inline_links: list) -> str:
        date_time = datetime.fromisoformat(truth['created_at'])
        top_line = f'-# :loudspeaker: [@realDonaldTrump]({truth["url"]}) • <t:{int(date_time.timestamp())}>\n'
        main_contents = parse_html(truth['content'])
        inline_links += main_contents['external_links']
        inline_links = build_line(' ｜ '.join(inline_links), '> -# ', line_break=False)

        header_text, header_text_en, footer_text, footer_text_en = '', '', '', ''
        if main_contents['header_card']:
            header_text = '转发自 ' + main_contents['header_card']
            header_text_en = 'Reposted from ' + main_contents['header_card']
        if main_contents['quote_in_line']:
            footer_text = '引用自 ' + main_contents['quote_in_line']
            footer_text_en = 'Quoted from ' + main_contents['quote_in_line']

        reblog_texts, quoted_texts = [], []
        if truth['reblog']:
            reblog_texts = parse_html(truth['reblog']['content'])[
                'paragraph_texts']
        if truth['quote']:
            quoted_texts = parse_html(truth['quote']['content'])[
                'paragraph_texts']

        attached_texts = '\n\n'.join(reblog_texts) or '\n\n'.join(quoted_texts)

        # No real contents
        if not main_contents['paragraph_texts'] and not reblog_texts and not quoted_texts:
            logger.debug(f"No real contents found.")
            return top_line + (header_text or footer_text) + inline_links

        if self.translation_enabled:
            joined_main_text = '\n\n'.join(main_contents['paragraph_texts'])
            texts_to_translate = [{'text': joined_main_text},
                                {'text': '\n\n'.join(reblog_texts)},
                                {'text': '\n\n'.join(quoted_texts)}]

            logger.debug(f"Translating content.")
            try:
                translation = azure_translate(texts_to_translate)
            except Exception as e:
                logger.error(f"Error translating content: {e}", exc_info=True)
                translation = None
            error_text = translation.get('error', '') if translation else ''
        # Not translating or translation failed, return original text
        if translation is None or error_text:
            logger.debug(f"Translation failed. Showing original text.")
            if self.translation_enabled:
                translation_failed_text = '\n-# :small_orange_diamond:Translation failed' + build_line(error_text, ': ', single_line_break=True)
            else:
                translation_failed_text = ''
            content = translation_failed_text + (
                build_line(header_text, '-# ') +
                joined_main_text +
                build_line(footer_text, '-# ') +
                attached_texts
            ).rstrip()
            content = trim_text_by_length(top_line + content, DISCORD_CHARACTER_LIMIT - len(inline_links) - 200)
            return content + inline_links

        main_text_translation, reblog_translation, quote_translation = translation['translations']
        content = (
            top_line +
            build_line(header_text, '\n-# ', single_line_break=True) +
            build_line(main_text_translation) +
            build_line(footer_text, '-# ', single_line_break=True) +
            build_line(reblog_translation, '> ') +
            build_line(quote_translation, '> ') +
            '-# :small_blue_diamond:原文：\n' +
            build_line(header_text_en, '-# ', single_line_break=True) +
            build_line("\n\n".join(main_contents['paragraph_texts']), '-# ') +
            build_line(footer_text_en, '-# ', single_line_break=True) +
            build_line("\n\n".join(reblog_texts), "> -# ", line_break=False) +
            build_line("\n\n".join(quoted_texts), "> -# ", line_break=False)
        ).rstrip()
        logger.debug(f"Content built.")
        return trim_text_by_length(content, DISCORD_CHARACTER_LIMIT - len(inline_links) - 200) + inline_links

    def _convert_attachments(self, truth: dict):
        if not truth['media_attachments'] and not (
            truth['reblog'] and truth['reblog']['media_attachments']) and not (
            truth['quote'] and truth['quote']['media_attachments']
        ):
            logger.debug(f"No attachments found.")
            return [], []

        def get_attachment_markup(attachment: dict):
            if attachment['type'] == 'video':
                return f':small_blue_diamond: [Click here to watch the video]({attachment["url"]})'
            else:
                return f':small_blue_diamond: [Click here to view the image]({attachment["url"]})'

        discord_attachments = []
        inline_links = []
        media_attachments = truth['media_attachments']
        if truth['reblog']:
            media_attachments += truth['reblog']['media_attachments']
        if truth['quote']:
            media_attachments += truth['quote']['media_attachments']

        for attachment in media_attachments:
            logger.debug(f"Processing attachment.")
            try:
                file_url = attachment['url']
                filename = attachment['url'].split('/')[-1]
                
                head_response = requests.head(file_url)
                content_length = int(head_response.headers.get('Content-Length', 0))
                
                # If file is larger than 15MB, skip download
                if content_length > 15 * 1024 * 1024:  # 15MB in bytes
                    inline_links.append(get_attachment_markup(attachment))
                    logger.debug(f"Attachment too large, skipped. File size: {content_length/1024/1024:.2f}MB")
                    continue

                response = requests.get(file_url)
                response.raise_for_status()
                file_data = response.content

                imgur_url = None
                logger.info(f"Attachment downloaded. File size: {len(file_data)/1024/1024:.2f}MB")
                if len(file_data) > DISCORD_FILE_LIMIT:
                    if attachment['type'] in ['image', 'video']:
                        imgur_url = self._upload_to_imgur(
                            file_data, attachment['type'])
                    inline_links.append(
                        imgur_url or get_attachment_markup(attachment))
                else:
                    discord_attachments.append({
                        'filename': filename,
                        'file': file_data
                    })

            except Exception as e:
                logger.error(
                    f"Failed to handle attachment {file_url}: {str(e)}", exc_info=True)
                inline_links.append(get_attachment_markup(attachment))

        return discord_attachments, inline_links

    def _upload_to_imgur(self, file_data: bytes, file_type: str):
        try:
            if file_type == 'image':
                resp = self.imgur.upload_image(file_data, force_base64=True)
            elif file_type == 'video':
                resp = self.imgur.upload_video(file_data, force_base64=True)
            if resp['truth'] == 200:
                return resp['data']['link']
        except Exception as e:
            logger.error(f"Error uploading to imgur: {e}", exc_info=True)

        return None