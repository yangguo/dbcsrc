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
  App,
  InputNumber,
  Descriptions,
  Tag,
  Statistic,
  Row,
  Col,
  Divider,
  Tooltip,
} from 'antd';
import { 
  SearchOutlined, 
  EyeOutlined, 
  ReloadOutlined, 
  DownloadOutlined,
  FilterOutlined,
  BarChartOutlined,
  FileTextOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { caseApi, SearchStats, EnhancedCaseDetail } from '@/services/api';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { Text, Paragraph, Title } = Typography;
const { TextArea } = Input;

const orgOptions = [
  '山西', '四川', '新疆', '山东', '大连', '湖北', '湖南', '陕西',
  '天津', '宁夏', '安徽', '总部', '北京', '江苏', '黑龙江', '甘肃',
  '宁波', '深圳', '河北', '广东', '厦门', '福建', '西藏', '青岛',
  '贵州', '河南', '广西', '内蒙古', '海南', '浙江', '云南', '辽宁',
  '吉林', '江西', '重庆', '上海', '青海'
];

// 扩展的案例详情接口已从api.ts导入

// 扩展的搜索参数接口
interface EnhancedSearchParams {
  startDate?: string;
  endDate?: string;
  wenhao?: string;
  people?: string;
  caseKeyword?: string;
  org?: string[];
  minPenalty?: number;
  lawSelect?: string;
  page?: number;
  pageSize?: number;
}

// 搜索统计信息接口已从api.ts导入

const CaseSearch: React.FC = () => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<EnhancedCaseDetail[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selectedCase, setSelectedCase] = useState<EnhancedCaseDetail | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [statsVisible, setStatsVisible] = useState(false);
  const [searchStats, setSearchStats] = useState<SearchStats | null>(null);
  const [advancedSearch, setAdvancedSearch] = useState(false);

  // 机构选项
  const orgOptions = [
    '证监会',
    '银保监会', 
    '央行',
    '上交所',
    '深交所',
    '北交所',
    '中证协',
    '基金业协会'
  ];

  const columns = [
    {
      title: '发文名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      width: '18%',
      render: (text: string) => (
        <Tooltip title={text}>
          <Text ellipsis>{text}</Text>
        </Tooltip>
      ),
    },
    {
      title: '文号',
      dataIndex: 'docNumber',
      key: 'docNumber',
      ellipsis: true,
      width: '12%',
    },
    {
      title: '发文日期',
      dataIndex: 'date',
      key: 'date',
      width: '10%',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
      sorter: (a: any, b: any) => 
        dayjs(a.date).unix() - dayjs(b.date).unix(),
    },
    {
      title: '发文机构',
      dataIndex: 'org',
      key: 'org',
      width: '8%',
      render: (org: string) => <Tag color="blue">{org}</Tag>,
    },
    {
      title: '当事人',
      dataIndex: 'party',
      key: 'party',
      ellipsis: true,
      width: '10%',
    },
    {
      title: '罚款金额',
      dataIndex: 'amount',
      key: 'amount',
      width: '10%',
      render: (amount: number) => {
        if (!amount || amount === 0) return '-';
        return (
          <Text strong style={{ color: '#f5222d' }}>
            ¥{amount.toLocaleString()}
          </Text>
        );
      },
      sorter: (a: any, b: any) => 
        (a.amount || 0) - (b.amount || 0),
    },
    {
      title: '案件类型',
      dataIndex: 'category',
      key: 'category',
      width: '8%',
      render: (type: string) => type ? <Tag color="green">{type}</Tag> : '-',
    },
    {
      title: '地区',
      dataIndex: 'region',
      key: 'region',
      width: '6%',
      render: (region: string) => region ? <Tag color="orange">{region}</Tag> : '-',
    },
    {
      title: '行业',
      dataIndex: 'industry',
      key: 'industry',
      width: '8%',
      render: (industry: string) => industry ? <Tag color="purple">{industry}</Tag> : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: '10%',
      render: (_: any, record: any) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => showDetail(record)}
            size="small"
          >
            详情
          </Button>
        </Space>
      ),
    },
  ];

  const showDetail = (caseDetail: EnhancedCaseDetail) => {
    setSelectedCase(caseDetail);
    setDetailVisible(true);
  };

  const handleSearch = async (values: any) => {
    setLoading(true);
    try {
      const params: EnhancedSearchParams = {
        keyword: values.keyword,
        docNumber: values.docNumber,
        party: values.party,
        org: values.org,
        minAmount: values.minAmount,
        legalBasis: values.legalBasis,
        startDate: values.dateRange?.[0]?.format('YYYY-MM-DD'),
        endDate: values.dateRange?.[1]?.format('YYYY-MM-DD'),
        page: 1,
        pageSize,
      };
      
      const response = await caseApi.searchCasesEnhanced(params);
      setData(response.data);
      setTotal(response.total);
      setCurrentPage(1);
      
      // 计算搜索统计信息
      const stats: SearchStats = {
        totalCases: response.total,
        totalAmount: response.data.reduce((sum, item) => sum + (item.amount || 0), 0),
        avgAmount: response.data.length > 0 ? 
          response.data.reduce((sum, item) => sum + (item.amount || 0), 0) / response.data.length : 0,
        orgDistribution: response.data.reduce((acc, item) => {
          acc[item.org] = (acc[item.org] || 0) + 1;
          return acc;
        }, {} as Record<string, number>),
        monthlyDistribution: response.data.reduce((acc, item) => {
          const month = dayjs(item.date).format('YYYY-MM');
          acc[month] = (acc[month] || 0) + 1;
          return acc;
        }, {} as Record<string, number>)
      };
      setSearchStats(stats);
      
      message.success(`搜索完成，共找到 ${response.total} 条记录`);
    } catch (error) {
      console.error('搜索失败:', error);
      message.error('搜索失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = async (page: number, size?: number) => {
    setLoading(true);
    try {
      const formValues = form.getFieldsValue();
      const searchParams = {
        keyword: formValues.keyword,
        docNumber: formValues.docNumber,
        party: formValues.party,
        org: formValues.org,
        minAmount: formValues.minAmount,
        legalBasis: formValues.legalBasis,
        startDate: formValues.dateRange?.[0]?.format('YYYY-MM-DD'),
        endDate: formValues.dateRange?.[1]?.format('YYYY-MM-DD'),
        page: page,
        pageSize: size || pageSize,
      };

      const response = await caseApi.searchCasesEnhanced(searchParams);
      setData(response.data);
      setTotal(response.total);
      setCurrentPage(page);
      if (size) setPageSize(size);
    } catch (error) {
      console.error('Page change failed:', error);
      message.error('加载数据失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    form.resetFields();
    setData([]);
    setTotal(0);
    setCurrentPage(1);
    setSearchStats(null);
  };

  const handleDownload = async () => {
    try {
      message.info('正在准备下载...');
      // 这里可以调用下载API
      // await caseApi.downloadSearchResults(data);
      message.success('下载完成');
    } catch (error) {
      message.error('下载失败');
    }
  };

  return (
    <div style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
      {/* Search Form */}
      <Card 
        title={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '18px', fontWeight: 'bold' }}>
              <FilterOutlined style={{ marginRight: '8px' }} />
              案例搜索
            </span>
            <Space>
              <Button 
                type="text" 
                icon={<BarChartOutlined />}
                onClick={() => setStatsVisible(!statsVisible)}
              >
                统计信息
              </Button>
              <Button 
                type="text" 
                onClick={() => setAdvancedSearch(!advancedSearch)}
              >
                {advancedSearch ? '简单搜索' : '高级搜索'}
              </Button>
            </Space>
          </div>
        }
        style={{ marginBottom: '24px' }}
        styles={{ body: { padding: '24px' } }}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSearch}
          style={{ marginBottom: '16px' }}
        >
          <Row gutter={[16, 16]}>
            <Col span={advancedSearch ? 6 : 8}>
              <Form.Item label="案件关键词" name="keyword">
                <Input 
                  placeholder="请输入案件关键词" 
                  allowClear 
                  prefix={<SearchOutlined />}
                />
              </Form.Item>
            </Col>
            {advancedSearch && (
              <Col span={6}>
                <Form.Item label="文号" name="docNumber">
                  <Input placeholder="请输入文号" allowClear />
                </Form.Item>
              </Col>
            )}
            <Col span={advancedSearch ? 6 : 8}>
              <Form.Item label="发文机构" name="org">
                <Select placeholder="请选择发文机构" allowClear>
                  {orgOptions.map(org => (
                    <Option key={org} value={org}>{org}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={advancedSearch ? 6 : 8}>
              <Form.Item label="日期范围" name="dateRange">
                <RangePicker 
                  style={{ width: '100%' }} 
                  placeholder={['开始日期', '结束日期']}
                />
              </Form.Item>
            </Col>
          </Row>
          
          {advancedSearch && (
            <Row gutter={[16, 16]}>
              <Col span={6}>
                <Form.Item label="当事人" name="party">
                  <Input placeholder="请输入当事人名称" allowClear />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="最低罚款金额" name="minAmount">
                  <InputNumber 
                    placeholder="请输入金额"
                    style={{ width: '100%' }}
                    formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    parser={value => value!.replace(/¥\s?|(,*)/g, '')}
                    min={0}
                  />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label="处罚依据" name="legalBasis">
                  <Select placeholder="请选择处罚依据" allowClear>
                    <Option value="证券法">证券法</Option>
                    <Option value="公司法">公司法</Option>
                    <Option value="基金法">基金法</Option>
                    <Option value="期货条例">期货条例</Option>
                    <Option value="上市公司信息披露管理办法">上市公司信息披露管理办法</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={6}>
                <div style={{ height: '32px' }} />
              </Col>
            </Row>
          )}
          
          <Row>
            <Col span={24}>
              <Space size="middle">
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={loading}
                  icon={<SearchOutlined />}
                  size="large"
                >
                  搜索案例
                </Button>
                <Button 
                  onClick={handleReset}
                  icon={<ReloadOutlined />}
                  size="large"
                >
                  重置条件
                </Button>
                {data.length > 0 && (
                  <Button 
                    onClick={handleDownload}
                    icon={<DownloadOutlined />}
                    size="large"
                  >
                    导出结果
                  </Button>
                )}
              </Space>
            </Col>
          </Row>
        </Form>
      </Card>

      {/* Statistics */}
      {statsVisible && searchStats && (
        <Card 
          title={
            <span>
              <BarChartOutlined style={{ marginRight: '8px' }} />
              搜索统计
            </span>
          }
          style={{ marginBottom: '24px' }}
        >
          <Row gutter={[16, 16]}>
            <Col span={6}>
              <Statistic
                title="案例总数"
                value={searchStats.totalCases}
                valueStyle={{ color: '#1890ff' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="罚款总额"
                value={searchStats.totalAmount}
                precision={0}
                prefix="¥"
                valueStyle={{ color: '#f5222d' }}
                formatter={(value) => `${Number(value).toLocaleString()}`}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="平均罚款"
                value={searchStats.avgAmount}
                precision={0}
                prefix="¥"
                valueStyle={{ color: '#52c41a' }}
                formatter={(value) => `${Number(value).toLocaleString()}`}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="涉及机构"
                value={Object.keys(searchStats.orgDistribution).length}
                suffix="个"
                valueStyle={{ color: '#722ed1' }}
              />
            </Col>
          </Row>
          
          <Divider />
          
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <div>
                <Text strong>机构分布：</Text>
                <div style={{ marginTop: '8px' }}>
                  {Object.entries(searchStats.orgDistribution)
                    .sort(([,a], [,b]) => b - a)
                    .slice(0, 5)
                    .map(([org, count]) => (
                      <Tag key={org} color="blue" style={{ margin: '2px' }}>
                        {org}: {count}件
                      </Tag>
                    ))
                  }
                </div>
              </div>
            </Col>
            <Col span={12}>
              <div>
                <Text strong>月度分布：</Text>
                <div style={{ marginTop: '8px' }}>
                  {Object.entries(searchStats.monthlyDistribution)
                    .sort(([a], [b]) => b.localeCompare(a))
                    .slice(0, 6)
                    .map(([month, count]) => (
                      <Tag key={month} color="green" style={{ margin: '2px' }}>
                        {month}: {count}件
                      </Tag>
                    ))
                  }
                </div>
              </div>
            </Col>
          </Row>
        </Card>
      )}

      {/* Results Table */}
      <Card 
        title={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>
              搜索结果 ({total.toLocaleString()} 条)
            </span>
            <Space>
              <Text type="secondary">
                显示第 {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, total)} 条
              </Text>
            </Space>
          </div>
        }
        styles={{ body: { padding: '0' } }}
      >
        <Table
          columns={columns}
          dataSource={data}
          rowKey={(record) => record.id || record.docNumber || Math.random().toString(36)}
          loading={loading}
          pagination={false}
          scroll={{ x: 1400 }}
          size="middle"
          bordered
          rowClassName={(record, index) => 
            index % 2 === 0 ? 'table-row-light' : 'table-row-dark'
          }
        />
        
        {total > 0 && (
          <div style={{ padding: '16px', textAlign: 'center', borderTop: '1px solid #f0f0f0' }}>
            <Pagination
              current={currentPage}
              total={total}
              pageSize={pageSize}
              showSizeChanger
              showQuickJumper
              showTotal={(total, range) => 
                `第 ${range[0].toLocaleString()}-${range[1].toLocaleString()} 条，共 ${total.toLocaleString()} 条`
              }
              onChange={handlePageChange}
              onShowSizeChange={handlePageChange}
              pageSizeOptions={['10', '20', '50', '100']}
            />
          </div>
        )}
      </Card>

      {/* Detail Modal */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <EyeOutlined style={{ marginRight: '8px' }} />
            案例详情
          </div>
        }
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)} size="large">
            关闭
          </Button>,
        ]}
        width={1000}
        styles={{ body: { maxHeight: '70vh', overflow: 'auto' } }}
      >
        {selectedCase && (
          <div>
            <Descriptions 
              title="基本信息" 
              bordered 
              column={2}
              size="middle"
              style={{ marginBottom: '24px' }}
            >
              <Descriptions.Item label="发文名称" span={2}>
                <Text strong>{selectedCase.name}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="文号">
                <Tag color="blue">{selectedCase.docNumber}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="发文日期">
                {dayjs(selectedCase.date).format('YYYY年MM月DD日')}
              </Descriptions.Item>
              <Descriptions.Item label="发文机构">
                <Tag color="green">{selectedCase.org}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="案件类型">
                {selectedCase.category ? (
                  <Tag color="orange">{selectedCase.category}</Tag>
                ) : (
                  <Text type="secondary">未分类</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="地区">
                {selectedCase.region ? (
                  <Tag color="blue">{selectedCase.region}</Tag>
                ) : (
                  <Text type="secondary">未指定</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="行业">
                {selectedCase.industry ? (
                  <Tag color="purple">{selectedCase.industry}</Tag>
                ) : (
                  <Text type="secondary">未指定</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="当事人" span={2}>
                <Text>{selectedCase.party || '未指定'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="罚款金额" span={2}>
                {selectedCase.amount ? (
                  <Text strong style={{ color: '#f5222d', fontSize: '16px' }}>
                    ¥{selectedCase.amount.toLocaleString()}
                  </Text>
                ) : (
                  <Text type="secondary">无罚款</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="违法事实" span={2}>
                <Text>{selectedCase.violationFacts || '未提供'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="法律依据" span={2}>
                <Text>{selectedCase.penaltyBasis || '未提供'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="处罚决定" span={2}>
                <Text>{selectedCase.penaltyDecision || '未提供'}</Text>
              </Descriptions.Item>
            </Descriptions>

            {selectedCase.content && (
              <Card 
                title="详细内容" 
                size="small" 
                style={{ marginBottom: '16px' }}
                styles={{ body: { maxHeight: '300px', overflow: 'auto' } }}
              >
                <pre style={{ 
                  whiteSpace: 'pre-wrap', 
                  fontSize: '13px', 
                  lineHeight: '1.5',
                  margin: 0,
                  fontFamily: 'inherit'
                }}>
                  {selectedCase.content}
                </pre>
              </Card>
            )}

            {selectedCase.id && (
              <div style={{ textAlign: 'center', marginTop: '16px' }}>
                <Button 
                  type="primary" 
                  icon={<EyeOutlined />}
                  href={selectedCase.id}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  查看原文
                </Button>
              </div>
            )}
          </div>
        )}
      </Modal>
      
      <style jsx global>{`
        .table-row-light {
          background-color: #fafafa;
        }
        .table-row-dark {
          background-color: #ffffff;
        }
        .table-row-light:hover,
        .table-row-dark:hover {
          background-color: #e6f7ff !important;
        }
      `}</style>
    </div>
  );
};

export default CaseSearch;