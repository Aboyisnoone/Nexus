// @ts-nocheck
/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, beforeEach } from 'vitest';
﻿
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';
import { NexusApi } from './api/client';
import { vi } from 'vitest';

vi.mock('./api/client', () => ({
  NexusApi: {
    runLive: vi.fn(),
    runReplay: vi.fn(),
    getTrace: vi.fn(),
    getMemory: vi.fn()
  },
  ApiError: class ApiError extends Error {
    code: string;
    status: number;
    constructor(code: string, message: string, status: number) {
      super(message);
      this.code = code;
      this.status = status;
    }
  }
}));

describe('App', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders application with scenario selector', () => {
    render(<App />);
    expect(screen.getByText('NEXUS v0.1')).toBeInTheDocument();
    expect(screen.getByText('Core 01: Simple Acceptance')).toBeInTheDocument();
  });

  it('handles live run and displays evaluation', async () => {
    vi.mocked(NexusApi.runLive).mockResolvedValueOnce({
      run_id: 'run-123',
      scenario_id: 'core_01',
      mode: 'LIVE',
      agent_version: 'v0.1',
      status: 'COMPLETED',
      evaluation: {
        status: 'PASS',
        total: 1,
        passed: 1,
        failed: 0,
        assertions: [{
          assertion: { type: 'test' },
          passed: true,
          actual: 'val',
          error: null
        }]
      },
      error: null
    });
    
    vi.mocked(NexusApi.getTrace).mockResolvedValueOnce({
      trace: {
        trace_id: 't-123',
        scenario_id: 'core_01',
        agent_version: 'v0.1',
        steps: [
          { step_index: 1, step_type: 'STATE_BEFORE', simulated_time: '2024', recorded_at: null }
        ]
      }
    });
    
    vi.mocked(NexusApi.getMemory).mockResolvedValueOnce({
      memories: []
    });

    render(<App />);
    
    fireEvent.click(screen.getByText('RUN LIVE'));
    
    await waitFor(() => {
      expect(screen.getByText('run-123')).toBeInTheDocument();
      expect(screen.getByText('STATE BEFORE')).toBeInTheDocument();
      expect(screen.getByText('PASS')).toBeInTheDocument();
      expect(screen.getByText('1 / 1 PASSED')).toBeInTheDocument();
    });
  });

  it('displays API error safely', async () => {
    vi.mocked(NexusApi.runLive).mockRejectedValueOnce(
        new (await import('./api/client')).ApiError('ERR_SYSTEM', 'Internal test error', 500)
    );

    render(<App />);
    
    fireEvent.click(screen.getByText('RUN LIVE'));
    
    await waitFor(() => {
      expect(screen.getByText(/Internal test error/)).toBeInTheDocument();
    });
  });
});
