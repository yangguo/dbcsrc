'use client';

import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Select,
  InputNumber,
  Button,
  Space,
  Progress,
  Alert,
  List,
  Typography,
  App,
  Divider,
  Checkbox,
} from 'antd';
import { SyncOutlined, ReloadOutlined } from '@ant-design/icons';
import { caseApi, UpdateParams } from '@/services/api';

const { Option } = Select;
const { Text, Title } = Typography;

// Organization ID mapping - each organization can have multiple IDs with names
type IdInfo = {
  id: string;
  name: string;
};

type Org2IdType = {
  [key: string]: IdInfo[];
};

interface UpdateResult {
  orgName: string;
  idName: string;
  success: boolean;
  count: number;
  error?: string;
}

const CaseUpdate: React.FC = () => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [updateResults, setUpdateResults] = useState<UpdateResult[]>([]);
  const [currentOrg, setCurrentOrg] = useState<string>('');
  const [selectedOrgs, setSelectedOrgs] = useState<string[]>([]);
  const [availableIds, setAvailableIds] = useState<{id: string, name: string, orgName: string}[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [org2id, setOrg2id] = useState<Org2IdType>({});
  const [orgOptions, setOrgOptions] = useState<string[]>([]);
  const [loadingOrg2id, setLoadingOrg2id] = useState(true);

  // Fetch org2id mapping from API
  const fetchOrg2idMapping = async () => {
    try {
      setLoadingOrg2id(true);
      const result = await caseApi.getOrg2idMapping();
      
      if (result.success && result.data) {
        setOrg2id(result.data);
        setOrgOptions(Object.keys(result.data));
        message.success('组织ID映射加载成功');
      } else {
        throw new Error(result.message || '获取组织ID映射失败');
      }
    } catch (error) {
      console.error('Failed to fetch org2id mapping:', error);
      message.error('获取组织ID映射失败，请刷新页面重试');
      // Fallback to empty mapping
      setOrg2id({});
      setOrgOptions([]);
    } finally {
      setLoadingOrg2id(false);
    }
  };

  // Load org2id mapping on component mount
  useEffect(() => {
    fetchOrg2idMapping();
  }, []);

  // Handle organization selection change
  const handleOrgChange = (orgs: string[]) => {
    setSelectedOrgs(orgs);
    
    // Update available IDs based on selected organizations
    const newAvailableIds: {id: string, name: string, orgName: string}[] = [];
    orgs.forEach(orgName => {
      if (org2id[orgName]) {
        org2id[orgName].forEach((idInfo: IdInfo) => {
          newAvailableIds.push({
            id: idInfo.id,
            name: idInfo.name,
            orgName: orgName
          });
        });
      }
    });
    setAvailableIds(newAvailableIds);
    
    // Clear selected IDs when organizations change
    setSelectedIds([]);
    form.setFieldsValue({ selectedIds: [] });
  };

  const handleUpdate = async (values: any) => {
    try {
      setLoading(true);
      setProgress(0);
      setUpdateResults([]);
      
      const { orgNames, selectedIds: formSelectedIds, startPage, endPage } = values;
      
      // Determine which IDs to update
      let idsToUpdate: {id: string, name: string, orgName: string}[] = [];
      
      if (formSelectedIds && formSelectedIds.length > 0) {
        // Use specifically selected IDs
        idsToUpdate = availableIds.filter(idInfo => formSelectedIds.includes(idInfo.id));
      } else if (orgNames && orgNames.length > 0) {
        // Use all IDs from selected organizations
        orgNames.forEach((orgName: string) => {
          if (org2id[orgName]) {
            org2id[orgName].forEach((idInfo: IdInfo) => {
              idsToUpdate.push({
                id: idInfo.id,
                name: idInfo.name,
                orgName: orgName
              });
            });
          }
        });
      } else {
        // Use all IDs from all organizations
        orgOptions.forEach(orgName => {
          if (org2id[orgName]) {
            org2id[orgName].forEach((idInfo: IdInfo) => {
              idsToUpdate.push({
                id: idInfo.id,
                name: idInfo.name,
                orgName: orgName
              });
            });
          }
        });
      }
      
      const totalIds = idsToUpdate.length;
      const totalPages = endPage - startPage + 1;
      const totalTasks = totalIds * totalPages; // 总任务数 = 机构数 × 页面数
      const results: UpdateResult[] = [];
      let completedTasks = 0;

      for (let i = 0; i < idsToUpdate.length; i++) {
        const idInfo = idsToUpdate[i];
        
        // 按页面范围逐页更新，提供更精确的进度
        for (let page = startPage; page <= endPage; page++) {
          setCurrentOrg(`${idInfo.orgName} - ${idInfo.name} (第${page}页/${totalPages}页)`);
          
          // 计算当前进度：已完成任务数 / 总任务数
          const currentProgress = Math.round((completedTasks / totalTasks) * 100);
          setProgress(currentProgress);

          try {
            const params = {
              orgName: idInfo.orgName,
              selectedIds: [idInfo.id],
              startPage: page,
              endPage: page, // 逐页处理
            };

            const result = await caseApi.updateCases(params);
            
            // 如果是该机构的第一页，创建结果记录
            if (page === startPage) {
              results.push({
                orgName: idInfo.orgName,
                idName: idInfo.name,
                success: true,
                count: result.count,
              });
            } else {
              // 累加后续页面的案例数
              const existingResult = results.find(r => 
                r.orgName === idInfo.orgName && r.idName === idInfo.name
              );
              if (existingResult) {
                existingResult.count += result.count;
              }
            }

            if (result.count > 0) {
              message.success(`${idInfo.orgName} - ${idInfo.name} 第${page}页更新完成，新增 ${result.count} 条案例`);
            }
          } catch (error) {
            // 如果是该机构的第一页且出错，创建失败记录
            if (page === startPage) {
              results.push({
                orgName: idInfo.orgName,
                idName: idInfo.name,
                success: false,
                count: 0,
                error: error instanceof Error ? error.message : '未知错误',
              });
            }
            message.error(`${idInfo.orgName} - ${idInfo.name} 第${page}页更新失败`);
          }

          completedTasks++;
          setUpdateResults([...results]);
        }
      }

      setProgress(100);
      setCurrentOrg('');
      
      const successCount = results.filter(r => r.success).length;
      const totalCount = results.reduce((sum, r) => sum + r.count, 0);
      
      message.success(
        `更新完成！成功更新 ${successCount}/${totalIds} 个ID，处理 ${totalPages} 页，共 ${totalCount} 条案例`
      );
    } catch (error) {
      message.error('更新过程中发生错误');
      console.error('Update error:', error);
    } finally {
      setLoading(false);
      setProgress(0);
      setCurrentOrg('');
    }
  };

  const handleUpdateAnalysisData = async () => {
    try {
      setLoading(true);
      // Call update analysis data API endpoint
      const response = await fetch('http://localhost:8000/update-analysis-data', { method: 'POST' });
      const result = await response.json();
      
      if (result.success) {
        message.success(`分析数据更新完成，共处理 ${result.count || 0} 条记录`);
      } else {
        message.error(`分析数据更新失败: ${result.error || '未知错误'}`);
      }
    } catch (error) {
      message.error('分析数据更新失败');
      console.error('Update analysis data error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    form.resetFields();
    setUpdateResults([]);
    setProgress(0);
    setCurrentOrg('');
  };

  const getTotalUpdated = () => {
    return updateResults.reduce((sum, result) => sum + result.count, 0);
  };

  const getSuccessRate = () => {
    if (updateResults.length === 0) return 0;
    const successCount = updateResults.filter(r => r.success).length;
    return Math.round((successCount / updateResults.length) * 100);
  };

  return (
    <div className="space-y-6">
      {/* Update Form */}
      <Card title="案例更新配置">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleUpdate}
          initialValues={{
            startPage: 1,
            endPage: 1,
          }}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Form.Item
              label="选择机构"
              name="orgNames"
              tooltip="选择机构后可进一步选择具体ID"
            >
              <Select
                mode="multiple"
                placeholder={loadingOrg2id ? "正在加载机构列表..." : "请选择机构（留空则选择全部）"}
                allowClear
                onChange={handleOrgChange}
                loading={loadingOrg2id}
                disabled={loadingOrg2id}
              >
                {orgOptions.map(org => (
                  <Option key={org} value={org}>{org}</Option>
                ))}
              </Select>
            </Form.Item>
            
            <Form.Item
              label="选择具体ID"
              name="selectedIds"
              tooltip="可选择具体的ID进行更新，留空则更新所选机构的所有ID"
            >
              <Select
                mode="multiple"
                placeholder="请先选择机构，然后选择具体ID（留空则选择所选机构的全部ID）"
                allowClear
                disabled={availableIds.length === 0}
                onChange={setSelectedIds}
              >
                {availableIds.map(idInfo => (
                  <Option key={idInfo.id} value={idInfo.id}>
                    {idInfo.orgName} - {idInfo.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Form.Item
              label="起始页"
              name="startPage"
              rules={[{ required: true, message: '请输入起始页' }]}
            >
              <InputNumber
                min={1}
                className="w-full"
                placeholder="起始页码"
              />
            </Form.Item>
            
            <Form.Item
              label="结束页"
              name="endPage"
              rules={[{ required: true, message: '请输入结束页' }]}
            >
              <InputNumber
                min={1}
                className="w-full"
                placeholder="结束页码"
              />
            </Form.Item>
          </div>
          
          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SyncOutlined />}
                loading={loading}
                disabled={loading}
              >
                开始更新
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleUpdateAnalysisData}
                loading={loading}
              >
                更新分析数据
              </Button>
              <Button onClick={handleReset}>
                重置
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {/* Progress */}
      {loading && (
        <Card title="更新进度">
          <div className="space-y-4">
            <Progress
              percent={progress}
              status={progress === 100 ? 'success' : 'active'}
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
              format={(percent) => `${percent}%`}
            />
            {currentOrg && (
              <Alert
                message={`正在更新: ${currentOrg}`}
                description={`总体进度: ${progress}% - 按页面逐步处理中`}
                type="info"
                showIcon
              />
            )}
            <div className="text-sm text-gray-500">
              提示：进度条根据页面范围和机构数量计算，每完成一页更新进度条会相应推进
            </div>
          </div>
        </Card>
      )}

      {/* Results Summary */}
      {updateResults.length > 0 && (
        <Card title="更新结果">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="text-center">
              <Title level={3} className="text-blue-600">
                {updateResults.length}
              </Title>
              <Text>处理机构数</Text>
            </div>
            <div className="text-center">
              <Title level={3} className="text-green-600">
                {getTotalUpdated()}
              </Title>
              <Text>更新案例数</Text>
            </div>
            <div className="text-center">
              <Title level={3} className="text-orange-600">
                {getSuccessRate()}%
              </Title>
              <Text>成功率</Text>
            </div>
          </div>
          
          <Divider />
          
          <List
            dataSource={updateResults}
            renderItem={(result) => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong>{result.orgName} - {result.idName}</Text>
                      {result.success ? (
                        <Text type="success">✓ 成功</Text>
                      ) : (
                        <Text type="danger">✗ 失败</Text>
                      )}
                    </Space>
                  }
                  description={
                    result.success
                      ? `更新了 ${result.count} 条案例`
                      : `错误: ${result.error}`
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  );
};

export default CaseUpdate;