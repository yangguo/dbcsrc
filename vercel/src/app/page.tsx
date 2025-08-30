"use client";

import { useState, useEffect } from "react";

// 日期选择组件
const DatePicker = ({ value, onChange, placeholder }: { value: string; onChange: (value: string) => void; placeholder: string }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [displayValue, setDisplayValue] = useState('');

  useEffect(() => {
    if (value) {
      const date = new Date(value);
      setDisplayValue(date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      }));
    } else {
      setDisplayValue('');
    }
  }, [value]);

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);
    setIsOpen(false);
  };

  const clearDate = () => {
    onChange('');
    setDisplayValue('');
  };

  return (
    <div className="date-picker-container">
      <div className="date-picker-input" onClick={() => setIsOpen(!isOpen)}>
        <input
          type="text"
          className="form-input date-display"
          placeholder={placeholder}
          value={displayValue}
          readOnly
        />
        <div className="date-picker-icons">
          {value && (
            <button
              type="button"
              className="date-clear-btn"
              onClick={(e) => {
                e.stopPropagation();
                clearDate();
              }}
            >
              ✕
            </button>
          )}
          <span className="date-calendar-icon">📅</span>
        </div>
      </div>
      {isOpen && (
        <div className="date-picker-overlay" onClick={() => setIsOpen(false)}>
          <div className="date-picker-popup" onClick={(e) => e.stopPropagation()}>
            <input
              type="date"
              className="date-picker-native"
              value={value}
              onChange={handleDateChange}
              autoFocus
            />
          </div>
        </div>
      )}
    </div>
  );
};

type Result = {
  id: string;
  name: string;
  docNumber: string;
  date: string;
  org: string;
  party: string;
  region?: string;
  caseType?: string;
  industry?: string;
  legalBasis?: string;
  amount: number;
  category?: string;
  violationFacts?: string;
  legalProvisions?: string;
  penaltyDecision?: string;
  detailedContent?: string;
  originalLink?: string;
};

