'use client';

import '@ant-design/v5-patch-for-react-19';
import React from 'react';
import { Inter } from 'next/font/google';
import './globals.css';
import { ConfigProvider, App, theme as antdTheme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { ThemeProvider, useTheme } from '@/contexts/ThemeContext';

const inter = Inter({ subsets: ['latin'] });

const lightTheme = {
  algorithm: antdTheme.defaultAlgorithm,
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 6,
  },
};

const darkTheme = {
  algorithm: antdTheme.darkAlgorithm,
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 6,
  },
};

function AppContent({ children }: { children: React.ReactNode }) {
  const { isDarkMode } = useTheme();
  
  return (
    <ConfigProvider theme={isDarkMode ? darkTheme : lightTheme} locale={zhCN}>
      <App>
        {children}
      </App>
    </ConfigProvider>
  );
}

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
        <ThemeProvider>
          <AppContent>
            {children}
          </AppContent>
        </ThemeProvider>
      </body>
    </html>
  );
}