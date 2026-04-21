# Product Acceptance PA2 Teacher Label Exploration Entry Layer Implementation Checklist

## kickoff

- [x] teacher-label split 기준으로 PA2 entry gap 재오픈
- [x] global loosen 대신 exploration overlay 방향 확정
- [x] soft guard bypass + reduced size + tagged logging 원칙 고정

## implementation steps

### Step 0. design

- [x] 1차 exploration family를 `lower_rebound_probe_observe`, `upper_reject_probe_observe`로 한정
- [x] probe scene allowlist 정의
- [x] 우회 가능한 soft guard 범위 한정

### Step 1. config surface

- [x] exploration enable flag 추가
- [x] allowlist / score ratio / threshold gap / size multiplier config 추가
- [x] flat-position requirement config 추가

### Step 2. try-open overlay

- [x] `probe_promotion_guard_v1` skip 직전에 exploration overlay 연결
- [x] `consumer_open_guard_v1` skip 직전에 exploration overlay 연결
- [x] exploration active 시 reduced lot 적용
- [x] hard block 계열은 그대로 유지

### Step 3. logging surface

- [x] decision row에 exploration scalar fields 추가
- [x] nested trace `teacher_label_exploration_entry_v1` 추가

### Step 4. tests

- [x] probe promotion guard bypass test
- [x] consumer entry-not-ready bypass test
- [x] 기존 entry guard regression 재확인

### Step 5. follow-up

- [ ] fresh runtime row에서 exploration tag 실제 발생 확인
- [ ] PA0 baseline/teacher-label anchor와 대조
- [ ] 2차 family 확장 여부 판단

## done condition

- teacher-label missed entry family가 exploration으로 좁게 열림
- 기존 broad guard regression은 없음
- row에 exploration 여부가 분명히 남음
