import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import re

from pyrogram import Client, filters

from db import init_db, upsert_stat

#Enter the data from the website https://my.telegram.org/apps
API_ID = "API ID"        
API_HASH = "API HASH"      
TARGET_CHAT = "Telegram CHAT"    


app = Client("my_userbot", api_id=API_ID, api_hash=API_HASH)


def parse_message(text):
    parts = [p.strip() for p in text.split(":")]
    geo = parts[0] if len(parts) > 0 else ""
    event_type = parts[1] if len(parts) > 1 else ""
    amount = parts[2] if len(parts) > 2 else ""
    token_segment = parts[3] if len(parts) > 3 else ""

    m = re.match(r"^(.*?)(\d+)(.*)$", token_segment)
    if m:
        token_id = m.group(2)
        token_name = " ".join(p for p in (m.group(1), m.group(3)) if p)
    else:
        token_id = ""
        token_name = token_segment

    return geo, event_type, amount, token_id, token_name


@app.on_message(filters.chat(TARGET_CHAT) & filters.text)
async def handle_message(client, message):
    text = message.text
    geo, event_type, amount, token_id, token_name = parse_message(text)
    upsert_stat(
        token_id=token_id,
        token_name=token_name,
        event_type=event_type,
        geo=geo,
    )
    print(
        f"Saved: geo={geo!r} | event_type={event_type!r} | "
        f"amount={amount!r} | token_id={token_id!r} | token_name={token_name!r}"
    )
    print(f"Counter incremented: token_id={token_id!r}, token_name={token_name!r}")


def main():
    init_db()
    print("Userbot started. Press Ctrl+C to stop.")
    app.run()


if __name__ == "__main__":
    main()
