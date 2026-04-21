# BC10 State25 Bounded Live Readiness / Apply 상세

- 목적: `state25 context bridge` bounded-live 후보를 실제 apply 전에 자동으로 점검한다.
- 핵심:
  - detector snapshot 기준으로 `weight / threshold` bounded-live review 후보를 다시 조립
  - cooldown, 현재 runtime bridge 값, active candidate binding mode를 같이 본다
  - 지금 즉시 apply 가능한지 `ready / blocked`로 나눈다
  - threshold는 현재 계약이 `single delta + allowlist`라서 심볼별 delta가 다르면 즉시 apply를 막는다

- 이번 단계에서 하는 일:
  - stale 또는 cooldown 후보를 그대로 live로 올리지 않음
  - `weight bounded live`, `threshold bounded live`의 review/apply 진입 가능성만 자동 판정
  - 가능할 때만 apply handler를 호출할 수 있게 경로를 열어둠

- 산출물:
  - `state25_context_bridge_bounded_live_readiness_latest.json`
  - `state25_context_bridge_bounded_live_readiness_latest.md`
