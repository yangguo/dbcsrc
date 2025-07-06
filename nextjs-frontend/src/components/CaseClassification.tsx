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
  Table,
  App,
  Typography,
  Divider,
  Tag,
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
  const [penaltyForm] = Form.useForm();

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

  // 为每个功能创建独立的loading状态
  const [labelLoading, setLabelLoading] = useState(false);
  const [singlePenaltyLoading, setSinglePenaltyLoading] = useState(false);
  const [batchPenaltyLoading, setBatchPenaltyLoading] = useState(false);
  
  const [categoryResults, setCategoryResults] = useState<any[]>([]);
  const [splitResults, setSplitResults] = useState<any[]>([]);
  const [labelResultsVisible, setLabelResultsVisible] = useState(false);

  const [penaltyResult, setPenaltyResult] = useState<any>(null);
  const [penaltyBatchResults, setPenaltyBatchResults] = useState<any[]>([]);
  const [penaltyFileList, setPenaltyFileList] = useState<UploadFile[]>([]);

  const [csvColumns, setCsvColumns] = useState<string[]>([]);
  

  
  // 表格行选择状态
  const [selectedCategoryRows, setSelectedCategoryRows] = useState<string[]>([]);
  const [selectedSplitRows, setSelectedSplitRows] = useState<string[]>([]);
  const [selectedPenaltyRows, setSelectedPenaltyRows] = useState<string[]>([]);



  const handleGenerateLabels = async () => {
    try {
      setLabelLoading(true);
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
      setLabelLoading(false);
    }
  };







  const handleSinglePenaltyAnalysis = async (values: any) => {
    try {
      setSinglePenaltyLoading(true);
      const result = await caseApi.analyzePenalty(values.penaltyText);
      console.log('Penalty analysis result:', result);
      console.log('Full result structure:', JSON.stringify(result, null, 2));
      console.log('result.data:', result.data);
      console.log('result.data.data:', result.data?.data);
      setPenaltyResult(result.data?.result || null);
      console.log('penaltyResult set, should trigger re-render');
      message.success('行政处罚分析完成');
    } catch (error) {
      message.error('行政处罚分析失败');
      console.error('Penalty analysis error:', error);
    } finally {
      setSinglePenaltyLoading(false);
    }
  };

  const parseCsvColumns = (file: File): Promise<string[]> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const text = e.target?.result as string;
          console.log('CSV文件内容预览:', text.substring(0, 200));
          const firstLine = text.split('\n')[0].trim();
          console.log('第一行内容:', firstLine);
          
          // 处理不同的分隔符和引号格式
          let columns: string[];
          if (firstLine.includes(',')) {
            columns = firstLine.split(',').map(col => col.trim().replace(/^["']|["']$/g, ''));
          } else if (firstLine.includes(';')) {
            columns = firstLine.split(';').map(col => col.trim().replace(/^["']|["']$/g, ''));
          } else {
            columns = [firstLine];
          }
          
          console.log('解析出的列名:', columns);
          
          if (columns.length === 0 || (columns.length === 1 && columns[0] === '')) {
            reject(new Error('未能解析出有效的列名'));
          } else {
            resolve(columns.filter(col => col.length > 0));
          }
        } catch (error) {
          console.error('CSV解析错误:', error);
          reject(error);
        }
      };
      reader.onerror = () => reject(new Error('文件读取失败'));
      reader.readAsText(file, 'utf-8');
    });
  };

  const handlePenaltyFileChange = async (info: any) => {
    console.log('文件上传信息:', info);
    
    setPenaltyFileList(info.fileList);
    
    // 清空之前的列名
    setCsvColumns([]);
    
    // 当有文件时解析列名
    if (info.fileList.length > 0) {
      const latestFile = info.fileList[info.fileList.length - 1];
      const file = latestFile.originFileObj || latestFile;
      
      console.log('准备解析的文件:', file);
      
      if (file && file instanceof File) {
        try {
          console.log('开始解析CSV列名...');
          const columns = await parseCsvColumns(file);
          console.log('解析完成，设置列名:', columns);
          setCsvColumns(columns);
          message.success(`文件上传成功，已解析${columns.length}个列名`);
        } catch (error) {
           console.error('解析CSV列名失败:', error);
           message.error(`解析CSV列名失败: ${error instanceof Error ? error.message : '未知错误'}`);
        }
      }
    }
  };

  const handleBatchPenaltyAnalysis = async (values: any) => {
    if (penaltyFileList.length === 0) {
      message.error('请上传文件');
      return;
    }

    try {
      setBatchPenaltyLoading(true);
      const file = penaltyFileList[0].originFileObj as File;
      
      const result = await caseApi.batchAnalyzePenalty(file, {
        idCol: values.penaltyIdCol,
        contentCol: values.penaltyContentCol,
      });
      
      setPenaltyBatchResults(result.data?.result?.data || []);
      message.success(`批量行政处罚分析完成，处理了 ${result.data?.result?.data?.length || 0} 条记录`);
    } catch (error) {
      message.error('批量行政处罚分析失败');
      console.error('Batch penalty analysis error:', error);
    } finally {
      setBatchPenaltyLoading(false);
    }
  };

  const downloadCategoryResults = (selectedOnly = false) => {
    const dataToDownload = selectedOnly 
      ? categoryResults.filter(item => selectedCategoryRows.includes(item.id))
      : categoryResults;
      
    if (dataToDownload.length === 0) {
      message.warning(selectedOnly ? '请先选择要下载的记录' : '没有待分类数据可下载');
      return;
    }

    // 准备CSV数据
    const csvData = dataToDownload.map(item => ({
       'ID': item.id || '',
       '标题': item.title || '',
       '文号': item.wenhao || '',
       '内容': item.content || '',
       '机构': item.organization || item.org || '',
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
    const fileName = selectedOnly 
      ? `待分类案例_选中${dataToDownload.length}条_${new Date().toISOString().split('T')[0]}.csv`
      : `待分类案例_${new Date().toISOString().split('T')[0]}.csv`;
    link.setAttribute('download', fileName);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    message.success(`下载成功：${dataToDownload.length} 条记录`);
  };

  const downloadSplitResults = (selectedOnly = false) => {
    const dataToDownload = selectedOnly 
      ? splitResults.filter(item => selectedSplitRows.includes(item.id))
      : splitResults;
      
    if (dataToDownload.length === 0) {
      message.warning(selectedOnly ? '请先选择要下载的记录' : '没有待拆分数据可下载');
      return;
    }

    // 准备CSV数据
    const csvData = dataToDownload.map(item => ({
       'ID': item.id || '',
       '标题': item.title || '',
       '文号': item.wenhao || '',
       '内容': item.content || '',
       '机构': item.organization || item.org || '',
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
    const fileName = selectedOnly 
      ? `待拆分案例_选中${dataToDownload.length}条_${new Date().toISOString().split('T')[0]}.csv`
      : `待拆分案例_${new Date().toISOString().split('T')[0]}.csv`;
    link.setAttribute('download', fileName);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    message.success(`下载成功：${dataToDownload.length} 条记录`);
  };

  const downloadPenaltyBatchResults = (selectedOnly = false) => {
    const dataToDownload = selectedOnly 
      ? penaltyBatchResults.filter(item => selectedPenaltyRows.includes(item.id))
      : penaltyBatchResults;
      
    if (!dataToDownload || dataToDownload.length === 0) {
      message.warning(selectedOnly ? '请先选择要下载的记录' : '没有可下载的数据');
      return;
    }
    
    console.log('开始生成CSV内容');
    console.log('批量分析结果数据:', dataToDownload);
    
    const csvContent = [
      // CSV 头部 - 包含所有字段
      'ID,行政处罚决定书文号,被处罚当事人,作出处罚决定的机关名称,作出处罚决定的日期,行业,罚没总金额,违规类型,监管地区,主要违法违规事实,行政处罚依据,行政处罚决定',
      // CSV 数据行
      ...dataToDownload.map(result => [
        result.id || '',
        `"${(result['行政处罚决定书文号'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['被处罚当事人'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['作出处罚决定的机关名称'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['作出处罚决定的日期'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['行业'] || '').toString().replace(/"/g, '""')}"`,
        result['罚没总金额'] || '',
        `"${(result['违规类型'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['监管地区'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['主要违法违规事实'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['行政处罚依据'] || '').toString().replace(/"/g, '""')}"`,
        `"${(result['行政处罚决定'] || '').toString().replace(/"/g, '""')}"`
      ].join(','))
    ].join('\n');
    
    console.log('CSV内容生成完成，长度:', csvContent.length);
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    const fileName = selectedOnly 
      ? `批量行政处罚分析结果_选中${dataToDownload.length}条_${new Date().toISOString().split('T')[0]}.csv`
      : `批量行政处罚分析结果_${new Date().toISOString().split('T')[0]}.csv`;
    link.setAttribute('download', fileName);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    console.log('下载链接已点击');
    message.success(`下载成功：${dataToDownload.length} 条记录`);
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
            loading={labelLoading}
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
                    <Space>
                      <Button
                        icon={<DownloadOutlined />}
                        onClick={() => downloadCategoryResults(true)}
                        disabled={selectedCategoryRows.length === 0}
                      >
                        下载选中 ({selectedCategoryRows.length})
                      </Button>
                      <Button
                        icon={<DownloadOutlined />}
                        onClick={() => downloadCategoryResults(false)}
                      >
                        下载全部
                      </Button>
                    </Space>
                  </div>
                  <Table
                    dataSource={categoryResults}
                    columns={labelColumns}
                    rowKey="id"
                    rowSelection={{
                      selectedRowKeys: selectedCategoryRows,
                      onChange: (selectedRowKeys) => {
                        setSelectedCategoryRows(selectedRowKeys as string[]);
                      },
                      getCheckboxProps: (record) => ({
                        name: record.id,
                      }),
                    }}
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
                    <Space>
                      <Button
                        icon={<DownloadOutlined />}
                        onClick={() => downloadSplitResults(true)}
                        disabled={selectedSplitRows.length === 0}
                      >
                        下载选中 ({selectedSplitRows.length})
                      </Button>
                      <Button
                        icon={<DownloadOutlined />}
                        onClick={() => downloadSplitResults(false)}
                      >
                        下载全部
                      </Button>
                    </Space>
                  </div>
                  <Table
                    dataSource={splitResults}
                    columns={labelColumns}
                    rowKey="id"
                    rowSelection={{
                      selectedRowKeys: selectedSplitRows,
                      onChange: (selectedRowKeys) => {
                        setSelectedSplitRows(selectedRowKeys as string[]);
                      },
                      getCheckboxProps: (record) => ({
                        name: record.id,
                      }),
                    }}
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
              loading={singlePenaltyLoading}
            >
              开始分析
            </Button>
          </Form.Item>
        </Form>
        
        {/* Debug Info */}
        <div className="mt-4 p-4 bg-yellow-100 border border-yellow-300 rounded">
          <Text strong>调试信息：</Text>
          <div>penaltyResult 状态: {penaltyResult ? 'Has Data' : 'No Data'}</div>
          <div>penaltyResult 类型: {typeof penaltyResult}</div>
          <div>penaltyResult 内容: {JSON.stringify(penaltyResult, null, 2)}</div>
        </div>

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
                
                <Text strong>罚没总金额：</Text>
                <div className="mb-2">{(() => {
                  const amount = penaltyResult['罚没总金额'];
                  if (amount === undefined || amount === null || amount === '' || isNaN(Number(amount))) {
                    return '0';
                  }
                  return amount;
                })()}</div>
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
          form={penaltyForm}
          layout="vertical"
          onFinish={handleBatchPenaltyAnalysis}
          onValuesChange={(changedValues, allValues) => {
            console.log('表单值变化:', changedValues, allValues);
          }}
        >
          <Form.Item
            label="上传文件"
            required
            tooltip="支持 CSV 格式文件"
          >
            <Upload
              fileList={penaltyFileList}
              onChange={handlePenaltyFileChange}
              beforeUpload={() => false}
              accept=".csv"
              maxCount={1}
            >
              <Button icon={<UploadOutlined />}>选择 CSV 文件</Button>
            </Upload>
          </Form.Item>
          
          {csvColumns.length > 0 && (
            <div className="mb-4 p-3 bg-blue-50 rounded">
              <div className="flex justify-between items-center">
                <Text type="secondary">检测到的列名：{csvColumns.join(', ')}</Text>
                <Button 
                  size="small" 
                  onClick={() => {
                    setCsvColumns([]);
                    setPenaltyFileList([]);
                    penaltyForm.resetFields(['penaltyIdCol', 'penaltyContentCol']);
                    message.info('已清除文件和列名');
                  }}
                >
                  清除
                </Button>
              </div>
            </div>
          )}
          
          {penaltyFileList.length > 0 && csvColumns.length === 0 && (
            <div className="mb-4 p-3 bg-yellow-50 rounded">
              <Text type="warning">文件已上传，但未能解析出列名。请检查文件格式是否正确。</Text>
            </div>
          )}
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Form.Item
              label="ID 字段"
              name="penaltyIdCol"
              rules={[{ required: true, message: '请选择 ID 字段' }]}
            >
              <Select
                placeholder="请选择 ID 字段"
                disabled={csvColumns.length === 0}
                showSearch
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                options={csvColumns.map(col => ({ label: col, value: col }))}
              />
            </Form.Item>
            
            <Form.Item
              label="内容字段"
              name="penaltyContentCol"
              rules={[{ required: true, message: '请选择内容字段' }]}
            >
              <Select
                placeholder="请选择内容字段"
                disabled={csvColumns.length === 0}
                showSearch
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                options={csvColumns.map(col => ({ label: col, value: col }))}
              />
            </Form.Item>
          </div>
          
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<FileTextOutlined />}
              loading={batchPenaltyLoading}
              disabled={penaltyFileList.length === 0}
            >
              开始批量分析
            </Button>
          </Form.Item>
        </Form>
        
        {/* Batch Penalty Analysis Results */}
        {penaltyBatchResults && penaltyBatchResults.length > 0 && (
          <div className="mt-6">
            <Divider />
            <div className="flex justify-between items-center mb-4">
              <Title level={4}>批量行政处罚分析结果 ({penaltyBatchResults.length} 条)</Title>
              <Space>
                <Button
                  icon={<DownloadOutlined />}
                  onClick={() => downloadPenaltyBatchResults(true)}
                  disabled={selectedPenaltyRows.length === 0}
                >
                  下载选中 ({selectedPenaltyRows.length})
                </Button>
                <Button
                  type="primary"
                  icon={<DownloadOutlined />}
                  onClick={() => downloadPenaltyBatchResults(false)}
                >
                  下载全部
                </Button>
              </Space>
            </div>
            <Table
              columns={[
                {
                  title: 'ID',
                  dataIndex: 'id',
                  key: 'id',
                  width: '6%',
                  fixed: 'left',
                },
                {
                  title: '决定书文号',
                  dataIndex: '行政处罚决定书文号',
                  key: 'documentNumber',
                  width: '12%',
                  ellipsis: true,
                },
                {
                  title: '被处罚当事人',
                  dataIndex: '被处罚当事人',
                  key: 'penalizedParty',
                  width: '10%',
                  ellipsis: true,
                },
                {
                  title: '处罚机关',
                  dataIndex: '作出处罚决定的机关名称',
                  key: 'authority',
                  width: '10%',
                  ellipsis: true,
                },
                {
                  title: '处罚日期',
                  dataIndex: '作出处罚决定的日期',
                  key: 'date',
                  width: '10%',
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
                  title: '罚没金额',
                  dataIndex: '罚没总金额',
                  key: 'fineAmount',
                  width: '8%',
                  render: (amount: any) => {
                    if (amount === undefined || amount === null || amount === '' || isNaN(Number(amount))) {
                      return '0';
                    }
                    return amount;
                  },
                },
                {
                  title: '违规类型',
                  dataIndex: '违规类型',
                  key: 'violationType',
                  width: '10%',
                  ellipsis: true,
                },
                {
                  title: '监管地区',
                  dataIndex: '监管地区',
                  key: 'region',
                  width: '8%',
                  ellipsis: true,
                },
                {
                  title: '违法事实',
                  dataIndex: '主要违法违规事实',
                  key: 'violationFacts',
                  width: '15%',
                  ellipsis: true,
                  render: (text: string) => (
                    <div title={text} style={{ maxHeight: '60px', overflow: 'hidden' }}>
                      {text || '未提取'}
                    </div>
                  ),
                },
                {
                  title: '处罚依据',
                  dataIndex: '行政处罚依据',
                  key: 'legalBasis',
                  width: '15%',
                  ellipsis: true,
                  render: (text: string) => (
                    <div title={text} style={{ maxHeight: '60px', overflow: 'hidden' }}>
                      {text || '未提取'}
                    </div>
                  ),
                },
                {
                  title: '处罚决定',
                  dataIndex: '行政处罚决定',
                  key: 'penaltyDecision',
                  width: '15%',
                  ellipsis: true,
                  render: (text: string) => (
                    <div title={text} style={{ maxHeight: '60px', overflow: 'hidden' }}>
                      {text || '未提取'}
                    </div>
                  ),
                },
              ]}
              dataSource={penaltyBatchResults}
              rowKey={(record) => record.id || `row-${Math.random()}`}
              rowSelection={{
                selectedRowKeys: selectedPenaltyRows,
                onChange: (selectedRowKeys) => {
                  setSelectedPenaltyRows(selectedRowKeys as string[]);
                },
                getCheckboxProps: (record) => ({
                  name: record.id,
                }),
              }}
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total, range) =>
                  `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
              }}
              scroll={{ x: 1400, y: 400 }}
            />
          </div>
        )}
      </Card>
      

    </div>
  );
};

export default CaseClassification;