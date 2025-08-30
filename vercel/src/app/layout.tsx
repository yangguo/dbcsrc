import { ReactNode } from 'react';
import './globals.css';

export const metadata = {
  title: '处罚案例搜索',
  description: '从MongoDB搜索处罚案例',
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>
        {children}
      </body>
    </html>
  );
}

