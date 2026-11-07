---
name: job-apply
description: 채용공고 하나로 지원 자료를 만든다. 분석(공고·Notion 경험·기존 포트폴리오) → 추천 → 계획 → 제작 → 검토를 서브에이전트에게 맡기고, 코드로 검사하며, 사용자 확인 2번을 거쳐 문항 답변과 Figma 플러그인 ZIP을 전달한다.
---

# job-apply 오케스트레이션

## 너(메인 세션)의 역할: 지휘자
- **한다**: 에이전트에게 일을 시킨다 / 에이전트의 결과를 사용자에게 **그대로** 보여 준다(파일 링크와 원문) / 사용자의 결정과 생각을 `JOB_DIR/user-notes.md`에 **원문 그대로** 적어 에이전트에게 전달한다 / 코드 검사를 다시 돌려 확인한다.
- **하지 않는다**: 원본 자료를 읽고 요약해 넘기기, 추천서·계획서·문구·디자인을 직접 쓰기, 검토 결과를 요약해 넘기기(검토 파일 경로를 그대로 넘긴다).
- 이유: 중간 요약이 정보 손실의 원인이었다(디자이너가 원본 페이지를 보지 못하고 요약만 받아 전혀 다른 페이지를 만듦). 각 에이전트는 원본을 직접 읽는다.

## 에이전트 (8종)
| 단계 | 에이전트 | 결과 |
|---|---|---|
| 분석 (병렬) | jd-analyzer · experience-indexer · portfolio-reader(처음 1회) | analysis.json · experiences.json · reads/, layouts/, templates/ |
| 추천 | recommender | recommendation.md |
| 계획 (병렬) | cover-letter-writer `MODE=plan` · portfolio-designer `MODE=plan` | cover-letter-plan.md · portfolio-plan.md |
| 제작 (병렬) | 같은 두 에이전트 `MODE=write` / `MODE=build` | cover-letter.json · portfolio ZIP |
| 검토 (병렬) | cover-letter-reviewer · portfolio-reviewer | review/*-rN.json |

## 호출 방법
- `.claude/agents/<name>.md`가 에이전트 목록에 있으면 그 이름으로 호출한다. 목록에 없거나 **이 세션에서 지침 파일을 고쳤으면** 파일 본문을 general-purpose 에이전트의 prompt로 넘기고 frontmatter의 `model`을 지정한다.
- prompt에는 `JOB_DIR=...`, `MODE=...`, `OUT_DIR=...`, 회차만 넣는다. 자료 내용을 붙이지 않는다.
- 계획을 쓴 writer·designer는 제작·수정 때 **SendMessage로 이어서** 부른다(맥락 유지). 이어 부를 수 없으면 새로 부르되 계획 파일을 읽게 한다.
- **병렬 단계의 에이전트는 한 메시지에서 동시에 호출한다.**

## 준비
- `JOB_DIR = data/jobs/<slug>`(번호로. 회사 이름 금지): 공고 원문 `jd.txt`, 문항·글자 수 `questions.json`(`count_rule.min_ratio` 기본 0.9), `user-notes.md`(비어 있어도 만든다).
- `data/config.json`(Notion DB, 행별 대표 파일, `design.figma_*`), `data/exclusions.json`이 있어야 한다.
- 행별 텍스트(`data/text/*.txt`)가 없으면: `python tools/extract_text.py <config의 portfolio·cover_letter 경로들> --out data/text`

## 단계
1. **분석 (병렬)**: jd-analyzer, experience-indexer, (reads·layouts가 없으면) portfolio-reader.
2. **검사 (코드)**: `check_analysis`, `check_exclusions`(experiences·reads). 실패한 에이전트만 오류 JSON 경로를 넘겨 1회 다시 맡긴다. 또 실패하면 멈추고 오류를 보여 준다. `run-log.jsonl`로 병렬 구간 겹침 확인.
3. **추천**: recommender.
4. **⏸ 경험 선택**: `recommendation.md`를 사용자에게 그대로 보여 준다. 사용자의 답은 **원문 그대로** `user-notes.md`에 날짜와 함께 적는다. 답 없이 다음으로 가지 않는다.
5. **계획 (병렬)**: writer `MODE=plan`, designer `MODE=plan`. 끝나면 `check_exclusions`(두 계획 파일).
6. **⏸ 승인**: 두 계획 파일을 그대로 보여 준다. 에이전트가 남긴 "사용자에게 물을 것"을 함께 묻는다. 답(승인·수정 요청·배운 점 문장 등)을 원문 그대로 `user-notes.md`에 적는다. 수정 요청이 있으면 해당 에이전트에 계획 수정을 맡기고 다시 ⏸. 승인 전에는 제작하지 않는다.
7. **제작 (병렬)**: writer `MODE=write`, designer `MODE=build`(OUT_DIR = `output/<slug>/vN`).
8. **검토 (병렬)**: cover-letter-reviewer, portfolio-reviewer(회차 N=1).
9. **수정 루프**: 검토 `verdict`가 fix면 해당 에이전트에 `MODE=revise`와 검토 파일 경로를 넘긴다 → 다시 검토(N+1). **최대 2회.** `needs_user: true` 항목은 고치지 않고 모아 둔다.
10. **확인 (코드, 지휘자)**: 최종본에 `check_length`, `check_numbers`(답변·spec), `check_exclusions`, `check_layout_diff`, `python -m pytest -q`를 직접 다시 돌린다. 결과만 본다. 내용을 고치지 않는다.
11. **전달 (자동, 사용자가 묻기 전에)**: `output/<slug>/DELIVERY.md`(ZIP·답변 경로, 검사 결과, 검토 회차별 고친 것, 남은 `needs_user` 항목, Figma 실행 방법)를 쓰고, `preview/overview.png`와 답변 원문을 대화에 보여 준다.

## 기록
- 실패·재시도는 `docs/verification-log.md`에 증상 → 발견 위치 → 원인 층 → 조치 → 재검증 순으로 남긴다.
- 같은 오류가 두 번 나오면 결과물이 아니라 에이전트 지침이나 코드를 고친다.
- 재시도·멈춤·역할 규칙은 이 지침이 정한 것이다. 코드로 강제되지 않는다는 점을 숨기지 않는다.
