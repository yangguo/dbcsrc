'use client';

import { useState } from 'react';
import { caseApi } from '../../services/api';

export default function TestDownload() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState('');

  const testDownload = async () => {
    try {
      setLoading(true);
      setResult('开始下载...');
      
      const blob = await caseApi.downloadOnlineData();
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `test_online_data_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      setResult('下载成功！');
    } catch (error) {
      console.error('Download error:', error);
      setResult(`下载失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">下载测试页面</h1>
      <button 
        onClick={testDownload}
        disabled={loading}
        className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50"
      >
        {loading ? '下载中...' : '测试下载在线数据'}
      </button>
      {result && (
        <div className="mt-4 p-4 border rounded">
          <p>{result}</p>
        </div>
      )}
    </div>
  );
}