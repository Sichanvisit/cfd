"use client";

import { useEffect } from "react";

export default function Error({ error, reset }) {
  useEffect(() => {
    // Keep console visibility for dev diagnostics.
    console.error(error);
  }, [error]);

  return (
    <main style={{ padding: 24, fontFamily: "system-ui, sans-serif" }}>
      <h2>페이지 처리 중 오류가 발생했습니다.</h2>
      <p style={{ opacity: 0.75 }}>잠시 후 다시 시도해 주세요.</p>
      <button onClick={() => reset()} style={{ marginTop: 12, padding: "8px 12px" }}>
        다시 시도
      </button>
    </main>
  );
}
