def format_settings(settings: dict, groups: dict, columns: int = 3) -> list[str]:
    lines = []
    for group_name, keys in groups.items():
        lines.append(f"--- {group_name} ---")

        # Make key: value pairs
        items = [f"{k}: {settings.get(k)}" for k in keys]

        # Determine rows
        rows = (len(items) + columns - 1) // columns

        # Make table
        table = []
        for r in range(rows):
            row = []
            for c in range(columns):
                idx = r + c * rows
                if idx < len(items):
                    row.append(items[idx])
            table.append(row)
            
        # Get column widths
        col_widths = []
        for c in range(columns):
            col_items = [table[r][c] for r in range(rows) if c < len(table[r])]
            if col_items:
                col_widths.append(max(len(item) for item in col_items))
            else:
                col_widths.append(0)

        # Format aligned rows
        for row in table:
            padded = [
                item.ljust(col_widths[i])
                for i, item in enumerate(row)
            ]
            lines.append("   ".join(padded))

        lines.append("")  # blank line between groups

    return lines

groups = {
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
