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
  Form,
  Input,
  Select,
  Descriptions,
  Steps,
} from 'antd';
import {
  CloudUploadOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  FileTextOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;
const { Option } = Select;
const { Step } = Steps;

interface UploadItem {
  id: string;
  title: string;
  org: string;
  date: string;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  uploadProgress: number;
  url?: string;
  errorMessage?: string;
  category?: string;
}

interface UploadConfig {
  targetEnvironment: 'production' | 'staging' | 'test';
  batchSize: number;
  retryCount: number;
}

const CaseUpload: React.FC = () => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [uploadItems, setUploadItems] = useState<UploadItem[]>([]);
  const [selectedRows, setSelectedRows] = useState<string[]>([]);
  const [detailVisible, setDetailVisible] = useState(false);
  const [configVisible, setConfigVisible] = useState(false);
  const [selectedItem, setSelectedItem] = useState<UploadItem | null>(null);
  const [overallProgress, setOverallProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [uploadConfig, setUploadConfig] = useState<UploadConfig>({
    targetEnvironment: 'staging',
    batchSize: 10,
    retryCount: 3,
  });

  // Mock data for demonstration
  const mockData: UploadItem[] = [
    {
      id: '1',
      title: '关于对某某公司信息披露违规的处罚决定',
      org: '北京',
      date: '2024-01-15',
      status: 'completed',
      uploadProgress: 100,
      url: 'https://example.com/case/1',
      category: '信息披露违规',
    },
    {
      id: '2',
      title: '关于对某某证券内幕交易的处罚决定',
      org: '上海',
      date: '2024-01-14',
      status: 'pending',
      uploadProgress: 0,
      category: '内幕交易',
    },
    {
      id: '3',
      title: '关于对某某基金违规操作的处罚决定',
      org: '深圳',
      date: '2024-01-13',
      status: 'failed',
      uploadProgress: 75,
      errorMessage: '服务器连接失败',
      category: '违规操作',
    },
  ];

  React.useEffect(() => {
    setUploadItems(mockData);
  }, []);

  const columns = [
    {
      title: '案例标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      width: '30%',
    },
    {
      title: '机构',
      dataIndex: 'org',
      key: 'org',
      width: '10%',
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: '12%',
      render: (category: string) => (
        <Tag color="blue">{category}</Tag>
      ),
    },
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
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
      width: '21%',
      render: (_: any, record: UploadItem) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => showDetail(record)}
          >
            详情
          </Button>
          {record.status === 'completed' && record.url && (
            <Button
              type="link"
              icon={<CloudUploadOutlined />}
              onClick={() => window.open(record.url, '_blank')}
            >
              访问
            </Button>
          )}
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
        selectedRows.includes(item.id) && item.status === 'pending'
      );
      
      // Step 1: Validation
      setCurrentStep(1);
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Step 2: Upload
      setCurrentStep(2);
      for (let i = 0; i < selectedItems.length; i++) {
        const item = selectedItems[i];
        
        // Update status to uploading
        setUploadItems(prev => 
          prev.map(prevItem => 
            prevItem.id === item.id
              ? { ...prevItem, status: 'uploading' as const, uploadProgress: 0 }
              : prevItem
          )
        );
        
        // Simulate upload progress
        for (let progress = 0; progress <= 100; progress += 20) {
          await new Promise(resolve => setTimeout(resolve, 200));
          
          setUploadItems(prev => 
            prev.map(prevItem => 
              prevItem.id === item.id
                ? { ...prevItem, uploadProgress: progress }
                : prevItem
            )
          );
        }
        
        // Mark as completed
        setUploadItems(prev => 
          prev.map(prevItem => 
            prevItem.id === item.id
              ? {
                  ...prevItem,
                  status: 'completed' as const,
                  uploadProgress: 100,
                  url: `https://example.com/case/${item.id}`,
                }
              : prevItem
          )
        );
        
        setOverallProgress(Math.round(((i + 1) / selectedItems.length) * 100));
      }
      
      // Step 3: Verification
      setCurrentStep(3);
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      message.success(`批量上线完成，共处理 ${selectedItems.length} 个案例`);
      setSelectedRows([]);
    } catch (error) {
      message.error('批量上线失败');
      console.error('Batch upload error:', error);
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

  const getStatusCounts = () => {
    const counts = {
      total: uploadItems.length,
      pending: uploadItems.filter(item => item.status === 'pending').length,
      uploading: uploadItems.filter(item => item.status === 'uploading').length,
      completed: uploadItems.filter(item => item.status === 'completed').length,
      failed: uploadItems.filter(item => item.status === 'failed').length,
    };
    return counts;
  };

  const statusCounts = getStatusCounts();

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
          selectedItem?.status === 'completed' && selectedItem?.url && (
            <Button
              key="visit"
              type="primary"
              icon={<CloudUploadOutlined />}
              onClick={() => selectedItem?.url && window.open(selectedItem.url, '_blank')}
            >
              访问链接
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
            <Descriptions.Item label="分类">
              <Tag color="blue">{selectedItem.category}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="日期">
              {selectedItem.date}
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
            {selectedItem.url && (
              <Descriptions.Item label="访问链接">
                <a href={selectedItem.url} target="_blank" rel="noopener noreferrer">
                  {selectedItem.url}
                </a>
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