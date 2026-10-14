"""Template tags for rendering professional avatars.

Checks local cache first, falls back to DiceBear CDN, then to initials.
"""
import hashlib
from django import template
from django.utils.html import format_html
from pathlib import Path

register = template.Library()

HUMAN_STYLES = ['avataaars', 'adventurer', 'micah', 'big-smile', 'lorelei', 'personas']

GRADIENTS = [
    ('#667eea', '#764ba2'), ('#f093fb', '#f5576c'), ('#4facfe', '#00f2fe'),
    ('#43e97b', '#38f9d7'), ('#fa709a', '#fee140'), ('#30cfd0', '#330867'),
    ('#a8edea', '#fed6e3'), ('#ff9a9e', '#fecfef'), ('#fbc2eb', '#a6c1ee'),
    ('#84fab0', '#8fd3f4'), ('#ffecd2', '#fcb69f'), ('#ff8177', '#b12a5b'),
    ('#f6d365', '#fda085'), ('#96fbc4', '#f9f586'), ('#c471f5', '#fa71cd'),
    ('#48cae4', '#0077b6'), ('#f0932b', '#eb4d4b'), ('#6ab04c', '#badc58'),
    ('#e056fd', '#686de0'), ('#7ed6df', '#22a6b3'),
]


def _initials(name):
    if not name:
        return '?'
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return '?'
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _stable_seed(text):
    return hashlib.md5((text or 'x').encode('utf-8'), usedforsecurity=False).hexdigest()[:12]


def _gradient_for(key):
    h = 0
    for ch in (key or 'x'):
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return GRADIENTS[h % len(GRADIENTS)]


@register.simple_tag
def avatar(person, size=72, style='avataaars'):
    size = int(size)
    name = ''
    photo_url = ''

    if isinstance(person, str):
        name = person
    else:
        name = (
            getattr(person, 'full_name', '') or
            getattr(person, 'organisation_name', '') or
            getattr(person, 'get_full_name', lambda: '')() or
            getattr(person, 'username', '') or
            getattr(person, 'email', '') or '?'
        )
        photo = getattr(person, 'photo', None)
        if photo:
            try:
                photo_url = photo.url
            except Exception:
                photo_url = ''

    name = str(name).strip() or 'User'

    # 1. Real photo
    if photo_url:
        return format_html(
            '<img src="{}" alt="{}" class="tl-avatar" '
            'style="width:{}px;height:{}px;object-fit:cover;'
            'border-radius:50%;background:#f0f0f0;" loading="lazy">',
            photo_url, name, size, size,
        )

    # 2. Try local cached avatar first (fast, no network)
    seed = _stable_seed(name)
    from django.templatetags.static import static
    local_url = static(f'avatars/{seed}.svg')

    # 3. DiceBear CDN fallback
    if style not in HUMAN_STYLES:
        style = 'avataaars'
    dice_url = (
        f'https://api.dicebear.com/7.x/{style}/svg'
        f'?seed={seed}&size={size * 2}&backgroundType=gradientLinear'
    )

    initials = _initials(name)
    color1, color2 = _gradient_for(name)
    font_size = max(12, int(size * 0.4))

    return format_html(
        '<span class="tl-avatar-wrap" style="display:inline-block;'
        'position:relative;width:{s}px;height:{s}px;">'
        '<span style="position:absolute;inset:0;display:flex;align-items:center;'
        'justify-content:center;border-radius:50%;'
        'background:linear-gradient(135deg,{c1} 0%,{c2} 100%);'
        'color:#fff;font-weight:600;font-size:{fs}px;">{init}</span>'
        '<img src="{url}" alt="{alt}" '
        'style="position:relative;width:{s}px;height:{s}px;border-radius:50%;'
        'background:#fff;display:block;" loading="lazy" '
        'onerror="this.src=\'{fallback}\'">'
        '</span>',
        s=size, c1=color1, c2=color2, fs=font_size,
        init=initials, url=local_url, alt=name,
        fallback=dice_url,
    )