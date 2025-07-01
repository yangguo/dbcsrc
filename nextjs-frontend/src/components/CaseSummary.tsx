'use client';

import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Spin, Alert } from 'antd';
import { FileTextOutlined, BankOutlined, CalendarOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { caseApi, CaseSummary as CaseSummaryType } from '@/services/api';

const CaseSummary: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<CaseSummaryType | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSummary();
  }, []);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      setError(null);
      const summaryData = await caseApi.getSummary();
      setData(summaryData);
    } catch (err) {
      setError('获取数据失败，请稍后重试');
      console.error('Error fetching summary:', err);
    } finally {
      setLoading(false);
    }
  };

  const getOrgChartOption = () => {
    if (!data?.byOrg) return {};
    
    const orgData = Object.entries(data.byOrg).map(([name, value]) => ({
      name,
      value,
    }));

    return {
      title: {
        text: '各机构案例分布',
        left: 'center',
      },
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)',
      },
      legend: {
        orient: 'vertical',
        left: 'left',
      },
      series: [
        {
          name: '案例数量',
          type: 'pie',
          radius: '50%',
          data: orgData,
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

  const getMonthChartOption = () => {
    if (!data?.byMonth) return {};
    
    const monthData = Object.entries(data.byMonth)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([month, count]) => ({ month, count }));

    return {
      title: {
        text: '月度案例趋势',
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
      },
      xAxis: {
        type: 'category',
        data: monthData.map(item => item.month),
      },
      yAxis: {
        type: 'value',
      },
      series: [
        {
          name: '案例数量',
          type: 'line',
          data: monthData.map(item => item.count),
          smooth: true,
          itemStyle: {
            color: '#1890ff',
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                {
                  offset: 0,
                  color: 'rgba(24, 144, 255, 0.3)',
                },
                {
                  offset: 1,
                  color: 'rgba(24, 144, 255, 0.1)',
                },
              ],
            },
          },
        },
      ],
    };
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" tip="加载中...">
          <div className="h-32 w-32" />
        </Spin>
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="错误"
        description={error}
        type="error"
        showIcon
        action={
          <button
            className="ant-btn ant-btn-primary ant-btn-sm"
            onClick={fetchSummary}
          >
            重试
          </button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Statistics Cards */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="案例总数"
              value={data?.total || 0}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="涉及机构"
              value={Object.keys(data?.byOrg || {}).length}
              prefix={<BankOutlined />}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="覆盖月份"
              value={Object.keys(data?.byMonth || {}).length}
              prefix={<CalendarOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="机构分布" className="h-96">
            <ReactECharts
              option={getOrgChartOption()}
              style={{ height: '300px' }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="时间趋势" className="h-96">
            <ReactECharts
              option={getMonthChartOption()}
              style={{ height: '300px' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default CaseSummary;