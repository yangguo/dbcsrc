'use client';

import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Spin, Alert, Button } from 'antd';
import { FileTextOutlined, BankOutlined, CalendarOutlined, ReloadOutlined } from '@ant-design/icons';
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
    } catch (err: any) {
      console.error('Error fetching summary:', err);
      
      // Provide more specific error messages
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
    fetchSummary();
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
        <Spin size="large" tip="正在加载案例数据，请稍候...">
          <div className="h-32 w-32" />
        </Spin>
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
          <Button
            type="primary"
            size="small"
            icon={<ReloadOutlined />}
            onClick={handleRetry}
            loading={loading}
          >
            重试
          </Button>
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