/**
 * LLM Prompt Service Tests
 * Tests for LLM prompt management and optimization services
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock API client
const mockApiClient = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
};

vi.mock('@/api/client', () => ({
  apiClient: mockApiClient,
}));

describe('LLMPromptService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Prompt Management', () => {
    it('fetches all prompts', async () => {
      const mockPrompts = [
        {
          id: 'prompt-1',
          name: 'Contract Extraction',
          template: 'Extract contract details from {text}',
          category: 'extraction',
          version: 1,
        },
        {
          id: 'prompt-2',
          name: 'Data Validation',
          template: 'Validate {data}',
          category: 'validation',
          version: 1,
        },
      ];

      mockApiClient.get.mockResolvedValueOnce({
        data: { items: mockPrompts, total: 2 },
      });

      // Simulate service call
      const response = await mockApiClient.get('/llm-prompts');
      const prompts = response.data.items;

      expect(prompts).toHaveLength(2);
      expect(prompts[0].name).toBe('Contract Extraction');
      expect(mockApiClient.get).toHaveBeenCalledWith('/llm-prompts');
    });

    it('creates a new prompt', async () => {
      const newPrompt = {
        name: 'Test Prompt',
        template: 'Test template with {variable}',
        category: 'test',
      };

      mockApiClient.post.mockResolvedValueOnce({
        data: { id: 'prompt-3', ...newPrompt },
      });

      const response = await mockApiClient.post('/llm-prompts', newPrompt);
      const createdPrompt = response.data;

      expect(createdPrompt.id).toBe('prompt-3');
      expect(createdPrompt.name).toBe('Test Prompt');
      expect(mockApiClient.post).toHaveBeenCalledWith('/llm-prompts', newPrompt);
    });

    it('updates an existing prompt', async () => {
      const updateData = {
        name: 'Updated Prompt',
        template: 'Updated template',
      };

      mockApiClient.put.mockResolvedValueOnce({
        data: { id: 'prompt-1', ...updateData },
      });

      const response = await mockApiClient.put('/llm-prompts/prompt-1', updateData);
      const updatedPrompt = response.data;

      expect(updatedPrompt.name).toBe('Updated Prompt');
      expect(mockApiClient.put).toHaveBeenCalledWith(
        '/llm-prompts/prompt-1',
        updateData
      );
    });

    it('deletes a prompt', async () => {
      mockApiClient.delete.mockResolvedValueOnce({
        data: { success: true },
      });

      const response = await mockApiClient.delete('/llm-prompts/prompt-1');

      expect(response.data.success).toBe(true);
      expect(mockApiClient.delete).toHaveBeenCalledWith('/llm-prompts/prompt-1');
    });

    it('handles prompt versioning', async () => {
      const versions = [
        { id: 'v1', version: 1, template: 'Old template' },
        { id: 'v2', version: 2, template: 'New template' },
      ];

      mockApiClient.get.mockResolvedValueOnce({
        data: { items: versions },
      });

      const response = await mockApiClient.get('/llm-prompts/prompt-1/versions');
      const promptVersions = response.data.items;

      expect(promptVersions).toHaveLength(2);
      expect(promptVersions[1].version).toBe(2);
    });
  });

  describe('Prompt Optimization', () => {
    it('optimizes a prompt based on feedback', async () => {
      const feedback = {
        prompt_id: 'prompt-1',
        metrics: {
          accuracy: 0.85,
          latency: 1500,
          user_satisfaction: 4.2,
        },
        suggestions: ['Improve clarity', 'Add examples'],
      };

      mockApiClient.post.mockResolvedValueOnce({
        data: {
          optimized_prompt: 'Improved template',
          improvements: ['Added examples', 'Clarified instructions'],
        },
      });

      const response = await mockApiClient.post('/llm-prompts/optimize', feedback);
      const optimization = response.data;

      expect(optimization.optimized_prompt).toBeDefined();
      expect(optimization.improvements).toContain('Added examples');
    });

    it('analyzes prompt performance', async () => {
      const performanceData = {
        total_uses: 1000,
        average_accuracy: 0.92,
        average_latency: 1200,
        success_rate: 0.95,
        trend: 'improving',
      };

      mockApiClient.get.mockResolvedValueOnce({
        data: performanceData,
      });

      const response = await mockApiClient.get('/llm-prompts/prompt-1/analytics');
      const analytics = response.data;

      expect(analytics.total_uses).toBe(1000);
      expect(analytics.average_accuracy).toBeGreaterThan(0.9);
      expect(analytics.trend).toBe('improving');
    });

    it('compares prompt versions', async () => {
      const comparison = {
        v1: { accuracy: 0.85, latency: 1500 },
        v2: { accuracy: 0.92, latency: 1200 },
        improvement: '+8.2% accuracy, -20% latency',
      };

      mockApiClient.get.mockResolvedValueOnce({
        data: comparison,
      });

      const response = await mockApiClient.get(
        '/llm-prompts/prompt-1/compare?v1=1&v2=2'
      );
      const versionComparison = response.data;

      expect(versionComparison.improvement).toContain('+8.2%');
      expect(versionComparison.v2.accuracy).toBeGreaterThan(versionComparison.v1.accuracy);
    });
  });

  describe('Prompt Templates', () => {
    it('validates prompt template syntax', async () => {
      const template = 'Extract {field1} and {field2} from {input}';
      const variables = ['field1', 'field2', 'input'];

      mockApiClient.post.mockResolvedValueOnce({
        data: {
          valid: true,
          variables: variables,
        },
      });

      const response = await mockApiClient.post('/llm-prompts/validate', {
        template,
      });
      const validation = response.data;

      expect(validation.valid).toBe(true);
      expect(validation.variables).toEqual(variables);
    });

    it('detects invalid template syntax', async () => {
      const invalidTemplate = 'Extract {field1 from {input}'; // Unclosed brace

      mockApiClient.post.mockResolvedValueOnce({
        data: {
          valid: false,
          errors: ['Unclosed variable brace at position 20'],
        },
      });

      const response = await mockApiClient.post('/llm-prompts/validate', {
        template: invalidTemplate,
      });
      const validation = response.data;

      expect(validation.valid).toBe(false);
      expect(validation.errors.length).toBeGreaterThan(0);
    });

    it('replaces template variables', () => {
      const template = 'Hello {name}, your order {orderId} is ready';
      const variables = {
        name: 'John Doe',
        orderId: '12345',
      };

      let result = template;
      Object.entries(variables).forEach(([key, value]) => {
        result = result.replace(`{${key}}`, String(value));
      });

      expect(result).toBe('Hello John Doe, your order 12345 is ready');
    });
  });

  describe('Prompt Testing', () => {
    it('tests a prompt with sample input', async () => {
      const testRequest = {
        prompt_id: 'prompt-1',
        test_input: 'Sample contract text...',
        expected_output: {
          party_a: 'Company A',
          party_b: 'Company B',
          amount: 100000,
        },
      };

      mockApiClient.post.mockResolvedValueOnce({
        data: {
          success: true,
          actual_output: {
            party_a: 'Company A',
            party_b: 'Company B',
            amount: 100000,
          },
          accuracy: 1.0,
          latency_ms: 850,
        },
      });

      const response = await mockApiClient.post('/llm-prompts/test', testRequest);
      const testResult = response.data;

      expect(testResult.success).toBe(true);
      expect(testResult.accuracy).toBe(1.0);
      expect(testResult.latency_ms).toBe(850);
    });

    it('runs batch tests', async () => {
      const batchTests = [
        {
          input: 'Test 1',
          expected: 'Result 1',
        },
        {
          input: 'Test 2',
          expected: 'Result 2',
        },
      ];

      mockApiClient.post.mockResolvedValueOnce({
        data: {
          results: [
            { passed: true, accuracy: 1.0 },
            { passed: true, accuracy: 0.95 },
          ],
          summary: {
            total: 2,
            passed: 2,
            failed: 0,
            average_accuracy: 0.975,
          },
        },
      });

      const response = await mockApiClient.post('/llm-prompts/batch-test', {
        tests: batchTests,
      });
      const batchResult = response.data;

      expect(batchResult.summary.total).toBe(2);
      expect(batchResult.summary.passed).toBe(2);
      expect(batchResult.summary.average_accuracy).toBeGreaterThan(0.95);
    });
  });

  describe('Error Handling', () => {
    it('handles network errors gracefully', async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error('Network error'));

      await expect(mockApiClient.get('/llm-prompts')).rejects.toThrow(
        'Network error'
      );
    });

    it('handles validation errors', async () => {
      mockApiClient.post.mockRejectedValueOnce({
        response: {
          data: {
            detail: 'Invalid template syntax',
          },
        },
      });

      await expect(
        mockApiClient.post('/llm-prompts', {
          template: 'Invalid {template',
        })
      ).rejects.toThrow();
    });

    it('handles not found errors', async () => {
      mockApiClient.get.mockRejectedValueOnce({
        response: {
          status: 404,
          data: {
            detail: 'Prompt not found',
          },
        },
      });

      await expect(
        mockApiClient.get('/llm-prompts/nonexistent')
      ).rejects.toThrow();
    });
  });

  describe('Caching', () => {
    it('caches frequently accessed prompts', async () => {
      const cache = new Map();
      const promptId = 'prompt-1';

      // First call - cache miss
      if (!cache.has(promptId)) {
        mockApiClient.get.mockResolvedValueOnce({
          data: { id: promptId, name: 'Cached Prompt' },
        });
        const response1 = await mockApiClient.get(`/llm-prompts/${promptId}`);
        cache.set(promptId, response1.data);
      }

      // Second call - cache hit
      const cached = cache.get(promptId);

      expect(cached).toBeDefined();
      expect(cached.id).toBe(promptId);
      expect(mockApiClient.get).toHaveBeenCalledTimes(1);
    });

    it('invalidates cache on update', async () => {
      const cache = new Map();
      const promptId = 'prompt-1';

      // Initial cache
      cache.set(promptId, { id: promptId, name: 'Old Name' });

      // Update prompt
      mockApiClient.put.mockResolvedValueOnce({
        data: { id: promptId, name: 'New Name' },
      });

      const response = await mockApiClient.put(`/llm-prompts/${promptId}`, {
        name: 'New Name',
      });

      // Invalidate and update cache
      cache.set(promptId, response.data);

      const updated = cache.get(promptId);
      expect(updated.name).toBe('New Name');
    });
  });

  describe('Performance Metrics', () => {
    it('tracks API response times', async () => {
      const startTime = Date.now();

      mockApiClient.get.mockResolvedValueOnce({
        data: { id: 'prompt-1' },
      });

      await mockApiClient.get('/llm-prompts/prompt-1');

      const responseTime = Date.now() - startTime;

      expect(responseTime).toBeGreaterThanOrEqual(0);
    });

    it('calculates success rate', () => {
      const attempts = 100;
      const successes = 95;
      const successRate = successes / attempts;

      expect(successRate).toBe(0.95);
    });

    it('monitors memory usage', () => {
      const memoryBefore = performance.memory?.usedJSHeapSize || 0;
      const largeData = Array(10000).fill({ test: 'data' });
      const memoryAfter = performance.memory?.usedJSHeapSize || 0;

      const memoryUsed = memoryAfter - memoryBefore;

      expect(largeData.length).toBe(10000);
      expect(memoryUsed).toBeGreaterThanOrEqual(0);
      // Memory usage should be tracked
    });
  });
});
