from datetime import datetime, timezone
import logging
import os
from time import sleep
from discord_webhook import DiscordWebhook
from dotenv import load_dotenv

from .truthsocial import TruthSocial
from .truthbuilder import TruthBuilder
from .utils import setup_logging

load_dotenv()

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
TRUTH_USER = os.getenv('TRUTHSOCIAL_USER')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
TRUTHSOCIAL_RATE_LIMIT = int(os.getenv('TRUTHSOCIAL_RATE_LIMIT', 60))


setup_logging(LOG_LEVEL)

logger = logging.getLogger(__name__)

if not TRUTH_USER or not DISCORD_WEBHOOK_URL:
    raise ValueError('TRUTH_USER and DISCORD_WEBHOOK_URL must be set in .env')


class TruthCord():
    def __init__(self, pull_since: datetime = datetime.now(timezone.utc)) -> None:
        logger.info("TruthCord initializing...")
        self.truth_user: str = TRUTH_USER
        self.discord_webhook_url: str = DISCORD_WEBHOOK_URL
        self.rate_limit: int = TRUTHSOCIAL_RATE_LIMIT
        self.last_pull: datetime = pull_since
        self.truth_social = TruthSocial()
        self.truth_builder = TruthBuilder()
        logger.info("TruthCord initialized.")
        logger.info(f"Set to monitor posts from {self.truth_user} published since {self.last_pull}.")
        
    def run(self) -> None:
        logger.info("TruthCord running...")
        while True:
            self.check_truth()
            sleep(self.rate_limit)

    def check_truth(self) -> None:
        posts = self._fetch_new_posts()
        self._process_posts(posts)

    def _fetch_new_posts(self) -> list:
        posts = []
        try:
            for post in self.truth_social.pull_statuses(self.truth_user, created_after=self.last_pull):
                posts.append(post)
        except Exception as e:
            logger.error(f"Error fetching new posts: {e}", exc_info=True)
        return posts

    def _process_posts(self, posts: list) -> None:
        success = 0
        for post in posts[::-1]:
            if self._process_single_post(post):
                success += 1
        logger.info(f"Found {len(posts)} new posts, sent {success} to Discord.")

    def _process_single_post(self, post: dict) -> bool:
        try:
            content, files = self.truth_builder.build_truth(post)
            self.last_pull = datetime.now(timezone.utc)
            self._send_to_discord(post, content, files)
            return True
        except Exception as e:
            logger.error(f"Error building truth for {self.truth_user}: {e}", exc_info=True)
            return False

    def _send_to_discord(self, post: dict, content: str, files: list) -> None:
        webhook = self._create_webhook(post, content, files)
        webhook.execute()
        logger.info(f"New post sent.")

    def _create_webhook(self, post: dict, content: str, files: list) -> DiscordWebhook:
        webhook = DiscordWebhook(
            url=self.discord_webhook_url,
            username=post['account']['display_name'],
            content=content
        )
        for file in files:
            webhook.add_file(file['file'], file['filename'])
        return webhook
        