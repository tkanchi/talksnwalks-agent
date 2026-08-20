# talksnwalks-agent

Automated Instagram publishing pipeline for **@talksnwalks101**.

## What the agent now does

`365 quote database -> approved illustration -> branded 9:16 image -> 8-second Reel -> fallback ambient audio -> public media URL -> Meta Instagram API -> publish`

No OpenAI API key is required. The pipeline uses the 12 approved illustration PNGs and deterministic Pillow layout code.

## Brand contract

Every Reel uses a 1080 x 1920 pure-white frame with:

1. One-line centered serif quote
2. Large black-and-white hand-drawn illustration
3. `@talksnwalks101` centered below the illustration
4. Large negative space and no extra visual clutter

## Required illustration files

Create an `illustrations/` folder in the repository and add these exact files:

```text
reading_01.png
reading_02.png
dancing_01.png
dancing_02.png
music_01.png
music_02.png
workout_01.png
workout_02.png
sleeping_01.png
sleeping_02.png
laughing_01.png
laughing_02.png
```

The workflow will stop rather than substitute an unapproved illustration if one is missing.

## Fallback audio

`build_reel.py` creates a quiet original ambient pad and embeds it into the MP4. This avoids copyright/licensing dependencies and ensures every automatically published Reel has audio.

Instagram's publishing API does not expose Instagram's native music/trending-audio library for choosing a song during API publishing. If a native trending song is important on a particular day, that remains a manual Instagram step.

## Meta requirements

Use an Instagram Professional account connected to your Meta app. The Facebook Login publishing flow requires an access token with the appropriate Instagram publishing permissions and the Instagram professional account ID.

Add these **GitHub repository secrets**:

- `IG_USER_ID` — the numeric Instagram Professional Account ID
- `META_ACCESS_TOKEN` — a valid Meta access token that can publish for that account

The automation currently defaults to Graph API `v23.0`. Change `META_API_VERSION` in the workflows later if you migrate API versions.

## Verify Meta before publishing

In GitHub:

1. Open **Actions**
2. Choose **Meta Connection Check**
3. Click **Run workflow**
4. Open the run log

A successful run prints the Instagram username/account type and attempts to read the content publishing limit.

## Test without publishing

Go to **Actions -> Daily Instagram Reel -> Run workflow**.

Enter a day such as `1` and leave **Actually publish to Instagram** unchecked.

The run will build the JPG, original fallback audio, and MP4 and upload them as a GitHub Actions artifact without posting to Instagram.

## Test a real Meta publish

After the Meta Connection Check succeeds:

1. Run **Daily Instagram Reel** manually
2. Enter the day you want to test
3. Check **Actually publish to Instagram**

The action will:

1. Build the Reel
2. Commit that MP4 to `public/`
3. Construct a stable public `raw.githubusercontent.com` URL
4. Ask Meta to create a Reel media container
5. Poll until Meta reports the container is ready
6. Call `/media_publish`
7. Save the returned media ID in `published_logs/`

## Daily schedule

The workflow starts at **02:25 UTC / 07:55 IST** each day so the media build and Meta processing can finish around the target **08:00 AM IST** posting time.

GitHub scheduled workflows are not guaranteed to start at the exact cron second, so the actual publication time can occasionally be a few minutes later.

The campaign start date is:

```text
2026-08-21
```

The script automatically maps the current India date to Day 1-365. After Day 365 it produces no new campaign post.

## Local test

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

Install `ffmpeg`, then place all 12 PNGs in `illustrations/` and run:

```bash
set DAY_NUMBER=1
python build_reel.py
```

On macOS/Linux use `export DAY_NUMBER=1` instead.

Output:

- `outputs/day_001.jpg`
- `outputs/day_001_fallback.wav`
- `outputs/caption.txt`
- `public/day_001.mp4`

## Important publishing constraint

Meta must be able to fetch the Reel from a public URL during publishing. The current workflow therefore commits each generated MP4 into this public GitHub repository immediately before calling Meta. If the repository becomes private, replace this media-hosting step with another publicly reachable storage solution or a supported direct-upload flow.
