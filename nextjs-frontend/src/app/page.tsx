'use client';

import React, { useState } from 'react';
import { Layout, Menu, theme } from 'antd';
import {
  BarChartOutlined,
  SearchOutlined,
  SyncOutlined,
  FileTextOutlined,
  TagsOutlined,
  DownloadOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import CaseSummary from '@/components/CaseSummary';
import CaseSearch from '@/components/CaseSearch';
import CaseUpdate from '@/components/CaseUpdate';
import AttachmentProcessing from '@/components/AttachmentProcessing';
import CaseClassification from '@/components/CaseClassification';
import CaseDownload from '@/components/CaseDownload';
import CaseUpload from '@/components/CaseUpload';
import DebugApiTest from '@/components/DebugApiTest';

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
    label: '案例搜索2',
  },
  {
    key: 'update',
    icon: <SyncOutlined />,
    label: '案例更新2',
  },
  {
    key: 'attachment',
    icon: <FileTextOutlined />,
    label: '附件处理2',
  },
  {
    key: 'classification',
    icon: <TagsOutlined />,
    label: '案例分类2',
  },
  {
    key: 'download',
    icon: <DownloadOutlined />,
    label: '案例下载2',
  },
  {
    key: 'upload',
    icon: <CloudUploadOutlined />,
    label: '案例上线2',
  },
];

const renderContent = (selectedKey: string) => {
  switch (selectedKey) {
    case 'summary':
      return (
        <div>
          <CaseSummary />
          <DebugApiTest />
        </div>
      );
    case 'search':
      return <CaseSearch />;
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
    default:
      return (
        <div>
          <CaseSummary />
          <DebugApiTest />
        </div>
      );
  }
};

export default function Home() {
  const [selectedKey, setSelectedKey] = useState('summary');
  const [collapsed, setCollapsed] = useState(false);
  const {
    token: { colorBgContainer },
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
          borderRight: '1px solid #f0f0f0',
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
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <h1 className="text-xl font-semibold">
            {menuItems.find(item => item.key === selectedKey)?.label}
          </h1>
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