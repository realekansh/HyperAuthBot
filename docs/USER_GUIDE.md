# HyperAuth User Guide

## What this does

HyperAuth is a Telegram join-request gate for protected supergroups. When you request to join a protected group, the bot sends a Mini App flow that:

1. Confirms the request is valid.
2. Shows the group rules if the owner configured them.
3. Lets you approve and continue, or decline.

## What you need

- Telegram Desktop or Telegram Mobile.
- A valid join request for a protected group.
- A live Telegram session. The verification screen will not work from a plain browser link alone.

## How to verify

1. Request to join a protected group.
2. Open the verification prompt sent by the bot.
3. Read the group rules if they are shown.
4. Scroll to the bottom if the rules page requires it.
5. Tap the confirmation button.

## What can fail

- If the verification screen says the session is unavailable, the join request expired or was already handled.
- If the app says verification failed, reopen the Mini App from Telegram so it can refresh its session data.
- If the app keeps showing an old screen, close the Mini App and open it again from the bot message.

## Common issues

- **Nothing happens when I tap verify**
  - The join request may have expired.
  - The bot may not have permission to approve joins in the group.

- **I see an error about Telegram data**
  - Reopen the Mini App from Telegram.
  - Do not use an old browser tab or a stale forwarded link.

- **I am approved but the group still looks locked**
  - Leave and rejoin the group only if the owner asks for it.
  - If the group is still blocked, the owner may need to check bot permissions.

## What group owners should tell users

- Use the Telegram prompt that the bot sends.
- Do not reuse old verification links.
- If the flow fails, reopen the prompt instead of manually editing the URL.
