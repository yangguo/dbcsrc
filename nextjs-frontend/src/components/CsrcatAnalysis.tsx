'use client';

import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Spin, Alert, Button, Table, Tag, Space } from 'antd';
import { ExclamationCircleOutlined, ReloadOutlined, DownloadOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { caseApi } from '@/services/api';

interface InvalidAmountRecord {
  id: string;
  url: string;
  title: string;
  date: string;
  org: string;
  amount: number | null;
  amountStatus: 'NaN' | 'Zero' | 'Negative' | 'NonNumeric';
  category: string;
  province: string;
  industry: string;
  lawlist: string;
}

interface AnalysisSummary {
  total: number;
  invalid: number;
  valid: number;
  invalidPercentage: number;
  nanCount: number;
  nonNumericCount: number;
  zeroCount: number;
  negativeCount: number;
}

interface AnalysisData {
  result: InvalidAmountRecord[];
  summary: AnalysisSummary;
}

const CsrcatAnalysis: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<AnalysisData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAnalysisData();
  }, []);

  const fetchAnalysisData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await caseApi.getCsrcatInvalidAmount();
      
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.message || '获取数据失败');
      }
    } catch (err: any) {
      console.error('Error fetching csrccat analysis:', err);
      
      let errorMessage = '获取数据失败，请稍后重试';
      
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        errorMessage = '请求超时，数据加载时间较长，请稍后重试';
      } else if (err.response?.status === 500) {
        errorMessage = '服务器内部错误，请联系管理员';
      } else if (err.response?.status === 404) {
        errorMessage = 'API接口未找到，请检查服务器配置';
      } else if (!navigator.onLine) {
        errorMessage = '网络连接异常，请检查网络设置';
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = () => {
    fetchAnalysisData();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'NaN':
        return 'red';
      case 'NonNumeric':
        return 'magenta';
      case 'Zero':
        return 'orange';
      case 'Negative':
        return 'volcano';
      default:
        return 'green';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'NaN':
        return '空值';
      case 'NonNumeric':
        return '非数字';
      case 'Zero':
        return '零值';
      case 'Negative':
        return '负值';
      default:
        return '有效';
    }
  };

  const getDistributionChartOption = () => {
    if (!data?.summary) return {};
    
    const { nanCount, zeroCount, negativeCount, nonNumericCount, valid } = data.summary;
    // 计算非零有效金额数量
    const nonZeroValidCount = valid - zeroCount;
    
    const chartData = [
      { name: '有效金额', value: nonZeroValidCount, itemStyle: { color: '#52c41a' } },
      { name: '零值', value: zeroCount, itemStyle: { color: '#fa8c16' } },
      { name: '空值', value: nanCount, itemStyle: { color: '#ff4d4f' } },
      { name: '非数字', value: nonNumericCount, itemStyle: { color: '#eb2f96' } },
      { name: '负值', value: negativeCount, itemStyle: { color: '#722ed1' } }
    ].filter(item => item.value > 0);

    return {
      title: {
        text: '金额字段分布',
        left: 'center',
        top: 10,
      },
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)',
      },
      legend: {
        orient: 'horizontal',
        bottom: 0,
        left: 'center',
      },
      series: [
        {
          name: '记录数量',
          type: 'pie',
          radius: ['20%', '60%'],
          center: ['50%', '45%'],
          data: chartData,
          label: {
            show: true,
            position: 'outside',
            formatter: '{b}\n{c}条\n({d}%)',
            fontSize: 10,
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)',
            },
          },
        },
      ],
    };
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
      ellipsis: true,
    },
    {
      title: '案例标题',
      dataIndex: 'title',
      key: 'title',
      width: 200,
      ellipsis: true,
    },
    {
      title: '发文日期',
      dataIndex: 'date',
      key: 'date',
      width: 120,
    },
    {
      title: '机构',
      dataIndex: 'org',
      key: 'org',
      width: 150,
      ellipsis: true,
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      width: 100,
      render: (amount: number | null) => {
        if (amount === null || amount === undefined) {
          return <Tag color="red">空值</Tag>;
        }
        if (amount === 0) {
          return <Tag color="orange">0</Tag>;
        }
        if (amount < 0) {
          return <Tag color="purple">{amount}</Tag>;
        }
        return amount;
      },
    },
    {
      title: '状态',
      dataIndex: 'amountStatus',
      key: 'amountStatus',
      width: 80,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {getStatusText(status)}
        </Tag>
      ),
    },
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      ellipsis: true,
    },
    {
      title: '省份',
      dataIndex: 'province',
      key: 'province',
      width: 100,
    },
    {
      title: '行业',
      dataIndex: 'industry',
      key: 'industry',
      width: 120,
      ellipsis: true,
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <p style={{ marginTop: 16 }}>正在分析CSRCCAT数据...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="数据加载失败"
        description={error}
        type="error"
        showIcon
        action={
          <Button size="small" danger onClick={handleRetry}>
            重试
          </Button>
        }
      />
    );
  }

  if (!data) {
    return (
      <Alert
        message="暂无数据"
        description="未找到CSRCCAT数据"
        type="info"
        showIcon
      />
    );
  }

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 操作按钮 */}
        <Row justify="space-between" align="middle">
          <Col>
            <h2>CSRCCAT金额字段分析</h2>
          </Col>
          <Col>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={handleRetry}>
                刷新数据
              </Button>
            </Space>
          </Col>
        </Row>

        {/* 统计卡片 */}
        <Row gutter={16}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="总记录数"
                value={data.summary.total}
                prefix={<ExclamationCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="无效记录数"
                value={data.summary.invalid}
                valueStyle={{ color: '#cf1322' }}
                prefix={<ExclamationCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="有效记录数"
                value={data.summary.valid}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="无效比例"
                value={data.summary.invalidPercentage}
                precision={2}
                suffix="%"
                valueStyle={{ color: data.summary.invalidPercentage > 10 ? '#cf1322' : '#fa8c16' }}
              />
            </Card>
          </Col>
        </Row>

        {/* 详细统计 */}
        <Row gutter={16}>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="空值记录"
                value={data.summary.nanCount}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="非数字记录"
                value={data.summary.nonNumericCount}
                valueStyle={{ color: '#eb2f96' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="零值记录"
                value={data.summary.zeroCount}
                valueStyle={{ color: '#fa8c16' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="负值记录"
                value={data.summary.negativeCount}
                valueStyle={{ color: '#fa541c' }}
              />
            </Card>
          </Col>
        </Row>

        {/* 分布图表 */}
        <Card title="金额字段分布图">
          <ReactECharts
            option={getDistributionChartOption()}
            style={{ height: '400px' }}
          />
        </Card>

        {/* 无效记录表格 */}
        <Card 
          title={`无效金额记录详情 (${data.result.length}条)`}
          extra={
            <Tag color="red">
              共发现 {data.result.length} 条无效记录
            </Tag>
          }
        >
          <Table
            columns={columns}
            dataSource={data.result}
            rowKey="id"
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
            }}
            scroll={{ x: 1200 }}
            size="small"
          />
        </Card>
      </Space>
    </div>
  );
};

export default CsrcatAnalysis;