"use client";

import { useState } from "react";

type Result = {
  id: string;
  name: string;
  docNumber: string;
  date: string;
  org: string;
  party: string;
  amount: number;
  category?: string;
};

export default function Page() {
  const [keyword, setKeyword] = useState("");
  const [org, setOrg] = useState("");
  const [docNumber, setDocNumber] = useState("");
  const [party, setParty] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [minAmount, setMinAmount] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Result[]>([]);
  const [total, setTotal] = useState(0);

  const search = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (keyword) params.set("keyword", keyword);
      if (org) params.set("org", org);
      if (docNumber) params.set("docNumber", docNumber);
      if (party) params.set("party", party);
      if (dateFrom) params.set("dateFrom", dateFrom);
      if (dateTo) params.set("dateTo", dateTo);
      if (minAmount) params.set("minAmount", minAmount);
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

  return (
    <main style={{ padding: 24 }}>
      <h1 style={{ marginBottom: 16 }}>Penalty Case Search</h1>
      <form onSubmit={search} style={{ display: "grid", gap: 12, maxWidth: 960 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          <input placeholder="Keyword" value={keyword} onChange={e => setKeyword(e.target.value)} />
          <input placeholder="Org (机构)" value={org} onChange={e => setOrg(e.target.value)} />
          <input placeholder="Doc Number (文号)" value={docNumber} onChange={e => setDocNumber(e.target.value)} />
          <input placeholder="Party (当事人)" value={party} onChange={e => setParty(e.target.value)} />
          <input placeholder="Date From (YYYY-MM-DD)" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
          <input placeholder="Date To (YYYY-MM-DD)" value={dateTo} onChange={e => setDateTo(e.target.value)} />
          <input placeholder="Min Amount (罚款金额)" value={minAmount} onChange={e => setMinAmount(e.target.value)} />
        </div>
        <div>
          <button type="submit" disabled={loading}>
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
      </form>

      <div style={{ marginTop: 24 }}>
        <div style={{ marginBottom: 8 }}>Total: {total}</div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>Name</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>Doc No.</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>Date</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>Org</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>Party</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>Amount</th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>Category</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={(r.id || r.docNumber || Math.random().toString(36))}>
                  <td style={{ borderBottom: "1px solid #f0f0f0", padding: 8 }}>{r.name}</td>
                  <td style={{ borderBottom: "1px solid #f0f0f0", padding: 8 }}>{r.docNumber}</td>
                  <td style={{ borderBottom: "1px solid #f0f0f0", padding: 8 }}>{r.date}</td>
                  <td style={{ borderBottom: "1px solid #f0f0f0", padding: 8 }}>{r.org}</td>
                  <td style={{ borderBottom: "1px solid #f0f0f0", padding: 8 }}>{r.party}</td>
                  <td style={{ borderBottom: "1px solid #f0f0f0", padding: 8 }}>{r.amount?.toLocaleString?.() ?? r.amount}</td>
                  <td style={{ borderBottom: "1px solid #f0f0f0", padding: 8 }}>{r.category || "-"}</td>
                </tr>
              ))}
              {results.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ padding: 12, color: "#888" }}>No results</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}

