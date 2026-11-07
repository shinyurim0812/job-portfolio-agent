"""Build editable Figma nodes and previews from an approved, company-neutral spec."""
import argparse
import base64
import io
import json
import math
from pathlib import Path
import re
import zipfile

from PIL import Image, ImageDraw, ImageFont, ImageOps

ASSETS = Path(__file__).resolve().parents[1] / 'assets'
HEX = re.compile(r'^#[0-9a-fA-F]{6}$')


def number(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise ValueError(f'{label}: expected finite number >= {minimum}')
    return value


def color(value, label):
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise ValueError(f'{label}: expected #RRGGBB')
    return value


def load_spec(path):
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    for key in ('width', 'height'):
        number(data[key], key, 1)
        if int(data[key]) != data[key] or data[key] > 10000:
            raise ValueError(f'{key}: expected integer <= 10000')
    if not isinstance(data.get('slides'), list) or not data['slides']:
        raise ValueError('slides must be a non-empty list')
    normalized = {}
    for key, asset in data.get('assets', {}).items():
        if 'path' in asset:
            raw = (path.parent / asset['path']).read_bytes()
        else:
            raw = base64.b64decode(asset['base64'], validate=True)
        with Image.open(io.BytesIO(raw)) as img:
            img = img.convert('RGBA')
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            normalized[key] = {'base64': base64.b64encode(buf.getvalue()).decode(), 'width': img.width, 'height': img.height}
    data['assets'] = normalized
    for page, slide in enumerate(data['slides'], 1):
        if not isinstance(slide.get('name'), str) or not isinstance(slide.get('elements'), list):
            raise ValueError(f'page {page}: name/elements required')
        for idx, e in enumerate(slide['elements']):
            label = f'page {page}, element {idx + 1}'
            if not isinstance(e.get('name'), str) or not e['name']:
                raise ValueError(f'{label}: name required')
            kind = e.get('type')
            if kind not in ('text', 'rect', 'ellipse', 'line', 'image'):
                raise ValueError(f'{label}: unsupported type {kind}')
            for key in ('x', 'y'):
                number(e[key], f'{label}.{key}')
            for key in ('w', 'h'):
                # Lines may point in any direction (negative w/h); areas may not.
                number(e[key], f'{label}.{key}', -data[key == 'w' and 'width' or 'height'] if kind == 'line' else 0)
            xs, ys = (e['x'], e['x'] + e['w']), (e['y'], e['y'] + e['h'])
            if min(xs) < -.01 or min(ys) < -.01 or max(xs) > data['width'] + .01 or max(ys) > data['height'] + .01:
                raise ValueError(f'{label}: outside canvas')
            if kind != 'line' and (e['w'] == 0 or e['h'] == 0):
                raise ValueError(f'{label}: empty area')
            if kind == 'text':
                if not isinstance(e.get('text'), str):
                    raise ValueError(f'{label}: text must be string')
                number(e['size'], label + '.size', 1)
                number(e['lh'], label + '.lh', e['size'])
                color(e['color'], label + '.color')
                if e.get('align', 'LEFT') not in ('LEFT', 'CENTER', 'RIGHT'):
                    raise ValueError(f'{label}: invalid alignment')
                e.setdefault('align', 'LEFT')
            elif kind in ('rect', 'ellipse'):
                for key in ('fill', 'stroke'):
                    if e.get(key):
                        color(e[key], label + '.' + key)
                if e.get('stroke'):
                    number(e.get('strokeWeight', 1), label + '.strokeWeight', .1)
                if kind == 'rect' and e.get('radiusBR'):
                    number(e['radiusBR'], label + '.radiusBR')
                    if e['radiusBR'] > min(e['w'], e['h']) / 2:
                        raise ValueError(f'{label}: excessive radius')
            elif kind == 'line':
                color(e['stroke'], label + '.stroke')
                number(e.get('weight', 1), label + '.weight', .1)
                if e.get('arrow', 'none') not in ARROWS:
                    raise ValueError(f'{label}: arrow must be one of {ARROWS}')
                if e['w'] == 0 and e['h'] == 0:
                    raise ValueError(f'{label}: zero-length line')
            elif kind == 'image':
                if e.get('key') not in normalized:
                    raise ValueError(f'{label}: unknown image key')
                if e.get('fit', 'FIT') not in ('FIT', 'FILL'):
                    raise ValueError(f'{label}: fit must be FIT/FILL')
        slide['elements'] = expand_arrows(slide['elements'])
    return data


ARROWS = ('none', 'start', 'end', 'both')


def expand_arrows(elements):
    """Arrowheads are two short native Lines meeting at the tip (no Vector nodes).

    Figma's LineNode strokeCap applies to both ends, so a one-ended arrow is drawn
    as extra Line elements instead.
    """
    out = []
    for e in elements:
        out.append(e)
        if e['type'] != 'line' or e.get('arrow', 'none') == 'none':
            continue
        size = e.get('arrowSize', 14)
        angle = math.atan2(e['h'], e['w'])
        tips = []
        if e['arrow'] in ('end', 'both'):
            tips.append(((e['x'] + e['w'], e['y'] + e['h']), angle))
        if e['arrow'] in ('start', 'both'):
            tips.append(((e['x'], e['y']), angle + math.pi))
        group = e['name'].split('/')[0]
        for (tx, ty), a in tips:
            for side in (-1, 1):
                back = a + math.pi + side * math.pi / 6
                out.append({'type': 'line', 'name': f'{group}/ArrowHead', 'x': tx, 'y': ty,
                            'w': round(size * math.cos(back), 2), 'h': round(size * math.sin(back), 2),
                            'stroke': e['stroke'], 'weight': e.get('weight', 1)})
    return out


def find_font(explicit):
    candidates = [explicit] if explicit else [
        'C:/Windows/Fonts/NotoSansKR-VF.ttf',
        'C:/Windows/Fonts/malgun.ttf',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    raise ValueError('Korean font not found; pass --font with a Korean TTF/OTF/TTC path')


def font_at(path, size, bold=False, scale=1):
    font = ImageFont.truetype(path, round(size * scale))
    try:
        axes = font.get_variation_axes()
        values = [(700 if bold else 400) if b'Weight' in a['name'] else a['default'] for a in axes]
        font.set_variation_by_axes(values)
    except (OSError, AttributeError):
        if bold:
            bold_path = Path(path).with_name('malgunbd.ttf')
            if Path(path).name.lower() == 'malgun.ttf' and bold_path.exists():
                font = ImageFont.truetype(str(bold_path), round(size * scale))
    return font


def validate_text(data, font):
    for page, slide in enumerate(data['slides'], 1):
        for e in slide['elements']:
            if e['type'] != 'text':
                continue
            face = font_at(font, e['size'], e.get('bold', False))
            lines = e['text'].split('\n')
            if len(lines) * e['lh'] > e['h'] + 1:
                raise ValueError(f'page {page}, {e["name"]}: text exceeds height; reflow layout')
            if any(face.getlength(line) > e['w'] + 1 for line in lines):
                raise ValueError(f'page {page}, {e["name"]}: text exceeds width; reflow layout')


def render(slide, data, font):
    scale = 2
    image = Image.new('RGB', (data['width'] * scale, data['height'] * scale), 'white')
    draw = ImageDraw.Draw(image)
    for e in slide['elements']:
        x, y, w, h = [round(e[k] * scale) for k in ('x', 'y', 'w', 'h')]
        kind = e['type']
        if kind == 'rect':
            radius = round(e.get('radiusBR', 0) * scale)
            fill, stroke = e.get('fill'), e.get('stroke')
            weight = max(1, round(e.get('strokeWeight', 1) * scale))
            if radius:
                draw.rounded_rectangle((x, y, x + w, y + h), radius, fill=fill, outline=stroke, width=weight,
                                       corners=(False, False, True, False))
            else:
                draw.rectangle((x, y, x + w, y + h), fill=fill, outline=stroke, width=weight)
        elif kind == 'ellipse':
            draw.ellipse((x, y, x + w, y + h), fill=e.get('fill'), outline=e.get('stroke'),
                         width=max(1, round(e.get('strokeWeight', 1) * scale)))
        elif kind == 'line':
            draw.line((x, y, x + w, y + h), fill=e['stroke'], width=max(1, round(e.get('weight', 1) * scale)))
        elif kind == 'text':
            face = font_at(font, e['size'], e.get('bold', False), scale)
            for row, line in enumerate(e['text'].split('\n')):
                width = face.getlength(line)
                offset = (w - width) / 2 if e['align'] == 'CENTER' else w - width if e['align'] == 'RIGHT' else 0
                draw.text((x + offset, y + row * e['lh'] * scale), line, font=face, fill=e['color'], anchor='lt')
        elif kind == 'image':
            source = Image.open(io.BytesIO(base64.b64decode(data['assets'][e['key']]['base64']))).convert('RGBA')
            if e.get('fit', 'FIT') == 'FILL':
                source = ImageOps.fit(source, (w, h), Image.Resampling.LANCZOS)
                image.paste(source, (x, y), source)
            else:
                source = ImageOps.contain(source, (w, h), Image.Resampling.LANCZOS)
                image.paste(source, (x + (w - source.width) // 2, y + (h - source.height) // 2), source)
    return image.resize((data['width'], data['height']), Image.Resampling.LANCZOS)


def build(spec, out, name, font):
    data = load_spec(spec)
    validate_text(data, font)
    if out.exists():
        raise ValueError('Output folder already exists; choose a new folder to preserve existing files')
    # Validate/rasterize before writing outputs so failed inputs leave no generated package.
    previews = [render(slide, data, font) for slide in data['slides']]
    out.mkdir(parents=True)
    package, preview = out / 'plugin', out / 'preview'
    package.mkdir()
    (preview / 'half').mkdir(parents=True)
    code = 'const PORTFOLIO = ' + json.dumps(data, ensure_ascii=False) + ';\n' + (ASSETS / 'figma-runtime.js').read_text(encoding='utf-8')
    manifest = {'name': name, 'id': 'job-portfolio-local', 'api': '1.0.0', 'main': 'code.js', 'ui': 'ui.html',
                'editorType': ['figma'], 'documentAccess': 'dynamic-page', 'networkAccess': {'allowedDomains': ['none']}}
    (package / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (package / 'code.js').write_text(code, encoding='utf-8')
    (package / 'ui.html').write_text((ASSETS / 'figma-ui.html').read_text(encoding='utf-8'), encoding='utf-8')
    (package / 'README.md').write_text(
        f'# {name}\n\nZIP 압축 해제 → Figma Design → Plugins / Development / Import plugin from manifest → manifest.json → 실행 → 한국어 글꼴 선택 → 생성.\n\n'
        f'{len(data["slides"])}장, {data["width"]}×{data["height"]}. 텍스트·도형·선은 편집 가능하며 실제 자료 이미지는 이미지입니다. '
        '기존 레이어 오른쪽에 새 세트를 추가합니다. 오류 시 이번 생성분만 정리합니다.\n\n'
        '입력 구조·폰트 영역·PNG 생성·ZIP 구성을 검사했습니다. 실제 Figma 실행·가독성 시각 검수는 별도 확인이 필요합니다.\n', encoding='utf-8')
    thumb_w = 480
    thumb_h = round(thumb_w * data['height'] / data['width'])
    rows = math.ceil(len(previews) / 3)
    overview = Image.new('RGB', (3 * (thumb_w + 24) + 24, rows * (thumb_h + 52) + 24), '#F2F4F7')
    draw = ImageDraw.Draw(overview)
    for index, image in enumerate(previews):
        image.save(preview / f'{index + 1:02d}.png')
        image.resize((max(1, data['width'] // 2), max(1, data['height'] // 2)), Image.Resampling.LANCZOS).save(preview / 'half' / f'{index + 1:02d}.png')
        x, y = 24 + index % 3 * (thumb_w + 24), 24 + index // 3 * (thumb_h + 52)
        overview.paste(image.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS), (x, y))
        draw.text((x, y + thumb_h + 5), f'{index + 1:02d}', font=font_at(font, 18), fill='#252B33')
    overview.save(preview / 'overview.png')
    with zipfile.ZipFile(out / 'portfolio-plugin.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in ('manifest.json', 'code.js', 'ui.html', 'README.md'):
            archive.write(package / name, name)
    with zipfile.ZipFile(out / 'portfolio-plugin.zip') as archive:
        assert archive.testzip() is None
    checks = {'spec': str(spec), 'slides': len(data['slides']), 'font': font,
              'input_validation': 'passed', 'text_bounds': 'passed', 'zip_integrity': 'passed',
              'visual_review': 'pending', 'actual_figma_execution': 'not_tested'}
    (out / 'validation.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--name', default='직무 맞춤 포트폴리오 생성')
    parser.add_argument('--font')
    args = parser.parse_args()
    try:
        result = build(args.spec.resolve(), args.out.resolve(), args.name, find_font(args.font))
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f'Build failed: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
