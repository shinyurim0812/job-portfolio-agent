---
name: job-apply
description: 채용공고 하나로 지원 자료를 만든다. 분석가가 공고 분석과 추천을 한 번에 하고, 작성·디자인 에이전트가 계획부터 제작까지 이어서 맡으며, 검토자 하나가 최대 3회차까지 검토한다. 코드로 검사하고 사용자 확인 2번을 거쳐 문항 답변과 Figma 플러그인 ZIP을 전달한다.
---

# job-apply 오케스트레이션

## 너(메인 세션)의 역할: 지휘자
- **한다**:
  - 에이전트가 끝나면 코드 검사를 돌린다.
  - 다음 에이전트를 `JOB_DIR`, `MODE`만 넣어 부른다("이제 일해").
  - ⏸에서는 결과 파일 링크와 바뀌는 문구를 그대로 보여 준다.
  - 사용자의 답은 `JOB_DIR/user-notes.md`에 **원문 그대로** 적는다.
- **하지 않는다**:
  - 원본 자료를 요약해 넘기기
  - 추천·계획·문구·디자인을 직접 쓰기
  - 검토 결과를 요약해 넘기기(검토 파일 경로만 넘긴다)
  - 에이전트 결과 파일을 통째로 읽기

## 에이전트 6종, 공고 1건당 세션 4개
| 언제 | 에이전트 | 결과 |
|---|---|---|
| 자료 창고 — 원본이 바뀔 때만 (병렬) | experience-indexer · portfolio-reader | `data/library/experiences.json` · `data/reads/`, `data/design/layouts/`, `templates/` |
| 공고마다 | analyst | `analysis.json` + `recommendation.md` |
| 공고마다 (병렬, 세션 이어 쓰기) | cover-letter-writer · portfolio-designer | 계획 → 답변·ZIP → 수정 |
| 공고마다 (세션 이어 쓰기) | reviewer | `review/rN.json` |

- 한 결정은 한 에이전트가 끝까지 맡는다. writer·designer·reviewer는 **같은 세션을 SendMessage로 이어 부른다.** 이미 읽은 맥락이 남아 다시 읽지 않는다. 이어 부를 수 없을 때만 새로 부르고, 새로 불렀다는 사실을 로그에 남긴다.
- 경험 사실의 출처는 `data/library/experiences.json` 하나다. 공고 폴더의 예전 experiences 파일은 보관용이고 읽지 않는다.
- 사용자 지적은 `data/feedback.md`에 누적한다. 새 지적이 나오면 지휘자가 원문을 추가한다. writer·designer·reviewer가 매번 읽는다.

## 호출 방법
- `.claude/agents/<name>.md`가 목록에 있으면 그 이름으로 부른다. 없거나 이 세션에서 지침을 고쳤으면 general-purpose에 "먼저 `.claude/agents/<name>.md`를 읽고 따른다"와 `JOB_DIR`, `MODE`를 넣고, frontmatter의 `model`을 지정한다.
- 병렬 단계의 에이전트는 한 메시지에서 동시에 부른다.

## 준비
- `JOB_DIR = data/jobs/<slug>`(번호로. 회사 이름 금지): `jd.txt`, `questions.json`(`count_rule.min_ratio` 기본 0.9), `user-notes.md`(비어 있어도 만든다).
- `data/config.json`, `data/exclusions.json`이 있어야 한다.
- 창고가 없으면 먼저 experience-indexer와 portfolio-reader를 병렬로 돌린다. 행별 텍스트(`data/text/*.txt`)가 없으면 `python tools/extract_text.py ... --out data/text`. 창고가 있으면 `experiences.json`의 `updated_at`을 ⏸1에서 사용자에게 같이 보여 준다.

