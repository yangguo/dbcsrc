import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
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

// Response interceptor
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

export interface CaseSummary {
  total: number;
  byOrg: Record<string, number>;
  byMonth: Record<string, number>;
}

export interface CaseDetail {
  id: string;
  title: string;
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
  // Get case summary
  getSummary: async (): Promise<CaseSummary> => {
    const response = await apiClient.get('/summary');
    return response.data;
  },

  // Search cases
  searchCases: async (params: SearchParams): Promise<{ data: CaseDetail[]; total: number }> => {
    const response = await apiClient.get('/search', { params });
    return response.data;
  },

  // Update cases
  updateCases: async (params: UpdateParams): Promise<{ success: boolean; count: number }> => {
    const response = await apiClient.post('/update', params);
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
    const response = await apiClient.post('/classify', params);
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
};

export default apiClient;