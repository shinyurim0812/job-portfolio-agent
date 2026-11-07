---
name: job-apply
description: 채용공고 하나로 지원 자료를 만든다. 공고 분석·Notion 경험 정리·기존 포트폴리오 정리를 병렬 서브에이전트로 돌리고, 코드로 검사한 뒤, 사용자 확인 2번을 거쳐 문항 답변 초안과 Figma 플러그인 ZIP을 만든다.
---

# job-apply 오케스트레이션

너(메인 세션)는 **지휘자**다. 직접 읽고 쓰는 대신 아래 서브에이전트에게 맡기고, 결과는 `tools/`의 코드로 검사하며, 판단(매칭·추천·계획)과 사용자 대화만 직접 한다.

## 준비
- `JOB_DIR = data/jobs/<slug>`: 사용자가 준 공고 원문을 `jd.txt`에, 문항·글자 수 제한을 `questions.json`에 저장한다.
- `data/config.json`(Notion DB, 행별 대표 파일), `data/exclusions.json`(제외 키워드)이 있어야 한다.
- 행별 텍스트(`data/text/*.txt`)가 없으면 먼저 실행한다: `python tools/extract_text.py <config의 portfolio·cover_letter 경로들> --out data/text`

## 서브에이전트 호출 방법
- `.claude/agents/<name>.md`가 에이전트 목록에 있으면 그 이름으로 호출한다.
- 목록에 없으면(세션 중에 파일을 만든 경우 등) 파일 본문을 읽어 general-purpose 에이전트의 prompt로 넘기고, frontmatter의 `model`을 Agent 호출의 `model`로 지정한다. prompt 앞에 `JOB_DIR=...`을 붙인다.
- **병렬로 실행할 에이전트는 한 메시지에서 동시에 호출한다.**

## 단계
1. **분석 단계 (병렬)**: `jd-analyzer`와 `experience-indexer`를 호출한다. `data/reads/`에 6개 행 결과가 없으면 `portfolio-reader`도 함께 호출한다. 세 작업은 서로의 결과를 기다리지 않는다.
2. **검사 (코드)**:
   - `python tools/check_analysis.py JOB_DIR/analysis.json JOB_DIR/jd.txt --out JOB_DIR/checks/analysis.json`
   - `python tools/check_exclusions.py JOB_DIR/experiences.json data/reads/*.json --out JOB_DIR/checks/exclusions-index.json`
   - 실패한 에이전트만 오류 JSON을 넣어 **1회** 다시 맡긴다. 또 실패하면 멈추고 사용자에게 오류를 보여 준다.
   - `run-log.jsonl`에서 병렬 구간이 겹쳤는지 확인한다(`tools/log.py`의 `overlapping`).
3. **추천 (메인 세션)**: analysis × experiences × reads를 보고 `JOB_DIR/recommendation.md`를 쓴다.
   - 핵심 업무 3개마다 맞는 경험 후보(page_id, 근거 문장, 본인/팀, 상태, 범위, 미확인)
   - **시작할 행**과 이유, 다른 행에서 **가져올 페이지**, Notion에만 있어 **새로 만들 페이지** 후보, 페이지 순서
   - 문항별로 쓸 만한 경험 후보
   - 그다음 `check_exclusions`를 실행한다.
4. **⏸ 경험 선택**: 사용자에게 추천을 보여 주고 쓸 경험을 고르게 한다. **사용자 답 없이 다음 단계로 가지 않는다.**
5. **수정 계획서 (메인 세션)**: 선택한 경험으로만 `JOB_DIR/revision-plan.md`를 쓴다. 두 부분으로 나눈다.
   - "포트폴리오 수정안": 페이지별로 유지·수정·가져오기·추가할 내용, 문구 방향, 배치
   - "문항별 작성안": 문항별 경험, 핵심 메시지, 다시 쓸 문장
   - `check_exclusions`를 실행한다.
6. **⏸ 승인**: 사용자가 승인하기 전에는 제작하지 않는다.
7. **제작 단계 (병렬)**: `cover-letter-writer`와 `portfolio-designer`를 동시에 호출한다.
8. **검사 (코드)**:
   - `check_length` (cover-letter.json)
   - `check_numbers JOB_DIR/cover-letter.json --sources JOB_DIR/experiences.json data/reads/*.json data/text/*.txt JOB_DIR/jd.txt`
   - spec에도 같은 `check_numbers`를 실행한다.
   - 두 결과물에 `check_exclusions`를 실행한다.
   - 실패하면 해당 에이전트에 1회 다시 맡긴다.
9. **전달**: 답변 초안, ZIP 경로, PNG 확인 결과, 검사 결과, 확인하지 못한 것을 보고한다. Figma에서 ZIP을 실행하는 건 사용자가 한다.

## 기록
- 검사에서 실패했거나 재시도한 일은 `docs/verification-log.md`에 증상 → 발견 위치 → 원인 층 → 조치 → 재검증 순으로 남긴다.
- 같은 오류가 두 번 나오면 결과물이 아니라 에이전트 지침이나 코드를 고친다.
- 재시도·멈춤 규칙은 이 지침이 정한 것이다. 코드로 강제되지 않는다는 점을 숨기지 않는다.
