# PA0 Refreeze After PA4 Countertrend Topdown Exit Context Fast-Exit Bias Delta

## 기준

- baseline latest: [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)
- generated_at: `2026-04-01T20:43:14`

## 요약

이번 refreeze 기준:

- `must_hold = 0`
- `must_release = 10`
- `bad_exit = 10`

즉 immediate cleanup은 아직 없다.

## 해석

이번 축은 `TopDown-only Exit Context` family를 future close에서 더 빨리 `exit_now`로 보내는 bias 패치다.
그래서 과거 backlog가 그대로 recent 120 close window 안에 남아 있으면 숫자는 바로 줄지 않는다.

현재 top queue는 여전히 아래 residue가 채우고 있다.

- `XAUUSD 99802294`
- `XAUUSD 99848313`
- `XAUUSD 99848319`
- `NAS100 99774778`
- `NAS100 98726456`
- `BTCUSD 96740516`
- `BTCUSD 96743677`

반면 fresh weak-peak adverse row:

- `104265149`
- `104264287`
- `104262775`
- `104263033`

는 latest queue에 직접 나타나지 않았다.

## 결론

- 코드/테스트/runtime 반영: 완료
- immediate PA0 숫자 감소: 대기
- next confirmation: fresh close가 더 쌓인 뒤 same family가 queue 밖으로 빠지는지 확인
