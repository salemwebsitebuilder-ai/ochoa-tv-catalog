"""Weekly health check for the Ochoa TV catalog (read-only).

Checks the ACTIVE release (manifest.json -> catalog-<version>.json):
  - every enabled HLS live channel: manifest downloads and starts with #EXTM3U
  - every enabled on-demand row: its public YouTube RSS feed returns entries
YouTube live channels are not checked (they are only live part of the day).
Writes health-report.md and exits 0; the workflow opens/updates/closes an
issue based on the "FAILURES:" count. Never modifies the catalog.
"""
import json
import time
import urllib.request

UA = 'Mozilla/5.0 (OchoaTV catalog health check)'


def get(url, timeout=20, limit=300_000):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read(limit).decode('utf-8', 'replace')


def retry(fn, tries=3):
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa
            last = e
            time.sleep(3 * (i + 1))
    raise last


def main():
    manifest = json.load(open('manifest.json', encoding='utf-8'))
    cat = json.load(open(manifest['catalog'], encoding='utf-8'))
    fails, lines = [], [f"# Catalog health: release {manifest['version']}", '', f"Checked {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}", '']

    lines += ['## Live channels (HLS)', '']
    for c in cat['channels']:
        pb = c.get('playback', {})
        if not c.get('enabled') or pb.get('type') != 'hls':
            continue
        try:
            code, body = retry(lambda: get(pb['url'], 15))
            ok = body.lstrip().startswith('#EXTM3U')
            note = f'HTTP {code}' + ('' if ok else ', not a playlist')
        except Exception as e:  # noqa
            ok, note = False, type(e).__name__ + (f' {getattr(e, "code", "")}' if hasattr(e, 'code') else '')
        lines.append(f"- {'✅' if ok else '❌'} {c['name']} ({note})")
        if not ok:
            fails.append(f"live channel **{c['name']}** (`{c['id']}`): {note}")

    lines += ['', '## On-demand rows (YouTube RSS)', '']
    feed_errors = 0
    rows = [s for s in cat['shows'] if s.get('enabled')]
    for s in rows:
        src = s['source']
        q = f"playlist_id={src['id']}" if src['type'] == 'playlist' else f"channel_id={src['id']}"
        try:
            _, x = retry(lambda: get(f'https://www.youtube.com/feeds/videos.xml?{q}'))
            n = x.count('<entry>')
            ok, note = n > 0, f'{n} videos'
        except Exception as e:  # noqa
            ok, note = False, type(e).__name__ + (f' {getattr(e, "code", "")}' if hasattr(e, 'code') else '')
            feed_errors += 1
        lines.append(f"- {'✅' if ok else '❌'} {s['title']} ({note})")
        if not ok:
            fails.append(f"row **{s['title']}** (`{s['id']}`): {note}")
        time.sleep(1)

    # If most feeds fail at once, YouTube is probably throttling the runner, not the catalog.
    if rows and feed_errors > len(rows) / 2:
        lines += ['', f'⚠️ {feed_errors}/{len(rows)} feeds failed at once. Likely YouTube throttling the '
                  'GitHub runner rather than broken rows. Re-run before acting.']
    lines += ['', f'FAILURES: {len(fails)}', '']
    if fails:
        lines += ['## Needs attention', ''] + [f'- {f}' for f in fails]
        lines += ['', 'Fix or disable these in the app project (src/data/*.json), then publish a new release with '
                  '`tools/catalog/publish.py`. This check never changes the catalog itself.']
    open('health-report.md', 'w', encoding='utf-8').write('\n'.join(lines))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
