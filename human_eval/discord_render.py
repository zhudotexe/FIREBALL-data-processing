"""
These functions inspired by https://github.com/Danktuary/discord-message-components
"""
import textwrap

import humanize
import markdown2


def fix(text):
    return textwrap.dedent(text).strip()


class MessageRenderer:
    def __init__(self, messages):
        self.messages = messages
        self.last_message = max(m["timestamp"] for m in messages)

    @staticmethod
    def render_markdown(md_text):
        if not md_text:
            return "<span></span>"
        inner_md = markdown2.markdown(md_text, extras=("break-on-newline", "fenced-code-blocks", "strike"))
        return f'<span class="discord-markdown">{inner_md}</span>'

    def render_embed_field(self, field_data):
        value = self.render_markdown(field_data["value"])
        inline_class = ' class="discord-embed-field-inline"' if field_data["inline"] else ""
        return fix(
            f"""
            <div class="discord-embed-field"{inline_class}>
                <div class="discord-embed-field-title">
                    {field_data["name"]}
                </div>
                {value}
            </div>
            """
        )

    def render_embed_fields(self, fields_data):
        if not fields_data:
            return ""
        fields = "\n".join(self.render_embed_field(f) for f in fields_data)
        return f'<div class="discord-embed-fields">\n{fields}\n</div>'

    def render_embed(self, embed_data):
        border_style = f"{{ 'background-color': #{embed_data.get('color', 0):0>6x} }}"

        # omitted for user privacy
        # author_data = embed_data["author"]
        # author_name = ""
        # if author_data["name"]:
        #     author_icon = ""
        #     if author_data["icon"]:
        #         author_icon = f'<img class="discord-embed-author-icon" src="{author_data["icon"]}"/>'
        #     author_name = fix(
        #         f"""
        #         <div class="discord-embed-author">
        #             {author_icon}
        #             <span>
        #                 {author_data["name"]}
        #             </span>
        #         </div>
        #         """
        #     )

        title = ""
        if embed_data.get("title"):
            title = fix(
                f"""
                <div class="discord-embed-title">
                    <span>
                        {embed_data["title"]}
                    </span>
                </div>
                """
            )

        description = self.render_markdown(embed_data["description"]) if embed_data.get("description") else ""
        fields = self.render_embed_fields(embed_data["fields"]) if embed_data.get("fields") else ""

        image = ""
        if embed_data.get("image"):
            image = f'<img class="discord-embed-image" src="{embed_data["image"]["url"]}"/>'

        thumb = ""
        if embed_data.get("thumbnail"):
            thumb = f'<img class="discord-embed-thumbnail" src="{embed_data["thumbnail"]["url"]}"/>'

        footer = ""
        if embed_data.get("footer"):
            footer_icon = ""
            if embed_data["footer"].get("icon_url"):
                footer_icon = f'<img class="discord-embed-footer-icon" src="{embed_data["footer"]["icon_url"]}"/>'
            footer_text = self.render_markdown(embed_data["footer"]["text"])
            footer = fix(
                f"""
                <div class="discord-embed-footer">
                    {footer_icon}
                    <span>
                        {footer_text}
                    </span>
                </div>
                """
            )

        return fix(
            f"""
            <div class="discord-embed">
                <div class="discord-embed-left-border" style="{border_style}"></div>
                <div class="discord-embed-container">
                    <div class="discord-embed-content">
                        <div>
                            {title}
                            <div class="discord-embed-description">
                                {description}
                            </div>
                            {fields}
                            {image}
                        </div>
                        {thumb}
                    </div>
                    {footer}
                </div>
            </div>
            """
        )

    def render_message(self, message_data):
        author_nick = message_data["author_name"]

        bot_span = ""
        if message_data.get("author_bot"):
            bot_span = fix("""<span class="discord-author-bot-tag">Bot</span>""")

        relative_timestamp = humanize.naturaltime(message_data["timestamp"] - self.last_message)

        content = self.render_markdown(message_data["content"])

        embeds = "\n".join(self.render_embed(e) for e in message_data["embeds"])

        return fix(
            f"""
            <div class="discord-message">
                <div class="discord-message-content">
                    <div class="discord-message-body">
                        <div>
                            <span class="discord-author-info">
                                <span class="discord-author-username">
                                    {author_nick}
                                </span>
                                {bot_span}
                            </span>
                            <span class="discord-message-timestamp">
                                {relative_timestamp}
                            </span>
                        </div>
                        {content}
                        {embeds}
                    </div>
                </div>
            </div>
            """
        )

    def render_messages(self):
        messages_rendered = "\n".join(self.render_message(m) for m in self.messages)
        return f'<div class="discord-messages">\n{messages_rendered}\n</div>'
