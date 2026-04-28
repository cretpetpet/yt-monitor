import subprocess
import json
import os
import sys
import webbrowser
from datetime import datetime

# ── paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CHANNELS    = os.path.join(BASE_DIR, "channels.txt")
SEEN_FILE   = os.path.join(BASE_DIR, "seen.json")
OUTPUT_HTML = os.path.join(BASE_DIR, "results.html")

# ── load / save seen IDs ───────────────────────────────────────────────────────
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f)

# ── fetch comments via yt-dlp ─────────────────────────────────────────────────
def fetch_channel(channel_url):
    print(f"  DEBUG: skipping video list, testing 2 hardcoded videos")
    
    video_ids = ["EvsVVOk7gFg", "Fx5wWHSYNwE"]  # from your earlier test
    entries = []

    for i, vid_id in enumerate(video_ids, 1):
        vid_url = f"https://www.youtube.com/watch?v={vid_id}"
        cmd = [
            "yt-dlp",
            "--write-comments",
            "--skip-download",
            "--no-warnings",
            "-J",
            vid_url
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            data = json.loads(result.stdout)
            comments = data.get("comments", []) or []
            print(f"  [{i}/2] returncode={result.returncode} comments={len(comments)}")
            print(f"  stderr: {result.stderr[:300]}")
        except Exception as e:
            print(f"  [error] {e}")
            continue

        vid_title = data.get("title", "Unknown")
        for c in comments:
            entries.append({
                "video_id":    vid_id,
                "video_title": vid_title,
                "video_url":   vid_url,
                "comment_id":  c.get("id", ""),
                "author":      c.get("author", "Unknown"),
                "text":        c.get("text", ""),
                "timestamp":   c.get("timestamp", 0),
            })

    return entries

# ── build HTML ─────────────────────────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YT Comment Monitor — {run_date}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

  :root {{
    --bg:        #0f0f0f;
    --bg2:       #161616;
    --bg3:       #1e1e1e;
    --border:    #2a2a2a;
    --text:      #e0e0e0;
    --muted:     #666;
    --accent:    #f5a623;
    --new-bg:    #1a1400;
    --new-border:#f5a623;
    --new-badge: #f5a623;
    --link:      #6ab0ff;
    --mono:      'IBM Plex Mono', monospace;
    --sans:      'IBM Plex Sans', sans-serif;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    font-size: 14px;
    line-height: 1.6;
    padding: 32px 24px;
    max-width: 900px;
    margin: 0 auto;
  }}

  header {{
    border-bottom: 1px solid var(--border);
    padding-bottom: 20px;
    margin-bottom: 32px;
  }}

  header h1 {{
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 6px;
  }}

  header .meta {{
    font-family: var(--mono);
    font-size: 12px;
    color: var(--muted);
  }}

  header .meta span {{ color: var(--text); }}

  .summary {{
    display: flex;
    gap: 24px;
    margin-top: 16px;
  }}

  .stat {{
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }}

  .stat strong {{
    display: block;
    font-size: 22px;
    color: var(--text);
    font-weight: 600;
    letter-spacing: 0;
    line-height: 1.2;
  }}

  .stat.highlight strong {{ color: var(--accent); }}

  .video-block {{
    margin-bottom: 40px;
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
  }}

  .video-header {{
    background: var(--bg2);
    padding: 14px 18px;
    display: flex;
    align-items: baseline;
    gap: 10px;
    border-bottom: 1px solid var(--border);
  }}

  .video-header a {{
    font-weight: 600;
    font-size: 14px;
    color: var(--link);
    text-decoration: none;
  }}

  .video-header a:hover {{ text-decoration: underline; }}

  .video-header .count {{
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted);
    margin-left: auto;
    white-space: nowrap;
  }}

  .comment {{
    padding: 14px 18px;
    border-bottom: 1px solid var(--border);
    position: relative;
  }}

  .comment:last-child {{ border-bottom: none; }}

  .comment.is-new {{
    background: var(--new-bg);
    border-left: 3px solid var(--new-border);
    padding-left: 15px;
  }}

  .comment-meta {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
  }}

  .author {{
    font-weight: 500;
    font-size: 13px;
    color: var(--text);
  }}

  .ts {{
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted);
  }}

  .badge-new {{
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    background: var(--new-badge);
    color: #000;
    padding: 2px 7px;
    border-radius: 3px;
    text-transform: uppercase;
  }}

  .comment-link {{
    margin-left: auto;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted);
    text-decoration: none;
  }}

  .comment-link:hover {{ color: var(--link); }}

  .comment-text {{
    font-size: 14px;
    color: var(--text);
    line-height: 1.65;
    word-break: break-word;
  }}

  .empty {{
    text-align: center;
    padding: 80px 20px;
    font-family: var(--mono);
    color: var(--muted);
    font-size: 13px;
  }}

  .empty strong {{ display: block; color: var(--text); font-size: 18px; margin-bottom: 8px; }}

  .channel-label {{
    font-family: var(--mono);
    font-size: 10px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    padding: 8px 18px;
    background: var(--bg3);
    border-bottom: 1px solid var(--border);
  }}
</style>
</head>
<body>

