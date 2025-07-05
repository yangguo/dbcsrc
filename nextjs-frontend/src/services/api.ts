import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // Increased to 300 seconds (5 minutes) for data-heavy operations
  headers: {
    'Content-Type': 'application/json',
  },
});

// Create a separate client for upload data with longer timeout
const uploadDataClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 180000, // 3 minutes for upload data operations
  headers: {
    'Content-Type': 'application/json',
  },
});

// Create a separate client for download operations with longer timeout
const downloadClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes for download operations
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for apiClient
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for apiClient
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Request interceptor for downloadClient
downloadClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for downloadClient
downloadClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export interface CaseSummary {
  total: number;
  byOrg: Record<string, number>;
  byMonth: Record<string, number>;
}

export interface OrgChartData {
  organizations: Record<string, number>;
  total_cases: number;
}

export interface OrgSummaryItem {
  orgName: string;
  caseCount: number;
  percentage: number;
  minDate: string;
  maxDate: string;
  dateRange: string;
}

export interface CaseDetail {
  id: string;
  title: string;
  name: string;
  docNumber: string;
  date: string;
  org: string;
  content: string;
  penalty: string;
  amount?: number;
}

export interface SearchParams {
  keyword?: string;
  org?: string;
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  pageSize?: number;
}

export interface UpdateParams {
  orgName: string;
  startPage: number;
  endPage: number;
}

export interface AttachmentAnalysis {
  contentLength: number;
  downloadFilter: string;
}

