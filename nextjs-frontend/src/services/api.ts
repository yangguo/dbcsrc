import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
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
    } else if (error.code === 'NETWORK_ERROR' || error.message === 'Network Error') {
      // Handle network errors (backend not available)
      const enhancedError = new Error(
        'Backend server is not available. Please ensure the backend server is running on port 8000.'
      );
      enhancedError.name = 'BackendUnavailableError';
      return Promise.reject(enhancedError);
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
    } else if (error.code === 'NETWORK_ERROR' || error.message === 'Network Error') {
      // Handle network errors (backend not available)
      const enhancedError = new Error(
        'Backend server is not available. Please ensure the backend server is running on port 8000.'
      );
      enhancedError.name = 'BackendUnavailableError';
      return Promise.reject(enhancedError);
    }
    return Promise.reject(error);
  }
);

// Request interceptor for uploadDataClient
uploadDataClient.interceptors.request.use(
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

// Response interceptor for uploadDataClient
uploadDataClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('token');
      window.location.href = '/login';
    } else if (error.code === 'NETWORK_ERROR' || error.message === 'Network Error') {
      // Handle network errors (backend not available)
      const enhancedError = new Error(
        'Backend server is not available. Please ensure the backend server is running on port 8000.'
      );
      enhancedError.name = 'BackendUnavailableError';
      return Promise.reject(enhancedError);
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

// Enhanced case detail interface for new search functionality
export interface EnhancedCaseDetail {
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
}

export interface SearchParams {
  keyword?: string;
  org?: string;
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  pageSize?: number;
}

// Enhanced search parameters interface
export interface EnhancedSearchParams {
  keyword?: string;        // 案件关键词
  docNumber?: string;      // 文号
  party?: string;          // 当事人
  org?: string;           // 发文地区
  minAmount?: number;     // 最低罚款金额
  legalBasis?: string;    // 处罚依据
  startDate?: string;     // 开始日期
  endDate?: string;       // 结束日期
  page?: number;
  pageSize?: number;
}

// Search statistics interface
export interface SearchStats {
  totalCases: number;
  totalAmount: number;
  avgAmount: number;
  orgDistribution: Record<string, number>;
  monthlyDistribution: Record<string, number>;
}

export interface UpdateParams {
  orgName: string;
  startPage: number;
  endPage: number;
  selectedIds?: string[];
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

  // Get organization to ID mapping
  getOrg2idMapping: async (): Promise<any> => {
    const response = await apiClient.get('/api/org2id');
    return response.data;
  },

  // Search cases
  searchCases: async (params: SearchParams): Promise<{ data: CaseDetail[]; total: number }> => {
    const response = await apiClient.get('/api/search', { params });
    return response.data;
  },

  // Enhanced search cases with more parameters
  searchCasesEnhanced: async (params: EnhancedSearchParams): Promise<{ data: EnhancedCaseDetail[]; total: number; stats?: SearchStats }> => {
    const response = await apiClient.get('/api/search-enhanced', { params });
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

  // Batch analyze penalty cases (async job)
  batchAnalyzePenalty: async (file: File, params: {
    idCol: string;
    contentCol: string;
    maxWorkers?: number;
  }): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    
    // Send idcol, contentcol, and max_workers as query parameters
    const queryParams = new URLSearchParams({
      idcol: params.idCol,
      contentcol: params.contentCol
    });
    
    // Add max_workers parameter if provided
    if (params.maxWorkers !== undefined && params.maxWorkers !== null) {
      queryParams.append('max_workers', params.maxWorkers.toString());
    }
    
    // Start the job with parallel processing support
    const response = await apiClient.post(`/batch-penalty-analysis?${queryParams}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Get batch penalty analysis job status
  getBatchPenaltyAnalysisStatus: async (jobId: string): Promise<any> => {
    // Use a reasonable timeout for status checks - increased for thinking models
    const response = await apiClient.get(`/batch-penalty-analysis/${jobId}/status`, {
      timeout: 60000 // 60 seconds - longer timeout for thinking models
    });
    return response.data;
  },

  // Get batch penalty analysis job result
  getBatchPenaltyAnalysisResult: async (jobId: string): Promise<any> => {
    const response = await apiClient.get(`/batch-penalty-analysis/${jobId}/result`);
    return response.data;
  },

  // List all batch penalty analysis jobs
  listBatchPenaltyAnalysisJobs: async (): Promise<any> => {
    const response = await apiClient.get('/batch-penalty-analysis/jobs');
    return response.data;
  },

  // Delete batch penalty analysis job
  deleteBatchPenaltyAnalysisJob: async (jobId: string): Promise<any> => {
    const response = await apiClient.delete(`/batch-penalty-analysis/${jobId}`);
    return response.data;
  },

  // Poll for job completion with progress updates - Async approach without timeout worries
  // This function handles long-running batch penalty analysis jobs with a fire-and-forget approach
  // It uses adaptive polling intervals and graceful error handling for maximum reliability
  pollBatchPenaltyAnalysisJob: async (
    jobId: string, 
    onProgress?: (progress: any) => void,
    onComplete?: (result: any) => void,
    onError?: (error: Error) => void,
    options?: {
      initialPollInterval?: number; // Initial poll interval in milliseconds
      maxPollInterval?: number; // Maximum poll interval in milliseconds
      maxConsecutiveFailures?: number; // Max consecutive failures before giving up
    }
  ): Promise<void> => {
    const initialPollInterval = options?.initialPollInterval || 2000; // Start with 2 seconds
    const maxPollInterval = options?.maxPollInterval || 30000; // Max 30 seconds between polls
    const maxConsecutiveFailures = options?.maxConsecutiveFailures || 10; // Allow more failures
    
    let currentPollInterval = initialPollInterval;
    let consecutiveFailures = 0;
    let isPolling = true;
    
    const poll = async (): Promise<void> => {
      if (!isPolling) return;
      
      try {
        const statusResponse = await caseApi.getBatchPenaltyAnalysisStatus(jobId);
        
        // Reset on successful status check
        consecutiveFailures = 0;
        currentPollInterval = initialPollInterval; // Reset to fast polling on success
        
        // Handle different response formats more robustly
        if (!statusResponse) {
          const error = new Error('No response received from status check');
          if (onError) onError(error);
          return;
        }

        // Check if response has success property and it's false
        if (statusResponse.hasOwnProperty('success') && !statusResponse.success) {
          const error = new Error(statusResponse.message || 'Failed to get job status');
          if (onError) onError(error);
          return;
        }

        // Extract job data - handle both wrapped and direct response formats
        const jobData = statusResponse.data || statusResponse;
        
        if (!jobData || !jobData.status) {
          const error = new Error('Invalid response format: missing job status');
          if (onError) onError(error);
          return;
        }
        
        // Call progress callback if provided
        if (onProgress) {
          onProgress(jobData);
        }

        if (jobData.status === 'completed') {
          isPolling = false;
          try {
            const resultResponse = await caseApi.getBatchPenaltyAnalysisResult(jobId);
            if (onComplete) onComplete(resultResponse);
          } catch (error) {
            if (onError) onError(error as Error);
          }
        } else if (jobData.status === 'failed') {
          isPolling = false;
          const error = new Error(jobData.error || 'Job failed');
          if (onError) onError(error);
        } else {
          // Job still running, schedule next poll
          setTimeout(poll, currentPollInterval);
        }
      } catch (error: any) {
        consecutiveFailures++;
        
        console.warn(`Status check failed (attempt ${consecutiveFailures}/${maxConsecutiveFailures}):`, error.message);
        
        // Handle various error types gracefully
        const isTimeoutError = error.code === 'ECONNABORTED' || error.message.includes('timeout');
        const isNetworkError = error.code === 'NETWORK_ERROR' || error.message === 'Network Error';
        const isServerError = error.response?.status >= 500;
        
        if ((isTimeoutError || isNetworkError || isServerError) && consecutiveFailures <= maxConsecutiveFailures) {
          // Increase poll interval on failures to reduce server load
          currentPollInterval = Math.min(currentPollInterval * 1.5, maxPollInterval);
          console.warn(`Retrying status check in ${Math.round(currentPollInterval / 1000)}s... (backoff applied)`);
          setTimeout(poll, currentPollInterval);
        } else if (consecutiveFailures > maxConsecutiveFailures) {
          isPolling = false;
          const finalError = new Error(
            `Status check failed after ${maxConsecutiveFailures} consecutive attempts. ` +
            `The job may still be running on the server. Please check manually or try again later. ` +
            `Last error: ${error.message}`
          );
          if (onError) onError(finalError);
        } else {
          // For other types of errors (like 4xx), fail immediately
          isPolling = false;
          if (onError) onError(error);
        }
      }
    };
    
    // Start polling immediately
    poll();
  },

  // Simplified polling method that returns a Promise (for backward compatibility)
  pollBatchPenaltyAnalysisJobSync: async (
    jobId: string, 
    onProgress?: (progress: any) => void,
    maxWaitTime: number = 3600000, // 1 hour default
    options?: {
      pollInterval?: number; // Poll interval in milliseconds
      maxRetries?: number; // Max retries for failed status checks
    }
  ): Promise<any> => {
    const startTime = Date.now();
    const pollInterval = options?.pollInterval || 10000; // Poll every 10 seconds (increased from 5)
    const maxRetries = options?.maxRetries || 30; // More retries for long jobs (increased from 20)
    let consecutiveFailures = 0;
    
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          // Check if we've exceeded max wait time
          if (Date.now() - startTime > maxWaitTime) {
            reject(new Error('Job polling timeout exceeded. The job may still be running on the server.'));
            return;
          }

          const statusResponse = await caseApi.getBatchPenaltyAnalysisStatus(jobId);
          
          // Reset consecutive failures on successful status check
          consecutiveFailures = 0;
          
          // Handle different response formats more robustly
          if (!statusResponse) {
            reject(new Error('No response received from status check'));
            return;
          }

          // Check if response has success property and it's false
          if (statusResponse.hasOwnProperty('success') && !statusResponse.success) {
            reject(new Error(statusResponse.message || 'Failed to get job status'));
            return;
          }

          // Extract job data - handle both wrapped and direct response formats
          const jobData = statusResponse.data || statusResponse;
          
          if (!jobData || !jobData.status) {
            reject(new Error('Invalid response format: missing job status'));
            return;
          }
          
          // Call progress callback if provided
          if (onProgress) {
            onProgress(jobData);
          }

          if (jobData.status === 'completed') {
            // Job completed, get the result
            try {
              const resultResponse = await caseApi.getBatchPenaltyAnalysisResult(jobId);
              resolve(resultResponse);
            } catch (error) {
              reject(error);
            }
          } else if (jobData.status === 'failed') {
            reject(new Error(jobData.error || 'Job failed'));
          } else {
            // Job still running, continue polling
            setTimeout(poll, pollInterval);
          }
        } catch (error: any) {
          consecutiveFailures++;
          
          console.warn(`Status check failed (attempt ${consecutiveFailures}/${maxRetries}):`, error.message);
          
          // Handle timeout errors and network issues more gracefully
          const isTimeoutError = error.code === 'ECONNABORTED' || error.message.includes('timeout');
          const isNetworkError = error.code === 'NETWORK_ERROR' || error.message === 'Network Error';
          
          if ((isTimeoutError || isNetworkError) && consecutiveFailures <= maxRetries) {
            console.warn(`Retrying status check in ${pollInterval}ms...`);
            // Continue polling after a timeout/network error
            setTimeout(poll, pollInterval);
          } else if (consecutiveFailures > maxRetries) {
            reject(new Error(
              `Status check failed after ${maxRetries} consecutive attempts. ` +
              `The job may still be running on the server. Please check manually. ` +
              `Last error: ${error.message}`
            ));
          } else {
            // For other types of errors, fail immediately
            reject(error);
          }
        }
      };
      
      // Start polling
      poll();
    });
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
    const response = await apiClient.get('/download/case-detail', {
      responseType: 'blob',
    });
    return response.data;
  },

  downloadAnalysisData: async (): Promise<Blob> => {
    const response = await apiClient.get('/download/analysis-data', {
      responseType: 'blob',
    });
    return response.data;
  },

  downloadCategoryData: async (): Promise<Blob> => {
    const response = await apiClient.get('/download/category-data', {
      responseType: 'blob',
    });
    return response.data;
  },

  downloadSplitData: async (): Promise<Blob> => {
    const response = await apiClient.get('/download/split-data', {
      responseType: 'blob',
    });
    return response.data;
  },

  // Generate labels for case classification
  generateLabels: async (): Promise<any> => {
    const response = await apiClient.post('/generate-labels');
    return response.data;
  },

  // Save penalty analysis results
  savePenaltyAnalysisResults: async (penaltyResults: any[]): Promise<any> => {
    const response = await apiClient.post('/api/save-penalty-analysis-results', {
      penaltyResults
    });
    return response.data;
  },

  // Upload and save analysis results file
  uploadAnalysisResultsFile: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post('/api/upload-analysis-results', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Download search results
  downloadSearchResults: async (params: EnhancedSearchParams): Promise<Blob> => {
    const response = await downloadClient.get('/api/download/search-results', {
      params,
      responseType: 'blob'
    });
    return response.data;
  },

  // Extract text from attachments
  extractText: async (attachmentIds: string[]): Promise<any> => {
    const response = await apiClient.post('/extract-text', {
      attachment_ids: attachmentIds
    });
    return response.data;
  },

  // Check if file exists
  checkFileExists: async (filePath: string): Promise<any> => {
    const response = await apiClient.post('/check-file-exists', {
      file_path: filePath
    });
    return response.data;
  },

  // Delete attachments
  deleteAttachments: async (attachmentIds: string[]): Promise<any> => {
    const response = await apiClient.post('/delete-attachments', {
      attachment_ids: attachmentIds
    });
    return response.data;
  },

  // Update attachment text
  updateAttachmentText: async (attachmentIds: string[]): Promise<any> => {
    const response = await apiClient.post('/update-attachment-text', {
      attachment_ids: attachmentIds
    });
    return response.data;
  },

  // Get downloaded file status from csrcmiscontent files
  getDownloadedFileStatus: async (): Promise<{
    data: Array<{
      url: string;
      filename: string;
      text: string;
    }>;
    count: number;
  }> => {
    const response = await apiClient.get('/api/downloaded-file-status');
    return response.data;
  },

  // Get updated csrclenanalysis data after text extraction
  getCsrclenanalysisData: async (): Promise<any> => {
    const response = await apiClient.get('/api/csrclenanalysis-data');
    return response.data;
  },
};

export default apiClient;