<header>
  <h1>// YT Comment Monitor</h1>
  <div class="meta">Last run: <span>{run_date}</span></div>
  <div class="summary">
    <div class="stat highlight"><strong>{new_count}</strong>new comments</div>
    <div class="stat"><strong>{total_count}</strong>total fetched</div>
    <div class="stat"><strong>{video_count}</strong>videos scanned</div>
    <div class="stat"><strong>{channel_count}</strong>channels</div>
  </div>
</header>

{body}

</body>
</html>"""

def format_ts(ts):
    if not ts:
        return ""
    try:
        return datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d")
    except:
        return ""

def comment_link(video_url, comment_id):
    return f"{video_url}&lc={comment_id}"

def build_html(video_blocks, new_count, total_count, channel_count):
    run_date   = datetime.now().strftime("%Y-%m-%d %H:%M")
    video_count = len(video_blocks)

    if not video_blocks:
        body = '<div class="empty"><strong>Nothing new.</strong>All comments already seen.</div>'
    else:
        parts = []
        for vb in video_blocks:
            channel_html = f'<div class="channel-label">{vb["channel"]}</div>'
            new_c  = [c for c in vb["comments"] if c["is_new"]]
            old_c  = [c for c in vb["comments"] if not c["is_new"]]
            ordered = new_c + old_c  # new on top

            new_label = f' — <span style="color:var(--accent);font-size:12px;">{len(new_c)} new</span>' if new_c else ''
            header = (
                f'<div class="video-header">'
                f'<a href="{vb["video_url"]}" target="_blank">{vb["video_title"]}</a>'
                f'{new_label}'
                f'<span class="count">{len(vb["comments"])} comments</span>'
                f'</div>'
            )

            comments_html = ""
            for c in ordered:
                cls    = "comment is-new" if c["is_new"] else "comment"
                badge  = '<span class="badge-new">new</span>' if c["is_new"] else ''
                ts_str = format_ts(c["timestamp"])
                clink  = comment_link(vb["video_url"], c["comment_id"])
                comments_html += (
                    f'<div class="{cls}">'
                    f'  <div class="comment-meta">'
                    f'    <span class="author">{c["author"]}</span>'
                    f'    {badge}'
                    f'    <span class="ts">{ts_str}</span>'
                    f'    <a class="comment-link" href="{clink}" target="_blank">↗ view</a>'
                    f'  </div>'
                    f'  <div class="comment-text">{c["text"]}</div>'
                    f'</div>'
                )

            parts.append(
                f'<div class="video-block">'
                f'{channel_html}{header}{comments_html}'
                f'</div>'
            )
        body = "\n".join(parts)

    return HTML_TEMPLATE.format(
        run_date=run_date,
        new_count=new_count,
        total_count=total_count,
        video_count=video_count,
        channel_count=channel_count,
        body=body,
    )

# ── main ───────────────────────────────────────────────────────────────────────
def main():   
    if not os.path.exists(CHANNELS):
        print("[error] channels.txt not found. Add one YouTube channel URL per line.")
        input("Press Enter to exit...")
        sys.exit(1)

    with open(CHANNELS, "r", encoding="utf-8") as f:
        channels = [l.strip() for l in f if l.strip() and not l.startswith("#")]

    if not channels:
        print("[error] channels.txt is empty.")
        input("Press Enter to exit...")
        sys.exit(1)

    first_run = not os.path.exists(SEEN_FILE)
    seen = load_seen()
    print(f"Loaded {len(seen)} previously seen comment IDs.\n")

    all_entries = []   # flat list of all comment dicts with channel name

    for ch in channels:
        entries = fetch_channel(ch)
        # tag with channel name (derive from URL or use URL itself)
        ch_name = ch.split("/")[-1] if "/" in ch else ch
        for e in entries:
            e["channel"] = ch_name
        all_entries.extend(entries)
        print(f"  → {len(entries)} comments fetched\n")

    # mark new / old
    new_ids = set()
    for e in all_entries:
        e["is_new"] = first_run or e["comment_id"] not in seen
        if e["is_new"]:
            new_ids.add(e["comment_id"])

    # group by video
    video_map = {}
    for e in all_entries:
        key = e["video_id"]
        if key not in video_map:
            video_map[key] = {
                "video_id":    e["video_id"],
                "video_title": e["video_title"],
                "video_url":   e["video_url"],
                "channel":     e["channel"],
                "comments":    [],
            }
        video_map[key]["comments"].append(e)

    # only include videos that have at least one new comment
    video_blocks = [v for v in video_map.values() if any(c["is_new"] for c in v["comments"])]

    new_count   = len(new_ids)
    total_count = len(all_entries)

    print(f"Total comments fetched : {total_count}")
    print(f"New comments this run  : {new_count}")
    print(f"Videos with new comments: {len(video_blocks)}\n")

    html = build_html(video_blocks, new_count, total_count, len(channels))

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    # update seen
    seen.update(e["comment_id"] for e in all_entries)
    save_seen(seen)

    print(f"Results saved to: {OUTPUT_HTML}")
    webbrowser.open(f"file:///{OUTPUT_HTML.replace(os.sep, '/')}")

if __name__ == "__main__":
    main()
