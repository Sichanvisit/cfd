# D10. State Slot Symbol Extension Surface 실행 로드맵

## 목적

- XAU pilot에서 검증한 decomposition 언어를 `NAS100`, `BTCUSD` row에 순차 확장한다.
- 이 단계는 일반화 확인 단계이며, 아직 lifecycle 행동 연결 단계가 아니다.

## 구현 범위

1. XAU row는 기존 `xau_*` surface를 common field로 mirror
2. NAS row는 continuation stage / extension 중심으로 common slot 산출
3. BTC row는 recovery / drift 중심으로 common slot 산출
4. D9 commonization judge 결과를 함께 읽어서
   - exact XAU slot match
   - common vocabulary compatibility
   를 분리 surface
5. runtime detail + summary artifact 생성

## 핵심 작업

- `state_slot_symbol_extension_surface_contract_v1` 추가
- row builder 추가
- `runtime_status.detail.json` export 추가
- artifact 생성
- unit test 추가

## 예상 summary

- `state_slot_symbol_extension_surface_summary_v1`

핵심 필드:
- `symbol_count`
- `surface_ready_count`
- `symbol_extension_state_count_summary`
- `common_vocabulary_compatibility_count_summary`
- `xau_slot_match_count_summary`
- `core_slot_count_summary`

## 핵심 통제 규칙

- extension surface는 read-only
- D10은 `dominant_side`를 바꾸지 않음
- D10은 `execution/state25`를 바꾸지 않음
- XAU exact slot match 부재는 곧 실패가 아님
- 공용 vocabulary compatibility가 더 상위 판단 축

## 완료 기준

- `XAU / NAS100 / BTCUSD` 세 심볼이 모두 common slot 언어로 설명된다.
- 세 심볼 모두 row-level common slot core와 modifier가 surface된다.
- XAU exact slot match 여부와 공용 compatibility가 동시에 보인다.

## 다음 단계와의 연결

- D10이 끝나면:
  - 공용 slot 언어가 진짜 다른 심볼에도 먹히는지 확인한 상태가 된다.
- 그다음에야:
  - `position lifecycle`
  - `state_slot -> execution_policy`
  쪽으로 넘어갈 수 있다.

## 한 문장 결론

이 단계의 본질은 XAU 전용 파일럿을 NAS/BTC에 강제 복사하는 것이 아니라, XAU에서 만든 decomposition 문법이 다른 심볼 row에서도 같은 core slot + modifier 구조로 읽히는지 확인하는 것이다.