## 단계
1. **분석**: analyst. 코드 검사만 한다(검토 에이전트 없음).
   - 검사: `check_analysis`(인용이 공고에 있는지·항목 수), `check_exclusions`(추천서)
   - 실패하면 1회 다시 맡기고, 또 실패하면 멈춘다.
   - 코드 검사가 보장하는 건 인용 존재와 제외 경험 없음까지다. 추천이 타당한지는 ⏸1에서 사용자가 판단한다.
2. **⏸ 경험 선택**: `recommendation.md`의 "사용자가 결정할 것"을 묻는다. 답 없이 진행하지 않는다.
   - 선택지를 만들 때 **제목과 설명이 같은 내용을 가리키게** 한다. 한 선택지에 성격이 다른 내용 두 가지가 섞여 있으면 나눠서 묻는다. (실패 사례: 제목 "설문 유도 설계"와 설명 "연령대 고려 15초 설계 + 보상 메시지"를 함께 보여 줘 사용자가 고른 초점과 기록이 어긋났다.)
3. **계획 (병렬)**: writer `MODE=plan`, designer `MODE=plan` → `check_exclusions`(두 계획).
4. **⏸ 승인**: 쪽·문항마다 "보여 줄 한 가지"와 바뀌는 문구를 보여 주고, 에이전트가 남긴 질문을 함께 묻는다.
   - 질문은 **답에 따라 결과가 달라지는 것만** 묻는다. 나머지는 기본값을 밝힌다.
   - **승인은 명시적으로 받는다.** 사용자가 질문 일부에만 답하고 승인 여부를 말하지 않으면 승인으로 보지 않고 다시 묻는다. 침묵을 승인으로 처리하지 않는다.
   - 수정 요청이 있으면 해당 에이전트에 계획 수정을 맡기고 다시 ⏸.
5. **제작 (병렬)**: 같은 세션으로 writer `MODE=write`(네 문항을 한 번에), designer `MODE=build`(OUT_DIR = `output/<slug>/vN`).
   - 포폴 결과물: 수정 쪽은 **수정 안내서**(`portfolio-guide.md`, 사용자가 Figma에서 직접 고침), 새 쪽만 **ZIP**. 사용자가 원하면 `OUTPUT=zip-all`로 수정 쪽도 ZIP.
6. **검토 루프** (유일한 회차 규칙):
   - 1회차: reviewer가 전체를 본다 → `review/r1.json`.
   - open high가 있으면 writer(`q*`)·designer(`p*`)에 `MODE=revise`와 파일 경로를 넘긴다(병렬).
   - 같은 reviewer 세션이 고친 항목과 그 주변만 다시 본다(`r2`, `r3`).
   - **최대 3회차.** 3회차 뒤에도 open high가 남으면 완료로 표시하지 않는다. DELIVERY.md에 "미해결" 항목과 이유를 적는다.
   - `needs_user` 항목은 루프에서 고치지 않고 전달할 때 묻는다.
7. **확인 (코드, 지휘자)**: `check_length`, `check_numbers`(답변·spec, sources에 `data/library/experiences.json`), `check_exclusions`, `check_layout_diff`, `python -m pytest -q`. 결과만 보고 내용을 고치지 않는다.
8. **전달 (자동, 사용자가 묻기 전에)**:
   - `output/<slug>/DELIVERY.md`에 적는 것: 수정 안내서·ZIP·답변 경로, 코드 검사 결과, 검토 회차별 고친 것, 미해결 high, `needs_user`, Figma 실행 방법
   - `preview/overview.png`와 답변 원문을 대화에 보여 준다.

## 기록
- 실패·재시도는 `docs/verification-log.md`에 증상 → 발견 위치 → 원인 층 → 조치 → 재검증 순으로 쓴다.
- 에이전트별 토큰(완료 알림)은 첫 실행과 이어 부른 회차를 나눠 기록한다.
- 같은 오류가 두 번 나오면 결과물이 아니라 에이전트 지침이나 코드를 고친다.
- 재시도·멈춤·역할 규칙은 이 지침이 정한 것이다. 코드로 강제되지 않는다는 점을 숨기지 않는다.
