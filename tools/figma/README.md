# Figma 플러그인 빌더

기존 스킬(`job-portfolio-builder`)에서 쓰던 빌더를 구조(`scripts/` + `assets/`) 그대로 복사했다. `build_plugin.py`가 `parents[1]/assets` 경로를 고정해서 쓰기 때문이다. Figma MCP는 쓰지 않는다(View 시트 읽기 호출이 월 20회).

```
python tools/figma/scripts/build_plugin.py --spec SPEC.json --out NEW_DIR --name "이름" --font C:/Windows/Fonts/malgun.ttf
```

출력: `plugin/{manifest.json, code.js, ui.html, README.md}`, `portfolio-plugin.zip`, `preview/*.png`, `preview/overview.png`, `validation.json`. 이미 있는 폴더에는 쓰지 않는다.

## spec 형식
```json
{"width": 1600, "height": 900,
 "assets": {"screen": {"path": "assets/screen.png"}},
 "slides": [{"name": "페이지 이름", "elements": [
   {"type": "text", "name": "Header/Title", "text": "제목\n두 번째 줄", "x": 72, "y": 72, "w": 1456, "h": 100, "size": 48, "lh": 64, "bold": true, "color": "#252B33", "align": "LEFT"},
   {"type": "rect", "name": "Card/Box", "x": 72, "y": 200, "w": 700, "h": 400, "fill": "#F5F7FA", "stroke": "#DAE1EB", "strokeWeight": 1},
   {"type": "line", "name": "Footer/Divider", "x": 72, "y": 800, "w": 1456, "h": 0, "stroke": "#DAE1EB", "weight": 1},
   {"type": "image", "name": "Evidence/Screen", "key": "screen", "x": 800, "y": 200, "w": 728, "h": 400, "fit": "FIT"}
 ]}]}
```
- 줄바꿈은 `\n`으로 직접 넣는다. 빌더가 실제 글꼴 폭으로 넘침을 검사한다(`text exceeds width/height`).
- `name`의 `/` 앞부분이 Figma 그룹 이름이 된다.

## 빌더가 검사하는 것과 검사하지 않는 것
- 검사함: 입력 구조, 캔버스 범위, 글자 넘침(로컬 폰트 기준), PNG 생성, ZIP 무결성.
- 검사하지 않음: 실제 Figma 실행 결과(Figma 글꼴의 줄바꿈이 다를 수 있음), 시각적 가독성. `validation.json`에 `visual_review: pending`, `actual_figma_execution: not_tested`로 남는다.
