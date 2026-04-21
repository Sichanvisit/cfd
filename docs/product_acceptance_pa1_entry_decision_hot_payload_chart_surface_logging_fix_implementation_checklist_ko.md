# Product Acceptance PA1 Entry-Decision Hot Payload Chart Surface Logging Fix Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. 문제 재확인

- [x] representative replay는 `WAIT + wait_check_repeat`인데 fresh CSV는 blank인지 확인
- [x] 문제 범위가 특정 family가 아니라 hot payload surface 공통 축인지 확인

## Step 1. hot column 확장

- [x] `ENTRY_DECISION_FULL_COLUMNS`에 `consumer_check_display_score` 추가
- [x] `ENTRY_DECISION_FULL_COLUMNS`에 `consumer_check_display_repeat_count` 추가
- [x] `ENTRY_DECISION_FULL_COLUMNS`에 `chart_event_kind_hint` 추가
- [x] `ENTRY_DECISION_FULL_COLUMNS`에 `chart_display_mode` 추가
- [x] `ENTRY_DECISION_FULL_COLUMNS`에 `chart_display_reason` 추가

## Step 2. compaction flattening 보강

- [x] nested `consumer_check_state_v1.display_score`를 flat score로 내리기
- [x] nested `consumer_check_state_v1.display_repeat_count`를 flat repeat로 내리기
- [x] nested `consumer_check_state_v1.chart_event_kind_hint`를 flat hint로 내리기
- [x] nested `consumer_check_state_v1.chart_display_mode`를 flat mode로 내리기
- [x] nested `consumer_check_state_v1.chart_display_reason`를 flat reason으로 내리기

## Step 3. 회귀 고정

- [x] hot payload preserve test 보강
- [x] entry engine surface test 통과 확인
- [x] rollover / active CSV 관련 최소 회귀 통과 확인

## Step 4. live 확인

- [x] `main.py` 재기동
- [x] active CSV header에 새 column이 실제로 생겼는지 확인
- [x] fresh row에서 non-empty `chart_display_reason`가 실제 기록되는지 확인

## Step 5. PA0 refreeze

- [x] 최신 active CSV 기준으로 PA0 재실행
- [x] 직전 snapshot 대비 summary delta 기록
- [x] 이번 delta는 queue cleanup보다 logging surface activation 증빙임을 명시

## Step 6. 문서 연결

- [x] 상세 reference 작성
- [x] 구현 memo 작성
- [x] PA0 delta 작성
- [x] fresh runtime follow-up 작성
- [x] common memo / roadmap / handoff 연결
