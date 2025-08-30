'use client';

import React, { useState } from 'react';
import { Card, Form, Input, DatePicker, Button, Table, Space, App, InputNumber, Select, Tag, Tooltip, Modal, Typography, Descriptions } from 'antd';
import { SearchOutlined, ReloadOutlined, EyeOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;

type EnhancedCaseDetail = {
  id: string;
  name: string;
  docNumber: string;
  date: string;
  org: string;
  party: string;
  amount: number;
  penalty: string;
  violationFacts: string;
  penaltyBasis: string;
  penaltyDecision: string;
  content: string;
  region: string;
  industry: string;
  category: string;
};

const orgOptions = [
  '总部','北京','上海','深圳','广东','浙江','江苏','山东','四川','湖北','湖南','河南','河北','安徽','福建','江西','辽宁','吉林','黑龙江','内蒙古','山西','陕西','甘肃','青海','新疆','西藏','宁夏','广西','海南','贵州','云南','重庆','天津','大连','青岛','宁波','厦门'
];

export default function PenaltySearchMongo() {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<EnhancedCaseDetail[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selectedCase, setSelectedCase] = useState<EnhancedCaseDetail | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);

  const columns = [
    {
      title: '发文名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      width: 200,
      render: (text: string) => (
        <Tooltip title={text}>
          <Typography.Text ellipsis>{text}</Typography.Text>
        </Tooltip>
      ),
    },
    { title: '文号', dataIndex: 'docNumber', key: 'docNumber', ellipsis: true, width: 140 },
    { title: '发文日期', dataIndex: 'date', key: 'date', width: 110, render: (v: string)=> dayjs(v).format('YYYY-MM-DD'), sorter: (a: any, b: any)=> dayjs(a.date).unix() - dayjs(b.date).unix() },
    { title: '发文地区', dataIndex: 'org', key: 'org', width: 80, render: (v: string)=> <Tag color="blue">{v}</Tag> },
    { title: '当事人', dataIndex: 'party', key: 'party', ellipsis: true, width: 120 },
    { title: '罚款金额', dataIndex: 'amount', key: 'amount', width: 120, render: (n:number)=> n? <Typography.Text strong style={{ color: '#f5222d' }}>¥{n.toLocaleString()}</Typography.Text> : '-' , sorter: (a:any,b:any)=> (a.amount||0)-(b.amount||0)},
    { title: '案件类型', dataIndex: 'category', key: 'category', width: 100, render: (v: string)=> v? <Tag color='green'>{v}</Tag>:'-' },
    { title: '地区', dataIndex: 'region', key: 'region', width: 80, render: (v: string)=> v? <Tag color='orange'>{v}</Tag>:'-' },
    { title: '行业', dataIndex: 'industry', key: 'industry', width: 100, render: (v: string)=> v? <Tag color='purple'>{v}</Tag>:'-' },
    {
      title: '操作',
      key: 'action',
      width: 80,
      fixed: 'right' as const,
      render: (_: any, record: EnhancedCaseDetail) => (
        <Space>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={()=>{ setSelectedCase(record); setDetailVisible(true); }}>详情</Button>
        </Space>
      ),
    },
  ];

  async function fetchPage(page = 1, size = pageSize) {
    const values = form.getFieldsValue();
    const params = new URLSearchParams();
    if (values.keyword) params.set('keyword', values.keyword);
    if (values.docNumber) params.set('docNumber', values.docNumber);
    if (values.party) params.set('party', values.party);
    if (values.org) params.set('org', values.org);
    if (values.minAmount != null) params.set('minAmount', String(values.minAmount));
    if (values.legalBasis) params.set('legalBasis', values.legalBasis);
    if (values.dateRange?.[0]) params.set('dateFrom', values.dateRange[0].format('YYYY-MM-DD'));
    if (values.dateRange?.[1]) params.set('dateTo', values.dateRange[1].format('YYYY-MM-DD'));
    params.set('page', String(page));
    params.set('pageSize', String(size));

    setLoading(true);
    try {
      const res = await fetch(`/api/mongo-search?${params.toString()}`);
      const json = await res.json();
      setData(json.data || []);
      setTotal(json.total || 0);
      setCurrentPage(page);
      setPageSize(size);
    } catch (e) {
      console.error(e);
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  }

  const onSearch = async () => { await fetchPage(1, pageSize); };
  const onReset = () => { form.resetFields(); setData([]); setTotal(0); setCurrentPage(1); };

  return (
    <div style={{ padding: 24 }}>
      <Card title="Penalty Search (MongoDB)">
        <Form layout="vertical" form={form} onFinish={onSearch}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16 }}>
            <Form.Item label="案件关键词" name="keyword"><Input allowClear placeholder="关键词"/></Form.Item>
            <Form.Item label="文号" name="docNumber"><Input allowClear placeholder="文号"/></Form.Item>
            <Form.Item label="当事人" name="party"><Input allowClear placeholder="当事人"/></Form.Item>
            <Form.Item label="发文地区" name="org">
              <Select allowClear placeholder="选择地区">
                {orgOptions.map(o => <Option key={o} value={o}>{o}</Option>)}
              </Select>
            </Form.Item>
            <Form.Item label="日期范围" name="dateRange"><RangePicker style={{ width: '100%' }}/></Form.Item>
            <Form.Item label="最低罚款金额" name="minAmount"><InputNumber min={0} style={{ width: '100%' }}/></Form.Item>
            <Form.Item label="处罚依据" name="legalBasis"><Input allowClear placeholder="法律条款"/></Form.Item>
          </div>
          <Space>
            <Button type="primary" htmlType="submit" icon={<SearchOutlined />} loading={loading}>搜索</Button>
            <Button onClick={onReset} icon={<ReloadOutlined />}>重置</Button>
          </Space>
        </Form>
      </Card>

      <Card style={{ marginTop: 16 }} title={`搜索结果 (${total})`}>
        <Table
          rowKey={(r)=> r.id || r.docNumber || Math.random().toString(36)}
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={{
            current: currentPage,
            pageSize,
            total,
            showSizeChanger: true,
            onChange: (p, s)=> fetchPage(p, s)
          }}
          scroll={{ x: 900 }}
        />
      </Card>

      <Modal
        title="案例详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[<Button key="close" onClick={() => setDetailVisible(false)}>关闭</Button>]}
        width={1000}
      >
        {selectedCase && (
          <div>
            <Descriptions title="基本信息" bordered column={2} size="middle" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="发文名称" span={2}>
                <Typography.Text strong>{selectedCase.name}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="文号"><Tag color="blue">{selectedCase.docNumber}</Tag></Descriptions.Item>
              <Descriptions.Item label="发文日期">{dayjs(selectedCase.date).format('YYYY年MM月DD日')}</Descriptions.Item>
              <Descriptions.Item label="发文机构"><Tag color="green">{selectedCase.org}</Tag></Descriptions.Item>
              <Descriptions.Item label="案件类型">{selectedCase.category ? (<Tag color="orange">{selectedCase.category}</Tag>) : ('-')}</Descriptions.Item>
              <Descriptions.Item label="地区">{selectedCase.region ? (<Tag color="blue">{selectedCase.region}</Tag>) : ('-')}</Descriptions.Item>
              <Descriptions.Item label="行业">{selectedCase.industry ? (<Tag color="purple">{selectedCase.industry}</Tag>) : ('-')}</Descriptions.Item>
              <Descriptions.Item label="当事人" span={2}>{selectedCase.party || '-'}</Descriptions.Item>
              <Descriptions.Item label="罚款金额" span={2}>{selectedCase.amount ? (<Typography.Text strong style={{ color: '#f5222d' }}>¥{selectedCase.amount.toLocaleString()}</Typography.Text>) : ('-')}</Descriptions.Item>
              <Descriptions.Item label="违法事实" span={2}>{selectedCase.violationFacts || '-'}</Descriptions.Item>
              <Descriptions.Item label="法律依据" span={2}>{selectedCase.penaltyBasis || '-'}</Descriptions.Item>
              <Descriptions.Item label="处罚决定" span={2}>{selectedCase.penaltyDecision || '-'}</Descriptions.Item>
            </Descriptions>
            {selectedCase.content && (
              <Card title="详细内容" size="small" styles={{ body: { maxHeight: '300px', overflow: 'auto' } }}>
                <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.5, margin: 0, fontFamily: 'inherit' }}>{selectedCase.content}</pre>
              </Card>
            )}
            {selectedCase.id && (
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <Button type="primary" icon={<EyeOutlined />} href={selectedCase.id} target="_blank" rel="noopener noreferrer">查看原文</Button>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
