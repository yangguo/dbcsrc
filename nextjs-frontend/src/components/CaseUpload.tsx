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
  Form,
  Input,
  Select,
  Descriptions,
  Steps,
  Divider,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  CloudUploadOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  FileTextOutlined,
  DownloadOutlined,
  DiffOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import apiClient, { caseApi } from '../services/api';

const { Text, Title } = Typography;
const { Option } = Select;
const { Step } = Steps;

interface CaseData {
  链接: string;
  标题: string;
  机构: string;
  发文日期: string;
  文号?: string;
  当事人?: string;
  处罚金额?: number;
  违规类型?: string;
  内容?: string;
}

interface UploadItem extends CaseData {
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  uploadProgress: number;
  errorMessage?: string;
  isOnline?: boolean;
}



interface UploadStats {
  total: number;
  pending: number;
  uploading: number;
  completed: number;
  failed: number;
  caseDetailCount: number;
  caseDetailUniqueCount: number;
  analysisDataCount: number;
  analysisDataUniqueCount: number;
  categoryDataCount: number;
  categoryDataUniqueCount: number;
  splitDataCount: number;
  splitDataUniqueCount: number;
  onlineDataCount: number;
  onlineDataUniqueCount: number;
  diffDataCount: number;
  diffDataUniqueCount: number;
}

