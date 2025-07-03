'use client';
import React, { useState, useEffect } from 'react';
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
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  DownloadOutlined,
  EyeOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
  BarChartOutlined,
  TagsOutlined,
  SplitCellsOutlined,
} from '@ant-design/icons';
import { caseApi } from '@/services/api';

const { Text, Title } = Typography;

interface DownloadDataStats {
  caseDetail: { data: any[]; count: number; uniqueCount: number };
  analysisData: { data: any[]; count: number; uniqueCount: number };
  categoryData: { data: any[]; count: number; uniqueCount: number };
  splitData: { data: any[]; count: number; uniqueCount: number };
}

interface DownloadItem {
  id: string;
  name: string;
  type: 'caseDetail' | 'analysisData' | 'categoryData' | 'splitData';
  count: number;
  uniqueCount: number;
  downloadStatus: 'ready' | 'downloading' | 'completed' | 'failed';
  downloadProgress: number;
  fileName?: string;
  errorMessage?: string;
}

const CaseDownload: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [dataLoading, setDataLoading] = useState(true);
  const [downloadItems, setDownloadItems] = useState<DownloadItem[]>([]);
  const [selectedRows, setSelectedRows] = useState<string[]>([]);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedItem, setSelectedItem] = useState<DownloadItem | null>(null);
  const [overallProgress, setOverallProgress] = useState(0);
  const [dataStats, setDataStats] = useState<DownloadDataStats | null>(null);

  // Get current date string
  const getCurrentDateString = () => {
    const now = new Date();
    return now.getFullYear().toString() + 
           (now.getMonth() + 1).toString().padStart(2, '0') + 
           now.getDate().toString().padStart(2, '0');
  };

  // Load download data statistics
  const loadDownloadData = async () => {
    try {
      setDataLoading(true);
      const stats = await caseApi.getDownloadData();
      setDataStats(stats);
      
      const dateStr = getCurrentDateString();
      const items: DownloadItem[] = [
        {
          id: 'caseDetail',
          name: '案例数据',
          type: 'caseDetail',
          count: stats.caseDetail.count,
          uniqueCount: stats.caseDetail.uniqueCount,
          downloadStatus: 'ready',
          downloadProgress: 0,
          fileName: `csrcdtlall${dateStr}.csv`,
        },
        {
          id: 'analysisData',
          name: '分析数据',
          type: 'analysisData',
          count: stats.analysisData.count,
          uniqueCount: stats.analysisData.uniqueCount,
          downloadStatus: 'ready',
          downloadProgress: 0,
          fileName: `csrc2analysis${dateStr}.csv`,
        },
        {
          id: 'categoryData',
          name: '分类数据',
          type: 'categoryData',
          count: stats.categoryData.count,
          uniqueCount: stats.categoryData.uniqueCount,
          downloadStatus: 'ready',
          downloadProgress: 0,
          fileName: `csrccat${dateStr}.csv`,
        },
        {
          id: 'splitData',
          name: '拆分数据',
          type: 'splitData',
          count: stats.splitData.count,
          uniqueCount: stats.splitData.uniqueCount,
          downloadStatus: 'ready',
          downloadProgress: 0,
          fileName: `csrcsplit${dateStr}.csv`,
        },
      ];
      
      setDownloadItems(items);
    } catch (error) {
      console.error('Failed to load download data:', error);
      message.error('加载下载数据失败');
    } finally {
      setDataLoading(false);
    }
  };

  useEffect(() => {
    loadDownloadData();
  }, []);

  const columns = [
    {
      title: '数据类型',
      dataIndex: 'name',
      key: 'name',
      width: '20%',
      render: (name: string, record: DownloadItem) => {
        const iconMap = {
          caseDetail: <DatabaseOutlined className="text-blue-500" />,
          analysisData: <BarChartOutlined className="text-green-500" />,
          categoryData: <TagsOutlined className="text-orange-500" />,
          splitData: <SplitCellsOutlined className="text-purple-500" />,
        };
        return (
          <Space>
            {iconMap[record.type]}
            <Text strong>{name}</Text>
          </Space>
        );
      },
    },
    {
      title: '数据量',
      dataIndex: 'count',
      key: 'count',
      width: '12%',
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: '唯一ID数',
      dataIndex: 'uniqueCount',
      key: 'uniqueCount',
      width: '12%',
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: '文件名',
      dataIndex: 'fileName',
      key: 'fileName',
      width: '25%',
      ellipsis: true,
    },
    {
      title: '下载状态',
      dataIndex: 'downloadStatus',
      key: 'downloadStatus',
      width: '15%',
      render: (status: string, record: DownloadItem) => {
        const statusConfig = {
          ready: { color: 'default', text: '准备就绪' },
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
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => downloadSingleFile(record)}
            disabled={record.downloadStatus === 'downloading'}
          >
            下载
          </Button>
        </Space>
      ),
    },
  ];

  const showDetail = (item: DownloadItem) => {
    setSelectedItem(item);
    setDetailVisible(true);
  };

  // Download single file
  const downloadSingleFile = async (item: DownloadItem) => {
    try {
      // Update status to downloading
      setDownloadItems(prev => 
        prev.map(prevItem => 
          prevItem.id === item.id
            ? { ...prevItem, downloadStatus: 'downloading' as const, downloadProgress: 0 }
            : prevItem
        )
      );

      let blob: Blob;
      
      // Call appropriate API based on type
      switch (item.type) {
        case 'caseDetail':
          blob = await caseApi.downloadCaseDetail();
          break;
        case 'analysisData':
          blob = await caseApi.downloadAnalysisData();
          break;
        case 'categoryData':
          blob = await caseApi.downloadCategoryData();
          break;
        case 'splitData':
          blob = await caseApi.downloadSplitData();
          break;
        default:
          throw new Error('Unknown download type');
      }

      // Simulate progress
      for (let progress = 0; progress <= 100; progress += 20) {
        await new Promise(resolve => setTimeout(resolve, 100));
        setDownloadItems(prev => 
          prev.map(prevItem => 
            prevItem.id === item.id
              ? { ...prevItem, downloadProgress: progress }
              : prevItem
          )
        );
      }

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = item.fileName || `${item.name}.csv`;
      link.click();
      window.URL.revokeObjectURL(url);

      // Update status to completed
      setDownloadItems(prev => 
        prev.map(prevItem => 
          prevItem.id === item.id
            ? { ...prevItem, downloadStatus: 'completed' as const, downloadProgress: 100 }
            : prevItem
        )
      );

      message.success(`${item.name}下载完成`);
    } catch (error) {
      console.error('Download failed:', error);
      
      // Update status to failed
      setDownloadItems(prev => 
        prev.map(prevItem => 
          prevItem.id === item.id
            ? { 
                ...prevItem, 
                downloadStatus: 'failed' as const, 
                errorMessage: error instanceof Error ? error.message : '下载失败'
              }
            : prevItem
        )
      );
      
      message.error(`${item.name}下载失败`);
    }
  };

  const handleBatchDownload = async () => {
    if (selectedRows.length === 0) {
      message.warning('请选择要下载的数据');
      return;
    }

    try {
      setLoading(true);
      setOverallProgress(0);
      
      const selectedItems = downloadItems.filter(item => 
        selectedRows.includes(item.id) && item.downloadStatus === 'ready'
      );
      
      for (let i = 0; i < selectedItems.length; i++) {
        const item = selectedItems[i];
        await downloadSingleFile(item);
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
    
    // Reset failed items to ready
    setDownloadItems(prev => 
      prev.map(item => 
        item.downloadStatus === 'failed'
          ? { ...item, downloadStatus: 'ready' as const, downloadProgress: 0, errorMessage: undefined }
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
      ready: downloadItems.filter(item => item.downloadStatus === 'ready').length,
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
            <Title level={3} className="text-orange-600">{statusCounts.ready}</Title>
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
              disabled={selectedRows.length === 0 || loading || !downloadItems.some(item => selectedRows.includes(item.id) && item.downloadStatus === 'ready')}
            >
              批量下载 ({selectedRows.length})
            </Button>
            <Button
              icon={<CheckCircleOutlined />}
              onClick={handleRetryFailed}
              disabled={statusCounts.failed === 0 || loading}
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
          <Button key="close" onClick={() => setDetailVisible(false)}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {selectedItem && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="数据类型">
              {selectedItem.name}
            </Descriptions.Item>
            <Descriptions.Item label="数据量">
              {selectedItem.count?.toLocaleString() || 0}
            </Descriptions.Item>
            <Descriptions.Item label="唯一ID数">
              {selectedItem.uniqueCount?.toLocaleString() || 0}
            </Descriptions.Item>
            <Descriptions.Item label="文件名">
              {selectedItem.fileName}
            </Descriptions.Item>
            <Descriptions.Item label="下载状态">
              <Tag color={
                selectedItem.downloadStatus === 'completed' ? 'success' :
                selectedItem.downloadStatus === 'failed' ? 'error' :
                selectedItem.downloadStatus === 'downloading' ? 'processing' : 'default'
              }>
                {{
                  ready: '准备就绪',
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