// API functions
export const caseApi = {
  // Get case summary with retry mechanism
  getSummary: async (retries: number = 2): Promise<CaseSummary> => {
    let lastError: any;
    
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        console.log(`Fetching summary data (attempt ${attempt + 1}/${retries + 1})`);
        const response = await apiClient.get('/api/summary');
        return response.data.data;
      } catch (error: any) {
        lastError = error;
        console.warn(`Summary fetch attempt ${attempt + 1} failed:`, error.message);
        
        // Don't retry on client errors (4xx) or if it's the last attempt
        if (error.response?.status >= 400 && error.response?.status < 500) {
          break;
        }
        
        if (attempt < retries) {
          // Wait before retrying (exponential backoff)
          const delay = Math.min(1000 * Math.pow(2, attempt), 5000);
          console.log(`Retrying in ${delay}ms...`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }
    
    throw lastError;
  },

  // Get organization summary with date ranges
  getOrgSummary: async (retries: number = 2): Promise<OrgSummaryItem[]> => {
    let lastError: any;
    
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        console.log(`Fetching organization summary data (attempt ${attempt + 1}/${retries + 1})`);
        const response = await apiClient.get('/api/org-summary');
        return response.data.data;
      } catch (error: any) {
        lastError = error;
        console.warn(`Organization summary fetch attempt ${attempt + 1} failed:`, error.message);
        
        // Don't retry on client errors (4xx) or if it's the last attempt
        if (error.response?.status >= 400 && error.response?.status < 500) {
          break;
        }
        
        if (attempt < retries) {
          // Wait before retrying (exponential backoff)
          const delay = Math.min(1000 * Math.pow(2, attempt), 5000);
          console.log(`Retrying in ${delay}ms...`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }
    
    throw lastError;
  },

  // Get organization chart data with consistent filtering
  getOrgChartData: async (retries: number = 2): Promise<CaseSummary> => {
    let lastError: any;
    
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        console.log(`Fetching organization chart data (attempt ${attempt + 1}/${retries + 1})`);
        const response = await apiClient.get('/api/org-chart-data');
        
        // Transform the response to match CaseSummary interface
        const orgChartData: OrgChartData = response.data.data;
        const caseSummary: CaseSummary = {
          total: orgChartData.total_cases,
          byOrg: orgChartData.organizations,
          byMonth: {} // Empty for chart data endpoint
        };
        
        return caseSummary;
      } catch (error: any) {
        lastError = error;
        console.warn(`Organization chart data fetch attempt ${attempt + 1} failed:`, error.message);
        
        // Don't retry on client errors (4xx) or if it's the last attempt
        if (error.response?.status >= 400 && error.response?.status < 500) {
          break;
        }
        
        if (attempt < retries) {
          // Wait before retrying (exponential backoff)
          const delay = Math.min(1000 * Math.pow(2, attempt), 5000);
          console.log(`Retrying in ${delay}ms...`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }
    
    throw lastError;
  },

  // Search cases
  searchCases: async (params: SearchParams): Promise<{ data: CaseDetail[]; total: number }> => {
    const response = await apiClient.get('/api/search', { params });
    return response.data;
  },

  // Update cases
  updateCases: async (params: UpdateParams): Promise<{ success: boolean; count: number }> => {
    const response = await apiClient.post('/update', params);
    return response.data;
  },

  // 案例上线相关API
  getUploadData: async (): Promise<any> => {
    const response = await apiClient.get('/api/upload-data');
    return response.data;
  },

  uploadCases: async (caseIds: string[]): Promise<{ message: string }> => {
    const response = await apiClient.post('/api/upload-cases', { case_ids: caseIds });
    return response.data;
  },

  deleteOnlineData: async (): Promise<{ message: string }> => {
    const response = await apiClient.delete('/api/online-data');
    return response.data;
  },

  downloadOnlineData: async (): Promise<Blob> => {
    const response = await apiClient.get('/api/download/online-data', { responseType: 'blob' });
    return response.data;
  },

  downloadDiffData: async (): Promise<Blob> => {
    const response = await apiClient.get('/api/download/diff-data', { responseType: 'blob' });
    return response.data;
  },

  // Analyze attachments
  analyzeAttachments: async (params: AttachmentAnalysis): Promise<any> => {
    const response = await apiClient.post('/analyze-attachments', params);
    return response.data;
  },

  // Download attachments
  downloadAttachments: async (positions: number[]): Promise<any> => {
    const response = await apiClient.post('/download-attachments', { positions });
    return response.data;
  },

  // Convert documents
  convertDocuments: async (files: File[]): Promise<any> => {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    
    const response = await apiClient.post('/convert-documents', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Classify cases
  classifyCases: async (params: {
    article: string;
    candidateLabels: string[];
    multiLabel: boolean;
  }): Promise<any> => {
    const requestParams = {
      article: params.article,
      candidate_labels: params.candidateLabels,
      multi_label: params.multiLabel
    };
    const response = await apiClient.post('/classify', requestParams);
    return response.data;
  },

  // Batch classify
  batchClassify: async (file: File, params: any): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    Object.keys(params).forEach(key => {
      formData.append(key, params[key]);
    });
    
    const response = await apiClient.post('/batch-classify', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Analyze penalty amounts
  analyzePenaltyAmounts: async (file: File, params: {
    idCol: string;
    contentCol: string;
  }): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('idcol', params.idCol);
    formData.append('contentcol', params.contentCol);
    
    const response = await apiClient.post('/amount-analysis', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Analyze locations
  analyzeLocations: async (file: File, params: {
    idCol: string;
    contentCol: string;
  }): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('idcol', params.idCol);
    formData.append('contentcol', params.contentCol);
    
    const response = await apiClient.post('/location-analysis', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Analyze people
  analyzePeople: async (file: File, params: {
    idCol: string;
    contentCol: string;
  }): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('idcol', params.idCol);
    formData.append('contentcol', params.contentCol);
    
    const response = await apiClient.post('/people-analysis', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Analyze single penalty case
  analyzePenalty: async (text: string): Promise<any> => {
    const response = await apiClient.post('/penalty-analysis', { text });
    return response.data;
  },

  // Batch analyze penalty cases
  batchAnalyzePenalty: async (file: File, params: {
    idCol: string;
    contentCol: string;
  }): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('idcol', params.idCol);
    formData.append('contentcol', params.contentCol);
    
    const response = await apiClient.post('/batch-penalty-analysis', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Download data functions
  getDownloadData: async (): Promise<{
    caseDetail: { data: any[]; count: number; uniqueCount: number };
    analysisData: { data: any[]; count: number; uniqueCount: number };
    categoryData: { data: any[]; count: number; uniqueCount: number };
    splitData: { data: any[]; count: number; uniqueCount: number };
  }> => {
    const response = await apiClient.get('/api/download-data');
    return response.data.data;
  },

  // Download CSV files
  downloadCaseDetail: async (): Promise<Blob> => {
    const response = await apiClient.get('/api/download/case-detail', {
      responseType: 'blob',
    });
    return response.data;
  },

  downloadAnalysisData: async (): Promise<Blob> => {
    const response = await apiClient.get('/api/download/analysis-data', {
      responseType: 'blob',
    });
    return response.data;
  },

  downloadCategoryData: async (): Promise<Blob> => {
    const response = await apiClient.get('/api/download/category-data', {
      responseType: 'blob',
    });
    return response.data;
  },

  downloadSplitData: async (): Promise<Blob> => {
    const response = await apiClient.get('/api/download/split-data', {
      responseType: 'blob',
    });
    return response.data;
  },

  // Generate labels for case classification
  generateLabels: async (): Promise<any> => {
    const response = await apiClient.post('/generate-labels');
    return response.data;
  },
};

export default apiClient;