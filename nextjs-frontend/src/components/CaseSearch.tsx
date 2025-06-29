'use client';

import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  Table,
  Space,
  Modal,
  Typography,
  Pagination,
  message,
} from 'antd';
import { SearchOutlined, EyeOutlined } from '@ant-design/icons';
import { caseApi, CaseDetail, SearchParams } from '@/services/api';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { Text, Paragraph } = Typography;

const orgOptions = [
  '山西', '四川', '新疆', '山东', '大连', '湖北', '湖南', '陕西',
  '天津', '宁夏', '安徽', '总部', '北京', '江苏', '黑龙江', '甘肃',
  '宁波', '深圳', '河北', '广东', '厦门', '福建', '西藏', '青岛',
  '贵州', '河南', '广西', '内蒙古', '海南', '浙江', '云南', '辽宁',
  '吉林', '江西', '重庆', '上海', '青海'
];

const CaseSearch: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<CaseDetail[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selectedCase, setSelectedCase] = useState<CaseDetail | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      width: '30%',
    },
    {
      title: '发文日期',
      dataIndex: 'date',
      key: 'date',
      width: '12%',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: '机构',
      dataIndex: 'org',
      key: 'org',
      width: '10%',
    },
    {
      title: '处罚金额',
      dataIndex: 'amount',
      key: 'amount',
      width: '12%',
      render: (amount: number) => amount ? `¥${amount.toLocaleString()}` : '-',
    },
    {
      title: '处罚内容',
      dataIndex: 'penalty',
      key: 'penalty',
      ellipsis: true,
      width: '25%',
    },
    {
      title: '操作',
      key: 'action',
      width: '11%',
      render: (_: any, record: CaseDetail) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => showDetail(record)}
        >
          查看详情
        </Button>
      ),
    },
  ];

  const showDetail = (caseDetail: CaseDetail) => {
    setSelectedCase(caseDetail);
    setDetailVisible(true);
  };

  const handleSearch = async (values: any) => {
    try {
      setLoading(true);
      const params: SearchParams = {
        keyword: values.keyword,
        org: values.org,
        page: 1,
        pageSize,
      };

      if (values.dateRange) {
        params.dateFrom = values.dateRange[0].format('YYYY-MM-DD');
        params.dateTo = values.dateRange[1].format('YYYY-MM-DD');
      }

      const result = await caseApi.searchCases(params);
      setData(result.data);
      setTotal(result.total);
      setCurrentPage(1);
      message.success(`找到 ${result.total} 条案例`);
    } catch (error) {
      message.error('搜索失败，请稍后重试');
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = async (page: number, size?: number) => {
    try {
      setLoading(true);
      const values = form.getFieldsValue();
      const params: SearchParams = {
        keyword: values.keyword,
        org: values.org,
        page,
        pageSize: size || pageSize,
      };

      if (values.dateRange) {
        params.dateFrom = values.dateRange[0].format('YYYY-MM-DD');
        params.dateTo = values.dateRange[1].format('YYYY-MM-DD');
      }

      const result = await caseApi.searchCases(params);
      setData(result.data);
      setCurrentPage(page);
      if (size) setPageSize(size);
    } catch (error) {
      message.error('加载数据失败');
      console.error('Pagination error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    form.resetFields();
    setData([]);
    setTotal(0);
    setCurrentPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <Card title="搜索条件">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSearch}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Form.Item
              label="关键词"
              name="keyword"
            >
              <Input placeholder="请输入关键词" />
            </Form.Item>
            
            <Form.Item
              label="机构"
              name="org"
            >
              <Select placeholder="请选择机构" allowClear>
                {orgOptions.map(org => (
                  <Option key={org} value={org}>{org}</Option>
                ))}
              </Select>
            </Form.Item>
            
            <Form.Item
              label="日期范围"
              name="dateRange"
            >
              <RangePicker className="w-full" />
            </Form.Item>
            
            <Form.Item label=" " className="flex items-end">
              <Space>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SearchOutlined />}
                  loading={loading}
                >
                  搜索
                </Button>
                <Button onClick={handleReset}>
                  重置
                </Button>
              </Space>
            </Form.Item>
          </div>
        </Form>
      </Card>

      {/* Results Table */}
      <Card title={`搜索结果 (共 ${total} 条)`}>
        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={false}
          scroll={{ x: 1000 }}
        />
        
        {total > 0 && (
          <div className="mt-4 flex justify-end">
            <Pagination
              current={currentPage}
              total={total}
              pageSize={pageSize}
              showSizeChanger
              showQuickJumper
              showTotal={(total, range) =>
                `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
              }
              onChange={handlePageChange}
              onShowSizeChange={handlePageChange}
            />
          </div>
        )}
      </Card>

      {/* Detail Modal */}
      <Modal
        title="案例详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={800}
      >
        {selectedCase && (
          <div className="space-y-4">
            <div>
              <Text strong>标题：</Text>
              <Paragraph>{selectedCase.title}</Paragraph>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Text strong>发文日期：</Text>
                <Text>{dayjs(selectedCase.date).format('YYYY-MM-DD')}</Text>
              </div>
              <div>
                <Text strong>机构：</Text>
                <Text>{selectedCase.org}</Text>
              </div>
            </div>
            
            {selectedCase.amount && (
              <div>
                <Text strong>处罚金额：</Text>
                <Text>¥{selectedCase.amount.toLocaleString()}</Text>
              </div>
            )}
            
            <div>
              <Text strong>处罚内容：</Text>
              <Paragraph>{selectedCase.penalty}</Paragraph>
            </div>
            
            <div>
              <Text strong>详细内容：</Text>
              <Paragraph
                ellipsis={{ rows: 10, expandable: true, symbol: '展开' }}
              >
                {selectedCase.content}
              </Paragraph>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default CaseSearch;