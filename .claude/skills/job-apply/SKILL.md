---
name: job-apply
description: 채용공고 하나로 지원 자료를 만든다. 분석가가 공고 분석과 추천을 한 번에 하고, 작성·디자인 에이전트가 계획부터 제작까지 이어서 맡는다. 검토자가 계획 방향을 먼저 보고, 제작 후 최대 3회차 검토와 마지막 수정을 거친다. 사용자 확인은 제작 전 1번이며, 문항 답변·수정 안내서·새 쪽과 변경 기록을 전달한다.
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
  - 지시에 자기 판단 섞기(예: "이전판 구성을 그대로 써라"). 사용자 말은 `user-notes.md`에 적고 파일 위치만 넘긴다. (실패 사례: 흐름도 수정 요청에 "v7 구성 그대로"를 붙여 디자이너가 옮겨 그리기만 했다.)
  - 본인 생각이 필요한 질문(배운 점, 하고 싶은 이유 등)에 기본값 채우기. (실패 사례: q4 "하고 싶은 이유"에 지휘자가 기본값을 넣어 문항과 어긋났다.)
  - 검토를 거치지 않은 결과물을 사용자에게 보여 주기

## 에이전트 6종, 공고 1건당 세션 4개
| 언제 | 에이전트 | 결과 |
|---|---|---|
| 자료 창고 — 원본이 바뀔 때만 (병렬) | experience-indexer · portfolio-reader | `data/library/experiences.json` · `data/reads/`, `data/design/layouts/`, `templates/` |
| 공고마다 | analyst | `analysis.json` + `recommendation.md` |
| 공고마다 (병렬, 세션 이어 쓰기) | cover-letter-writer · portfolio-designer | 계획 → 제작 → 수정 → 마지막 수정 |
| 공고마다 (세션 이어 쓰기) | reviewer | 계획 검토 `review/plan.json`, 제작 검토 `review/rN.json` |

- 한 결정은 한 에이전트가 끝까지 맡는다. writer·designer·reviewer는 **같은 세션을 SendMessage로 이어 부른다.** 이어 부를 수 없을 때만 새로 부르고, 새로 불렀다는 사실을 로그에 남긴다.
- 경험 사실의 출처는 `data/library/experiences.json` 하나다. 공고 폴더의 예전 experiences 파일은 보관용이고 읽지 않는다.
- 사용자 지적은 `data/feedback.md`에 누적한다. 새 지적이 나오면 지휘자가 원문을 추가한다. writer·designer·reviewer가 매번 읽는다.
- `recommendation.md`는 writer와 designer가 같은 경험을 쓰게 하는 연결 파일이다. 사용자에게 따로 보여 주지 않고, 그 내용(고른 경험)은 ⏸에서 계획과 함께 보여 준다.

## 호출 방법
- `.claude/agents/<name>.md`가 목록에 있으면 그 이름으로 부른다. 없거나 이 세션에서 지침을 고쳤으면 general-purpose에 "먼저 `.claude/agents/<name>.md`를 읽고 따른다"와 `JOB_DIR`, `MODE`를 넣고, frontmatter의 `model`을 지정한다.
- 병렬 단계의 에이전트는 한 메시지에서 동시에 부른다.

## 준비
- `JOB_DIR = data/jobs/<slug>`(번호로. 회사 이름 금지): `jd.txt`, `questions.json`(`count_rule.min_ratio` 기본 0.9), `user-notes.md`(비어 있어도 만든다).
- `data/config.json`, `data/exclusions.json`이 있어야 한다.
- 창고가 없으면 먼저 experience-indexer와 portfolio-reader를 병렬로 돌린다. 행별 텍스트(`data/text/*.txt`)가 없으면 `python tools/extract_text.py ... --out data/text`. 창고가 있으면 `experiences.json`의 `updated_at`을 ⏸에서 사용자에게 같이 보여 준다.

## 단계
```
분석 → 계획(writer ∥ designer) → 계획 검토 → 계획 수정 → ⏸ 1번 → 제작
 → 검토1(전체) → 수정 → 검토2(고친 곳) → 수정 → 검토3(고친 곳) → 마지막 수정 → 코드 확인 → 전달
```
1. **분석**: analyst. 공고 분석, 회사 조사(최신 뉴스·채용 배경, `company-research.md`, 결정 20), 추천을 한다. 코드 검사만 한다.
   - 검사: `check_analysis`(인용이 공고에 있는지·항목 수), `check_exclusions`(추천서)
   - 실패하면 1회 다시 맡기고, 또 실패하면 멈춘다.
   - 멈추지 않고 바로 계획으로 간다. analyst의 "사용자가 결정할 것"은 ⏸에서 계획 질문과 함께 묻는다.
