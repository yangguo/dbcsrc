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

  // Label results table columns
  const labelColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
      ellipsis: true,
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 200,
      ellipsis: true,
      render: (text: string) => (
        <span title={text}>{text}</span>
      ),
    },
    {
      title: '文号',
      dataIndex: 'wenhao',
      key: 'wenhao',
      width: 150,
      ellipsis: true,
      render: (text: string) => (
        <span title={text}>{text || '-'}</span>
      ),
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      width: 300,
      ellipsis: true,
      render: (text: string) => (
        <span title={text}>{text?.substring(0, 100)}...</span>
      ),
    },
    {
      title: '机构',
      dataIndex: 'organization',
      key: 'organization',
      width: 150,
      ellipsis: true,
    },
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      width: 120,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => (
        <Tag color={type === 'category' ? 'blue' : 'green'}>
          {type === 'category' ? '分类' : '拆分'}
        </Tag>
      ),
    },
    {
       title: '状态',
       dataIndex: 'status',
       key: 'status',
       width: 120,
       render: (status: string) => {
         let color = 'orange';
         let text = '待标注';
         
         if (status === 'pending_category_label') {
           color = 'orange';
           text = '待分类标注';
         } else if (status === 'pending_split_label') {
           color = 'purple';
           text = '待拆分标注';
         } else if (status) {
           text = status;
         }
         
         return <Tag color={color}>{text}</Tag>;
       },
     },
  ];

  const [loading, setLoading] = useState(false);
  const [categoryResults, setCategoryResults] = useState<any[]>([]);
  const [splitResults, setSplitResults] = useState<any[]>([]);
  const [labelResultsVisible, setLabelResultsVisible] = useState(false);

  const [penaltyResult, setPenaltyResult] = useState<any>(null);
  const [penaltyBatchResults, setPenaltyBatchResults] = useState<any[]>([]);
  const [penaltyFileList, setPenaltyFileList] = useState<UploadFile[]>([]);
  const [penaltyResultModalVisible, setPenaltyResultModalVisible] = useState(false);



  const handleGenerateLabels = async () => {
    try {
      setLoading(true);
      const response = await caseApi.generateLabels();
      if (response.success) {
        // Separate category and split cases
        setCategoryResults(response.data.category_cases || []);
        setSplitResults(response.data.split_cases || []);
        setLabelResultsVisible(true);
        
        if (response.count > 0) {
          message.success(response.message);
        } else {
          message.info(response.message || '所有数据已更新，无需标注');
        }
      } else {
        message.error(response.message || '生成标签失败');
      }
    } catch (error) {
      console.error('Generate labels error:', error);
      message.error('生成标签失败');
    } finally {
      setLoading(false);
    }
  };







  const handleSinglePenaltyAnalysis = async (values: any) => {
    try {
      setLoading(true);
      const result = await caseApi.analyzePenalty(values.penaltyText);
      setPenaltyResult(result.data?.result?.data || null);
      message.success('行政处罚分析完成');
    } catch (error) {
      message.error('行政处罚分析失败');
      console.error('Penalty analysis error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBatchPenaltyAnalysis = async (values: any) => {
    if (penaltyFileList.length === 0) {
      message.error('请上传文件');
      return;
    }

    try {
      setLoading(true);
      const file = penaltyFileList[0].originFileObj as File;
      
      const result = await caseApi.batchAnalyzePenalty(file, {
        idCol: values.penaltyIdCol,
        contentCol: values.penaltyContentCol,
      });
      
      setPenaltyBatchResults(result.data?.result?.data || []);
      setPenaltyResultModalVisible(true);
      message.success(`批量行政处罚分析完成，处理了 ${result.data?.result?.data?.length || 0} 条记录`);
    } catch (error) {
      message.error('批量行政处罚分析失败');
      console.error('Batch penalty analysis error:', error);
    } finally {
      setLoading(false);
    }
  };

  const downloadCategoryResults = () => {
    if (categoryResults.length === 0) {
      message.warning('没有待分类数据可下载');
      return;
    }

    // 准备CSV数据
    const csvData = categoryResults.map(item => ({
       'ID': item.id || '',
       '标题': item.title || '',
       '文号': item.wenhao || '',
       '内容': item.content || '',
       '机构': item.org || '',
       '日期': item.date || '',
       '类型': '待分类标注',
       '状态': '待分类标注'
     }));

    // 转换为CSV格式
    const headers = Object.keys(csvData[0]);
    const csvContent = [
      headers.join(','),
      ...csvData.map(row => 
        headers.map(header => 
          `"${String(row[header as keyof typeof row]).replace(/"/g, '""')}"`
        ).join(',')
      )
    ].join('\n');

    // 创建下载链接
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `待分类案例_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    message.success('下载成功');
  };

  const downloadSplitResults = () => {
    if (splitResults.length === 0) {
      message.warning('没有待拆分数据可下载');
      return;
    }

    // 准备CSV数据
    const csvData = splitResults.map(item => ({
       'ID': item.id || '',
       '标题': item.title || '',
       '文号': item.wenhao || '',
       '内容': item.content || '',
       '机构': item.org || '',
       '日期': item.date || '',
       '类型': '待拆分标注',
       '状态': '待拆分标注'
     }));

    // 转换为CSV格式
    const headers = Object.keys(csvData[0]);
    const csvContent = [
      headers.join(','),
      ...csvData.map(row => 
        headers.map(header => 
          `"${String(row[header as keyof typeof row]).replace(/"/g, '""')}"`
        ).join(',')
      )
    ].join('\n');

    // 创建下载链接
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `待拆分案例_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    message.success('下载成功');
  };

  const downloadPenaltyBatchResults = () => {
    if (penaltyBatchResults.length === 0) return;
    
    const csvContent = [
      ['ID', '行政处罚决定书文号', '被处罚当事人', '主要违法违规事实', '行政处罚依据', '行政处罚决定', '作出处罚决定的机关名称', '作出处罚决定的日期', '行业', '罚款总金额', '违规类型', '监管地区'].join(','),
      ...penaltyBatchResults.map(result => [
        result.id || '',
        `"${(result['行政处罚决定书文号'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['被处罚当事人'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['主要违法违规事实'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['行政处罚依据'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['行政处罚决定'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['作出处罚决定的机关名称'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['作出处罚决定的日期'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['行业'] || '').toString().replace(/"/g, '""')}"`,
        result['罚款总金额'] || '',
        `"${(result['违规类型'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['监管地区'] || '').toString().replace(/"/g, '""')}"`,
      ].join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'penalty_analysis_results.csv';
    link.click();
  };



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
          
          {/* Label Results */}
          {labelResultsVisible && (
            <>
              {categoryResults.length > 0 && (
                <div className="mt-6">
                  <Divider />
                  <div className="flex justify-between items-center mb-4">
                    <Title level={4}>待分类数据 ({categoryResults.length} 条)</Title>
                    <Button
                      icon={<DownloadOutlined />}
                      onClick={downloadCategoryResults}
                    >
                      下载待分类数据
                    </Button>
                  </div>
                  <Table
                    dataSource={categoryResults}
                    columns={labelColumns}
                    rowKey="id"
                    pagination={{
                      pageSize: 10,
                      showSizeChanger: true,
                      showQuickJumper: true,
                      showTotal: (total) => `共 ${total} 条记录`,
                    }}
                    scroll={{ x: 1200 }}
                    size="small"
                  />
                </div>
              )}
              
              {splitResults.length > 0 && (
                <div className="mt-6">
                  <Divider />
                  <div className="flex justify-between items-center mb-4">
                    <Title level={4}>待拆分标注数据 ({splitResults.length} 条)</Title>
                    <Button
                      icon={<DownloadOutlined />}
                      onClick={downloadSplitResults}
                    >
                      下载待拆分数据
                    </Button>
                  </div>
                  <Table
                    dataSource={splitResults}
                    columns={labelColumns}
                    rowKey="id"
                    pagination={{
                      pageSize: 10,
                      showSizeChanger: true,
                      showQuickJumper: true,
                      showTotal: (total) => `共 ${total} 条记录`,
                    }}
                    scroll={{ x: 1200 }}
                    size="small"
                  />
                </div>
              )}
            </>
          )}
        </div>
      </Card>





      {/* Single Penalty Analysis */}
      <Card title="单个行政处罚分析">
        <Form
          layout="vertical"
          onFinish={handleSinglePenaltyAnalysis}
        >
          <Form.Item
            label="行政处罚决定书文本"
            name="penaltyText"
            rules={[{ required: true, message: '请输入行政处罚决定书文本' }]}
          >
            <TextArea
              rows={8}
              placeholder="请输入完整的行政处罚决定书文本..."
            />
          </Form.Item>
          
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<FileTextOutlined />}
              loading={loading}
            >
              开始分析
            </Button>
          </Form.Item>
        </Form>
        
        {/* Single Penalty Analysis Results */}
        {penaltyResult && (
          <div className="mt-6">
            <Divider />
            <Title level={5}>分析结果</Title>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Text strong>行政处罚决定书文号：</Text>
                <div className="mb-2">{penaltyResult['行政处罚决定书文号'] || '未提取'}</div>
                
                <Text strong>被处罚当事人：</Text>
                <div className="mb-2">{penaltyResult['被处罚当事人'] || '未提取'}</div>
                
                <Text strong>作出处罚决定的机关名称：</Text>
                <div className="mb-2">{penaltyResult['作出处罚决定的机关名称'] || '未提取'}</div>
                
                <Text strong>作出处罚决定的日期：</Text>
                <div className="mb-2">{penaltyResult['作出处罚决定的日期'] || '未提取'}</div>
                
                <Text strong>行业：</Text>
                <div className="mb-2">{penaltyResult['行业'] || '未提取'}</div>
                
                <Text strong>罚款总金额：</Text>
                <div className="mb-2">{penaltyResult['罚款总金额'] || '未提取'}</div>
              </div>
              <div>
                <Text strong>违规类型：</Text>
                <div className="mb-2">{penaltyResult['违规类型'] || '未提取'}</div>
                
                <Text strong>监管地区：</Text>
                <div className="mb-2">{penaltyResult['监管地区'] || '未提取'}</div>
                
                <Text strong>主要违法违规事实：</Text>
                <div className="mb-2 max-h-20 overflow-y-auto">{penaltyResult['主要违法违规事实'] || '未提取'}</div>
                
                <Text strong>行政处罚依据：</Text>
                <div className="mb-2 max-h-20 overflow-y-auto">{penaltyResult['行政处罚依据'] || '未提取'}</div>
                
                <Text strong>行政处罚决定：</Text>
                <div className="mb-2 max-h-20 overflow-y-auto">{penaltyResult['行政处罚决定'] || '未提取'}</div>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Batch Penalty Analysis */}
      <Card title="批量行政处罚分析">
        <Form
          layout="vertical"
          onFinish={handleBatchPenaltyAnalysis}
        >
          <Form.Item
            label="上传文件"
            required
            tooltip="支持 CSV 格式文件"
          >
            <Upload
              fileList={penaltyFileList}
              onChange={({ fileList }) => setPenaltyFileList(fileList)}
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
              name="penaltyIdCol"
              rules={[{ required: true, message: '请输入 ID 字段名' }]}
            >
              <Input placeholder="例如: id" />
            </Form.Item>
            
            <Form.Item
              label="内容字段"
              name="penaltyContentCol"
              rules={[{ required: true, message: '请输入内容字段名' }]}
            >
              <Input placeholder="例如: content" />
            </Form.Item>
          </div>
          
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<FileTextOutlined />}
              loading={loading}
              disabled={penaltyFileList.length === 0}
            >
              开始批量分析
            </Button>
          </Form.Item>
        </Form>
      </Card>



      {/* Batch Penalty Analysis Results Modal */}
      <Modal
        title="批量行政处罚分析结果"
        open={penaltyResultModalVisible}
        onCancel={() => setPenaltyResultModalVisible(false)}
        width={1200}
        footer={[
          <Button
            key="download"
            type="primary"
            icon={<DownloadOutlined />}
            onClick={downloadPenaltyBatchResults}
          >
            下载结果
          </Button>,
          <Button key="close" onClick={() => setPenaltyResultModalVisible(false)}>
            关闭
          </Button>,
        ]}
      >
        <Table
          columns={[
            {
              title: 'ID',
              dataIndex: 'id',
              key: 'id',
              width: '8%',
            },
            {
              title: '决定书文号',
              dataIndex: '行政处罚决定书文号',
              key: 'documentNumber',
              width: '15%',
              ellipsis: true,
            },
            {
              title: '被处罚当事人',
              dataIndex: '被处罚当事人',
              key: 'penalizedParty',
              width: '12%',
              ellipsis: true,
            },
            {
              title: '处罚机关',
              dataIndex: '作出处罚决定的机关名称',
              key: 'authority',
              width: '12%',
              ellipsis: true,
            },
            {
              title: '罚款金额',
              dataIndex: '罚款总金额',
              key: 'fineAmount',
              width: '10%',
              render: (amount: any) => amount || '未提取',
            },
            {
              title: '违规类型',
              dataIndex: '违规类型',
              key: 'violationType',
              width: '12%',
              ellipsis: true,
            },
            {
              title: '行业',
              dataIndex: '行业',
              key: 'industry',
              width: '8%',
              ellipsis: true,
            },
            {
              title: '监管地区',
              dataIndex: '监管地区',
              key: 'region',
              width: '10%',
              ellipsis: true,
            },
            {
              title: '作出处罚决定的日期',
              dataIndex: '作出处罚决定的日期',
              key: 'date',
              width: '13%',
              ellipsis: true,
            },
          ]}
          dataSource={penaltyBatchResults}
          rowKey={(record, index) => record.id || index}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total, range) =>
              `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
          scroll={{ x: 1000 }}
        />
      </Modal>
    </div>
  );
};

export default CaseClassification;