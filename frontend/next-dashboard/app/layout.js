import "./globals.css";

export const metadata = {
  title: "CFD Dashboard",
  description: "Trading monitor for MT5 + FastAPI"
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}

