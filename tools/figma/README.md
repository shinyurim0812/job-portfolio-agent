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
- `ellipse`: `rect`와 같은 속성(fill, stroke, strokeWeight)으로 원·타원을 만든다.
- `rect`의 `"radius": 16`은 네 모서리, 기존 `radiusBR`은 오른쪽 아래만 둥글게 한다. `rect`·`ellipse`의 `"dash": [6, 6]`은 점선 테두리(Figma dashPattern)다. 미리보기에서는 점선이 실선으로 그려진다.
- `line`: `w`, `h`는 음수 가능(모든 방향). `"arrow": "none" | "start" | "end" | "both"`, `"arrowSize": 14`. 화살촉은 **짧은 Line 2개**로 만든다. Figma Line의 끝 모양(strokeCap)은 양쪽 끝에 함께 적용되고 한쪽만 지정하는 방법이 문서에 없기 때문이다.
- 줄바꿈은 `\n`으로 직접 넣는다. 빌더가 실제 글꼴 폭으로 넘침을 검사한다(`text exceeds width/height`).
- `name`의 `/` 앞부분이 Figma 그룹 이름이 된다.

## ZIP 규칙 (사용자 지정)
- 캔버스 1920×1080. 결과물은 ZIP 하나(manifest.json, code.js, ui.html, README.md). Figma → Plugins → Development → Import plugin from manifest로 실행한다.
- ZIP 안에 PDF나 미리보기를 넣지 않는다. `preview/` PNG는 검수용으로만 쓴다.
- 텍스트는 Text, 도형은 Rectangle·Ellipse·Line, 화살표도 Line으로 만든다. Vector나 SVG Path를 쓰지 않고, 슬라이드 전체를 하나의 벡터로 그리지 않는다(`tests/test_build_plugin_shapes.py`가 확인).
- 이미지는 Rectangle에 이미지 채우기로 넣는다.

## 선 회전 방향 (수정한 부분, Figma 실행 확인 필요)
Figma 문서는 `rotation = Math.atan2(-m10, m00)`으로 정의한다. 화면에서 아래로 향하는 선은 회전값이 음수여야 한다. 기존 빌더는 부호가 반대여서 세로선과 대각선이 위로 그려졌을 가능성이 있어 `-atan2`로 바꿨다. 미리보기(Pillow)에서는 맞게 그려지는 것을 확인했지만, **Figma에서 실제로 같은 방향으로 그려지는지는 아직 확인하지 않았다.** `samples/figma-orientation-check.json`으로 ZIP을 만들어 Figma에서 실행해 확인한다.

## 빌더가 검사하는 것과 검사하지 않는 것
- 검사함: 입력 구조, 캔버스 범위, 글자 넘침(로컬 폰트 기준), PNG 생성, ZIP 무결성.
- 검사하지 않음: 실제 Figma 실행 결과(Figma 글꼴의 줄바꿈이 다를 수 있음), 시각적 가독성. `validation.json`에 `visual_review: pending`, `actual_figma_execution: not_tested`로 남는다.
