'use client';

import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Spin, Alert, Button, Table } from 'antd';
import { FileTextOutlined, BankOutlined, CalendarOutlined, ReloadOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { caseApi, CaseSummary as CaseSummaryType, OrgSummaryItem, OrgChartData } from '@/services/api';

const CaseSummary: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<CaseSummaryType | null>(null);
  const [orgData, setOrgData] = useState<OrgSummaryItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSummary();
  }, []);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch org chart data, time trend data, and organization summary in parallel
      // Use org-chart-data for pie chart to ensure consistency with table
      const [orgChartData, timeTrendData, orgSummaryData] = await Promise.all([
        caseApi.getOrgChartData(),
        caseApi.getSummary(), // Still need this for time trend data
        caseApi.getOrgSummary()
      ]);
      
      // Combine the data: use org chart data for organization counts, time trend data for months
      const combinedData = {
        total: orgChartData.total,
        byOrg: orgChartData.byOrg,
        byMonth: timeTrendData.byMonth
      };
      
      setData(combinedData);
      setOrgData(orgSummaryData);
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
    if (!orgData || orgData.length === 0) return {};
    
    // Use the same data as the table for consistency
    // Limit to top 15 for chart readability, group the rest as "其他"
    const topOrgData = orgData.slice(0, 15);
    const otherOrgData = orgData.slice(15);
    
    let chartData = topOrgData.map((org) => ({
      name: org.orgName,
      value: org.caseCount,
    }));
    
    // Add "其他" category if there are more institutions
    if (otherOrgData.length > 0) {
      const otherSum = otherOrgData.reduce((sum, org) => sum + org.caseCount, 0);
      chartData.push({
        name: '其他',
        value: otherSum,
      });
    }

    return {
      title: {
        text: '各机构案例分布',
        left: 'center',
        top: 10,
      },
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)',
      },
      legend: {
        type: 'scroll',
        orient: 'horizontal',
        bottom: 0,
        left: 'center',
        itemWidth: 10,
        itemHeight: 10,
        textStyle: {
          fontSize: 10,
        },
        pageButtonItemGap: 5,
        pageIconSize: 10,
      },
      series: [
        {
          name: '案例数量',
          type: 'pie',
          radius: ['20%', '60%'], // Use donut chart for better readability
          center: ['50%', '45%'], // Adjust center to accommodate bottom legend
          data: chartData,
          label: {
            show: true,
            position: 'outside',
            formatter: function(params: any) {
              // Only show label for slices larger than 3%
              if (params.percent < 3) {
                return '';
              }
              return `${params.name}\n${params.percent}%`;
            },
            fontSize: 10,
          },
          labelLine: {
            show: true,
            length: 15,
            length2: 10,
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)',
            },
            label: {
              show: true,
              fontSize: 12,
              fontWeight: 'bold',
            },
          },
          // Set minimum angle for small slices to improve readability
          minAngle: 5,
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

  const getOrgTableData = () => {
    if (!orgData || orgData.length === 0) return [];
    
    return orgData.map((org, index) => ({
      key: index + 1,
      rank: index + 1,
      orgName: org.orgName,
      caseCount: org.caseCount,
      percentage: org.percentage.toFixed(2),
      dateRange: org.dateRange,
    }));
  };

  const orgTableColumns = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 80,
      align: 'center' as const,
    },
    {
      title: '机构名称',
      dataIndex: 'orgName',
      key: 'orgName',
      ellipsis: true,
    },
    {
      title: '案例数量',
      dataIndex: 'caseCount',
      key: 'caseCount',
      width: 120,
      align: 'right' as const,
      sorter: (a: any, b: any) => a.caseCount - b.caseCount,
    },
    {
      title: '占比 (%)',
      dataIndex: 'percentage',
      key: 'percentage',
      width: 100,
      align: 'right' as const,
      render: (value: string) => `${value}%`,
    },
    {
      title: '案例时间范围',
      dataIndex: 'dateRange',
      key: 'dateRange',
      width: 180,
      align: 'center' as const,
      render: (value: string) => (
        <span className="text-gray-600 text-sm">
          {value}
        </span>
      ),
    },
  ];

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
          <Card title="机构分布" className="h-[480px]">
            <ReactECharts
              option={getOrgChartOption()}
              style={{ height: '400px' }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="时间趋势" className="h-[480px]">
            <ReactECharts
              option={getMonthChartOption()}
              style={{ height: '400px' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Organization Summary Table */}
      <Row gutter={[16, 16]}>
        <Col xs={24}>
          <Card title="机构案例数量汇总表">
            <Table
              columns={orgTableColumns}
              dataSource={getOrgTableData()}
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => 
                  `第 ${range[0]}-${range[1]} 条，共 ${total} 个机构`,
              }}
              scroll={{ y: 400 }}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default CaseSummary;