const CaseUpload: React.FC = () => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [dataLoading, setDataLoading] = useState(false);
  const [uploadItems, setUploadItems] = useState<UploadItem[]>([]);
  const [onlineData, setOnlineData] = useState<CaseData[]>([]);
  const [diffData, setDiffData] = useState<UploadItem[]>([]);
  const [selectedRows, setSelectedRows] = useState<string[]>([]);
  const [detailVisible, setDetailVisible] = useState(false);

  const [selectedItem, setSelectedItem] = useState<UploadItem | null>(null);
  const [overallProgress, setOverallProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(100);
  const [stats, setStats] = useState<UploadStats>({
    total: 0,
    pending: 0,
    uploading: 0,
    completed: 0,
    failed: 0,
    caseDetailCount: 0,
    caseDetailUniqueCount: 0,
    analysisDataCount: 0,
    analysisDataUniqueCount: 0,
    categoryDataCount: 0,
    categoryDataUniqueCount: 0,
    splitDataCount: 0,
    splitDataUniqueCount: 0,
    onlineDataCount: 0,
    onlineDataUniqueCount: 0,
    diffDataCount: 0,
    diffDataUniqueCount: 0,
  });


  // Load upload data
  const loadUploadData = async () => {
    try {
      setDataLoading(true);
      
      // Get upload data from backend API with extended timeout
      const response = await apiClient.get('/api/upload-data', {
        timeout: 180000, // 3 minutes timeout for this specific request
      });
      const data = response.data?.data || {};
      
      // Use backend-generated diff data directly (cases not in online)
      const diffData = data.diffData?.data || [];
      const diffItems: UploadItem[] = diffData.map((item: CaseData) => ({
        ...item,
        status: 'pending' as const,
        uploadProgress: 0,
        isOnline: false,
      }));
      
      setDiffData(diffItems);
      
      // Set upload items to only show pending items (diff data)
      setUploadItems(diffItems);
      
      // Keep online items for statistics only
      const onlineItems: UploadItem[] = (data.onlineData?.data || []).map((item: CaseData) => ({
        ...item,
        status: 'completed' as const,
        uploadProgress: 100,
        isOnline: true,
      }));
      
      // Update stats - use backend counts for accurate totals
      setStats({
        total: data.diffData?.count || diffItems.length,
        pending: data.diffData?.count || diffItems.length,
        uploading: 0,
        completed: data.onlineData?.count || onlineItems.length,
        failed: 0,
        caseDetailCount: data.caseDetail?.count || 0,
        caseDetailUniqueCount: data.caseDetail?.uniqueCount || 0,
        analysisDataCount: data.analysisData?.count || 0,
        analysisDataUniqueCount: data.analysisData?.uniqueCount || 0,
        categoryDataCount: data.categoryData?.count || 0,
        categoryDataUniqueCount: data.categoryData?.uniqueCount || 0,
        splitDataCount: data.splitData?.count || 0,
        splitDataUniqueCount: data.splitData?.uniqueCount || 0,
        onlineDataCount: data.onlineData?.count || 0,
        onlineDataUniqueCount: data.onlineData?.uniqueCount || 0,
        diffDataCount: data.diffData?.count || 0,
        diffDataUniqueCount: data.diffData?.uniqueCount || 0,
      });
      
      // Set online data
      setOnlineData(data.onlineData?.data || []);
      
    } catch (error: any) {
      console.error('Failed to load upload data:', error);
      
      // Provide more specific error messages
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        message.error('加载数据超时，请检查网络连接或稍后重试');
      } else if (error.response?.status === 500) {
        message.error('服务器内部错误，请稍后重试');
      } else if (error.response?.status === 404) {
        message.error('数据接口不存在');
      } else {
        message.error(`加载上线数据失败: ${error.message || '未知错误'}`);
      }
    } finally {
      setDataLoading(false);
    }
  };

  useEffect(() => {
    loadUploadData();
  }, []);

  // Handle pagination changes
  const handlePageChange = (page: number, size?: number) => {
    setCurrentPage(page);
    if (size && size !== pageSize) {
      setPageSize(size);
      setCurrentPage(1); // Reset to first page when page size changes
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: '链接',
      key: '链接',
      width: 80,
      ellipsis: true,
      fixed: 'left' as const,
      render: (url: string) => {
        // 从URL中提取ID或使用URL的最后部分作为ID
        const id = url.split('/').pop() || url.substring(url.length - 8);
        return <span title={url}>{id}</span>;
      },
    },
    {
      title: '名称',
      dataIndex: '名称',
      key: '名称',
      width: 200,
      ellipsis: true,
      render: (text: string) => (
        <span title={text}>{text || '-'}</span>
      ),
    },
    {
      title: '文号',
      dataIndex: '文号',
      key: '文号',
      width: 150,
      ellipsis: true,
      render: (text: string) => (
        <span title={text}>{text || '-'}</span>
      ),
    },
    {
      title: '发文日期',
      dataIndex: '发文日期',
      key: '发文日期',
      width: 100,
      ellipsis: true,
    },
    {
      title: '序列号',
      dataIndex: '序列号',
      key: '序列号',
      width: 100,
      ellipsis: true,
      render: (text: string) => (
        <span title={text}>{text || '-'}</span>
      ),
    },
    {
      title: '机构',
      dataIndex: '机构',
      key: '机构',
      width: 120,
      ellipsis: true,
    },
    {
      title: '内容',
      dataIndex: '内容',
      key: '内容',
      width: 300,
      ellipsis: true,
      render: (text: string) => (
        <span title={text}>{text?.substring(0, 100)}...</span>
      ),
    },
    {
      title: '处罚金额',
      dataIndex: 'amount',
      key: 'amount',
      width: 100,
      render: (amount: any) => {
        if (amount === undefined || amount === null || amount === '' || isNaN(Number(amount))) {
          return '0';
        }
        return Number(amount).toLocaleString();
      },
    },
    {
      title: '违规类型',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      ellipsis: true,
      render: (category: string) => (
        category ? <Tag color="blue">{category}</Tag> : '-'
      ),
    },
    {
      title: '省份',
      dataIndex: 'province',
      key: 'province',
      width: 100,
      ellipsis: true,
      render: (text: string) => (
        <span title={text}>{text || '-'}</span>
      ),
    },
    {
      title: '行业',
      dataIndex: 'industry',
      key: 'industry',
      width: 120,
      ellipsis: true,
      render: (text: string) => (
        <span title={text}>{text || '-'}</span>
      ),
    },
    {
      title: '当事人',
      dataIndex: 'people',
      key: 'people',
      width: 120,
      ellipsis: true,
      render: (text: string) => (
        <span title={text}>{text || '-'}</span>
      ),
    },
    {
      title: '违法事实',
      dataIndex: 'event',
      key: 'event',
      width: 200,
      ellipsis: true,
      render: (text: string) => (
        <span title={text}>{text?.substring(0, 50)}...</span>
      ),
    },
    {
      title: '处罚依据',
      dataIndex: 'law',
      key: 'law',
      width: 150,
      ellipsis: true,
      render: (text: string) => (
        <span title={text}>{text?.substring(0, 50)}...</span>
      ),
    },
    {
      title: '处罚决定',
      dataIndex: 'penalty',
      key: 'penalty',
      width: 200,
      ellipsis: true,
      render: (text: string) => (
        <span title={text}>{text?.substring(0, 50)}...</span>
      ),
    },
    {
      title: '处罚机关',
      dataIndex: 'org',
      key: 'org',
      width: 120,
      ellipsis: true,
      render: (text: string) => (
        <span title={text}>{text || '-'}</span>
      ),
    },
    {
      title: '处罚日期',
      dataIndex: 'date',
      key: 'date',
      width: 100,
      ellipsis: true,
      render: (text: string) => (
        <span title={text}>{text || '-'}</span>
      ),
    },
    {
      title: '链接',
      dataIndex: '链接',
      key: '链接_url',
      width: 100,
      ellipsis: true,
      render: (url: string) => (
        <a href={url} target="_blank" rel="noopener noreferrer" title={url}>
          查看详情
        </a>
      ),
    },
    {
      title: '上线状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      fixed: 'right' as const,
      render: (status: string, record: UploadItem) => {
        const statusConfig = {
          pending: { color: 'default', text: '待上线' },
          uploading: { color: 'processing', text: '上线中' },
          completed: { color: 'success', text: '已上线' },
          failed: { color: 'error', text: '上线失败' },
        };
        
        const config = statusConfig[status as keyof typeof statusConfig];
        
        return (
          <div>
            <Tag color={config.color}>{config.text}</Tag>
            {status === 'uploading' && (
              <Progress
                percent={record.uploadProgress}
                size="small"
                className="mt-1"
              />
            )}
          </div>
        );
      },
    },
  ];



  const handleBatchUpload = async () => {
    if (selectedRows.length === 0) {
      message.warning('请选择要上线的案例');
      return;
    }

    let uploadSuccess = false;
    try {
      setLoading(true);
      setOverallProgress(0);
      setCurrentStep(0);
      
      const selectedItems = uploadItems.filter(item => 
        selectedRows.includes(item.链接) && item.status === 'pending'
      );
      
      if (selectedItems.length === 0) {
        message.warning('没有可上线的案例');
        return;
      }
      
      // Step 1: Validation
      setCurrentStep(1);
      setOverallProgress(10);
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Step 2: Upload to database
      setCurrentStep(2);
      setOverallProgress(30);
      
      // Update status to uploading for selected items
      setUploadItems(prev => 
        prev.map(prevItem => 
          selectedRows.includes(prevItem.链接)
            ? { ...prevItem, status: 'uploading' as const, uploadProgress: 0 }
            : prevItem
        )
      );
      
      // Call backend API to upload data
      console.log('开始调用上传API，案例数量:', selectedItems.length);
      const response = await apiClient.post('/api/upload-cases', {
        case_ids: selectedItems.map(item => item.链接),
      }, {
        timeout: 300000, // 5分钟超时
      });
      
      console.log('API响应:', response.data);
      
      // Check if upload was successful
      if (!response.data?.success) {
        throw new Error(response.data?.message || response.data?.error || '上传失败');
      }
      
      console.log('上传成功，继续更新进度');
      setOverallProgress(70);
      
      // Update progress for each item
      for (let i = 0; i < selectedItems.length; i++) {
        const item = selectedItems[i];
        const progress = Math.round(((i + 1) / selectedItems.length) * 100);
        
        setUploadItems(prev => 
          prev.map(prevItem => 
            prevItem.链接 === item.链接
              ? { ...prevItem, uploadProgress: progress }
              : prevItem
          )
        );
        
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
      // Step 3: Verification
      setCurrentStep(3);
      setOverallProgress(90);
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Mark as completed
      setUploadItems(prev => 
        prev.map(prevItem => 
          selectedRows.includes(prevItem.链接)
            ? {
                ...prevItem,
                status: 'completed' as const,
                uploadProgress: 100,
                isOnline: true,
              }
            : prevItem
        )
      );
      
      setOverallProgress(100);
      uploadSuccess = true;
      
      message.success(`批量上线完成，共处理 ${selectedItems.length} 个案例`);
      setSelectedRows([]);
      
      // Reload data to get updated stats
      setTimeout(() => {
        loadUploadData();
      }, 1000);
      
    } catch (error) {
      console.error('Batch upload error:', error);
      
      // Get error message
      let errorMessage = '上线失败，请重试';
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      }
      
      message.error(`批量上线失败: ${errorMessage}`);
      
      // Mark failed items
      setUploadItems(prev => 
        prev.map(prevItem => 
          selectedRows.includes(prevItem.链接)
            ? {
                ...prevItem,
                status: 'failed' as const,
                errorMessage: errorMessage,
              }
            : prevItem
        )
      );
    } finally {
      setLoading(false);
      // 根据上传结果决定如何重置进度
      if (uploadSuccess) {
        // 成功时延迟重置，让用户看到完成状态
        setTimeout(() => {
          setOverallProgress(0);
          setCurrentStep(0);
        }, 3000);
      } else {
        // 失败时立即重置
        setOverallProgress(0);
        setCurrentStep(0);
      }
    }
  };

  const handleRetryFailed = async () => {
    const failedItems = uploadItems.filter(item => item.status === 'failed');
    
    if (failedItems.length === 0) {
      message.info('没有失败的上线任务');
      return;
    }
    
    // Reset failed items to pending
    setUploadItems(prev => 
      prev.map(item => 
        item.status === 'failed'
          ? { ...item, status: 'pending' as const, uploadProgress: 0, errorMessage: undefined }
          : item
      )
    );
    
    message.success(`已重置 ${failedItems.length} 个失败任务`);
  };



  const handleDownloadOnlineData = async () => {
    try {
      setLoading(true);
      message.info('正在下载在线数据，请稍候...');
      
      const blob = await caseApi.downloadOnlineData();
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `online_csrc2analysis_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      message.success('在线数据下载成功');
    } catch (error) {
      message.error('下载在线数据失败');
      console.error('Download error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadDiffData = async () => {
    try {
      setLoading(true);
      message.info('正在下载差异数据，请稍候...');
      
      const blob = await caseApi.downloadDiffData();
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `diff_csrc2analysis_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      message.success('差异数据下载成功');
    } catch (error) {
      message.error(`下载差异数据失败：${error instanceof Error ? error.message : String(error)}`);
      console.error('Download error:', error);
    } finally {
      setLoading(false);
    }
  };



  const rowSelection = {
    selectedRowKeys: selectedRows,
    onChange: (selectedRowKeys: React.Key[]) => {
      setSelectedRows(selectedRowKeys as string[]);
    },
    getCheckboxProps: (record: UploadItem) => ({
      disabled: record.status === 'uploading' || record.status === 'completed',
    }),
  };

  const pendingCount = uploadItems.filter(item => item.status === 'pending').length;
  const uploadingCount = uploadItems.filter(item => item.status === 'uploading').length;
  const completedCount = uploadItems.filter(item => item.status === 'completed').length;
  const failedCount = uploadItems.filter(item => item.status === 'failed').length;

  const statusCounts = {
    total: uploadItems.length,
    pending: pendingCount,
    uploading: uploadingCount,
    completed: completedCount,
    failed: failedCount,
  };

  const uploadSteps = [
    {
      title: '准备',
      description: '准备上线数据',
    },
    {
      title: '验证',
      description: '验证数据完整性',
    },
    {
      title: '上线',
      description: '上传到目标环境',
    },
    {
      title: '完成',
      description: '验证上线结果',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Data Statistics */}
      <Card title="数据统计概览" loading={dataLoading}>
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <Statistic
              title="案例数据量"
              value={stats.caseDetailCount}
              suffix={`/ ${stats.caseDetailUniqueCount} 唯一`}
              prefix={<FileTextOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="分析数据量"
              value={stats.analysisDataCount}
              suffix={`/ ${stats.analysisDataUniqueCount} 唯一`}
              prefix={<DatabaseOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="分类数据量"
              value={stats.categoryDataCount}
              suffix={`/ ${stats.categoryDataUniqueCount} 唯一`}
              prefix={<DatabaseOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="拆分数据量"
              value={stats.splitDataCount}
              suffix={`/ ${stats.splitDataUniqueCount} 唯一`}
              prefix={<DatabaseOutlined />}
            />
          </Col>
        </Row>
        <Divider />
        <Row gutter={[16, 16]}>
          <Col span={8}>
            <Statistic
              title="在线数据量"
              value={stats.onlineDataCount}
              suffix={`/ ${stats.onlineDataUniqueCount} 唯一`}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="待上线数据量（三表交集）"
              value={stats.diffDataCount}
              suffix={`/ ${stats.diffDataUniqueCount} 唯一`}
              prefix={<DiffOutlined style={{ color: '#1890ff' }} />}
            />
          </Col>
          <Col span={8}>
            <div className="text-center">
              <Text strong style={{ color: '#1890ff' }}>待上线列表逻辑</Text>
              <br />
              <Text type="secondary" style={{ fontSize: '12px' }}>
                csrc2analysis ∩ csrc2cat ∩ csrc2split - 在线数据
              </Text>
              <br />
              <Text type="secondary" style={{ fontSize: '11px' }}>
                （三个表的交集，排除已在线案例）
              </Text>
            </div>
          </Col>
        </Row>
        
        <Divider />
        
        <Space>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleDownloadOnlineData}
          >
            下载在线数据
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleDownloadDiffData}
            disabled={stats.diffDataCount === 0}
          >
            下载差异数据
          </Button>

          <Button
            icon={<SyncOutlined />}
            onClick={loadUploadData}
            loading={dataLoading}
          >
            刷新数据
          </Button>
        </Space>
      </Card>

      {/* Status Overview */}
      <Card title="上线状态概览">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="text-center">
            <Title level={3} className="text-blue-600">{statusCounts.total}</Title>
            <Text>总计</Text>
          </div>
          <div className="text-center">
            <Title level={3} className="text-orange-600">{statusCounts.pending}</Title>
            <Text>待上线</Text>
          </div>
          <div className="text-center">
            <Title level={3} className="text-purple-600">{statusCounts.uploading}</Title>
            <Text>上线中</Text>
          </div>
          <div className="text-center">
            <Title level={3} className="text-green-600">{statusCounts.completed}</Title>
            <Text>已上线</Text>
          </div>
          <div className="text-center">
            <Title level={3} className="text-red-600">{statusCounts.failed}</Title>
            <Text>失败</Text>
          </div>
        </div>
      </Card>

      {/* Upload Progress */}
      {loading && (
        <Card title="上线进度">
          <div className="space-y-4">
            <Steps current={currentStep} items={uploadSteps} />
            {overallProgress > 0 && (
              <Progress
                percent={overallProgress}
                status={overallProgress === 100 ? 'success' : 'active'}
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />
            )}
          </div>
        </Card>
      )}

      {/* Upload Table */}
      <Card 
        title="待上线列表（三表交集）"
        extra={
          <Space>
            <Button
              type="primary"
              icon={<CloudUploadOutlined />}
              onClick={handleBatchUpload}
              disabled={selectedRows.length === 0 || loading}
            >
              批量上线 ({selectedRows.length})
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
          dataSource={uploadItems}
          rowKey={(record) => record.链接 || `row-${Math.random()}`}
          rowSelection={rowSelection}
          loading={loading || dataLoading}
          pagination={{
            current: currentPage,
            pageSize: pageSize,
            total: uploadItems.length,
            showSizeChanger: true,
            showQuickJumper: true,
            pageSizeOptions: uploadItems.length <= 1000 
              ? ['50', '100', '200', '500', '1000', '全部']
              : ['50', '100', '200', '500', '1000'],
            showTotal: (total, range) => {
              return `显示第 ${range[0]}-${range[1]} 条，共 ${total} 条待上线数据`;
            },
            onChange: handlePageChange,
            onShowSizeChange: handlePageChange
          }}
          scroll={{ x: 2800, y: 400 }}
          size="small"
        />
      </Card>

      {/* Detail Modal */}
      <Modal
        title="上线详情"
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
            <Descriptions.Item label="案例标题">
              {selectedItem.标题}
            </Descriptions.Item>
            <Descriptions.Item label="机构">
              {selectedItem.机构}
            </Descriptions.Item>
            <Descriptions.Item label="违规类型">
              {selectedItem.违规类型 ? (
                <Tag color="blue">{selectedItem.违规类型}</Tag>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="发文日期">
              {selectedItem.发文日期}
            </Descriptions.Item>
            {selectedItem.文号 && (
              <Descriptions.Item label="文号">
                {selectedItem.文号}
              </Descriptions.Item>
            )}
            {selectedItem.当事人 && (
              <Descriptions.Item label="当事人">
                {selectedItem.当事人}
              </Descriptions.Item>
            )}
            {selectedItem.处罚金额 && (
              <Descriptions.Item label="处罚金额">
                {selectedItem.处罚金额.toLocaleString()} 元
              </Descriptions.Item>
            )}
            <Descriptions.Item label="链接">
              <a href={selectedItem.链接} target="_blank" rel="noopener noreferrer">
                {selectedItem.链接}
              </a>
            </Descriptions.Item>
            <Descriptions.Item label="上线状态">
              <Tag color={
                selectedItem.status === 'completed' ? 'success' :
                selectedItem.status === 'failed' ? 'error' :
                selectedItem.status === 'uploading' ? 'processing' : 'default'
              }>
                {{
                  pending: '待上线',
                  uploading: '上线中',
                  completed: '已上线',
                  failed: '上线失败',
                }[selectedItem.status]}
              </Tag>
            </Descriptions.Item>
            {selectedItem.status === 'uploading' && (
              <Descriptions.Item label="上线进度">
                <Progress percent={selectedItem.uploadProgress} />
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

export default CaseUpload;