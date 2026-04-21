# D7. XAU-specific read-only surface 실행 로드맵

## 목표

XAU retained pilot에서 정한 공용 decomposition 언어를 runtime row에 read-only로 보이게 만든다.

## 작업 순서

### 1. contract 추가

- `xau_readonly_surface_contract_v1`
- XAU 전용 row-level field catalog 고정
- dominance 보호 / execution 금지 규칙 명시

### 2. row builder 추가

- `XAUUSD`면 symbol profile과 raw row를 함께 보고
  - polarity
  - intent
  - stage
  - rejection split
  - texture
  - location
  - tempo
  - ambiguity
  를 surface
- `XAUUSD`가 아니면 `NOT_APPLICABLE`

### 3. summary / artifact 추가

- `xau_readonly_surface_summary_v1`
- `xau_readonly_surface_latest.json`
- `xau_readonly_surface_latest.md`

### 4. runtime detail export 연결

- contract / summary / artifact path를 detail payload에 추가

### 5. 검증

- 단위 테스트
- runtime export 테스트
- 현재 workspace `latest_signal_by_symbol` 기준 스모크

## 완료 후 기대 상태

- XAU row가 공용 decomposition 언어로 직접 읽힌다.
- D8에서 should-have-done / dominance 검증과 바로 결합 가능하다.
- execution/state25는 그대로 유지된다.
