import { describe, it, expect } from 'vitest';
import { ApiError } from './http';

describe('ApiError contract and message formatting', () => {
  it('strips single quotes from backend 404 strings', () => {
    const err = new ApiError(404, '/cases/abc', 'GET', "'No case abc'");
    expect(err.displayMessage()).toBe('No case abc');
  });

  it('formats Pydantic 422 validation error arrays cleanly', () => {
    const pydanticDetail = [
      { loc: ['body', 'reliability_tier'], msg: 'Input should be a valid integer', type: 'int_type' },
      { loc: ['body', 'value_type'], msg: 'Field required', type: 'missing' },
    ];
    const err = new ApiError(422, '/cases/123/observations', 'POST', pydanticDetail);
    expect(err.displayMessage()).toBe(
      'reliability_tier: Input should be a valid integer; value_type: Field required'
    );
    const map = err.getValidationErrors();
    expect(map['reliability_tier']).toBe('Input should be a valid integer');
    expect(map['value_type']).toBe('Field required');
  });

  it('detects 409 capacity conflict correctly', () => {
    const conflictPayload = {
      detail: 'No TREATMENT_SPACE resource is available.',
      resource_type: 'TREATMENT_SPACE' as const,
      candidate_actions: [
        'Expedite a discharge to free a space',
        'Use an alternative space or resource type',
        'Escalate to the on-call team',
      ],
    };
    const err = new ApiError(
      409,
      '/cases/123/assign-resource',
      'POST',
      conflictPayload.detail,
      conflictPayload
    );
    expect(err.isCapacityConflict).toBe(true);
    expect(err.capacityConflictData?.candidate_actions.length).toBe(3);
    expect(err.displayMessage()).toBe('No TREATMENT_SPACE resource is available.');
  });
});
