import { spotifyFetch } from './utils.js';

export interface DeviceInfo {
  id: string;
  is_active: boolean;
  name: string;
  volume_percent?: number | null;
}

export interface PlaybackStateResponse {
  is_playing?: boolean;
  progress_ms?: number;
  shuffle_state?: boolean;
  repeat_state?: string;
  device?: DeviceInfo;
  item?: {
    uri?: string;
    id?: string;
    name?: string;
    duration_ms?: number;
  };
}

export async function verifyDeviceActive(
  deviceId: string,
  timeoutMs = 2500,
): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const data = await spotifyFetch<{ devices: DeviceInfo[] }>('me/player/devices');
      const dev = data?.devices?.find((d) => d.id === deviceId);
      if (dev?.is_active) return true;
    } catch {
      // Continue polling until deadline
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  return false;
}

export async function verifyPlaybackState(
  expectedPlaying: boolean,
  timeoutMs = 2500,
): Promise<{ verified: boolean; state?: PlaybackStateResponse }> {
  const start = Date.now();
  let lastState: PlaybackStateResponse | undefined;
  while (Date.now() - start < timeoutMs) {
    try {
      const state = await spotifyFetch<PlaybackStateResponse>('me/player');
      lastState = state;
      if (state && typeof state.is_playing === 'boolean') {
        if (state.is_playing === expectedPlaying) {
          return { verified: true, state };
        }
      }
    } catch {
      // Endpoint may return 204 No Content if playback is stopped
      if (!expectedPlaying) {
        return { verified: true };
      }
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  return { verified: false, state: lastState };
}

export async function verifyVolumeState(
  expectedVolume: number,
  tolerance = 2,
  timeoutMs = 2000,
): Promise<{ verified: boolean; actualVolume?: number }> {
  const start = Date.now();
  let actualVol: number | undefined;
  while (Date.now() - start < timeoutMs) {
    try {
      const state = await spotifyFetch<PlaybackStateResponse>('me/player');
      const vol = state?.device?.volume_percent;
      if (typeof vol === 'number') {
        actualVol = vol;
        if (Math.abs(vol - expectedVolume) <= tolerance) {
          return { verified: true, actualVolume: vol };
        }
      }
    } catch {
      // Ignore transient errors
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  return { verified: false, actualVolume: actualVol };
}

export async function verifyPositionState(
  expectedPositionMs: number,
  toleranceMs = 4000,
  timeoutMs = 2000,
): Promise<{ verified: boolean; actualPositionMs?: number }> {
  const start = Date.now();
  let lastPos: number | undefined;
  while (Date.now() - start < timeoutMs) {
    try {
      const state = await spotifyFetch<PlaybackStateResponse>('me/player');
      const pos = state?.progress_ms;
      if (typeof pos === 'number') {
        lastPos = pos;
        if (Math.abs(pos - expectedPositionMs) <= toleranceMs) {
          return { verified: true, actualPositionMs: pos };
        }
      }
    } catch {
      // Ignore transient errors
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  return { verified: false, actualPositionMs: lastPos };
}

export async function verifyShuffleState(
  expectedShuffle: boolean,
  timeoutMs = 2000,
): Promise<{ verified: boolean; actualShuffle?: boolean }> {
  const start = Date.now();
  let actualShuffle: boolean | undefined;
  while (Date.now() - start < timeoutMs) {
    try {
      const state = await spotifyFetch<PlaybackStateResponse>('me/player');
      if (state && typeof state.shuffle_state === 'boolean') {
        actualShuffle = state.shuffle_state;
        if (state.shuffle_state === expectedShuffle) {
          return { verified: true, actualShuffle };
        }
      }
    } catch {
      // Ignore transient errors
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  return { verified: false, actualShuffle };
}

export async function verifyRepeatState(
  expectedRepeat: string,
  timeoutMs = 2000,
): Promise<{ verified: boolean; actualRepeat?: string }> {
  const start = Date.now();
  let actualRepeat: string | undefined;
  while (Date.now() - start < timeoutMs) {
    try {
      const state = await spotifyFetch<PlaybackStateResponse>('me/player');
      if (state?.repeat_state) {
        actualRepeat = state.repeat_state;
        if (state.repeat_state === expectedRepeat) {
          return { verified: true, actualRepeat };
        }
      }
    } catch {
      // Ignore transient errors
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  return { verified: false, actualRepeat };
}

export interface ExactPlaybackExpected {
  trackId: string;
  deviceId?: string;
}

export interface ExactPlaybackVerificationResult {
  status:
    | 'PLAYBACK_VERIFIED'
    | 'TRACK_MISMATCH'
    | 'DEVICE_MISMATCH'
    | 'TRACK_NOT_PLAYING'
    | 'PLAYBACK_STATE_UNAVAILABLE';
  verified: boolean;
  state?: PlaybackStateResponse;
}

export async function verifyExactTrackPlayback(
  expected: ExactPlaybackExpected,
  timeoutMs = 3000,
): Promise<ExactPlaybackVerificationResult> {
  const start = Date.now();
  let lastState: PlaybackStateResponse | undefined;

  while (Date.now() - start < timeoutMs) {
    try {
      const state = await spotifyFetch<PlaybackStateResponse>('me/player');
      lastState = state;

      if (state && state.item) {
        if (expected.deviceId && state.device?.id && state.device.id !== expected.deviceId) {
          return {
            status: 'DEVICE_MISMATCH',
            verified: false,
            state,
          };
        }

        const normExpected = expected.trackId.replace('spotify:track:', '');
        const trackMatches =
          state.item.id === normExpected ||
          state.item.uri === expected.trackId ||
          state.item.uri === `spotify:track:${normExpected}`;

        if (!trackMatches) {
          return {
            status: 'TRACK_MISMATCH',
            verified: false,
            state,
          };
        }

        if (state.is_playing !== true) {
          return {
            status: 'TRACK_NOT_PLAYING',
            verified: false,
            state,
          };
        }

        return {
          status: 'PLAYBACK_VERIFIED',
          verified: true,
          state,
        };
      }
    } catch {
      // transient polling error
    }
    await new Promise((r) => setTimeout(r, 250));
  }

  return {
    status: 'PLAYBACK_STATE_UNAVAILABLE',
    verified: false,
    state: lastState,
  };
}
