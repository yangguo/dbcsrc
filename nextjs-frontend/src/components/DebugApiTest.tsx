'use client';

import React, { useEffect, useState } from 'react';
import { Card, Button, Alert } from 'antd';
import { caseApi } from '@/services/api';

const DebugApiTest: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const testApi = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('Testing API call...');
      
      const data = await caseApi.getSummary();
      console.log('API Response:', data);
      setResult(data);
    } catch (err: any) {
      console.error('API Error:', err);
      setError(err.message || 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    testApi();
  }, []);

  return (
    <Card title="API Debug Test" style={{ margin: '20px' }}>
      <div style={{ marginBottom: '16px' }}>
        <Button onClick={testApi} loading={loading}>
          Test API Call
        </Button>
      </div>
      
      {error && (
        <Alert
          message="API Error"
          description={error}
          type="error"
          style={{ marginBottom: '16px' }}
        />
      )}
      
      {result && (
        <div>
          <h4>API Response:</h4>
          <pre style={{ background: '#f5f5f5', padding: '10px', borderRadius: '4px' }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </Card>
  );
};

export default DebugApiTest;