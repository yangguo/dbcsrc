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
  Tooltip,
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
  sourceFilename?: string;
}

interface DownloadResult {
  id: string;
  url: string;
  filename: string;
  text: string;
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
  const [activeTab, setActiveTab] = useState('analysis');
  const [downloadResults, setDownloadResults] = useState<DownloadResult[]>([]);


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

  // 统一的文件检查函数（使用批量检查避免速率限制）
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
      // 收集需要检查的文件路径
      const filesToCheck: { index: number; filePath: string }[] = [];
      const updatedData = [...dataToCheck];
      
      dataToCheck.forEach((item, index) => {
        if (item.downloadStatus === 'downloaded' && item.filename) {
          const filePath = item.localFilePath || `/temp/${item.filename}`;
          filesToCheck.push({ index, filePath });
          updatedData[index] = {
            ...item,
            localFilePath: filePath,
          };
        } else {
          updatedData[index] = {
            ...item,
            fileExists: false,
          };
        }
      });
      
      // 如果有文件需要检查，使用批量检查API
      if (filesToCheck.length > 0) {
        const filePaths = filesToCheck.map(f => f.filePath);
        const batchResponse = await caseApi.checkFilesBatch(filePaths);
        
        if (batchResponse.success && batchResponse.data?.results) {
          // 将批量检查结果映射回原数据
          batchResponse.data.results.forEach((result: any, resultIndex: number) => {
            const fileInfo = filesToCheck[resultIndex];
            if (fileInfo) {
              updatedData[fileInfo.index] = {
                ...updatedData[fileInfo.index],
                fileExists: result.exists || false,
              };
            }
          });
        } else {
          // 批量检查失败，回退到单个检查（但添加延迟避免速率限制）
          console.warn('批量文件检查失败，回退到单个检查模式');
          for (let i = 0; i < filesToCheck.length; i++) {
            const { index, filePath } = filesToCheck[i];
            try {
              const fileExists = await checkFileExists(filePath);
              updatedData[index] = {
                ...updatedData[index],
                fileExists,
              };
              // 添加小延迟避免速率限制
              if (i < filesToCheck.length - 1) {
                await new Promise(resolve => setTimeout(resolve, 100));
              }
            } catch (error) {
              console.error(`检查文件 ${filePath} 时出错:`, error);
              updatedData[index] = {
                ...updatedData[index],
                fileExists: false,
              };
            }
          }
        }
      }
      
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
        <Tooltip 
          title={content || '暂无内容'}
          placement="topLeft"
          styles={{ root: { maxWidth: '400px', wordWrap: 'break-word' } }}
        >
          <div 
            style={{ 
              maxWidth: '150px', 
              overflow: 'hidden', 
              textOverflow: 'ellipsis',
              cursor: 'pointer'
            }}
          >
            {content || '暂无内容'}
          </div>
        </Tooltip>
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
      width: '10%',
      ellipsis: true,
      render: (filename: string) => filename || '-',
    },
    {
      title: '来源文件',
      dataIndex: 'sourceFilename',
      key: 'sourceFilename',
      width: '12%',
      ellipsis: true,
      render: (sourceFilename: string) => sourceFilename || '-',
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
        sourceFilename: item.source_filename || '',
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
      
      if (positions.length === 0) {
        message.error('无法找到选中项目的位置信息');
        return;
      }
      
      const result = await caseApi.downloadAttachments(positions);
      
      // Transform download results - handle both 'results' and 'result' keys for compatibility
      const downloadData = result.data?.results || result.data?.result || [];
      
      // Always create download results even if backend returns empty data
      // This helps with debugging and shows the user what happened
      const newDownloadResults: DownloadResult[] = [];
      
      if (Array.isArray(downloadData) && downloadData.length > 0) {
        // Process actual download data
        downloadData.forEach((item: any, index: number) => {
          const hasValidFilename = item.filename && 
                                 item.filename !== '' && 
                                 item.filename !== null && 
                                 item.filename !== 'undefined' &&
                                 item.filename !== 'NaN';
          
          newDownloadResults.push({
            id: `download-${Date.now()}-${index}`,
            url: item.url || '',
            filename: hasValidFilename ? item.filename : '下载失败',
            text: item.text || '',
            status: hasValidFilename ? 'success' as const : 'failed' as const,
          });
        });
      } else {
        // Create placeholder results for selected items to show what was attempted
        selectedRows.forEach((rowId, index) => {
          const item = analysisData.find(data => data.id === rowId);
          if (item) {
            newDownloadResults.push({
              id: `download-${Date.now()}-${index}`,
              url: item.url || '',
              filename: '下载失败 - 后端无响应',
              text: '',
              status: 'failed' as const,
            });
          }
        });
      }
      
      setDownloadResults(prev => [...prev, ...newDownloadResults]);
      
      // Create a map of successful downloads for efficient lookup
      const successfulDownloads = new Map();
      downloadData.forEach((item: any) => {
        if (item.filename && item.filename !== '' && item.filename !== null) {
          successfulDownloads.set(item.url, {
            filename: item.filename,
            text: item.text || '',
            downloaded: true
          });
        }
      });
      
      // Update download status based on actual results
      const updatedData = analysisData.map(item => {
        if (selectedRows.includes(item.id)) {
          const downloadInfo = successfulDownloads.get(item.url);
          if (downloadInfo) {
            return {
              ...item,
              downloadStatus: 'downloaded' as const,
              filename: downloadInfo.filename,
              content: downloadInfo.text || item.content,
              contentLength: downloadInfo.text ? downloadInfo.text.length : item.contentLength,
              textExtracted: !!downloadInfo.text,
            };
          } else {
            return {
              ...item,
              downloadStatus: 'failed' as const,
            };
          }
        }
        return item;
      });
      
      setAnalysisData(updatedData);
      
      setProgress(100);
      
      const successCount = newDownloadResults.filter(item => item.status === 'success').length;
      const failCount = newDownloadResults.filter(item => item.status === 'failed').length;
      
      if (successCount > 0) {
        message.success(`下载完成，成功 ${successCount} 个，失败 ${failCount} 个附件`);
      } else {
        message.warning(`下载完成，但所有 ${failCount} 个附件都下载失败`);
      }
      

      
      // 自动检查下载文件的存在性
      await autoCheckFilesExistence(updatedData);
      
      // 重新读取csrclenanalysis数据以更新表格状态
      try {
        setCurrentTask('刷新数据中...');
        const refreshedData = await caseApi.getCsrclenanalysisData();
        if (refreshedData.success && refreshedData.data?.result) {
          // Create a map of updated data for efficient lookup
          const updatedDataMap = new Map();
          refreshedData.data.result.forEach((item: any) => {
            updatedDataMap.set(item.url || item.id, item);
          });
          
          // Merge updated data with existing data, preserving all original fields
          setAnalysisData(prev => 
            prev.map(item => {
              const updatedItem = updatedDataMap.get(item.url || item.id);
              if (updatedItem) {
                return {
                  ...item,
                  content: updatedItem.content || item.content,
                  contentLength: updatedItem.contentLength || item.contentLength,
                  filename: updatedItem.filename || item.filename,
                  downloadStatus: updatedItem.filename ? 'downloaded' as const : item.downloadStatus,
                  textExtracted: !!updatedItem.content
                };
              }
              return item;
            })
          );
        }
      } catch (refreshError) {
        console.warn('Failed to refresh table data after download:', refreshError);
      }
      
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
      
      // Process extraction results
      const extractionData = result.data?.result || [];
      const successCount = extractionData.filter((item: any) => item.text).length;
      
      // Update text extraction status
      setAnalysisData(prev => 
        prev.map(item => 
          selectedRows.includes(item.id)
            ? { ...item, textExtracted: true }
            : item
        )
      );
      
      // Auto-refresh table data from updated csrclenanalysis file
      try {
        const updatedData = await caseApi.getCsrclenanalysisData();
        if (updatedData.success && updatedData.data?.result) {
          // Create a map of updated data for efficient lookup
          const updatedDataMap = new Map();
          updatedData.data.result.forEach((item: any) => {
            updatedDataMap.set(item.url || item.id, item);
          });
          
          // Merge updated data with existing data, preserving all original fields
          setAnalysisData(prev => 
            prev.map(item => {
              const updatedItem = updatedDataMap.get(item.url || item.id);
              if (updatedItem) {
                // Only update content and contentLength, preserve all other fields
                return {
                  ...item,
                  content: updatedItem.content || item.content,
                  contentLength: updatedItem.contentLength || item.contentLength,
                  textExtracted: true // Mark as text extracted
                };
              }
              return item;
            })
          );
          
          message.success(`成功抽取 ${successCount} 个附件的文本，已更新现有的csrclenanalysis文件并刷新表格数据`);
        } else {
          message.success(`成功抽取 ${successCount} 个附件的文本，已更新现有的csrclenanalysis文件（仅更新已存在的文件）`);
        }
      } catch (refreshError) {
        console.warn('Failed to refresh table data:', refreshError);
        message.success(`成功抽取 ${successCount} 个附件的文本，已更新现有的csrclenanalysis文件（仅更新已存在的文件）`);
      }
      
      // 保持在当前分析结果页面
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
      
      // 获取选中行对应的URL，而不是传递组合ID
      const selectedUrls = selectedRows.map(id => {
        const item = analysisData.find(data => data.id === id);
        return item?.url || id; // 如果找不到对应的item，则使用原ID作为fallback
      }).filter(url => url); // 过滤掉空值
      
      // 调用后端API更新文本内容，传递URL列表
      const result = await caseApi.updateAttachmentText(selectedUrls);
      
      if (result.success) {
        // 自动刷新数据以获取最新状态
        setCurrentTask('刷新数据中...');
        
        try {
          // 获取当前表单值用于刷新数据
          const formValues = form.getFieldsValue();
          const currentContentLength = formValues.contentLength || 10;
          const currentDownloadFilter = formValues.downloadFilter || 'none';
          
          // 重新获取分析数据
          const refreshedData = await caseApi.analyzeAttachments({
            contentLength: currentContentLength,
            downloadFilter: currentDownloadFilter,
          });
          
          if (refreshedData.success && refreshedData.data?.result) {
            const transformedData = refreshedData.data.result.map((item: any, index: number) => ({
              id: item.链接 || item.url || `item-${index}`,
              title: item.名称 || item.title || '',
              content: item.内容 || item.content || '',
              contentLength: item.len || item.contentLength || 0,
              hasAttachment: item.filename ? true : false,
              downloadStatus: 'pending' as const,
              textExtracted: false,
              filename: item.filename || '',
              url: item.链接 || item.url || '',
              publishDate: item.发文日期 || item.date || '',
              sourceFilename: item.source_filename || '',
            }));
            
            setAnalysisData(transformedData);
            
            // 清除选中状态
            setSelectedRows([]);
            
            message.success(`成功更新 ${selectedUrls.length} 个附件的文本，数据已自动刷新`);
          } else {
            // 如果刷新失败，仍然更新本地数据
            if (result.data) {
              setAnalysisData(prev => 
                prev.map(item => {
                  const updatedItem = result.data.find((updated: any) => updated.id === item.id);
                  return updatedItem ? { ...item, content: updatedItem.content, contentLength: updatedItem.contentLength } : item;
                })
              );
            }
            // 清除选中状态
            setSelectedRows([]);
            message.success(`成功更新 ${selectedUrls.length} 个附件的文本`);
          }
        } catch (refreshError) {
          console.warn('数据刷新失败，使用本地更新:', refreshError);
          // 如果刷新失败，仍然更新本地数据
          if (result.data) {
            setAnalysisData(prev => 
              prev.map(item => {
                const updatedItem = result.data.find((updated: any) => updated.id === item.id);
                return updatedItem ? { ...item, content: updatedItem.content, contentLength: updatedItem.contentLength } : item;
              })
            );
          }
          // 清除选中状态
          setSelectedRows([]);
          message.warning(`成功更新 ${selectedUrls.length} 个附件的文本，但数据刷新失败，请手动重新分析`);
        }
      } else {
        message.error(result.message || '文本更新失败');
      }
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

      {/* Results */}
      {analysisData.length > 0 && (
        <Card title={`附件分析结果 (${analysisData.length})`}>
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