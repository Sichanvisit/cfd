# ST4 Runtime Payload Context Merge 실행 로드맵

## 목표

state-first context 계산 결과를 runtime payload export 선에 합류시켜,
운영 row가 실제로 사람이 보는 좌표계를 담기 시작하게 만든다.


## ST4-1. merge helper 구현

할 일:

- row 단위 context enrich helper
- rows 단위 batch enrich helper
- current price/share state extraction helper

완료 기준:

- `TradingApplication` 내부에서 row enrich 가능


## ST4-2. _write_runtime_status 합류

할 일:

- normalized rows -> context enriched rows
- detail payload에 enriched rows 사용
- slim payload에 enriched rows 사용

완료 기준:

- runtime export가 새 context 필드를 같이 기록


## ST4-3. 테스트

할 일:

- `_write_runtime_status(...)` 실경로 테스트
- HTF/previous box/context field 존재 검증
- 기존 runtime status 회귀 확인

완료 기준:

- focused pytest 통과
- `py_compile` 통과


## ST4 이후

다음 단계:

1. `ST5 15M trend state v1`은 이미 HTF cache 안에 일부 포함돼 있으므로 필요 시 별도 정리
2. `ST7 detector bridge`
3. `ST8 notifier bridge`

즉 `ST4`가 끝나면 그다음부터는 detector/notifier가 진짜 같은 좌표계를 읽기 시작한다.