2. **계획 (병렬)**: writer `MODE=plan`, designer `MODE=plan` → `check_exclusions`(두 계획).
3. **계획 검토**: reviewer `MODE=plan-review` → `review/plan.json`. 방향만 본다(문항·공고 일치, 문항 간 겹침, 답변↔포폴 일치, 과정 그림↔실제 절차). open 항목이 있으면 writer·designer가 계획을 1회 고친다(재검토 없이 ⏸로).
4. **⏸ 사용자 확인 (1번, 제작 전)**: 한 화면에 보여 준다.
   - 고른 경험, 문항·쪽마다 "보여 줄 한 가지", 바뀌는 문구, 사용자만 답할 수 있는 질문(본인 생각·사실 확인, analyst의 "사용자가 결정할 것" 포함)
   - 질문은 **답에 따라 결과가 달라지는 것만** 묻는다. 나머지는 기본값을 밝힌다.
   - 선택지를 만들 때 **제목과 설명이 같은 내용을 가리키게** 한다. 성격이 다른 내용 두 가지가 섞이면 나눠서 묻는다. (실패 사례: 제목 "설문 유도 설계"와 설명 "연령대 고려 15초 설계 + 보상 메시지"를 함께 보여 줘 사용자가 고른 초점과 기록이 어긋났다.)
   - 본인 생각 질문에 답이 없으면 기본값을 채우지 않는다. writer가 근거 자료로 쓸 수 있는 문장으로 바꾸거나 다시 묻는다. 공고 업무 중 고르는 것은 writer가 판단한다.
   - **승인은 명시적으로 받는다.** 질문 일부에만 답하고 승인 여부를 말하지 않으면 다시 묻는다. 침묵을 승인으로 처리하지 않는다.
   - 수정 요청(경험 변경 포함)이 있으면 해당 문항·쪽만 계획을 다시 쓰고 다시 ⏸.
5. **제작 (병렬)**: 같은 세션으로 writer `MODE=write`(네 문항을 한 번에), designer `MODE=build`(OUT_DIR = `output/<slug>/vN`).
   - 포폴 결과물: 기본은 **수정 안내서**(`portfolio-guide.md`) 하나다. 프로젝트 순서, 쪽별 수정, 다른 행에서 가져올 쪽, 새 쪽 문구까지 담는다(결정 21). 사용자가 요청할 때만 `OUTPUT=zip`(새 쪽 ZIP, 결정 19) 또는 `OUTPUT=zip-all`.
   - 이력서: analyst가 `recommendation.md`의 `## 이력서 수정` 절에 쓴 것을 그대로 전달한다(문구만).
6. **검토 루프** (유일한 회차 규칙):
   - 1회차: reviewer가 전체를 본다 → `review/r1.json`.
   - open 항목(high·low 모두, `needs_user: false`)을 writer(`q*`)·designer(`p*`)에 `MODE=revise`로 넘긴다(병렬).
   - 2·3회차: 같은 reviewer가 **(a) 이전 항목이 해결됐는지, (b) 고치면서 새로 생긴 문제**만 본다. 손대지 않은 문장에서 새 흠을 찾지 않는다.
   - open 항목이 모두 없어지면 끝난다. **최대 3회차.**
   - **마지막 수정**: 3회차에 open 항목이 남으면 writer·designer가 `MODE=final`로 한 번 더 고치고 코드 검사로 확인한다(검토 없음). 루프는 항상 수정으로 끝난다.
   - 3회차 뒤에도 high가 남으면 자료·결정 부족이다. 더 돌리지 않고 그 항목을 한 줄 질문(`needs_user`)으로 사용자에게 묻는다. 답을 받으면 그 항목만 고치고 1회 검토한다.
   - 답변 하나·쪽 하나를 통째로 다시 쓰면 새 초안이다. 그 대상만 1회차부터 센다.
   - 전달 뒤 사용자가 수정을 요청하면: `user-notes.md`에 적고 → 해당 에이전트 revise → 같은 루프(이전판 그림을 reviewer에게 함께 줌) → 그다음에 보여 준다.
7. **확인 (코드, 지휘자)**: `check_length`, `check_numbers`(답변·spec, sources에 `data/library/experiences.json`), `check_exclusions`, `check_layout_diff`(spec이 있을 때), `python -m pytest -q`. 결과만 보고 내용을 고치지 않는다.
8. **전달 (자동, 사용자가 묻기 전에)**:
   - `output/<slug>/DELIVERY.md`에 적는 것: 답변·수정 안내서·이력서 수정 절·새 쪽 경로, 코드 검사 결과, **변경 기록**(회차별로 무엇을 왜 고쳤는지), **에이전트가 사용자 대신 판단한 곳**, 남은 것과 `needs_user`, 사용자가 직접 할 일
   - 새 쪽 그림과 답변 원문을 대화에 보여 준다.

## 사용 한도로 끊겼을 때
- 에이전트가 사용 한도(429, "limit · resets …")로 끊기면 새로 부르지 않는다. 작업 내용이 남아 있으므로 같은 에이전트를 SendMessage로 이어 부른다("끊긴 곳부터 이어서").
- 알림에 풀리는 시각이 있으면 그 시각에 한 번 깨어나도록 예약(CronCreate, 1회)하고, 깨어나면 사용자에게 묻지 않고 바로 이어 부른다. 세션이 닫혀 있으면 예약은 돌지 않는다. 그때는 다음에 세션이 열렸을 때 바로 이어 부른다.

## 기록
- 실패·재시도는 `docs/verification-log.md`에 증상 → 발견 위치 → 원인 층 → 조치 → 재검증 순으로 쓴다.
- 에이전트별 토큰(완료 알림)은 첫 실행과 이어 부른 회차를 나눠 기록한다.
- 같은 오류가 두 번 나오면 결과물이 아니라 에이전트 지침이나 코드를 고친다.
- 재시도·멈춤·역할 규칙은 이 지침이 정한 것이다. 코드로 강제되지 않는다는 점을 숨기지 않는다.
