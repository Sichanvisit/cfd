"use client";

export default function GlobalError({ error, reset }) {
  return (
    <html lang="ko">
      <body style={{ margin: 0 }}>
        <main style={{ padding: 24, fontFamily: "system-ui, sans-serif" }}>
          <h2>치명적 오류가 발생했습니다.</h2>
          <p style={{ opacity: 0.75 }}>{String(error?.message || "알 수 없는 오류")}</p>
          <button onClick={() => reset()} style={{ marginTop: 12, padding: "8px 12px" }}>
            다시 시도
          </button>
        </main>
      </body>
    </html>
  );
}
