import os
import sys
from timeit import default_timer as timer
from datetime import datetime, timedelta

from mkdocs import utils as mkdocs_utils
from mkdocs.config import config_options, Config
from mkdocs.plugins import BasePlugin
from mkdocs.utils import copy_file

cur_dir = os.path.dirname(os.path.abspath(__file__))

class ChatPlugin(BasePlugin):

    config_scheme = (
        ('param', config_options.Type(str, default='')),
    )

    def __init__(self):
        self.enabled = True
        self.total_time = 0

    def on_post_build(self, config, **kwargs):
        """
        The post_build event does not alter any variables. Use this event to call post-build scripts.
        See https://www.mkdocs.org/user-guide/plugins/#on_post_build.
        """

        # Add mkdocs-charts-plugin.js
        js_output_base_path = os.path.join(config["site_dir"], "js")
        css_output_base_path = os.path.join(config["site_dir"], "css")
        js_file_path = os.path.join(js_output_base_path, "mkdocs-charts-plugin.js")

        copy_file(
            os.path.join(os.path.join(cur_dir, "js"), "chat-dialog-plugin.js"),
            os.path.join(js_output_base_path, "chat-dialog-plugin.js"),
        )

        copy_file(
            os.path.join(os.path.join(cur_dir, "js"), "chat-dialog-plugin.css"),
            os.path.join(css_output_base_path, "chat-dialog-plugin.css"),
        )

    def on_post_page(self, html, page, config):
        plugin_config = self.config.copy()

        if page.url == '/':
            relative_path = './'
        else:
            relative_path = '../'
        link = f'''
  <link rel="stylesheet" href="{relative_path}css/chat-dialog-plugin.css">
'''
        idx = html.index("</head>")
        html = html[:idx] + link + html[idx:]

        plugin = f"""
<script>
console.log("hello, plugin")
var mkdocs_chat_plugin = {plugin_config};
</script>
<script src="{relative_path}js/chat-dialog-plugin.js"></script>

        """
        idx = html.index("</body>")
        html = html[:idx] + plugin + html[idx:]
        return html