export default function Page() {
  const [keyword, setKeyword] = useState("");
  const [org, setOrg] = useState("");
  const [party, setParty] = useState("");
  const [region, setRegion] = useState("");
  const [caseType, setCaseType] = useState("");
  const [industry, setIndustry] = useState("");
  const [legalBasis, setLegalBasis] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [minAmount, setMinAmount] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Result[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [selectedCase, setSelectedCase] = useState<Result | null>(null);
  const [showModal, setShowModal] = useState(false);

  // 初始化主题
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    const initialTheme = savedTheme || systemTheme;
    setTheme(initialTheme);
    document.documentElement.setAttribute('data-theme', initialTheme);
  }, []);

  // 切换主题
  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  const search = async (e: React.FormEvent, resetPage = true) => {
    e.preventDefault();
    if (resetPage) setPage(1);
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (keyword) params.set("keyword", keyword);
      if (org) params.set("org", org);
      if (party) params.set("party", party);
      if (region) params.set("region", region);
      if (caseType) params.set("caseType", caseType);
      if (industry) params.set("industry", industry);
      if (legalBasis) params.set("legalBasis", legalBasis);
      if (dateFrom) params.set("dateFrom", dateFrom);
      if (dateTo) params.set("dateTo", dateTo);
      if (minAmount) params.set("minAmount", minAmount);
      params.set("page", page.toString());
      params.set("pageSize", pageSize.toString());
      const res = await fetch(`/api/search?${params.toString()}`);
      const data = await res.json();
      setResults(data.data || []);
      setTotal(data.total || 0);
    } catch (e) {
      console.error(e);
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  // 当页码改变时重新搜索
  useEffect(() => {
    if (page > 1) {
      const searchWithCurrentParams = async () => {
        setLoading(true);
        try {
          const params = new URLSearchParams();
          if (keyword) params.set("keyword", keyword);
          if (org) params.set("org", org);
          if (party) params.set("party", party);
          if (region) params.set("region", region);
          if (caseType) params.set("caseType", caseType);
          if (industry) params.set("industry", industry);
          if (legalBasis) params.set("legalBasis", legalBasis);
          if (dateFrom) params.set("dateFrom", dateFrom);
          if (dateTo) params.set("dateTo", dateTo);
          if (minAmount) params.set("minAmount", minAmount);
          params.set("page", page.toString());
          params.set("pageSize", pageSize.toString());
          const res = await fetch(`/api/search?${params.toString()}`);
          const data = await res.json();
          setResults(data.data || []);
          setTotal(data.total || 0);
        } catch (e) {
          console.error(e);
          setResults([]);
          setTotal(0);
        } finally {
          setLoading(false);
        }
      };
      searchWithCurrentParams();
    }
  }, [page, keyword, org, party, region, caseType, industry, legalBasis, dateFrom, dateTo, minAmount, pageSize]);

  const totalPages = Math.ceil(total / pageSize);

  const goToPage = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      });
    } catch {
      return dateString;
    }
  };

  const formatAmount = (amount: number) => {
    if (amount === 0) return '0';
    return amount?.toLocaleString?.('zh-CN') ?? amount;
  };

  const openCaseDetail = (caseData: Result) => {
    setSelectedCase(caseData);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setSelectedCase(null);
  };

  const downloadResults = (format: 'csv' | 'json') => {
    if (results.length === 0) {
      alert('没有搜索结果可以下载');
      return;
    }

    let content = '';
    let filename = '';
    let mimeType = '';

    if (format === 'csv') {
      // CSV格式
      const headers = [
        '案例名称', '处罚决定书文号', '处罚日期', '监管机构', '当事人', 
        '地区', '案件类型', '行业', '处罚依据', '罚款金额', 
        '违法事实', '法律依据', '处罚决定', '详细内容', '原文链接'
      ];
      
      const csvRows = [headers.join(',')];
      
      results.forEach(r => {
        const row = [
          `"${r.name || ''}"`,
          `"${r.docNumber || ''}"`,
          `"${formatDate(r.date)}"`,
          `"${r.org || ''}"`,
          `"${r.party || ''}"`,
          `"${r.region || ''}"`,
          `"${r.caseType || ''}"`,
          `"${r.industry || ''}"`,
          `"${r.legalBasis || ''}"`,
          `"${formatAmount(r.amount)}"`,
          `"${r.violationFacts || ''}"`,
          `"${r.legalProvisions || ''}"`,
          `"${r.penaltyDecision || ''}"`,
          `"${r.detailedContent || ''}"`,
          `"${r.originalLink || ''}"`
        ];
        csvRows.push(row.join(','));
      });
      
      content = csvRows.join('\n');
      filename = `处罚案例搜索结果_${new Date().toISOString().split('T')[0]}.csv`;
      mimeType = 'text/csv;charset=utf-8;';
    } else {
      // JSON格式
      const jsonData = results.map(r => ({
        案例名称: r.name || '',
        处罚决定书文号: r.docNumber || '',
        处罚日期: formatDate(r.date),
        监管机构: r.org || '',
        当事人: r.party || '',
        地区: r.region || '',
        案件类型: r.caseType || '',
        行业: r.industry || '',
        处罚依据: r.legalBasis || '',
        罚款金额: formatAmount(r.amount),
        违法事实: r.violationFacts || '',
        法律依据: r.legalProvisions || '',
        处罚决定: r.penaltyDecision || '',
        详细内容: r.detailedContent || '',
        原文链接: r.originalLink || ''
      }));
      
      content = JSON.stringify(jsonData, null, 2);
      filename = `处罚案例搜索结果_${new Date().toISOString().split('T')[0]}.json`;
      mimeType = 'application/json;charset=utf-8;';
    }

    // 创建下载链接
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="main-container">
      <button className="theme-toggle" onClick={toggleTheme}>
        {theme === 'light' ? '🌙 暗色' : '☀️ 亮色'}
      </button>
      
      <h1 className="page-title">处罚案例搜索</h1>
      
      <form onSubmit={search} className="search-form">
        <div className="input-grid">
          <input 
            className="form-input"
            placeholder="关键词" 
            value={keyword} 
            onChange={e => setKeyword(e.target.value)} 
          />
          <input 
            className="form-input"
            placeholder="监管机构" 
            value={org} 
            onChange={e => setOrg(e.target.value)} 
          />

          <input 
            className="form-input"
            placeholder="当事人" 
            value={party} 
            onChange={e => setParty(e.target.value)} 
          />
          <input 
            className="form-input"
            placeholder="地区" 
            value={region} 
            onChange={e => setRegion(e.target.value)} 
          />
          <input 
            className="form-input"
            placeholder="案件类型" 
            value={caseType} 
            onChange={e => setCaseType(e.target.value)} 
          />
          <input 
            className="form-input"
            placeholder="行业" 
            value={industry} 
            onChange={e => setIndustry(e.target.value)} 
          />
          <input 
            className="form-input"
            placeholder="处罚依据" 
            value={legalBasis} 
            onChange={e => setLegalBasis(e.target.value)} 
          />
          <DatePicker
            value={dateFrom}
            onChange={setDateFrom}
            placeholder="开始日期"
          />
          <DatePicker
            value={dateTo}
            onChange={setDateTo}
            placeholder="结束日期"
          />
          <input 
            className="form-input"
            type="number"
            placeholder="最小罚款金额" 
            value={minAmount} 
            onChange={e => setMinAmount(e.target.value)} 
          />
        </div>
        <div>
          <button type="submit" disabled={loading} className="search-button">
            {loading ? "搜索中..." : "搜索"}
          </button>
        </div>
      </form>

      <div className="results-section">
        <div className="results-header">
          <div className="results-info">
            共找到 {total} 条记录 {total > 0 && `(第 ${page} 页，共 ${totalPages} 页)`}
          </div>
          {results.length > 0 && (
            <div className="download-buttons">
              <button 
                onClick={() => downloadResults('csv')} 
                className="download-btn csv-btn"
                title="下载为CSV格式"
              >
                📊 下载CSV
              </button>
              <button 
                onClick={() => downloadResults('json')} 
                className="download-btn json-btn"
                title="下载为JSON格式"
              >
                📄 下载JSON
              </button>
            </div>
          )}
        </div>
        <div className="table-container">
          <table className="results-table">
            <thead>
              <tr>
                <th className="table-header">案例名称</th>
                <th className="table-header">处罚日期</th>
                <th className="table-header">监管机构</th>
                <th className="table-header">当事人</th>
                <th className="table-header">地区</th>
                <th className="table-header">案件类型</th>
                <th className="table-header">行业</th>
                <th className="table-header">处罚依据</th>
                <th className="table-header">罚款金额</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={(r.id || r.docNumber || Math.random().toString(36))} className="table-row clickable-row" onClick={() => openCaseDetail(r)}>
                  <td className="table-cell">{r.name}</td>
                  <td className="table-cell">{formatDate(r.date)}</td>
                  <td className="table-cell">{r.org}</td>
                  <td className="table-cell">{r.party}</td>
                  <td className="table-cell">{r.region || "-"}</td>
                  <td className="table-cell">{r.caseType || "-"}</td>
                  <td className="table-cell">{r.industry || "-"}</td>
                  <td className="table-cell">{r.legalBasis || "-"}</td>
                  <td className="table-cell">{formatAmount(r.amount)}</td>
                </tr>
              ))}
              {results.length === 0 && !loading && (
                <tr>
                  <td colSpan={9} className="no-results">暂无数据</td>
                </tr>
              )}
              {loading && (
                <tr>
                  <td colSpan={9} className="no-results loading">搜索中...</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        
        {/* 分页控件 */}
        {totalPages > 1 && (
          <div className="pagination">
            <button 
              onClick={() => goToPage(page - 1)} 
              disabled={page === 1}
              className="pagination-btn"
            >
              上一页
            </button>
            
            <div className="pagination-info">
              <span>第 {page} 页 / 共 {totalPages} 页</span>
            </div>
            
            <div className="pagination-pages">
              {/* 显示页码按钮 */}
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (page <= 3) {
                  pageNum = i + 1;
                } else if (page >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = page - 2 + i;
                }
                
                return (
                  <button
                    key={pageNum}
                    onClick={() => goToPage(pageNum)}
                    className={`pagination-page ${page === pageNum ? 'active' : ''}`}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>
            
            <button 
              onClick={() => goToPage(page + 1)} 
              disabled={page === totalPages}
              className="pagination-btn"
            >
              下一页
            </button>
          </div>
        )}
      </div>

      {/* 案例详情模态框 */}
      {showModal && selectedCase && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">案例详情</h2>
              <button className="modal-close" onClick={closeModal}>
                ✕
              </button>
            </div>
            <div className="modal-body">
              <div className="detail-grid">
                <div className="detail-item">
                  <label className="detail-label">案例名称：</label>
                  <span className="detail-value">{selectedCase.name}</span>
                </div>
                <div className="detail-item">
                  <label className="detail-label">处罚决定书文号：</label>
                  <span className="detail-value">{selectedCase.docNumber}</span>
                </div>
                <div className="detail-item">
                  <label className="detail-label">处罚日期：</label>
                  <span className="detail-value">{formatDate(selectedCase.date)}</span>
                </div>
                <div className="detail-item">
                  <label className="detail-label">监管机构：</label>
                  <span className="detail-value">{selectedCase.org}</span>
                </div>
                <div className="detail-item">
                  <label className="detail-label">当事人：</label>
                  <span className="detail-value">{selectedCase.party}</span>
                </div>
                <div className="detail-item">
                  <label className="detail-label">地区：</label>
                  <span className="detail-value">{selectedCase.region || "-"}</span>
                </div>
                <div className="detail-item">
                  <label className="detail-label">案件类型：</label>
                  <span className="detail-value">{selectedCase.caseType || "-"}</span>
                </div>
                <div className="detail-item">
                  <label className="detail-label">行业：</label>
                  <span className="detail-value">{selectedCase.industry || "-"}</span>
                </div>
                <div className="detail-item">
                  <label className="detail-label">处罚依据：</label>
                  <span className="detail-value">{selectedCase.legalBasis || "-"}</span>
                </div>
                <div className="detail-item">
                  <label className="detail-label">罚款金额：</label>
                  <span className="detail-value">{formatAmount(selectedCase.amount)}万元</span>
                </div>

                <div className="detail-item">
                  <label className="detail-label">违法事实：</label>
                  <span className="detail-value">{selectedCase.violationFacts || "-"}</span>
                </div>
                <div className="detail-item">
                  <label className="detail-label">法律依据：</label>
                  <span className="detail-value">{selectedCase.legalProvisions || "-"}</span>
                </div>
                <div className="detail-item">
                  <label className="detail-label">处罚决定：</label>
                  <span className="detail-value">{selectedCase.penaltyDecision || "-"}</span>
                </div>
                <div className="detail-item">
                  <label className="detail-label">详细内容：</label>
                  <span className="detail-value">{selectedCase.detailedContent || "-"}</span>
                </div>
                <div className="detail-item">
                  <label className="detail-label">原文链接：</label>
                  <span className="detail-value">
                    {selectedCase.originalLink ? (
                      <a 
                        href={selectedCase.originalLink} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="detail-link"
                      >
                        查看原文
                      </a>
                    ) : "-"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

