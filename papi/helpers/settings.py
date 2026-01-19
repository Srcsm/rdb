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
    def build_embed(self, settings: dict, title: str, wrap: int = 40) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            color=discord.Color.blurple()
        )

        for group_name, keys in self.groups.items():
            embed.add_field(
                name=f"__{group_name}__",
                value="\u200b",
                inline=False
            )

            for key in keys:
                value = settings.get(key)
                if isinstance(value, (list, dict)):
                    value = str(value)

                wrapped = self._wrap_value(str(value), wrap)

                embed.add_field(
                    name=key,
                    value=wrapped or "None",
                    inline=True
                )
        return embed

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
        "api_url", "allowed_roles", "debug"
    ],
    "Embed Settings": [
        "footer_name", "footer_icon",
        "embed_value_title", "embed_context_title", "embed_placeholder_title"
    ],
    "Watch Settings": [
        "watch_enabled", "watch_mode", "watch_strict_mode",
        "watch_channels", "watch_cooldown", "watch_max_placeholders",
        "watch_reply_type", "watch_show_errors",
        "watch_require_roles", "watch_delete_trigger"
    ]
}
