---
name: job-apply
description: 채용공고 하나로 지원 자료를 만든다. 분석 에이전트가 공고 분석·회사 조사·추천(어떤 경험을 어떤 순서로)을 하고, 작성·디자인 에이전트가 자소서 답변, 이력서 수정 안내, 포폴 수정 안내서를 만든다. 검토 에이전트가 계획 방향과 결과물을 본다.
---

# job-apply 오케스트레이션

목적: 공고에 맞게 자소서·이력서·포폴의 경험 선택, 경험 순서, 문구를 정해 합격 가능성을 높인다.

## 너(메인 세션)의 역할: 지휘자
- **한다**:
  - 에이전트를 `JOB_DIR`, `MODE`만 넣어 부르고, 끝나면 코드 검사를 돌린다.
  - 사용자의 결정은 `JOB_DIR/user-notes.md`에 한 줄씩 적는다("무엇을 어떻게 한다"). 해석이 갈릴 수 있을 때만 원문을 짧게 덧붙인다.
  - 사용자 지적이 모든 공고에 통하는 것이면 `data/rules.md`(공용 원칙)나 해당 에이전트 지침을 원칙 문장으로 고친다. 같은 주제의 줄이 있으면 그 줄을 다듬고, 새 줄을 쌓지 않는다. 날짜·원문은 넣지 않는다.
  - 사용자가 의견을 물으면 근거로 판단을 말한다. 근거가 바뀌지 않으면 사용자 의견에 맞춰 바꾸지 않고, 판단이 바뀌면 무엇이 바뀌었는지 말한다.
- **하지 않는다**:
  - 원본 자료·검토 결과를 요약해 넘기기(파일 경로만 넘긴다), 에이전트 결과 파일을 통째로 읽기
  - 추천·계획·문구를 직접 쓰기, 지시에 자기 판단 섞기
  - 본인 생각이 필요한 질문(하고 싶은 이유, 배운 점 등)에 기본값 채우기
  - 기존 자소서·포폴에 이미 쓴 표현이나 한 번 기본값을 밝힌 것을 다시 묻기
  - 검토를 거치지 않은 결과물을 보여 주기

## 에이전트
| 언제 | 에이전트 | 결과 |
|---|---|---|
| 자료 창고 — 원본이 바뀔 때만 (병렬) | experience-indexer · portfolio-reader | `data/library/experiences.json` · `data/reads/`, `data/design/layouts/`, `templates/` |
| 공고마다 | analyst | `analysis.json`, `company-research.md`, `recommendation.md` |
| 공고마다 (병렬) | cover-letter-writer · portfolio-designer | 계획 → 제작 → 수정 |
| 공고마다 | reviewer | `review/plan.json`, `review/rN.json` |

- writer·designer·reviewer는 같은 세션을 SendMessage로 이어 부른다. 이어 부를 수 없거나 이 세션에서 지침을 고쳤으면 general-purpose에 "먼저 `.claude/agents/<name>.md`를 읽고 따른다"와 `JOB_DIR`, `MODE`, frontmatter의 `model`을 넣어 새로 부른다.
- 경험 사실의 출처는 `data/library/experiences.json` 하나다.
- `recommendation.md`(경험 선택·순서·시작 행)가 writer와 designer를 묶는다. 둘 다 이것을 따른다.

## 준비
- `JOB_DIR = data/jobs/job-NNN`(회사 이름 금지): `jd.txt`, `questions.json`(`count_rule.min_ratio` 기본 0.9), `user-notes.md`(비어 있어도 만든다).
- 창고가 없으면 experience-indexer와 portfolio-reader를 먼저 병렬로 돌린다.
- 기본 결과물은 세 가지다: 자소서 답변, 이력서 수정 안내(`resume-guide.md`), 포폴 수정 안내서(`portfolio-guide.md`). 사용자가 빼라고 하지 않으면 셋 다 만든다. 포폴 ZIP은 사용자가 요청할 때만(`OUTPUT=zip`).

## 단계
```
분석 → 계획(writer ∥ designer) → 계획 검토 → 계획 수정 → (필요할 때만 ⏸) → 제작
 → 검토(최대 3회차) → 코드 확인 → 전달
```
1. **분석**: analyst. 검사 `check_analysis`, `check_exclusions`(추천). 실패하면 1회 다시 맡기고, 또 실패하면 멈춘다.
2. **계획 (병렬)**: writer `MODE=plan`, designer `MODE=plan` → `check_exclusions`.
3. **계획 검토**: reviewer `MODE=plan-review`. open 항목이 있으면 writer·designer가 계획을 1회 고친다(재검토 없음).
4. **⏸ 사용자 확인**: 사용자만 답할 수 있는 것(본인 생각, 사실 확인, 지원동기 회사 소재 고르기)이 있거나 ZIP을 만들 때만 한다. 없으면 바로 제작하고, 결과물과 함께 계획 요약을 보여 준다.
   - 질문은 답에 따라 결과가 달라지는 것만. 선택지는 제목과 설명이 같은 내용을 가리키게.
   - 승인은 명시적으로 받는다. 일부만 답하면 다시 묻는다.
5. **제작 (병렬)**: writer `MODE=write`(답변 + `resume-guide.md`), designer `MODE=build`(`portfolio-guide.md`, ZIP이면 `OUT_DIR = output/job-NNN/vN`).
6. **검토 루프**:
   - 1회차: 전체 → `review/r1.json`. open 항목(`needs_user: false`)을 writer(`q*`, `resume`)·designer(`p*`)에 `MODE=revise`로 넘긴다.
   - 2·3회차: 이전 항목이 해결됐는지와 고치면서 새로 생긴 문제만 본다.
   - open이 없으면 끝. 3회차 뒤에도 남으면 `MODE=final`로 한 번 더 고치고 코드 검사로 확인한다. high가 남으면 한 줄 질문으로 사용자에게 묻는다.
   - 전달 뒤 수정 요청: `user-notes.md`에 적고 → 해당 에이전트 revise → 같은 루프 → 보여 준다.
7. **확인 (코드)**: `check_length`, `check_numbers`(sources에 `data/library/experiences.json`), `check_exclusions`, `python -m pytest -q`. 결과만 보고 내용은 고치지 않는다.
8. **전달**: `output/job-NNN/DELIVERY.md`에 결과물 경로, 코드 검사 결과, 회차별로 고친 것, 에이전트가 대신 판단한 곳, 사용자가 직접 할 일을 적고, 답변 원문과 바뀌는 문구를 대화에 보여 준다.

## 사용 한도로 끊겼을 때
- 새로 부르지 않고 같은 에이전트를 SendMessage로 이어 부른다. 풀리는 시각이 있으면 그때 1회 깨어나도록 예약(CronCreate)하고, 깨어나면 묻지 않고 이어 부른다.

## 오류가 났을 때
- `docs/verification-log.md`에 증상 → 원인 층 → 수정 → 재검증을 쓴다. 같은 오류가 두 번 나오면 결과물이 아니라 지침이나 코드를 고친다.
