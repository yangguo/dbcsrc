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
  EyeOutlined,
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

interface UploadConfig {
  targetEnvironment: 'production' | 'staging' | 'test';
  batchSize: number;
  retryCount: number;
}

interface UploadStats {
  caseDetailCount: number;
  caseDetailUniqueCount: number;
  analysisDataCount: number;
  analysisDataUniqueCount: number;
  categoryDataCount: number;
  categoryDataUniqueCount: number;
  splitDataCount: number;
  splitDataUniqueCount: number;
  onlineDataCount: number;
  diffDataCount: number;
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
  const [configVisible, setConfigVisible] = useState(false);
  const [selectedItem, setSelectedItem] = useState<UploadItem | null>(null);
  const [overallProgress, setOverallProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [stats, setStats] = useState<UploadStats>({
    caseDetailCount: 0,
    caseDetailUniqueCount: 0,
    analysisDataCount: 0,
    analysisDataUniqueCount: 0,
    categoryDataCount: 0,
    categoryDataUniqueCount: 0,
    splitDataCount: 0,
    splitDataUniqueCount: 0,
    onlineDataCount: 0,
    diffDataCount: 0,
  });
  const [uploadConfig, setUploadConfig] = useState<UploadConfig>({
    targetEnvironment: 'staging',
    batchSize: 10,
    retryCount: 3,
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
      
      // Update stats
      setStats({
        caseDetailCount: data.caseDetail?.count || 0,
        caseDetailUniqueCount: data.caseDetail?.uniqueCount || 0,
        analysisDataCount: data.analysisData?.count || 0,
        analysisDataUniqueCount: data.analysisData?.uniqueCount || 0,
        categoryDataCount: data.categoryData?.count || 0,
        categoryDataUniqueCount: data.categoryData?.uniqueCount || 0,
        splitDataCount: data.splitData?.count || 0,
        splitDataUniqueCount: data.splitData?.uniqueCount || 0,
        onlineDataCount: data.onlineData?.count || 0,
        diffDataCount: data.diffData?.length || 0,
      });
      
      // Set online data
      setOnlineData(data.onlineData?.data || []);
      
      // Set upload items (analysis data with upload status)
      const analysisData = data.analysisData?.data || [];
      const onlineUrls = new Set((data.onlineData?.data || []).map((item: CaseData) => item.链接));
      
      const uploadItems: UploadItem[] = analysisData.map((item: CaseData) => ({
        ...item,
        status: onlineUrls.has(item.链接) ? 'completed' as const : 'pending' as const,
        uploadProgress: onlineUrls.has(item.链接) ? 100 : 0,
        isOnline: onlineUrls.has(item.链接),
      }));
      
      setUploadItems(uploadItems);
      
      // Set diff data (items not online)
      const diffItems = uploadItems.filter(item => !item.isOnline);
      setDiffData(diffItems);
      
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

  const columns = [
    {
      title: '案例标题',
      dataIndex: '标题',
      key: '标题',
      ellipsis: true,
      width: '30%',
    },
    {
      title: '机构',
      dataIndex: '机构',
      key: '机构',
      width: '10%',
    },
    {
      title: '违规类型',
      dataIndex: '违规类型',
      key: '违规类型',
      width: '12%',
      render: (category: string) => (
        category ? <Tag color="blue">{category}</Tag> : '-'
      ),
    },
    {
      title: '发文日期',
      dataIndex: '发文日期',
      key: '发文日期',
      width: '12%',
    },
    {
      title: '上线状态',
      dataIndex: 'status',
      key: 'status',
      width: '15%',
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
    {
      title: '操作',
      key: 'action',
      width: '15%',
      render: (_: any, record: UploadItem) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => showDetail(record)}
          >
            详情
          </Button>
        </Space>
      ),
    },
  ];

  const showDetail = (item: UploadItem) => {
    setSelectedItem(item);
    setDetailVisible(true);
  };

  const handleBatchUpload = async () => {
    if (selectedRows.length === 0) {
      message.warning('请选择要上线的案例');
      return;
    }

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
      const response = await apiClient.post('/api/upload-cases', {
        cases: selectedItems.map(item => ({
          链接: item.链接,
          标题: item.标题,
          机构: item.机构,
          发文日期: item.发文日期,
          文号: item.文号,
          当事人: item.当事人,
          处罚金额: item.处罚金额,
          违规类型: item.违规类型,
          内容: item.内容,
        })),
        config: uploadConfig,
      });
      
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
      
      message.success(`批量上线完成，共处理 ${selectedItems.length} 个案例`);
      setSelectedRows([]);
      
      // Reload data to get updated stats
      setTimeout(() => {
        loadUploadData();
      }, 1000);
      
    } catch (error) {
      message.error('批量上线失败');
      console.error('Batch upload error:', error);
      
      // Mark failed items
      setUploadItems(prev => 
        prev.map(prevItem => 
          selectedRows.includes(prevItem.链接)
            ? {
                ...prevItem,
                status: 'failed' as const,
                errorMessage: '上线失败，请重试',
              }
            : prevItem
        )
      );
    } finally {
      setLoading(false);
      setOverallProgress(0);
      setCurrentStep(0);
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
      const response = await apiClient.get('/api/download/diff-data', {
        responseType: 'blob',
      });
      
      const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' });
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
      message.error('下载差异数据失败');
      console.error('Download error:', error);
    }
  };

  const handleConfigSave = (values: UploadConfig) => {
    setUploadConfig(values);
    setConfigVisible(false);
    message.success('配置保存成功');
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
      <Card title="数据统计" loading={dataLoading}>
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <Statistic
              title="案例数据量"
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
              prefix={<FileTextOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="在线数据量"
              value={stats.onlineDataCount}
              prefix={<CloudUploadOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="差异数据量"
              value={stats.diffDataCount}
              prefix={<DiffOutlined />}
            />
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
        title="上线列表"
        extra={
          <Space>
            <Button
              icon={<SyncOutlined />}
              onClick={() => setConfigVisible(true)}
            >
              配置
            </Button>
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
          rowKey="链接"
          rowSelection={rowSelection}
          loading={loading || dataLoading}
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

      {/* Configuration Modal */}
      <Modal
        title="上线配置"
        open={configVisible}
        onCancel={() => setConfigVisible(false)}
        footer={null}
        width={500}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={uploadConfig}
          onFinish={handleConfigSave}
        >
          <Form.Item
            label="目标环境"
            name="targetEnvironment"
            rules={[{ required: true, message: '请选择目标环境' }]}
          >
            <Select>
              <Option value="test">测试环境</Option>
              <Option value="staging">预发布环境</Option>
              <Option value="production">生产环境</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            label="批处理大小"
            name="batchSize"
            rules={[{ required: true, message: '请输入批处理大小' }]}
          >
            <Input type="number" min={1} max={100} />
          </Form.Item>
          
          <Form.Item
            label="重试次数"
            name="retryCount"
            rules={[{ required: true, message: '请输入重试次数' }]}
          >
            <Input type="number" min={0} max={10} />
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                保存配置
              </Button>
              <Button onClick={() => setConfigVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

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