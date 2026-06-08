import os
import json
import requests
from urllib.parse import urlencode, quote


def esc(v):
    """Escape for Telegram HTML parse_mode."""
    if v is None or v == '':
        return '—'
    v_str = str(v)
    return (v_str
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;'))


def first_ip(xff):
    """Extract first IP from X-Forwarded-For header."""
    if not xff:
        return ''
    return str(xff).split(',')[0].strip()


def handler(req, res):
    """Main handler for tracking visitor data and sending to Telegram."""
    if req.method != 'POST':
        res.status(405)
        res.set_header('Allow', 'POST')
        return res.json({'error': 'Method not allowed'})

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        res.status(500)
        return res.json({'error': 'Telegram env not configured.'})

    # Client fingerprint payload
    body = req.body
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            body = {}
    if not isinstance(body, dict):
        body = {}
    c = body  # client-collected data

    # -------- Server-side request data --------
    h = req.headers or {}
    ip = first_ip(h.get('x-forwarded-for')) or h.get('x-real-ip') or (req.socket.remoteAddress if hasattr(req, 'socket') and hasattr(req.socket, 'remoteAddress') else '') or ''
    ua = h.get('user-agent') or ''
    lang = h.get('accept-language') or ''
    referer = h.get('referer') or h.get('referrer') or ''
    dnt = h.get('dnt') or ''

    # Vercel injects geo headers automatically on deployed functions (free)
    country = h.get('x-vercel-ip-country') or ''
    region = h.get('x-vercel-ip-country-region') or ''
    city = h.get('x-vercel-ip-city') or ''
    lat = h.get('x-vercel-ip-latitude') or ''
    lon = h.get('x-vercel-ip-longitude') or ''
    isp = ''

    # Fallback geo (local dev or missing headers) via free ip-api.com
    private_ip_pattern = r'^(127\.|::1|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)'
    import re
    if not country and ip and not re.match(private_ip_pattern, ip):
        try:
            geo_url = f'http://ip-api.com/json/{quote(ip)}?fields=status,country,regionName,city,lat,lon,isp,query'
            geo_response = requests.get(geo_url, timeout=5)
            if geo_response.status_code == 200:
                geo_data = geo_response.json()
                if geo_data and geo_data.get('status') == 'success':
                    country = country or geo_data.get('country', '')
                    region = region or geo_data.get('regionName', '')
                    city = city or geo_data.get('city', '')
                    lat = lat or geo_data.get('lat', '')
                    lon = lon or geo_data.get('lon', '')
                    isp = geo_data.get('isp', '')
        except Exception:
            pass  # geo best-effort

    try:
        city = quote(city, safe='')
    except Exception:
        pass  # keep raw

    try:
        region = quote(region, safe='')
    except Exception:
        pass  # keep raw

    map_link = f'https://maps.google.com/?q={lat},{lon}' if lat and lon else ''

    # -------- Build Telegram message (HTML) --------
    lines = []
    lines.append('🔔 <b>New Visitor To Website</b>')
    lines.append('')
    lines.append('🌐 <b>Network</b>')
    lines.append('• IP: <code>' + esc(ip) + '</code>')
    if c.get('webrtcIps'):
        lines.append('• WebRTC/local IPs: <code>' + esc(c.get('webrtcIps')) + '</code>')
    location_parts = [city, region, country]
    location_str = ', '.join(p for p in location_parts if p)
    lines.append('• Location: ' + esc(location_str))
    if isp:
        lines.append('• ISP: ' + esc(isp))
    if map_link:
        lines.append('• Map: <a href="' + esc(map_link) + '">' + esc(f'{lat},{lon}') + '</a>')

    if c.get('connection'):
        n = c.get('connection')
        conn_str = esc(n.get('effectiveType', '')) + ' · ' + esc(n.get('downlink', '')) + 'Mbps'
        if n.get('downlinkMax'):
            conn_str += '/' + esc(n.get('downlinkMax', '')) + 'max'
        conn_str += ' · rtt ' + esc(n.get('rtt', '')) + 'ms'
        if n.get('type'):
            conn_str += ' · ' + esc(n.get('type', ''))
        if n.get('saveData'):
            conn_str += ' · saveData'
        lines.append('• Conn: ' + conn_str)

    if c.get('perf'):
        p = c.get('perf')
        perf_str = ('• Timing: ttfb ' + esc(p.get('ttfb', '')) + 'ms · dns ' + esc(p.get('dns', '')) +
                    'ms · tcp ' + esc(p.get('tcp', '')) + 'ms · dom ' + esc(p.get('domLoad', '')) + 'ms')
        lines.append(perf_str)

    lines.append('')
    lines.append('💻 <b>Device / Browser</b>')
    lines.append('• UA: <code>' + esc(ua) + '</code>')
    if c.get('uaData'):
        lines.append('• Hints: ' + esc(c.get('uaData')))
    if c.get('uaHighEntropy'):
        u = c.get('uaHighEntropy')
        lines.append('• UA-full: ' + esc(u.get('brands') or u.get('uaFullVersion', '')))
        arch_str = esc(u.get('arch', '')) + ' ' + esc(u.get('bitness', ''))
        if u.get('wow64'):
            arch_str += ' wow64'
        lines.append('• Arch: ' + arch_str + ' · Model: ' + esc(u.get('model', '')) +
                     ' · OS: ' + esc(u.get('platformVersion', '')))

    lines.append('• Platform: ' + esc(c.get('platform', '')) + ' · Vendor: ' +
                 esc(c.get('vendor', '')) + ((' · ' + esc(c.get('oscpu', ''))) if c.get('oscpu') else ''))
    lines.append('• CPU cores: ' + esc(c.get('cores', '')) + ' · RAM: ' + esc(c.get('ram', '')) + 'GB')
    if c.get('jsHeap'):
        lines.append('• JS heap: ' + esc(c.get('jsHeap', {}).get('used', '')) + '/' +
                     esc(c.get('jsHeap', {}).get('limit', '')) + 'MB')
    if c.get('storage'):
        lines.append('• Storage: ' + esc(c.get('storage', {}).get('usedMB', '')) + 'MB used / ' +
                     esc(c.get('storage', {}).get('quotaGB', '')) + 'GB quota')
    lines.append('• Touch points: ' + esc(c.get('touch', '')))
    lines.append('• Languages: ' + esc(c.get('languages') or lang) + ' · Locale: ' + esc(c.get('locale', '')))
    lines.append('• Timezone: ' + esc(c.get('timezone', '')) + ' (offset ' + esc(c.get('tzOffset', '')) + ')')
    lines.append('• Screen: ' + esc(c.get('screen', '')) + ' (avail ' + esc(c.get('availScreen', '')) +
                 ') · Viewport: ' + esc(c.get('viewport', '')) + ' · DPR ' + esc(c.get('dpr', '')))
    if c.get('outerWindow'):
        window_str = '• Window: ' + esc(c.get('outerWindow', '')) + ' @ ' + esc(c.get('screenPos', ''))
        if c.get('orientation'):
            window_str += ' · ' + esc(c.get('orientation', ''))
        lines.append(window_str)

    lines.append('• Color depth: ' + esc(c.get('colorDepth', '')) + '/' + esc(c.get('pixelDepth', '')) +
                 ' · Dark mode: ' + esc(c.get('darkMode', '')))
    lines.append('• cookies=' + esc(c.get('cookieEnabled', '')) + ' · DNT=' + esc(c.get('doNotTrack', '')) +
                 ' · pdf=' + esc(c.get('pdfViewer', '')) + ' · plugins=' + esc(c.get('plugins', '')))
    if c.get('keyboardLayout'):
        lines.append('• Keyboard: ' + esc(c.get('keyboardLayout')))
    if c.get('permissions'):
        lines.append('• Permissions: ' + esc(c.get('permissions')))
    if c.get('battery'):
        battery_str = '• Battery: ' + esc(c.get('battery', {}).get('level', '')) + '% '
        if c.get('battery', {}).get('charging'):
            battery_str += '(charging)'
        else:
            battery_str += '(on battery)'
        lines.append(battery_str)

    lines.append('')
    lines.append('🧬 <b>Fingerprint</b>')
    lines.append('• Persistent ID: <code>' + esc(c.get('persistentId', '')) + '</code>')
    gpu_str = esc(c.get('gpu', ''))
    if c.get('glVersion'):
        gpu_str += ' · ' + esc(c.get('glVersion', ''))
    if c.get('glMaxTexture'):
        gpu_str += ' · maxTex ' + esc(c.get('glMaxTexture', ''))
    if c.get('glExts'):
        gpu_str += ' · ' + esc(c.get('glExts', ''))
    lines.append('• GPU: ' + gpu_str)
    lines.append('• Canvas: <code>' + esc(c.get('canvasHash', '')) + '</code> · Audio: <code>' +
                 esc(c.get('audioHash', '')) + '</code> · Math: <code>' + esc(c.get('mathHash', '')) + '</code>')
    if c.get('fonts'):
        lines.append('• Fonts: ' + esc(c.get('fonts')))
    if c.get('voices'):
        lines.append('• Voices: ' + esc(c.get('voices')))
    if c.get('codecs'):
        cd = c.get('codecs')
        lines.append('• Codecs: h264=' + esc(cd.get('h264', '')) + ' av1=' + esc(cd.get('av1', '')) +
                     ' hevc=' + esc(cd.get('hevc', '')) + ' webm=' + esc(cd.get('webm', '')))
    if c.get('features'):
        f = c.get('features')
        display_str = ('• Display: gamut=' + esc(f.get('gamut', '')) + ' hdr=' + esc(f.get('hdr', '')) +
                       ' pointer=' + esc(f.get('pointer', '')) + ' hover=' + esc(f.get('hover', '')) +
                       ' contrast=' + esc(f.get('contrast', '')))
        if f.get('reducedMotion'):
            display_str += ' reduced-motion'
        if f.get('forcedColors'):
            display_str += ' forced-colors'
        if f.get('invertedColors'):
            display_str += ' inverted'
        if f.get('monochrome'):
            display_str += ' monochrome'
        lines.append(display_str)
    if c.get('webdriver'):
        lines.append('• ⚠️ Automation/bot flag: true')

    lines.append('')
    lines.append('📄 <b>Visit</b>')
    lines.append('• Page: ' + esc(c.get('page', '')) + (' — ' + esc(c.get('title', '')) if c.get('title') else ''))
    lines.append('• Referrer: ' + esc(referer or c.get('referrer', '')))
    if dnt:
        lines.append('• DNT header: ' + esc(dnt))

    text = '\n'.join(lines)[:4000]  # Telegram 4096 char cap

    try:
        tg_url = f'https://api.telegram.org/bot{token}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        tg_response = requests.post(
            tg_url,
            json=payload,
            timeout=10
        )
        if tg_response.status_code != 200:
            detail = tg_response.text[:300]
            res.status(502)
            return res.json({'error': 'Telegram error', 'detail': detail})
        res.status(200)
        return res.json({'ok': True})
    except Exception as err:
        res.status(500)
        return res.json({'error': 'Request failed', 'detail': str(err)[:300]})
