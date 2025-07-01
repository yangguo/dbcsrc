'use client';

import React, { useState } from 'react';
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
} from 'antd';
import { SyncOutlined, ReloadOutlined } from '@ant-design/icons';
import { caseApi, UpdateParams } from '@/services/api';

const { Option } = Select;
const { Text, Title } = Typography;

const orgOptions = [
  '山西', '四川', '新疆', '山东', '大连', '湖北', '湖南', '陕西',
  '天津', '宁夏', '安徽', '总部', '北京', '江苏', '黑龙江', '甘肃',
  '宁波', '深圳', '河北', '广东', '厦门', '福建', '西藏', '青岛',
  '贵州', '河南', '广西', '内蒙古', '海南', '浙江', '云南', '辽宁',
  '吉林', '江西', '重庆', '上海', '青海'
];

interface UpdateResult {
  orgName: string;
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

  const handleUpdate = async (values: any) => {
    try {
      setLoading(true);
      setProgress(0);
      setUpdateResults([]);
      
      const { orgNames, startPage, endPage } = values;
      const selectedOrgs = orgNames.length > 0 ? orgNames : orgOptions;
      const totalOrgs = selectedOrgs.length;
      const results: UpdateResult[] = [];

      for (let i = 0; i < selectedOrgs.length; i++) {
        const orgName = selectedOrgs[i];
        setCurrentOrg(orgName);
        setProgress(Math.round((i / totalOrgs) * 100));

        try {
          const params: UpdateParams = {
            orgName,
            startPage,
            endPage,
          };

          const result = await caseApi.updateCases(params);
          
          results.push({
            orgName,
            success: true,
            count: result.count,
          });

          message.success(`${orgName} 更新完成，共 ${result.count} 条案例`);
        } catch (error) {
          results.push({
            orgName,
            success: false,
            count: 0,
            error: error instanceof Error ? error.message : '未知错误',
          });
          message.error(`${orgName} 更新失败`);
        }

        setUpdateResults([...results]);
      }

      setProgress(100);
      setCurrentOrg('');
      
      const successCount = results.filter(r => r.success).length;
      const totalCount = results.reduce((sum, r) => sum + r.count, 0);
      
      message.success(
        `更新完成！成功更新 ${successCount}/${totalOrgs} 个机构，共 ${totalCount} 条案例`
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

  const handleRefreshData = async () => {
    try {
      setLoading(true);
      // Call refresh API endpoint
      await fetch('/api/refresh-data', { method: 'POST' });
      message.success('数据刷新完成');
    } catch (error) {
      message.error('数据刷新失败');
      console.error('Refresh error:', error);
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Form.Item
              label="选择机构"
              name="orgNames"
              tooltip="不选择则更新所有机构"
            >
              <Select
                mode="multiple"
                placeholder="请选择机构（留空则选择全部）"
                allowClear
              >
                {orgOptions.map(org => (
                  <Option key={org} value={org}>{org}</Option>
                ))}
              </Select>
            </Form.Item>
            
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
                onClick={handleRefreshData}
                loading={loading}
              >
                刷新数据
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
            />
            {currentOrg && (
              <Alert
                message={`正在更新: ${currentOrg}`}
                type="info"
                showIcon
              />
            )}
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
                      <Text strong>{result.orgName}</Text>
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