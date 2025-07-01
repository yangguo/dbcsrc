'use client';

import React, { useState } from 'react';
import {
  Card,
  Button,
  Table,
  Space,
  Progress,
  Alert,
  App,
  Typography,
  Tag,
  Modal,
  Descriptions,
} from 'antd';
import {
  DownloadOutlined,
  EyeOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;

interface DownloadItem {
  id: string;
  title: string;
  org: string;
  date: string;
  fileSize: number;
  downloadStatus: 'pending' | 'downloading' | 'completed' | 'failed';
  downloadProgress: number;
  filePath?: string;
  errorMessage?: string;
}

const CaseDownload: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [downloadItems, setDownloadItems] = useState<DownloadItem[]>([]);
  const [selectedRows, setSelectedRows] = useState<string[]>([]);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedItem, setSelectedItem] = useState<DownloadItem | null>(null);
  const [overallProgress, setOverallProgress] = useState(0);

  // Mock data for demonstration
  const mockData: DownloadItem[] = [
    {
      id: '1',
      title: '关于对某某公司信息披露违规的处罚决定',
      org: '北京',
      date: '2024-01-15',
      fileSize: 2048576,
      downloadStatus: 'completed',
      downloadProgress: 100,
      filePath: '/downloads/case_1.pdf',
    },
    {
      id: '2',
      title: '关于对某某证券内幕交易的处罚决定',
      org: '上海',
      date: '2024-01-14',
      fileSize: 1536000,
      downloadStatus: 'pending',
      downloadProgress: 0,
    },
    {
      id: '3',
      title: '关于对某某基金违规操作的处罚决定',
      org: '深圳',
      date: '2024-01-13',
      fileSize: 3072000,
      downloadStatus: 'failed',
      downloadProgress: 45,
      errorMessage: '网络连接超时',
    },
  ];

  React.useEffect(() => {
    setDownloadItems(mockData);
  }, []);

  const columns = [
    {
      title: '案例标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      width: '35%',
    },
    {
      title: '机构',
      dataIndex: 'org',
      key: 'org',
      width: '10%',
    },
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      width: '12%',
    },
    {
      title: '文件大小',
      dataIndex: 'fileSize',
      key: 'fileSize',
      width: '12%',
      render: (size: number) => {
        const mb = size / (1024 * 1024);
        return `${mb.toFixed(2)} MB`;
      },
    },
    {
      title: '下载状态',
      dataIndex: 'downloadStatus',
      key: 'downloadStatus',
      width: '15%',
      render: (status: string, record: DownloadItem) => {
        const statusConfig = {
          pending: { color: 'default', text: '待下载' },
          downloading: { color: 'processing', text: '下载中' },
          completed: { color: 'success', text: '已完成' },
          failed: { color: 'error', text: '下载失败' },
        };
        
        const config = statusConfig[status as keyof typeof statusConfig];
        
        return (
          <div>
            <Tag color={config.color}>{config.text}</Tag>
            {status === 'downloading' && (
              <Progress
                percent={record.downloadProgress}
                size="small"
                className="mt-1"
              />
            )}
          </div>
        );
      },
    },
    {
      title: '操作',
      key: 'action',
      width: '16%',
      render: (_: any, record: DownloadItem) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => showDetail(record)}
          >
            详情
          </Button>
          {record.downloadStatus === 'completed' && (
            <Button
              type="link"
              icon={<DownloadOutlined />}
              onClick={() => downloadFile(record)}
            >
              下载
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const showDetail = (item: DownloadItem) => {
    setSelectedItem(item);
    setDetailVisible(true);
  };

  const downloadFile = (item: DownloadItem) => {
    if (item.filePath) {
      // Create a temporary link to download the file
      const link = document.createElement('a');
      link.href = item.filePath;
      link.download = `${item.title}.pdf`;
      link.click();
      message.success('文件下载开始');
    }
  };

  const handleBatchDownload = async () => {
    if (selectedRows.length === 0) {
      message.warning('请选择要下载的案例');
      return;
    }

    try {
      setLoading(true);
      setOverallProgress(0);
      
      // Simulate batch download process
      const selectedItems = downloadItems.filter(item => 
        selectedRows.includes(item.id) && item.downloadStatus === 'pending'
      );
      
      for (let i = 0; i < selectedItems.length; i++) {
        const item = selectedItems[i];
        
        // Update status to downloading
        setDownloadItems(prev => 
          prev.map(prevItem => 
            prevItem.id === item.id
              ? { ...prevItem, downloadStatus: 'downloading' as const, downloadProgress: 0 }
              : prevItem
          )
        );
        
        // Simulate download progress
        for (let progress = 0; progress <= 100; progress += 10) {
          await new Promise(resolve => setTimeout(resolve, 100));
          
          setDownloadItems(prev => 
            prev.map(prevItem => 
              prevItem.id === item.id
                ? { ...prevItem, downloadProgress: progress }
                : prevItem
            )
          );
        }
        
        // Mark as completed
        setDownloadItems(prev => 
          prev.map(prevItem => 
            prevItem.id === item.id
              ? {
                  ...prevItem,
                  downloadStatus: 'completed' as const,
                  downloadProgress: 100,
                  filePath: `/downloads/case_${item.id}.pdf`,
                }
              : prevItem
          )
        );
        
        setOverallProgress(Math.round(((i + 1) / selectedItems.length) * 100));
      }
      
      message.success(`批量下载完成，共处理 ${selectedItems.length} 个文件`);
      setSelectedRows([]);
    } catch (error) {
      message.error('批量下载失败');
      console.error('Batch download error:', error);
    } finally {
      setLoading(false);
      setOverallProgress(0);
    }
  };

  const handleRetryFailed = async () => {
    const failedItems = downloadItems.filter(item => item.downloadStatus === 'failed');
    
    if (failedItems.length === 0) {
      message.info('没有失败的下载任务');
      return;
    }
    
    // Reset failed items to pending
    setDownloadItems(prev => 
      prev.map(item => 
        item.downloadStatus === 'failed'
          ? { ...item, downloadStatus: 'pending' as const, downloadProgress: 0, errorMessage: undefined }
          : item
      )
    );
    
    message.success(`已重置 ${failedItems.length} 个失败任务`);
  };

  const rowSelection = {
    selectedRowKeys: selectedRows,
    onChange: (selectedRowKeys: React.Key[]) => {
      setSelectedRows(selectedRowKeys as string[]);
    },
    getCheckboxProps: (record: DownloadItem) => ({
      disabled: record.downloadStatus === 'downloading' || record.downloadStatus === 'completed',
    }),
  };

  const getStatusCounts = () => {
    const counts = {
      total: downloadItems.length,
      pending: downloadItems.filter(item => item.downloadStatus === 'pending').length,
      downloading: downloadItems.filter(item => item.downloadStatus === 'downloading').length,
      completed: downloadItems.filter(item => item.downloadStatus === 'completed').length,
      failed: downloadItems.filter(item => item.downloadStatus === 'failed').length,
    };
    return counts;
  };

  const statusCounts = getStatusCounts();

  return (
    <div className="space-y-6">
      {/* Status Overview */}
      <Card title="下载状态概览">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="text-center">
            <Title level={3} className="text-blue-600">{statusCounts.total}</Title>
            <Text>总计</Text>
          </div>
          <div className="text-center">
            <Title level={3} className="text-orange-600">{statusCounts.pending}</Title>
            <Text>待下载</Text>
          </div>
          <div className="text-center">
            <Title level={3} className="text-purple-600">{statusCounts.downloading}</Title>
            <Text>下载中</Text>
          </div>
          <div className="text-center">
            <Title level={3} className="text-green-600">{statusCounts.completed}</Title>
            <Text>已完成</Text>
          </div>
          <div className="text-center">
            <Title level={3} className="text-red-600">{statusCounts.failed}</Title>
            <Text>失败</Text>
          </div>
        </div>
      </Card>

      {/* Progress */}
      {loading && overallProgress > 0 && (
        <Card>
          <Alert
            message="批量下载进行中..."
            description={
              <Progress
                percent={overallProgress}
                status={overallProgress === 100 ? 'success' : 'active'}
                className="mt-2"
              />
            }
            type="info"
            showIcon
          />
        </Card>
      )}

      {/* Download Table */}
      <Card 
        title="下载列表"
        extra={
          <Space>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={handleBatchDownload}
              disabled={selectedRows.length === 0 || loading}
            >
              批量下载 ({selectedRows.length})
            </Button>
            <Button
              icon={<CheckCircleOutlined />}
              onClick={handleRetryFailed}
              disabled={statusCounts.failed === 0}
            >
              重试失败任务
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={downloadItems}
          rowKey="id"
          rowSelection={rowSelection}
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
          scroll={{ x: 1000 }}
        />
      </Card>

      {/* Detail Modal */}
      <Modal
        title="下载详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          selectedItem?.downloadStatus === 'completed' && (
            <Button
              key="download"
              type="primary"
              icon={<DownloadOutlined />}
              onClick={() => selectedItem && downloadFile(selectedItem)}
            >
              下载文件
            </Button>
          ),
          <Button key="close" onClick={() => setDetailVisible(false)}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {selectedItem && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="案例标题">
              {selectedItem.title}
            </Descriptions.Item>
            <Descriptions.Item label="机构">
              {selectedItem.org}
            </Descriptions.Item>
            <Descriptions.Item label="日期">
              {selectedItem.date}
            </Descriptions.Item>
            <Descriptions.Item label="文件大小">
              {(selectedItem.fileSize / (1024 * 1024)).toFixed(2)} MB
            </Descriptions.Item>
            <Descriptions.Item label="下载状态">
              <Tag color={
                selectedItem.downloadStatus === 'completed' ? 'success' :
                selectedItem.downloadStatus === 'failed' ? 'error' :
                selectedItem.downloadStatus === 'downloading' ? 'processing' : 'default'
              }>
                {{
                  pending: '待下载',
                  downloading: '下载中',
                  completed: '已完成',
                  failed: '下载失败',
                }[selectedItem.downloadStatus]}
              </Tag>
            </Descriptions.Item>
            {selectedItem.downloadStatus === 'downloading' && (
              <Descriptions.Item label="下载进度">
                <Progress percent={selectedItem.downloadProgress} />
              </Descriptions.Item>
            )}
            {selectedItem.filePath && (
              <Descriptions.Item label="文件路径">
                {selectedItem.filePath}
              </Descriptions.Item>
            )}
            {selectedItem.errorMessage && (
              <Descriptions.Item label="错误信息">
                <Text type="danger">{selectedItem.errorMessage}</Text>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default CaseDownload;