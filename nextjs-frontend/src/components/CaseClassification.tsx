'use client';

import React, { useState } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Space,
  Upload,
  Select,
  Checkbox,
  Table,
  App,
  Typography,
  Divider,
  Tag,
  Modal,
} from 'antd';
import {
  TagsOutlined,
  UploadOutlined,
  DownloadOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { caseApi } from '@/services/api';
import type { UploadFile } from 'antd/es/upload/interface';

const { TextArea } = Input;
const { Option } = Select;
const { Text, Title } = Typography;

interface ClassificationResult {
  label: string;
  score: number;
}

interface BatchResult {
  id: string;
  text: string;
  predictions: ClassificationResult[];
}

const CaseClassification: React.FC = () => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [batchForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [singleResult, setSingleResult] = useState<ClassificationResult[] | null>(null);
  const [batchResults, setBatchResults] = useState<BatchResult[]>([]);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [resultModalVisible, setResultModalVisible] = useState(false);

  const predefinedLabels = [
    '信息披露违规',
    '内幕交易',
    '市场操纵',
    '违规减持',
    '资金占用',
    '关联交易',
    '财务造假',
    '违规担保',
    '其他违规行为',
  ];

  const handleGenerateLabels = async () => {
    try {
      setLoading(true);
      const result = await caseApi.generateLabels();
      message.success('标签生成完成');
    } catch (error) {
      message.error('标签生成失败');
      console.error('Generate labels error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSingleClassify = async (values: any) => {
    try {
      setLoading(true);
      const labels = values.labels || predefinedLabels;
      
      const result = await caseApi.classifyCases({
        article: values.text,
        candidateLabels: labels,
        multiLabel: values.multiLabel || false,
      });
      
      setSingleResult(result.predictions || []);
      message.success('分类完成');
    } catch (error) {
      message.error('分类失败');
      console.error('Classification error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBatchClassify = async (values: any) => {
    if (fileList.length === 0) {
      message.error('请上传文件');
      return;
    }

    try {
      setLoading(true);
      const file = fileList[0].originFileObj as File;
      const labels = values.batchLabels || predefinedLabels;
      
      const result = await caseApi.batchClassify(file, {
        idCol: values.idCol,
        contentCol: values.contentCol,
        candidateLabels: labels,
        multiLabel: values.batchMultiLabel || false,
      });
      
      setBatchResults(result.data || []);
      setResultModalVisible(true);
      message.success(`批量分类完成，处理了 ${result.data?.length || 0} 条记录`);
    } catch (error) {
      message.error('批量分类失败');
      console.error('Batch classification error:', error);
    } finally {
      setLoading(false);
    }
  };

  const downloadBatchResults = () => {
    if (batchResults.length === 0) return;
    
    const csvContent = [
      ['ID', '文本', '预测标签', '置信度'].join(','),
      ...batchResults.map(result => [
        result.id,
        `"${result.text.replace(/"/g, '""')}"`,
        result.predictions.map(p => p.label).join(';'),
        result.predictions.map(p => p.score.toFixed(3)).join(';'),
      ].join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'classification_results.csv';
    link.click();
  };

  const batchColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: '15%',
    },
    {
      title: '文本内容',
      dataIndex: 'text',
      key: 'text',
      ellipsis: true,
      width: '40%',
    },
    {
      title: '预测结果',
      dataIndex: 'predictions',
      key: 'predictions',
      width: '45%',
      render: (predictions: ClassificationResult[]) => (
        <Space direction="vertical" size="small">
          {predictions.slice(0, 3).map((pred, index) => (
            <Tag
              key={index}
              color={pred.score > 0.7 ? 'green' : pred.score > 0.4 ? 'orange' : 'red'}
            >
              {pred.label}: {(pred.score * 100).toFixed(1)}%
            </Tag>
          ))}
        </Space>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Generate Labels */}
      <Card title="标签管理">
        <div className="space-y-4">
          <div>
            <Text>生成待标签案例文本，用于后续的分类训练。</Text>
          </div>
          <Button
            type="primary"
            icon={<TagsOutlined />}
            onClick={handleGenerateLabels}
            loading={loading}
          >
            生成待标签文本
          </Button>
        </div>
      </Card>

      {/* Single Text Classification */}
      <Card title="单文本分类">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSingleClassify}
        >
          <Form.Item
            label="输入文本"
            name="text"
            rules={[{ required: true, message: '请输入要分类的文本' }]}
          >
            <TextArea
              rows={6}
              placeholder="请输入要分类的案例文本..."
            />
          </Form.Item>
          
          <Form.Item
            label="候选标签"
            name="labels"
            tooltip="留空则使用预定义标签"
          >
            <Select
              mode="tags"
              placeholder="输入自定义标签或使用预定义标签"
              allowClear
            >
              {predefinedLabels.map(label => (
                <Option key={label} value={label}>{label}</Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item name="multiLabel" valuePropName="checked">
            <Checkbox>多标签分类</Checkbox>
          </Form.Item>
          
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<TagsOutlined />}
              loading={loading}
            >
              开始分类
            </Button>
          </Form.Item>
        </Form>
        
        {/* Single Classification Results */}
        {singleResult && (
          <div className="mt-6">
            <Divider />
            <Title level={5}>分类结果</Title>
            <Space direction="vertical" size="small">
              {singleResult.map((result, index) => (
                <Tag
                  key={index}
                  color={result.score > 0.7 ? 'green' : result.score > 0.4 ? 'orange' : 'red'}
                  className="text-sm py-1 px-2"
                >
                  {result.label}: {(result.score * 100).toFixed(2)}%
                </Tag>
              ))}
            </Space>
          </div>
        )}
      </Card>

      {/* Batch Classification */}
      <Card title="批量分类">
        <Form
          form={batchForm}
          layout="vertical"
          onFinish={handleBatchClassify}
        >
          <Form.Item
            label="上传文件"
            required
            tooltip="支持 CSV 格式文件"
          >
            <Upload
              fileList={fileList}
              onChange={({ fileList }) => setFileList(fileList)}
              beforeUpload={() => false}
              accept=".csv"
              maxCount={1}
            >
              <Button icon={<UploadOutlined />}>选择 CSV 文件</Button>
            </Upload>
          </Form.Item>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Form.Item
              label="ID 字段"
              name="idCol"
              rules={[{ required: true, message: '请输入 ID 字段名' }]}
            >
              <Input placeholder="例如: id" />
            </Form.Item>
            
            <Form.Item
              label="内容字段"
              name="contentCol"
              rules={[{ required: true, message: '请输入内容字段名' }]}
            >
              <Input placeholder="例如: content" />
            </Form.Item>
          </div>
          
          <Form.Item
            label="候选标签"
            name="batchLabels"
            tooltip="留空则使用预定义标签"
          >
            <Select
              mode="tags"
              placeholder="输入自定义标签或使用预定义标签"
              allowClear
            >
              {predefinedLabels.map(label => (
                <Option key={label} value={label}>{label}</Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item name="batchMultiLabel" valuePropName="checked">
            <Checkbox>多标签分类</Checkbox>
          </Form.Item>
          
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<FileTextOutlined />}
              loading={loading}
              disabled={fileList.length === 0}
            >
              开始批量分类
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* Batch Results Modal */}
      <Modal
        title="批量分类结果"
        open={resultModalVisible}
        onCancel={() => setResultModalVisible(false)}
        width={1000}
        footer={[
          <Button
            key="download"
            type="primary"
            icon={<DownloadOutlined />}
            onClick={downloadBatchResults}
          >
            下载结果
          </Button>,
          <Button key="close" onClick={() => setResultModalVisible(false)}>
            关闭
          </Button>,
        ]}
      >
        <Table
          columns={batchColumns}
          dataSource={batchResults}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total, range) =>
              `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
          scroll={{ x: 800 }}
        />
      </Modal>
    </div>
  );
};

export default CaseClassification;