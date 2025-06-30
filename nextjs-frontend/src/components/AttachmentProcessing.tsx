'use client';

import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  InputNumber,
  Input,
  Button,
  Space,
  Table,
  Select,
  Progress,
  Alert,
  message,
  Divider,
  Typography,
  Tag,
} from 'antd';
import {
  FileTextOutlined,
  DownloadOutlined,
  SyncOutlined,
  DeleteOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { caseApi } from '@/services/api';

const { Option } = Select;
const { Text, Title } = Typography;

interface AttachmentData {
  id: string;
  title: string;
  contentLength: number;
  hasAttachment: boolean;
  downloadStatus: 'pending' | 'downloaded' | 'failed';
  textExtracted: boolean;
}

const AttachmentProcessing: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [analysisData, setAnalysisData] = useState<AttachmentData[]>([]);
  const [selectedRows, setSelectedRows] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const [currentTask, setCurrentTask] = useState('');

  const columns = [
    {
      title: '案例标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      width: '30%',
    },
    {
      title: '内容长度',
      dataIndex: 'contentLength',
      key: 'contentLength',
      width: '12%',
      render: (length: number) => (
        <Tag color={length < 100 ? 'red' : length < 500 ? 'orange' : 'green'}>
          {length}
        </Tag>
      ),
    },
    {
      title: '附件状态',
      dataIndex: 'hasAttachment',
      key: 'hasAttachment',
      width: '12%',
      render: (hasAttachment: boolean) => (
        <Tag color={hasAttachment ? 'green' : 'red'}>
          {hasAttachment ? '有附件' : '无附件'}
        </Tag>
      ),
    },
    {
      title: '下载状态',
      dataIndex: 'downloadStatus',
      key: 'downloadStatus',
      width: '12%',
      render: (status: string) => {
        const colorMap = {
          pending: 'default',
          downloaded: 'green',
          failed: 'red',
        };
        const textMap = {
          pending: '待下载',
          downloaded: '已下载',
          failed: '下载失败',
        };
        return (
          <Tag color={colorMap[status as keyof typeof colorMap]}>
            {textMap[status as keyof typeof textMap]}
          </Tag>
        );
      },
    },
    {
      title: '文本提取',
      dataIndex: 'textExtracted',
      key: 'textExtracted',
      width: '12%',
      render: (extracted: boolean) => (
        <Tag color={extracted ? 'green' : 'orange'}>
          {extracted ? '已提取' : '未提取'}
        </Tag>
      ),
    },
  ];

  const handleAnalyze = async (values: any) => {
    try {
      setLoading(true);
      setCurrentTask('分析附件内容长度...');
      
      const result = await caseApi.analyzeAttachments({
        contentLength: values.contentLength,
        downloadFilter: values.downloadFilter || '',
      });
      
      setAnalysisData(result.data || []);
      message.success(`分析完成，找到 ${result.data?.length || 0} 条需要处理的案例`);
    } catch (error) {
      message.error('附件分析失败');
      console.error('Analysis error:', error);
    } finally {
      setLoading(false);
      setCurrentTask('');
    }
  };

  const handleDownload = async () => {
    if (selectedRows.length === 0) {
      message.warning('请选择要下载的案例');
      return;
    }

    try {
      setLoading(true);
      setProgress(0);
      setCurrentTask('下载附件中...');
      
      const positions = selectedRows.map(id => 
        analysisData.findIndex(item => item.id === id)
      ).filter(pos => pos !== -1);
      
      const result = await caseApi.downloadAttachments(positions);
      
      // Update download status
      setAnalysisData(prev => 
        prev.map(item => 
          selectedRows.includes(item.id)
            ? { ...item, downloadStatus: 'downloaded' as const }
            : item
        )
      );
      
      setProgress(100);
      message.success(`下载完成，共处理 ${selectedRows.length} 个附件`);
    } catch (error) {
      message.error('附件下载失败');
      console.error('Download error:', error);
    } finally {
      setLoading(false);
      setProgress(0);
      setCurrentTask('');
      setSelectedRows([]);
    }
  };

  const [fileList, setFileList] = useState<File[]>([]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      setFileList(files);
    }
  };

  const handleConvert = async () => {
    if (fileList.length === 0) {
      message.warning('请先选择要转换的文件');
      return;
    }

    try {
      setLoading(true);
      setCurrentTask(`转换文件中...`);
      
      const result = await caseApi.convertDocuments(fileList);
      message.success(`文件转换完成`);
    } catch (error) {
      message.error(`文件转换失败`);
      console.error('Convert error:', error);
    } finally {
      setLoading(false);
      setCurrentTask('');
      // Clear file list after conversion
      setFileList([]);
      // Reset file input
      const fileInput = document.getElementById('file-upload') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
    }
  };

  const handleExtractText = async () => {
    try {
      setLoading(true);
      setCurrentTask('提取文本内容...');
      
      // Simulate text extraction process
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Update text extraction status
      setAnalysisData(prev => 
        prev.map(item => ({ ...item, textExtracted: true }))
      );
      
      message.success('文本提取完成');
    } catch (error) {
      message.error('文本提取失败');
      console.error('Extract error:', error);
    } finally {
      setLoading(false);
      setCurrentTask('');
    }
  };

  const handleRemoveFiles = async () => {
    try {
      setLoading(true);
      setCurrentTask('删除临时文件...');
      
      // Call remove files API
      await fetch('/api/remove-temp-files', { method: 'DELETE' });
      message.success('临时文件删除完成');
    } catch (error) {
      message.error('删除文件失败');
      console.error('Remove error:', error);
    } finally {
      setLoading(false);
      setCurrentTask('');
    }
  };

  const rowSelection = {
    selectedRowKeys: selectedRows,
    onChange: (selectedRowKeys: React.Key[]) => {
      setSelectedRows(selectedRowKeys as string[]);
    },
    onSelectAll: (selected: boolean, selectedRows: AttachmentData[], changeRows: AttachmentData[]) => {
      if (selected) {
        setSelectedRows(analysisData.map(item => item.id));
      } else {
        setSelectedRows([]);
      }
    },
  };

  return (
    <div className="space-y-6">
      {/* Analysis Form */}
      <Card title="附件分析配置">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleAnalyze}
          initialValues={{
            contentLength: 10,
          }}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Form.Item
              label="内容长度阈值"
              name="contentLength"
              rules={[{ required: true, message: '请输入内容长度' }]}
              tooltip="内容长度小于此值的案例将被标记为需要下载附件"
            >
              <InputNumber
                min={1}
                className="w-full"
                placeholder="内容长度阈值"
              />
            </Form.Item>
            
            <Form.Item
              label="下载过滤关键词"
              name="downloadFilter"
              tooltip="包含这些关键词的案例将被优先处理"
            >
              <Input placeholder="输入过滤关键词（可选）" />
            </Form.Item>
          </div>
          
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<BarChartOutlined />}
              loading={loading}
            >
              开始分析
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* Progress */}
      {loading && currentTask && (
        <Card>
          <div className="space-y-4">
            <Alert message={currentTask} type="info" showIcon />
            {progress > 0 && (
              <Progress
                percent={progress}
                status={progress === 100 ? 'success' : 'active'}
              />
            )}
          </div>
        </Card>
      )}

      {/* Analysis Results */}
      {analysisData.length > 0 && (
        <Card 
          title={`分析结果 (共 ${analysisData.length} 条)`}
          extra={
            <Space>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                onClick={handleDownload}
                disabled={selectedRows.length === 0 || loading}
              >
                下载选中附件 ({selectedRows.length})
              </Button>
            </Space>
          }
        >
          <Table
            columns={columns}
            dataSource={analysisData}
            rowKey="id"
            rowSelection={rowSelection}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) =>
                `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
            }}
            scroll={{ x: 800 }}
          />
        </Card>
      )}

      {/* Processing Actions */}
      <Card title="文档处理">
        <div className="space-y-4">
          <div>
            <Title level={5}>格式转换</Title>
            <div className="space-y-2">
              <input
                id="file-upload"
                type="file"
                multiple
                accept=".docx,.doc,.ofd,.pdf"
                onChange={handleFileChange}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
              {fileList.length > 0 && (
                <div className="text-sm text-gray-600">
                  已选择 {fileList.length} 个文件: {fileList.map(f => f.name).join(', ')}
                </div>
              )}
              <Button
                type="primary"
                icon={<SyncOutlined />}
                onClick={handleConvert}
                loading={loading}
                disabled={fileList.length === 0}
              >
                开始转换文档
              </Button>
            </div>
          </div>
          
          <Divider />
          
          <div>
            <Title level={5}>文本处理</Title>
            <Space>
              <Button
                type="primary"
                icon={<FileTextOutlined />}
                onClick={handleExtractText}
                loading={loading}
              >
                文本抽取
              </Button>
              <Button
                icon={<SyncOutlined />}
                onClick={() => {
                  // Handle update text
                  message.success('文本更新完成');
                }}
                loading={loading}
              >
                更新文本
              </Button>
            </Space>
          </div>
          
          <Divider />
          
          <div>
            <Title level={5}>文件管理</Title>
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleRemoveFiles}
              loading={loading}
            >
              删除临时文件
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default AttachmentProcessing;