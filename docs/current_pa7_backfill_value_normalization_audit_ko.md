# PA7 Backfill Value Normalization Audit

## 목적

`mixed_backfill_value_scale_review`는 rule patch로 바로 다루기보다,
먼저 `closed/open trade backfill`의 `current_profit` 스케일이 live row와 같은 단위인지
감사해야 한다.

이번 단계의 목표는 아래 3가지를 분리하는 것이다.

- 실제 rule mismatch
- backfill source 때문에 생긴 value scale mismatch
- hydration이 비어서 생긴 표면적 mixed-review

## 이번 audit에서 보는 것

- 같은 `group_key` 안에서
  - backfill source 행의 `abs(current_profit)` 중앙값
  - non-backfill source 행의 `abs(current_profit)` 중앙값
  - 두 값의 비율 `scale_ratio_hint`
- 같은 `checkpoint_id` 안에서
  - backfill / non-backfill peer ratio가 반복되는지
- `giveback_ratio`는 거의 0인데 `current_profit`만 매우 큰지

## 해석 기준

- `scale_ratio_hint >= 10`
  - `source_scale_incompatibility_likely`
- `scale_ratio_hint >= 5`
  - `source_scale_incompatibility_possible`
- live peer가 너무 적으면
  - `insufficient_live_peer_reference`

## 현재 의도

이 audit는 아직 값을 자동 정규화하지 않는다.

대신 아래 결론을 먼저 내리기 위한 레이어다.

- raw `current_profit`을 그대로 rule patch 근거로 써도 되는가
- 아니면 source별 scale이 섞여 있으니
  `backfill normalization hint`를 별도 축으로 둬야 하는가

## 산출물

- service:
  - [path_checkpoint_backfill_value_normalization_audit.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\path_checkpoint_backfill_value_normalization_audit.py)
- builder:
  - [build_checkpoint_backfill_value_normalization_audit.py](C:\Users\bhs33\Desktop\project\cfd\scripts\build_checkpoint_backfill_value_normalization_audit.py)
- artifact:
  - [checkpoint_backfill_value_normalization_audit_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_backfill_value_normalization_audit_latest.json)

## 다음 판단

이 audit에서 `source_scale_incompatibility_likely`가 반복되면,
다음 단계는 rule patch가 아니라 아래 둘 중 하나다.

- `closed_trade_*_backfill`용 normalized profit hint 추가
- PA7 processor에서 raw value 대신 normalized comparison hint 사용
