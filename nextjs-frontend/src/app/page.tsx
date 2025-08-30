'use client';

import React, { useState } from 'react';
import { Layout, Menu, theme, Button, Space } from 'antd';
import {
  BarChartOutlined,
  SearchOutlined,
  SyncOutlined,
  FileTextOutlined,
  TagsOutlined,
  DownloadOutlined,
  CloudUploadOutlined,
  SunOutlined,
  MoonOutlined,
} from '@ant-design/icons';
import { useTheme } from '@/contexts/ThemeContext';
import CaseSummary from '@/components/CaseSummary';
import CaseSearch from '@/components/CaseSearch';
import CaseUpdate from '@/components/CaseUpdate';
import AttachmentProcessing from '@/components/AttachmentProcessing';
import CaseClassification from '@/components/CaseClassification';
import CaseDownload from '@/components/CaseDownload';
import CaseUpload from '@/components/CaseUpload';
import CsrcatAnalysis from '@/components/CsrcatAnalysis';
import PenaltySearchMongo from '@/components/PenaltySearchMongo';

const { Header, Sider, Content } = Layout;

type MenuItem = {
  key: string;
  icon: React.ReactNode;
  label: string;
};

const menuItems: MenuItem[] = [
  {
    key: 'summary',
    icon: <BarChartOutlined />,
    label: '案例总数',
  },
  {
    key: 'search',
    icon: <SearchOutlined />,
    label: '处罚搜索',
  },
  {
    key: 'penalty',
    icon: <SearchOutlined />,
    label: '处罚搜索 (备选)',
  },
  {
    key: 'update',
    icon: <SyncOutlined />,
    label: '案例更新',
  },
  {
    key: 'attachment',
    icon: <FileTextOutlined />,
    label: '附件处理',
  },
  {
    key: 'classification',
    icon: <TagsOutlined />,
    label: '案例分类',
  },
  {
    key: 'download',
    icon: <DownloadOutlined />,
    label: '案例下载',
  },
  {
    key: 'upload',
    icon: <CloudUploadOutlined />,
    label: '案例上线',
  },
  {
    key: 'csrccat-analysis',
    icon: <BarChartOutlined />,
    label: '数据修复',
  },
];

const renderContent = (selectedKey: string) => {
  switch (selectedKey) {
    case 'summary':
      return <CaseSummary />;
    case 'search':
      return <CaseSearch />;
    case 'penalty':
      return <PenaltySearchMongo />;
    case 'update':
      return <CaseUpdate />;
    case 'attachment':
      return <AttachmentProcessing />;
    case 'classification':
      return <CaseClassification />;
    case 'download':
      return <CaseDownload />;
    case 'upload':
      return <CaseUpload />;
    case 'csrccat-analysis':
      return <CsrcatAnalysis />;
    default:
      return <CaseSummary />;
  }
};

export default function Home() {
  const [selectedKey, setSelectedKey] = useState('summary');
  const [collapsed, setCollapsed] = useState(false);
  const { isDarkMode, toggleTheme } = useTheme();
  const {
    token: { colorBgContainer, colorBorder },
  } = theme.useToken();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={(value) => setCollapsed(value)}
        width={250}
        style={{
          background: colorBgContainer,
          borderRight: `1px solid ${colorBorder}`,
        }}
      >
        <div className="p-4">
          <h2 className="text-lg font-bold text-center mb-4">
            {collapsed ? '案例' : '案例分析系统'}
          </h2>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => setSelectedKey(key)}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: colorBgContainer,
            borderBottom: `1px solid ${colorBorder}`,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <h1 className="text-xl font-semibold">
            {menuItems.find(item => item.key === selectedKey)?.label}
          </h1>
          <Space>
            <Button
              type="text"
              icon={isDarkMode ? <SunOutlined /> : <MoonOutlined />}
              onClick={toggleTheme}
              size="large"
              title={isDarkMode ? '切换到浅色模式' : '切换到深色模式'}
            >
              {isDarkMode ? '浅色' : '深色'}
            </Button>
          </Space>
        </Header>
        <Content
          style={{
            margin: '24px',
            padding: '24px',
            background: colorBgContainer,
            borderRadius: '8px',
            minHeight: 280,
          }}
        >
          {renderContent(selectedKey)}
        </Content>
      </Layout>
    </Layout>
  );
}
