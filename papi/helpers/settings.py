import discord

class SettingsFormatter:
    def __init__(self, groups: dict, columns: int = 3):
        self.groups = groups
        self.columns = columns

    # Console friendly table of current settings
    def format_console(self, settings: dict) -> list[str]:
        lines = []

        for group_name, keys in self.groups.items():
            lines.append(f"--- {group_name} ---")
            items = [f"{k}: {settings.get(k)}" for k in keys]
            rows = (len(items) + self.columns - 1) // self.columns

            table = []
            for r in range(rows):
                row = []
                for c in range(self.columns):
                    idx = r + c * rows
                    if idx < len(items):
                        row.append(items[idx])
                table.append(row)

            col_widths = []
            for c in range(self.columns):
                col_items = [table[r][c] for r in range(rows) if c < len(table[r])]
                col_widths.append(max(len(item) for item in col_items) if col_items else 0)

            for row in table:
                padded = [
                    item.ljust(col_widths[i])
                    for i, item in enumerate(row)
                ]
                lines.append("   ".join(padded))

            lines.append("")

        return lines

    # Embed friendly table of current settings
    def build_embed(self, settings: dict, title: str | None, wrap: int = 40) -> discord.Embed:
        embed = discord.Embed(
            description=f"## {title}\n" if title else "",
            color=discord.Color.blurple()
        )

        for group_name, keys in self.groups.items():
            embed.add_field(
                name="\u200b",
                value=f"__**{group_name}:**__",
                inline=False
            )

            for key in keys:
                value = settings.get(key)
                if isinstance(value, (list, dict)):
                    value = str(value)

                wrapped = self._wrap_value(str(value), wrap)
                formatted_key = self._format_key(key, group_name)

                embed.add_field(
                    name=formatted_key,
                    value=f"`{wrapped}`" or "`None`",
                    inline=True
                )
        return embed

    def _format_key(self, key: str, group_name: str) -> str:
        prefix = group_name.split()[0].lower()
        if key.startswith(prefix + "_"):
            key = key[len(prefix) + 1:]
        return key.replace("_", " ").title()

    def _wrap_value(self, text: str, width: int) -> str:
        if len(text) <= width:
            return text

        parts = []
        while len(text) > width:
            parts.append(text[:width])
            text = text[width:]
        parts.append(text)
        return "\n".join(parts)



SETTINGS_TABLE = {
    "Core Settings": [
        "debug", "api_url",
        "allowed_roles"
    ],
    "Embed Settings": [
        "embed_placeholder_title", "embed_context_title", "embed_value_title",
        "footer_name", "footer_icon"
    ],
    "Watch Settings": [
        "watch_enabled", "watch_mode", "watch_strict_mode",
        "watch_cooldown", "watch_reply_type", "watch_max_placeholders",
        "watch_require_roles", "watch_delete_trigger", "watch_show_errors",
        "watch_channels"
    ]
}
