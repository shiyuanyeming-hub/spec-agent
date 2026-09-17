import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Spec Agent · 多语种 PRD 生成",
  description: "把模糊需求变成中日英三语标准 PRD 的多智能体流水线",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
