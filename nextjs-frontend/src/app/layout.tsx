'use client';

import '@ant-design/v5-patch-for-react-19';
import React from 'react';
import { Inter } from 'next/font/google';
import './globals.css';
import { ConfigProvider, App } from 'antd';
import zhCN from 'antd/locale/zh_CN';

const inter = Inter({ subsets: ['latin'] });

const theme = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 6,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <head>
        <title>CSRC Case Analysis System</title>
        <meta name="description" content="China Securities Regulatory Commission Case Analysis System" />
      </head>
      <body className={inter.className} suppressHydrationWarning={true}>
        <ConfigProvider theme={theme} locale={zhCN}>
          <App>
            {children}
          </App>
        </ConfigProvider>
      </body>
    </html>
  );
}