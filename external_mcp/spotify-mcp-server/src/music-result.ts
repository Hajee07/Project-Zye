export type MusicStatus =
  | 'VERIFIED'
  | 'ACCEPTED_UNVERIFIED'
  | 'FAILED'
  | 'UNAVAILABLE'
  | 'AUTH_REQUIRED'
  | 'UNSUPPORTED'
  | 'NO_AVAILABLE_DEVICE';

export function musicSuccess(
  operation: string,
  status: MusicStatus,
  data: Record<string, unknown> = {},
) {
  return {
    content: [
      {
        type: 'text' as const,
        text: JSON.stringify({
          status,
          operation,
          data,
        }),
      },
    ],
    isError: false,
  };
}

export function musicFailure(
  operation: string,
  code: string,
  message: string,
  data: Record<string, unknown> = {},
) {
  return {
    content: [
      {
        type: 'text' as const,
        text: JSON.stringify({
          status: 'FAILED',
          operation,
          error: {
            code,
            message,
          },
          data,
        }),
      },
    ],
    isError: true,
  };
}
