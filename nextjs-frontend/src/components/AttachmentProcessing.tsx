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
  App,
  Divider,
  Typography,
  Tag,
  Tabs,
} from 'antd';
import {
  FileTextOutlined,
  DownloadOutlined,
  SyncOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { caseApi } from '@/services/api';

const { Option } = Select;
const { Text, Title } = Typography;

interface AttachmentData {
  id: string;
  title: string;
  content: string;
  contentLength: number;
  hasAttachment: boolean;
  downloadStatus: 'pending' | 'downloaded' | 'failed';
  textExtracted: boolean;
  filename?: string;
  url?: string;
  publishDate?: string;
  localFilePath?: string;
  fileExists?: boolean;
}

interface DownloadResult {
  id: string;
  url: string;
  filename: string;
  text: string;
  status: 'success' | 'failed';
}

interface TextExtractionResult {
  id: string;
  url: string;
  filename: string;
  extractedText: string;
  status: 'success' | 'failed';
}

const AttachmentProcessing: React.FC = () => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [analysisData, setAnalysisData] = useState<AttachmentData[]>([]);
  const [selectedRows, setSelectedRows] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const [currentTask, setCurrentTask] = useState('');
  const [downloadResults, setDownloadResults] = useState<DownloadResult[]>([]);
  const [textExtractionResults, setTextExtractionResults] = useState<TextExtractionResult[]>([]);
  const [activeTab, setActiveTab] = useState('analysis');


  // 检查文件是否存在的函数
  const checkFileExists = async (filePath: string): Promise<boolean> => {
    try {
      if (!filePath || filePath.trim() === '') {
        return false;
      }
      
      // 调用后端API检查文件是否存在
      const response = await caseApi.checkFileExists(filePath);
      return response.exists || false;
    } catch (error) {
      console.error('检查文件存在性时出错:', error);
      return false;
    }
  };

  // 文件检查配置选项接口
  interface FileCheckOptions {
    showMessage?: boolean;
    messagePrefix?: string;
    updateState?: boolean;
    setLoadingState?: boolean;
    messageType?: 'info' | 'success';
  }

  // 统一的文件检查函数
  const checkFilesExistence = async (
    dataToCheck: AttachmentData[], 
    options: FileCheckOptions = {}
  ) => {
    const { 
      showMessage = false, 
      messagePrefix = '文件检查', 
      updateState = true,
      setLoadingState = false,
      messageType = 'success'
    } = options;
    
    setCurrentTask(`${messagePrefix}中...`);
    
    if (setLoadingState) {
      setLoading(true);
    }
    
    try {
      const updatedData = await Promise.all(
        dataToCheck.map(async (item) => {
          if (item.downloadStatus === 'downloaded' && item.filename) {
            const filePath = item.localFilePath || `/temp/${item.filename}`;
            const fileExists = await checkFileExists(filePath);
            return {
              ...item,
              fileExists,
              localFilePath: filePath,
            };
          }
          return {
            ...item,
            fileExists: false,
          };
        })
      );
      
      if (updateState) {
        setAnalysisData(updatedData);
      }
      
      const existingFiles = updatedData.filter(item => item.fileExists).length;
      const totalDownloaded = updatedData.filter(item => item.downloadStatus === 'downloaded').length;
      
      if (showMessage && totalDownloaded > 0) {
        const messageText = `${messagePrefix}完成：${existingFiles}/${totalDownloaded} 个文件存在`;
        if (messageType === 'info') {
          message.info(messageText);
        } else {
          message.success(messageText);
        }
      }
      
      return updatedData;
    } catch (error: any) {
      console.error(`${messagePrefix}时出错:`, error);
      if (showMessage) {
        message.error(`${messagePrefix}失败: ${error.message}`);
      }
      throw error;
    } finally {
      if (setLoadingState) {
        setLoading(false);
        setCurrentTask('');
      }
    }
  };

  // 自动检查文件存在性（在分析完成后调用）
  const autoCheckFilesExistence = async (dataToCheck: AttachmentData[]) => {
    try {
      await checkFilesExistence(dataToCheck, {
        showMessage: true,
        messagePrefix: '自动检查文件存在性',
        messageType: 'info'
      });
    } catch (error) {
      // 不显示错误消息，避免干扰用户体验
    }
  };

  // 批量检查文件存在性（手动触发）
  const checkAllFilesExistence = async () => {
    if (analysisData.length === 0) {
      message.warning('没有可检查的附件数据');
      return;
    }

    try {
      await checkFilesExistence(analysisData, {
        showMessage: true,
        messagePrefix: '批量检查文件存在性',
        setLoadingState: true,
        messageType: 'success'
      });
    } catch (error) {
      // 错误已在统一函数中处理
    }
  };

  const columns = [
    {
      title: '发文日期',
      dataIndex: 'publishDate',
      key: 'publishDate',
      width: '10%',
      render: (date: string) => date || '-',
    },
    {
      title: '案例标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      width: '20%',
    },
    {
      title: '链接',
      dataIndex: 'url',
      key: 'url',
      width: '15%',
      ellipsis: true,
      render: (url: string) => (
        url ? (
          <a href={url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800">
            查看原文
          </a>
        ) : '-'
      ),
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
      width: '20%',
      render: (content: string) => (
        <div style={{ maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {content || '暂无内容'}
        </div>
      ),
    },
    {
      title: '内容长度',
      dataIndex: 'contentLength',
      key: 'contentLength',
      width: '8%',
      render: (length: number) => (
        <Tag color={length < 100 ? 'red' : length < 500 ? 'orange' : 'green'}>
          {length}
        </Tag>
      ),
    },
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      width: '12%',
      ellipsis: true,
      render: (filename: string) => filename || '-',
    },
    {
      title: '下载状态',
      dataIndex: 'downloadStatus',
      key: 'downloadStatus',
      width: '10%',
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
      title: '文件状态',
      dataIndex: 'fileExists',
      key: 'fileExists',
      width: '8%',
      render: (exists: boolean, record: AttachmentData) => {
        if (record.downloadStatus === 'pending') {
          return <Tag color="default">未检查</Tag>;
        }
        return (
          <Tag color={exists ? 'green' : 'red'}>
            {exists ? '文件存在' : '文件缺失'}
          </Tag>
        );
      },
    },
    {
      title: '文本提取',
      dataIndex: 'textExtracted',
      key: 'textExtracted',
      width: '8%',
      render: (extracted: boolean) => (
        <Tag color={extracted ? 'green' : 'orange'}>
          {extracted ? '已提取' : '未提取'}
        </Tag>
      ),
    },
  ];

  // 附件下载结果表格列
  const downloadColumns = [
    {
      title: 'URL',
      dataIndex: 'url',
      key: 'url',
      ellipsis: true,
      width: '30%',
    },
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      width: '25%',
    },
    {
      title: '文本内容',
      dataIndex: 'text',
      key: 'text',
      ellipsis: true,
      width: '30%',
      render: (text: string) => (
        <div style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {text || '暂无内容'}
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: '15%',
      render: (status: string) => (
        <Tag color={status === 'success' ? 'green' : 'red'}>
          {status === 'success' ? '成功' : '失败'}
        </Tag>
      ),
    },
  ];

  // 文本抽取结果表格列
  const textExtractionColumns = [
    {
      title: 'URL',
      dataIndex: 'url',
      key: 'url',
      ellipsis: true,
      width: '25%',
      render: (url: string) => (
        url ? (
          <a href={url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800">
            查看原文
          </a>
        ) : '-'
      ),
    },
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      width: '25%',
      ellipsis: true,
      render: (filename: string) => (
        <div style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }} title={filename}>
          {filename || '暂无文件名'}
        </div>
      ),
    },
    {
      title: '抽取的文本',
      dataIndex: 'extractedText',
      key: 'extractedText',
      ellipsis: true,
      width: '35%',
      render: (text: string) => (
        <div style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }} title={text}>
          {text || '暂无内容'}
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: '15%',
      render: (status: string) => (
        <Tag color={status === 'success' ? 'green' : 'red'}>
          {status === 'success' ? '成功' : '失败'}
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
        downloadFilter: values.downloadFilter || 'none',
      });
      
      // Transform backend response to frontend interface
      // Backend returns: { success: true, data: { result: [...] } }
      const backendData = result.data?.result || [];
      let transformedData: AttachmentData[] = backendData.map((item: any, index: number) => ({
        id: `${item.链接 || 'unknown'}-${index}`, // Ensure unique ID by combining URL and index
        title: item.名称 || '未知标题',
        content: item.内容 || '',
        contentLength: item.len || 0,
        hasAttachment: item.filename ? true : false,
        downloadStatus: 'pending' as const,
        textExtracted: false,
        filename: item.filename || '',
        url: item.链接 || '',
        publishDate: item.发文日期 || '',
      }));
      
      // 获取已下载文件状态并更新数据
      setCurrentTask('获取已下载文件状态...');
      try {
        const downloadedStatus = await caseApi.getDownloadedFileStatus();
        const downloadedFiles = downloadedStatus.data || [];
        
        // 创建一个映射，用于快速查找已下载的文件
        const downloadedMap = new Map();
        downloadedFiles.forEach((file: any) => {
          downloadedMap.set(file.url, {
            filename: file.filename,
            text: file.text,
            downloaded: true
          });
        });
        
        // 更新transformedData，标记已下载的文件
        transformedData = transformedData.map(item => {
          const downloadedInfo = downloadedMap.get(item.url);
          if (downloadedInfo) {
            return {
              ...item,
              downloadStatus: 'downloaded' as const,
              filename: downloadedInfo.filename || item.filename,
              content: downloadedInfo.text || item.content,
              contentLength: downloadedInfo.text ? downloadedInfo.text.length : item.contentLength,
              textExtracted: !!downloadedInfo.text,
            };
          }
          return item;
        });
        
        const downloadedCount = transformedData.filter(item => item.downloadStatus === 'downloaded').length;
        if (downloadedCount > 0) {
          message.info(`发现 ${downloadedCount} 个已下载的文件`);
        }
      } catch (downloadError) {
        console.warn('获取已下载文件状态失败:', downloadError);
        // 不阻断主流程，继续执行
      }
      
      setAnalysisData(transformedData);
      message.success(`分析完成，找到 ${transformedData.length} 条需要处理的案例`);
      
      // 自动检查文件存在性
      if (transformedData.length > 0) {
        await autoCheckFilesExistence(transformedData);
      }
    } catch (error: any) {
      if (error.name === 'BackendUnavailableError') {
        message.error({
          content: '后端服务器未启动，请确保后端服务器在端口8000上运行',
          duration: 6,
        });
      } else {
        message.error('附件分析失败');
      }
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
      
      // Transform download results
      const downloadData = result.data?.result || [];
      const newDownloadResults: DownloadResult[] = downloadData.map((item: any, index: number) => ({
        id: `download-${Date.now()}-${index}`,
        url: item.url || '',
        filename: item.filename || '',
        text: item.text || '',
        status: item.filename ? 'success' as const : 'failed' as const,
      }));
      
      setDownloadResults(prev => [...prev, ...newDownloadResults]);
      
      // Update download status
      const updatedData = analysisData.map(item => 
        selectedRows.includes(item.id)
          ? { ...item, downloadStatus: 'downloaded' as const }
          : item
      );
      setAnalysisData(updatedData);
      
      setProgress(100);
      message.success(`下载完成，共处理 ${selectedRows.length} 个附件`);
      
      // 自动检查下载文件的存在性
      await autoCheckFilesExistence(updatedData);
      
      // Switch to download results tab
      setActiveTab('download');
    } catch (error: any) {
      if (error.name === 'BackendUnavailableError') {
        message.error({
          content: '后端服务器未启动，请确保后端服务器在端口8000上运行',
          duration: 6,
        });
      } else {
        message.error('附件下载失败');
      }
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
    } catch (error: any) {
      if (error.name === 'BackendUnavailableError') {
        message.error({
          content: '后端服务器未启动，请确保后端服务器在端口8000上运行',
          duration: 6,
        });
      } else {
        message.error('文件转换失败');
      }
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

  const handleTextExtraction = async () => {
    if (selectedRows.length === 0) {
      message.warning('请先选择要抽取文本的附件');
      return;
    }

    setLoading(true);
    setCurrentTask('抽取文本中...');
    
    try {
      // 获取选中行对应的URL，而不是传递组合ID
      const selectedUrls = selectedRows.map(id => {
        const item = analysisData.find(data => data.id === id);
        return item?.url || id; // 如果找不到对应的item，则使用原ID作为fallback
      }).filter(url => url); // 过滤掉空值
      
      // 调用后端API进行文本抽取，传递URL列表
      const result = await caseApi.extractText(selectedUrls);
      
      // Transform extraction results
      const extractionData = result.data?.result || [];
      const extractionResults: TextExtractionResult[] = extractionData.map((item: any, index: number) => ({
        id: `extraction-${Date.now()}-${index}`,
        url: item.url || '',
        filename: item.filename || '',
        extractedText: item.text || '',
        status: item.text ? 'success' as const : 'failed' as const,
      }));
      
      setTextExtractionResults(prev => [...prev, ...extractionResults]);
      
      // Update text extraction status
      setAnalysisData(prev => 
        prev.map(item => 
          selectedRows.includes(item.id)
            ? { ...item, textExtracted: true }
            : item
        )
      );
      
      setActiveTab('textExtraction');
      message.success(`成功抽取 ${extractionResults.length} 个附件的文本`);
    } catch (error: any) {
      if (error.name === 'BackendUnavailableError') {
        message.error({
          content: '后端服务器未启动，请确保后端服务器在端口8000上运行',
          duration: 6,
        });
      } else {
        message.error('文本抽取失败');
      }
      console.error('Text extraction error:', error);
    } finally {
      setLoading(false);
      setCurrentTask('');
    }
  };

  const handleUpdateText = async () => {
    if (selectedRows.length === 0) {
      message.warning('请先选择要更新文本的附件');
      return;
    }

    try {
      setLoading(true);
      setCurrentTask('更新文本内容...');
      
      // 调用后端API更新文本内容
      const result = await caseApi.updateAttachmentText(selectedRows);
      
      // 更新本地数据
      if (result.success && result.data) {
        setAnalysisData(prev => 
          prev.map(item => {
            const updatedItem = result.data.find((updated: any) => updated.id === item.id);
            return updatedItem ? { ...item, content: updatedItem.content, contentLength: updatedItem.contentLength } : item;
          })
        );
      }
      
      message.success(`成功更新 ${selectedRows.length} 个附件的文本`);
    } catch (error: any) {
      console.error('更新文本失败:', error);
      message.error(error.response?.data?.message || '文本更新失败，请稍后重试');
    } finally {
      setLoading(false);
      setCurrentTask('');
    }
  };

  const handleRemoveAttachments = async () => {
    if (selectedRows.length === 0) {
      message.warning('请先选择要删除的附件');
      return;
    }

    try {
      setLoading(true);
      setCurrentTask('删除附件中...');
      
      // 调用后端API删除附件
      await caseApi.deleteAttachments(selectedRows);
      
      // 从本地数据中移除已删除的附件
      setAnalysisData(prev => prev.filter(item => !selectedRows.includes(item.id)));
      setDownloadResults(prev => prev.filter(item => !selectedRows.includes(item.id)));
      setTextExtractionResults(prev => prev.filter(item => !selectedRows.includes(item.id)));
      setSelectedRows([]);
      
      message.success(`成功删除 ${selectedRows.length} 个附件`);
    } catch (error: any) {
      console.error('删除附件失败:', error);
      message.error(error.response?.data?.message || '删除附件失败，请稍后重试');
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

      {/* Results Tabs */}
      {(analysisData.length > 0 || downloadResults.length > 0 || textExtractionResults.length > 0) && (
        <Card>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: 'analysis',
                label: `附件分析结果 (${analysisData.length})`,
                children: (
                  <div>
                    {analysisData.length > 0 ? (
                      <>
                        <div className="mb-4">
                           <Space wrap>
                             <Button
                               type="primary"
                               icon={<DownloadOutlined />}
                               onClick={handleDownload}
                               disabled={selectedRows.length === 0 || loading}
                             >
                               下载选中附件 ({selectedRows.length})
                             </Button>
                             <Button
                                onClick={handleTextExtraction}
                                disabled={loading}
                              >
                                文本抽取
                              </Button>
                             <Button
                               onClick={handleUpdateText}
                               disabled={loading}
                             >
                               更新文本
                             </Button>
                             <Button
                               danger
                               onClick={handleRemoveAttachments}
                               disabled={loading}
                             >
                               删除附件
                             </Button>
                             <Button
                               icon={<SyncOutlined />}
                               onClick={checkAllFilesExistence}
                               disabled={loading || analysisData.length === 0}
                             >
                               检查文件存在性
                             </Button>
                           </Space>
                         </div>
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
                          scroll={{ x: 1200 }}
                        />
                      </>
                    ) : (
                      <Alert message="暂无分析结果，请先进行附件分析" type="info" />
                    )}
                  </div>
                ),
              },
              {
                key: 'download',
                label: `附件下载结果 (${downloadResults.length})`,
                children: (
                  <div>
                    {downloadResults.length > 0 ? (
                      <Table
                        columns={downloadColumns}
                        dataSource={downloadResults}
                        rowKey="id"
                        pagination={{
                          pageSize: 10,
                          showSizeChanger: true,
                          showQuickJumper: true,
                          showTotal: (total, range) =>
                            `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
                        }}
                        scroll={{ x: 800 }}
                      />
                    ) : (
                      <Alert message="暂无下载结果，请先下载附件" type="info" />
                    )}
                  </div>
                ),
              },
              {
                key: 'textExtraction',
                label: `文本抽取结果 (${textExtractionResults.length})`,
                children: (
                  <div>
                    {textExtractionResults.length > 0 ? (
                      <Table
                        columns={textExtractionColumns}
                        dataSource={textExtractionResults}
                        rowKey="id"
                        pagination={{
                          pageSize: 10,
                          showSizeChanger: true,
                          showQuickJumper: true,
                          showTotal: (total, range) =>
                            `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
                        }}
                        scroll={{ x: 900 }}
                      />
                    ) : (
                      <Alert message="暂无文本抽取结果，请先进行文本抽取" type="info" />
                    )}
                  </div>
                ),
              },
            ]}
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
                accept=".docx,.doc,.pdf"
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
                onClick={handleTextExtraction}
                loading={loading}
              >
                文本抽取
              </Button>
              <Button
                icon={<SyncOutlined />}
                onClick={handleUpdateText}
                loading={loading}
              >
                更新文本
              </Button>
            </Space>
          </div>
          

        </div>
      </Card>
    </div>
  );
};

export default AttachmentProcessing;